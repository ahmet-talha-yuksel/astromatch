const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const { validateTerrainData, TerrainValidationError } = require('../.test-build/validation/terrain.js');
const { createTerrainGeometry } = require('../.test-build/geometry/terrainGeometry.js');
const { loadTerrain } = require('../.test-build/loading/loadTerrain.js');
const { validateSimilarityResult, validateCandidateMetadata, requireCandidateTerrainLink } = require('../.test-build/integration/adapters.js');
const { validateRealEngineSnapshot } = require('../.test-build/integration/realSimilarity.js');
const fixture = name => JSON.parse(readFileSync(path.join(__dirname, '../public/terrain', `${name}_demo.json`), 'utf8'));
const base = () => fixture('mars');
function rejectsPatch(patch, field) {
  assert.throws(() => validateTerrainData({ ...base(), ...patch }), error => error instanceof TerrainValidationError && error.message.includes(field));
}

test('all three synthetic JSON fixtures validate and produce finite geometry', () => {
  for (const body of ['mars', 'moon', 'earth']) {
    const terrain = validateTerrainData(fixture(body));
    assert.equal(terrain.dataType, 'synthetic');
    const geometry = createTerrainGeometry(terrain);
    assert.ok(geometry.index.count > 0);
    for (const attribute of ['position', 'normal', 'color']) assert.ok([...geometry.getAttribute(attribute).array].every(Number.isFinite));
    geometry.dispose();
  }
});
test('real terrain requires complete traceable provenance', () => {
  const real = { ...base(), dataType: 'real', source: 'Test provenance only; not a measured fixture',
    verticalDatum: 'Test reference', coordinateReferenceSystem: 'Test projected metric CRS',
    processingMetadata: { provenance: { dataset: 'Test dataset', productId: 'test-product', version: '1', url: 'https://example.org/products/test-product' },
      steps: ['Test crop'], processedAt: '2026-11-14T10:00:00Z', software: 'test' } };
  assert.equal(validateTerrainData(real).processingMetadata.provenance.productId, 'test-product');
  assert.throws(() => validateTerrainData({ ...real, processingMetadata: undefined }), /processingMetadata/);
  for (const key of ['dataset', 'productId', 'version', 'url']) {
    const changed = structuredClone(real);
    delete changed.processingMetadata.provenance[key];
    assert.throws(() => validateTerrainData(changed), new RegExp(key));
  }
  const changed = structuredClone(real);
  changed.processingMetadata.provenance.url = 'file:///local.tif';
  assert.throws(() => validateTerrainData(changed), /HTTP\(S\)/);
});
test('missing required fields and malformed root values are rejected', () => {
  for (const field of ['id','name','body','width','height','heights','cellSizeMeters','source','resolutionMeters','dataType','horizontalWindowMeters','verticalDatum','coordinateReferenceSystem']) {
    const value = base(); delete value[field];
    assert.throws(() => validateTerrainData(value), TerrainValidationError, field);
  }
  for (const value of [null, [], 3, 'json', {}]) assert.throws(() => validateTerrainData(value), TerrainValidationError);
});
test('unsupported bodies, empty strings, and inconsistent labels are rejected', () => {
  rejectsPatch({ body: 'Venus' }, 'body');
  rejectsPatch({ source: ' ' }, 'source');
  rejectsPatch({ dataType: 'simulation' }, 'dataType');
  rejectsPatch({ dataType: null }, 'dataType');
  rejectsPatch({ isSynthetic: false }, 'conflicts');
  rejectsPatch({ isSynthetic: 'true' }, 'isSynthetic');
});
test('height array must contain exactly width * height samples', () => {
  for (const heights of [[], [1], null, 'samples', new Array(16)]) rejectsPatch({ heights }, 'heights');
});
test('dimensions must be safe integers >= 2', () => {
  for (const dimension of ['width', 'height']) for (const value of [0, -1, 1, 2.5, NaN, Infinity, '4', Number.MAX_SAFE_INTEGER + 1]) rejectsPatch({ [dimension]: value }, dimension);
  rejectsPatch({ width: Number.MAX_SAFE_INTEGER, height: 2 }, 'safe integer');
});
test('physical spacing and original DEM resolution must be positive in both axes', () => {
  for (const field of ['cellSizeMeters','resolutionMeters']) {
    for (const value of [0,-1,NaN,Infinity,null,'100',{ x: 100 },{ x: 100, y: 0 },{ x: 100, y: -1 }]) rejectsPatch({ [field]: value }, field);
  }
});
test('NaN and Infinity never pass, including masked numeric sentinels', () => {
  for (const value of [NaN, Infinity, -Infinity]) {
    const terrain = base(); terrain.heights[5] = value;
    assert.throws(() => validateTerrainData(terrain), /heights\[5\]/);
    terrain.validMask = Array(16).fill(true); terrain.validMask[5] = false;
    assert.throws(() => validateTerrainData(terrain), /heights\[5\]/);
  }
});
test('validity masks require one boolean per sample and null requires a false mask', () => {
  rejectsPatch({ validMask: [true] }, 'validMask');
  rejectsPatch({ validMask: Array(16).fill(1) }, 'boolean');
  rejectsPatch({ validMask: new Array(16) }, 'boolean');
  const t = base(); t.heights[5] = null;
  assert.throws(() => validateTerrainData(t), /validMask\[5\]/);
  rejectsPatch({ validMask: Array(16).fill(false) }, 'at least one');
  const mask = Array(16).fill(false); mask[0] = true;
  rejectsPatch({ validMask: mask }, 'triangles');
});
test('masked central sample leaves a hole, preserves adjacent valid triangles, and never creates a pit', () => {
  const terrain = base();
  terrain.heights = [10,20,30,40,50,60,70,80,90];
  terrain.width = terrain.height = 3;
  terrain.horizontalWindowMeters = { width: 200, height: 200 };
  terrain.validMask = [true,true,true,true,false,true,true,true,true];
  terrain.heights[4] = -9999;
  const normalized = validateTerrainData(terrain);
  assert.equal(normalized.heights[4], null);
  const geometry = createTerrainGeometry(terrain);
  assert.equal(geometry.getAttribute('position').count, 8);
  assert.equal(geometry.index.count, 6); // two independent triangles survive the central hole
  assert.deepEqual([...geometry.index.array], [0,3,1,4,6,7]);
  for (let i = 0; i < 8; i++) {
    const positions = geometry.getAttribute('position');
    assert.ok(positions.getX(i) !== 0 || positions.getZ(i) !== 0);
    assert.ok(positions.getY(i) >= 0 && positions.getY(i) <= 4);
  }
  geometry.dispose();
});
test('rectangular spacing preserves physical aspect ratio and independent exaggeration', () => {
  const t = fixture('earth');
  const geometry = createTerrainGeometry(t);
  geometry.computeBoundingBox();
  assert.ok(Math.abs(geometry.boundingBox.max.z - geometry.boundingBox.min.z - 10) < 1e-5);
  assert.ok(Math.abs(geometry.boundingBox.max.x - geometry.boundingBox.min.x - 10 * 300 / 450) < 1e-5);
  const exaggerated = createTerrainGeometry({ ...t, verticalExaggeration: 3 });
  const a = geometry.getAttribute('position'), b = exaggerated.getAttribute('position');
  for (let i = 0; i < a.count; i++) {
    assert.equal(a.getX(i), b.getX(i)); assert.equal(a.getZ(i), b.getZ(i));
    assert.ok(Math.abs(b.getY(i) - 3 * a.getY(i)) < 1e-5);
  }
  geometry.dispose(); exaggerated.dispose();
});
test('vertical exaggeration defaults to 1 and rejects invalid values', () => {
  const t = base(); delete t.verticalExaggeration;
  assert.equal(validateTerrainData(t).verticalExaggeration, 1);
  for (const value of [0,-1,NaN,Infinity,'2',null]) rejectsPatch({ verticalExaggeration: value }, 'verticalExaggeration');
});
test('physical windows use sample centers and reject inconsistent, missing or overflowing spans', () => {
  for (const window of [{width:400,height:400},{width:300,height:0},{width:300},null]) rejectsPatch({horizontalWindowMeters:window}, 'horizontalWindowMeters');
  rejectsPatch({ cellSizeMeters: Number.MAX_VALUE }, 'computed horizontal');
  const t = base(); t.heights[0] = Number.MAX_VALUE;
  assert.throws(() => validateTerrainData(t), /float32/);
});
test('legacy synthetic objects remain usable, without guessing real scientific metadata', () => {
  const old = { id:'old',name:'Old synthetic',body:'Mars',width:2,height:2,elevationsMeters:[0,1,2,3],cellSizeMeters:100,source:'Generated',isSynthetic:true };
  assert.deepEqual(validateTerrainData(old).horizontalWindowMeters, {width:100,height:100});
  assert.deepEqual(validateTerrainData(old).heights, old.elevationsMeters);
  assert.throws(() => validateTerrainData({...old,isSynthetic:undefined}), /dataType/);
  assert.throws(() => validateTerrainData({...old,isSynthetic:false}), /resolutionMeters/);
  rejectsPatch({ elevationsMeters: Array(16).fill(0) }, 'conflicts');
});
test('malformed processing details are rejected', () => {
  for (const metadata of [[],null,{steps:'crop'},{steps:[null]},{software:0},{processedAt:'yesterday'},{processedAt:'2026-02-30T10:00:00Z'}]) rejectsPatch({processingMetadata:metadata}, 'processingMetadata');
});
test('JSON loader validates success, handles HTTP/parse/network failures, and forwards aborts', async t => {
  t.mock.method(globalThis, 'fetch');
  fetch.mock.mockImplementation(async () => new Response(JSON.stringify(base())));
  assert.equal((await loadTerrain('/terrain/mars_demo.json')).body, 'Mars');
  fetch.mock.mockImplementation(async () => new Response('missing', {status:404,statusText:'Not Found'}));
  await assert.rejects(loadTerrain('/missing.json'), /HTTP 404 Not Found/);
  fetch.mock.mockImplementation(async () => new Response('{bad json'));
  await assert.rejects(loadTerrain('/bad.json'), /not valid JSON/);
  fetch.mock.mockImplementation(async () => new Response('{}'));
  await assert.rejects(loadTerrain('/invalid.json'), /Invalid terrain: id/);
  fetch.mock.mockImplementation(async () => { throw new TypeError('Network unavailable'); });
  await assert.rejects(loadTerrain('/offline.json'), /Network unavailable/);
  const controller = new AbortController(); controller.abort();
  fetch.mock.mockImplementation(async (_url, options) => { assert.equal(options.signal,controller.signal); options.signal.throwIfAborted(); });
  await assert.rejects(loadTerrain('/aborted.json',controller.signal), {name:'AbortError'});
  await assert.rejects(loadTerrain(' '), /non-empty/);
});

test('integration adapters preserve valid similarity and candidate IDs without calculating scores', () => {
  const result = validateSimilarityResult({ target_id: 'mars_jezero', candidate_id: 'salda', total_similarity: 0.985, criterion_similarity: { slope_deg: 0.98 }, source: { label: 'synthetic test fixture' } });
  assert.equal(result.target_id, 'mars_jezero');
  assert.equal(result.candidate_id, 'salda');
  assert.equal(result.total_similarity, 0.985);
  const candidate = validateCandidateMetadata({ id: 'salda', lat: 37.55, lon: 29.68 });
  assert.equal(candidate.id, 'salda');
});

test('integration adapters reject malformed scores and unresolved candidate terrain links', () => {
  for (const score of [-0.1, 1.1, NaN, Infinity, '0.9']) assert.throws(() => validateSimilarityResult({ target_id: 't', candidate_id: 'c', total_similarity: score }), /total_similarity/);
  assert.throws(() => validateSimilarityResult({ target_id: 't', candidate_id: 'c', total_similarity: 0.5, criterion_similarity: { slope: 2 } }), /criterion_similarity/);
  assert.throws(() => validateCandidateMetadata({ id: '', lat: 1, lon: 2 }), /candidate: id/);
  assert.throws(() => requireCandidateTerrainLink({ id: 'salda' }, ['earth-salda']), /no terrain link/);
  assert.throws(() => requireCandidateTerrainLink({ id: 'salda', terrainId: 'missing' }, ['earth-salda']), /unavailable terrain/);
  assert.equal(requireCandidateTerrainLink({ id: 'salda', terrain_id: 'earth-salda' }, ['earth-salda']), 'earth-salda');
});

test('integration adapters do not fabricate absent producer outputs', () => {
  for (const absent of [undefined, null, {}, { id: 'ahmetson-candidate' }]) {
    assert.throws(() => validateSimilarityResult(absent), TerrainValidationError);
    assert.throws(() => requireCandidateTerrainLink(absent, []), TerrainValidationError);
  }
  assert.throws(() => validateCandidateMetadata(undefined), TerrainValidationError);
  assert.throws(() => requireCandidateTerrainLink({ id: 'david-result', terrainId: '' }, ['terrain-1']), /no terrain link/);
  assert.throws(() => requireCandidateTerrainLink({ id: 'yenge-candidate', terrain_id: 'unpublished' }, []), /unavailable terrain/);
});

test('real Shackleton engine snapshot is accepted and mock or mismatched results are rejected', () => {
  const snapshot = JSON.parse(readFileSync(path.join(__dirname, '../public/similarity/shackleton_local_balanced.json'), 'utf8'));
  const result = validateRealEngineSnapshot(snapshot);
  assert.equal(result.targetId, 'moon_shackleton_local');
  assert.equal(result.candidateId, 'earth_kula_local');
  assert.equal(result.rank, 3);
  assert.equal(result.candidateCount, 8);
  assert.equal(result.sigmaSource, 'fixed_default');
  assert.equal(Object.keys(result.contributions).length, 6);
  assert.throws(() => validateRealEngineSnapshot({...snapshot, engine_result: {...snapshot.engine_result, data_status: 'mock'}}), /real result/);
  assert.throws(() => validateRealEngineSnapshot(snapshot, 'mars_jezero_local'), /target mismatch/);
  const incomplete = structuredClone(snapshot); delete incomplete.integration_metadata.target;
  assert.throws(() => validateRealEngineSnapshot(incomplete), /target/);
});
