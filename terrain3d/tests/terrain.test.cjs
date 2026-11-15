const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const { validateTerrainData, TerrainValidationError } = require('../.test-build/validation/terrain.js');
const { createTerrainGeometry } = require('../.test-build/geometry/terrainGeometry.js');
const { loadTerrain } = require('../.test-build/loading/loadTerrain.js');
const { validateSimilarityResult, validateCandidateMetadata, requireCandidateTerrainLink } = require('../.test-build/integration/adapters.js');
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

test('terrain UVs follow valid vertices and preserve physical texture proportions', () => {
  const geometry = createTerrainGeometry(fixture('moon'));
  const uv = geometry.getAttribute('uv');
  assert.equal(uv.count, geometry.getAttribute('position').count);
  assert.ok([...uv.array].every(v => Number.isFinite(v) && v >= 0 && v <= 1));
  assert.deepEqual([uv.getX(0), uv.getY(0)], [0, 0]);
  assert.deepEqual([uv.getX(uv.count - 1), uv.getY(uv.count - 1)], [1, 1]);
  geometry.dispose();
  const earth = validateTerrainData(fixture('earth'));
  const rectangle = createTerrainGeometry(earth);
  const texture = rectangle.getAttribute('uv');
  const last = texture.count - 1;
  assert.ok(Math.abs(texture.getX(last) / texture.getY(last) - earth.horizontalWindowMeters.width / earth.horizontalWindowMeters.height) < 1e-6);
  rectangle.dispose();
});

const { surfaceElevation, findSurfaceSpawn } = require('../.test-build/geometry/surfaceNavigation.js');
test('POV ground sampling follows both rendered triangles rather than bilinear interpolation', () => {
  const terrain = validateTerrainData({ ...base(), width: 2, height: 2, heights: [0, 10, 20, 100],
    cellSizeMeters: 10, horizontalWindowMeters: { width: 10, height: 10 } });
  assert.equal(surfaceElevation(terrain, 0.25, 0.25), 7.5);
  assert.equal(surfaceElevation(terrain, 0.75, 0.75), 57.5);
  assert.equal(surfaceElevation(terrain, 1, 1), 100);
  for (const uv of [[-0.01, 0.5], [0.5, 1.01], [NaN, 0]]) assert.equal(surfaceElevation(terrain, ...uv), null);
});
test('POV spawn lands on a valid triangle and movement sampling rejects NoData', () => {
  const terrain = validateTerrainData(fixture('moon'));
  assert.equal(surfaceElevation(terrain, 1 / 3, 1 / 3), null);
  const spawn = findSurfaceSpawn(terrain);
  assert.equal(typeof surfaceElevation(terrain, spawn.u, spawn.v), 'number');
  const sparse = validateTerrainData({ ...base(), width: 2, height: 2, heights: [null, 10, 20, 100], validMask: [false, true, true, true],
    cellSizeMeters: 10, horizontalWindowMeters: { width: 10, height: 10 } });
  const safe = findSurfaceSpawn(sparse);
  assert.ok(safe.u + safe.v > 1);
  assert.equal(typeof surfaceElevation(sparse, safe.u, safe.v), 'number');
  assert.equal(surfaceElevation(sparse, 0.2, 0.2), null);
});

const { explorationWorld, createContextGeometry } = require('../.test-build/geometry/explorationWorld.js');
test('exploration context preserves source heights and NoData, and is deterministic outside the parcel', () => {
  const terrain = validateTerrainData(fixture('moon'));
  const world = explorationWorld(terrain, 2);
  const valid = terrain.heights.filter(h => h !== null), min = Math.min(...valid);
  for (const [u, v] of [[0, 0], [0.8, 0.8], [1 / 3, 1 / 3]]) {
    const original = surfaceElevation(terrain, u, v);
    assert.equal(world.at(u, v), original === null ? null : (original - min) * world.scale * 2);
  }
  assert.equal(world.at(-2.01, 0), null);
  assert.equal(world.at(3.01, 0), null);
  assert.equal(world.at(NaN, 0), null);
  assert.equal(world.at(-0.7, 1.2), explorationWorld(terrain, 2).at(-0.7, 1.2));
  assert.ok(Number.isFinite(world.at(-0.7, 1.2)));
  const geometry = createContextGeometry(world);
  assert.equal(geometry.index.count, 24 * 40 * 40 * 6);
  const position = geometry.getAttribute('position');
  for (let i = 0; i < geometry.index.count; i += 3) {
    const ids = [0, 1, 2].map(j => geometry.index.getX(i + j));
    const x = ids.reduce((total, id) => total + position.getX(id), 0) / 3;
    const z = ids.reduce((total, id) => total + position.getZ(id), 0) / 3;
    assert.ok(Math.abs(x) >= world.width / 2 - 1e-5 || Math.abs(z) >= world.depth / 2 - 1e-5, 'context must never cover the source parcel');
  }
  for (const name of ['position', 'normal', 'uv']) assert.ok([...geometry.getAttribute(name).array].every(Number.isFinite));
  geometry.dispose();
});

test('overview context shares comparison scale and elevation offset with the selected DEM', () => {
  const terrain = validateTerrainData(fixture('earth'));
  const native = explorationWorld(terrain, 2);
  const span = Math.max(terrain.horizontalWindowMeters.width, terrain.horizontalWindowMeters.height);
  const overview = explorationWorld(terrain, 2, { worldSpanMeters: span * 2, elevationOffset: -100 });
  assert.equal(overview.width, native.width / 2);
  assert.equal(overview.depth, native.depth / 2);
  const offset = -100 * overview.scale * 2;
  assert.equal(overview.at(0.5, 0.5), native.at(0.5, 0.5) / 2 + offset);
  const edge = overview.at(1, 0.5), adjacent = overview.at(1 + 1e-9, 0.5);
  assert.ok(Math.abs(edge - adjacent) < 1e-6, 'generated context must meet the displayed source boundary');
});

const { Vector3 } = require('three');
const { renderedWorldHeight, keepOverviewAboveGround } = require('../.test-build/geometry/overviewCollision.js');
test('overview camera guard clears source ridges, respects relative heights and samples context triangles', () => {
  const terrain = validateTerrainData(fixture('earth'));
  const world = explorationWorld(terrain, 5, { elevationOffset: -123 });
  for (const [u, v] of [[0.4, 0.7], [-0.4, 1.3], [2.99, -1.2]]) {
    const floor = renderedWorldHeight(world, u, v);
    assert.equal(typeof floor, 'number');
    const p = new Vector3((u - 0.5) * world.width, floor - 5, (v - 0.5) * world.depth);
    keepOverviewAboveGround(p, world, 0.2);
    assert.ok(Math.abs(p.y - (floor + 0.2)) < 1e-9);
    assert.equal(p.x, (u - 0.5) * world.width);
    p.y += 100; const high = p.y;
    keepOverviewAboveGround(p, world, 0.2); assert.equal(p.y, high);
  }
  assert.equal(renderedWorldHeight(world, 0.4, 0.7), world.at(0.4, 0.7));
  assert.equal(renderedWorldHeight(world, -3, 0), null);
});

const { SURFACE_GRAVITY, CHARACTER_SCALE, JUMP_SPEED, groundedJump, launchJump, stepJump } = require('../.test-build/geometry/jumpPhysics.js');
test('same jump impulse produces progressively higher, longer jumps on Earth, Mars and Moon', () => {
  const flights = [];
  for (const body of ['Earth', 'Mars', 'Moon']) {
    const gravity = SURFACE_GRAVITY[body] * CHARACTER_SCALE;
    let state = launchJump(groundedJump(3)), peak = 0, time = 0;
    const dt = 1 / 120;
    while (!state.grounded && time < 10) {
      state = stepJump(state, body, dt, 3); time += dt;
      peak = Math.max(peak, state.y - 3);
      assert.ok(state.y >= 3);
    }
    assert.equal(state.grounded, true);
    assert.equal(state.velocity, 0);
    assert.equal(state.y, 3);
    assert.ok(Math.abs(peak - JUMP_SPEED ** 2 / (2 * gravity)) < 0.001);
    assert.ok(Math.abs(time - 2 * JUMP_SPEED / gravity) < dt + 1e-8);
    flights.push({ peak, time });
  }
  assert.ok(flights[0].peak < flights[1].peak && flights[1].peak < flights[2].peak);
  assert.ok(flights[0].time < flights[1].time && flights[1].time < flights[2].time);
});
test('jump integration is independent of frame rate, cannot double-jump, and lands on changing terrain', () => {
  for (const body of ['Earth', 'Mars', 'Moon']) {
    const initial = launchJump(groundedJump(10));
    assert.strictEqual(launchJump(initial), initial);
    let fine = initial, coarse = initial;
    for (let i = 0; i < 30; i++) fine = stepJump(fine, body, 0.01, 10);
    for (let i = 0; i < 3; i++) coarse = stepJump(coarse, body, 0.1, 10);
    assert.ok(Math.abs(fine.y - coarse.y) < 1e-10);
    assert.ok(Math.abs(fine.velocity - coarse.velocity) < 1e-10);
    assert.strictEqual(stepJump(initial, body, 0, 10), initial);
    assert.deepEqual(stepJump(fine, body, 0.1, fine.y + 1), groundedJump(fine.y + 1));
    assert.equal(stepJump(fine, body, 0.1, 8).grounded, false);
  }
});
const { moveWithinParcel, parcelSegmentIsValid } = require('../.test-build/geometry/surfaceNavigation.js');
test('walking and airborne horizontal movement cannot leave any side or corner of the selected parcel', () => {
  const earth = validateTerrainData(fixture('earth'));
  const from = { u: 0.5, v: 0.5 };
  for (const du of [-3, 0, 3]) for (const dv of [-3, 0, 3]) {
    const next = moveWithinParcel(earth, from, du, dv, { u: 0.01, v: 0.02 });
    assert.ok(next && next.u >= 0.01 && next.u <= 0.99 && next.v >= 0.02 && next.v <= 0.98);
    assert.equal(typeof surfaceElevation(earth, next.u, next.v), 'number');
  }
});
test('parcel movement rejects NoData crossed between valid endpoints and allows safe nearby routes', () => {
  const moon = validateTerrainData(fixture('moon'));
  const from = { u: 0.02, v: 0.02 }, to = { u: 0.98, v: 0.98 };
  assert.notEqual(surfaceElevation(moon, from.u, from.v), null);
  assert.notEqual(surfaceElevation(moon, to.u, to.v), null);
  assert.equal(parcelSegmentIsValid(moon, from, to), false);
  assert.equal(moveWithinParcel(moon, from, to.u - from.u, to.v - from.v), null);
  assert.equal(parcelSegmentIsValid(moon, { u: 0.1, v: 0.9 }, { u: 0.9, v: 0.9 }), true);
});

const { createNoDataGeometry } = require('../.test-build/geometry/noDataGeometry.js');
test('NoData hatching covers exactly the omitted triangles without changing measured terrain', () => {
  for (const name of ['moon', 'earth']) {
    const terrain = validateTerrainData(fixture(name));
    const before = JSON.stringify(terrain);
    const source = createTerrainGeometry(terrain);
    const mask = createNoDataGeometry(terrain);
    const totalFaces = 2 * (terrain.width - 1) * (terrain.height - 1);
    if (!mask) {
      assert.equal(source.index.count / 3, totalFaces);
    } else {
      assert.equal((source.index.count + mask.index.count) / 3, totalFaces);
      const footprint = geometry => {
        const p = geometry.getAttribute('position'), result = new Set();
        for (let i = 0; i < geometry.index.count; i += 3) {
          const corners = [0, 1, 2].map(j => {
            const vertex = geometry.index.getX(i + j);
            return `${p.getX(vertex).toFixed(5)},${p.getZ(vertex).toFixed(5)}`;
          }).sort();
          result.add(corners.join('|'));
        }
        return result;
      };
      const validFaces = footprint(source), missingFaces = footprint(mask);
      assert.equal([...missingFaces].filter(face => validFaces.has(face)).length, 0);
      assert.equal(validFaces.size + missingFaces.size, totalFaces);
      assert.ok([...mask.getAttribute('position').array].every(Number.isFinite));
      assert.equal(surfaceElevation(terrain, 1 / 3, 1 / 3), null, 'diagnostic overlay must not create walkable/inspectable elevations');
      mask.dispose();
    }
    assert.equal(JSON.stringify(terrain), before);
    source.dispose();
  }
});
test('NoData reference plane follows shared scale and datum offset, not missing sample values', () => {
  const terrain = validateTerrainData(fixture('moon'));
  const span = Math.max(terrain.horizontalWindowMeters.width, terrain.horizontalWindowMeters.height);
  const geometry = createNoDataGeometry(terrain, { worldSpanMeters: span * 2, elevationOffset: -25, verticalExaggeration: 2 });
  const positions = geometry.getAttribute('position');
  const y = -25 * 10 / (span * 2) * 2 - 0.005;
  for (let i = 0; i < positions.count; i++) {
    assert.ok(Math.abs(positions.getY(i) - y) < 1e-6);
    assert.ok(Math.abs(positions.getX(i)) <= 2.5);
    assert.ok(Math.abs(positions.getZ(i)) <= 2.5);
  }
  geometry.dispose();
});

const { interpolateTerrainForDisplay, createVisualFillGeometry } = require('../.test-build/geometry/visualInterpolation.js');
test('visual interpolation fills all gaps without altering observations, source mask or provenance', () => {
  const terrain = validateTerrainData(fixture('moon'));
  const original = JSON.stringify(terrain);
  const display = interpolateTerrainForDisplay(terrain);
  assert.equal(display.missingCount, terrain.heights.filter(h => h === null).length);
  assert.equal(display.terrain.dataType, 'synthetic');
  assert.match(display.terrain.source, /Visualization-only/);
  const valid = terrain.heights.filter(h => h !== null), low = Math.min(...valid), high = Math.max(...valid);
  display.terrain.heights.forEach((h, i) => {
    assert.ok(Number.isFinite(h) && h >= low && h <= high);
    assert.equal(display.estimatedMask[i], terrain.heights[i] === null);
    if (terrain.heights[i] !== null) assert.equal(h, terrain.heights[i]);
  });
  assert.equal(JSON.stringify(terrain), original);
  assert.equal(surfaceElevation(terrain, 1 / 3, 1 / 3), null, 'raw NoData stays uninspectable and unwalkable');
  assert.strictEqual(interpolateTerrainForDisplay(terrain), display);
});
test('visual interpolation uses physical X/Y spacing and handles negative or zero elevations', () => {
  const terrain = validateTerrainData({ ...base(), width: 3, height: 3,
    heights: [0, 0, 0, 10, null, 20, 100, 100, 100], validMask: [true,true,true,true,false,true,true,true,true],
    cellSizeMeters: { x: 100, y: 200 }, horizontalWindowMeters: { width: 200, height: 400 } });
  assert.ok(Math.abs(interpolateTerrainForDisplay(terrain).terrain.heights[4] - 22) < 1e-8);
  for (const level of [-50, 0, 50]) {
    const constant = validateTerrainData({ ...terrain, heights: [level,level,level,level,null,null,null,null,null], validMask: [true,true,true,true,false,false,false,false,false] });
    assert.deepEqual(interpolateTerrainForDisplay(constant).terrain.heights, Array(9).fill(level));
  }
  const noGaps = validateTerrainData(fixture('earth'));
  assert.deepEqual(interpolateTerrainForDisplay(noGaps).terrain.heights, noGaps.heights);
  assert.equal(interpolateTerrainForDisplay(noGaps).terrain.source, noGaps.source);
});
test('filled geometry is continuous with per-sample estimate tags and unchanged raw gap geometry', () => {
  const terrain = validateTerrainData(fixture('moon'));
  const raw = createTerrainGeometry(terrain), filled = createVisualFillGeometry(terrain);
  assert.equal(filled.index.count, 6 * (terrain.width - 1) * (terrain.height - 1));
  assert.ok(filled.index.count > raw.index.count);
  const tag = filled.getAttribute('visualEstimate');
  assert.equal(tag.count, terrain.width * terrain.height);
  for (let i = 0; i < tag.count; i++) assert.equal(tag.getX(i), terrain.heights[i] === null ? 1 : 0);
  for (const name of ['position','normal','color','uv','visualEstimate']) assert.ok([...filled.getAttribute(name).array].every(Number.isFinite));
  assert.equal(createTerrainGeometry(terrain).index.count, raw.index.count);
  raw.dispose(); filled.dispose();
});

const { vehicleGround, findRoverSpawn, findLandingSite, LANDER_RADIUS } = require('../.test-build/geometry/explorerVehicles.js');
const { stepLander } = require('../.test-build/geometry/manualLanding.js');
function vehicleFixture() {
  return validateTerrainData({ ...base(), width: 11, height: 11, heights: Array(121).fill(0), validMask: Array(121).fill(true),
    cellSizeMeters: { x: 100, y: 100 }, horizontalWindowMeters: { width: 1000, height: 1000 }, resolutionMeters: 100 });
}
const vehicleWorld = { width: 10, depth: 10, at: (u, v) => u >= 0 && u <= 1 && v >= 0 && v <= 1 ? 0 : null };
test('vehicles require a measured footprint and landing search never accepts generated scenery or NoData', () => {
  const terrain = vehicleFixture();
  assert.ok(vehicleGround(terrain, vehicleWorld, { u: .5, v: .5 }).measured);
  assert.equal(vehicleGround(terrain, vehicleWorld, { u: .01, v: .5 }).measured, false);
  const hole = structuredClone(terrain); hole.heights[5*11+7] = null; hole.validMask[5*11+7] = false;
  assert.notEqual(surfaceElevation(hole, .5, .5), null);
  assert.equal(vehicleGround(hole, vehicleWorld, { u: .5, v: .5 }, 1.2).measured, false);
  const dense = validateTerrainData({ ...terrain, width: 41, height: 41, cellSizeMeters: 25, resolutionMeters: 25,
    heights: Array(1681).fill(0), validMask: Array(1681).fill(true) });
  dense.heights[18*41+18] = null; dense.validMask[18*41+18] = false;
  for (const u of [.395,.5,.605]) for (const v of [.395,.5,.605]) assert.notEqual(surfaceElevation(dense,u,v),null);
  assert.equal(vehicleGround(dense,vehicleWorld,{u:.5,v:.5},1.05).measured,false,'detect NoData between the nine footprint probes');
  const site = findLandingSite(terrain, vehicleWorld, { u: .5, v: .68 }, 0);
  assert.ok(site && site.u > 0 && site.u < 1 && site.v > 0 && site.v < 1);
  assert.ok(Math.abs(site.x) <= vehicleWorld.width / 2 - LANDER_RADIUS && Math.abs(site.z) <= vehicleWorld.depth / 2 - LANDER_RADIUS);
  assert.ok(vehicleGround(terrain, vehicleWorld, site, .52).measured);
  const empty = { ...terrain, heights: Array(121).fill(null), validMask: Array(121).fill(false) };
  assert.equal(findRoverSpawn(empty, vehicleWorld, { u: .5, v: .5 }, .01), null);
  assert.equal(findLandingSite(empty, vehicleWorld, { u: .5, v: .5 }, 0), null);
});
const flightInput = { forward: 0, strafe: 0, yaw: 0, thrust: false, brake: false };
const flightStart = { x: 0, y: 6.3, z: 0, vx: 0, vy: 0, vz: 0, fuel: 100, phase: 'ready', reason: '', boundaryBlocked: false };
const flightFloor = () => ({ height: 0, measured: true, spread: 0 });
const flightBounds = { width: 10, depth: 10, radius: .5 }, flightTarget = { x: 0, z: 0 };
test('manual landing waits for input; gravity, thrust, fuel and braking respond to pilot controls', () => {
  assert.equal(stepLander(flightStart, flightInput, 'Earth', .1, flightFloor, flightBounds, flightTarget), flightStart);
  const falling = { ...flightStart, phase: 'flying' };
  const earth = stepLander(falling, flightInput, 'Earth', .1, flightFloor, flightBounds, flightTarget);
  const moon = stepLander(falling, flightInput, 'Moon', .1, flightFloor, flightBounds, flightTarget);
  assert.ok(earth.vy < moon.vy && earth.y < moon.y);
  const powered = stepLander(falling, { ...flightInput, thrust: true }, 'Earth', .1, flightFloor, flightBounds, flightTarget);
  assert.ok(powered.vy > 0 && powered.fuel < 100);
  const empty = stepLander({ ...falling, fuel: 0 }, { ...flightInput, thrust: true }, 'Earth', .1, flightFloor, flightBounds, flightTarget);
  assert.equal(empty.vy, earth.vy);
  const braking = stepLander({ ...falling, vx: .5 }, { ...flightInput, brake: true }, 'Moon', .1, flightFloor, flightBounds, flightTarget);
  const coasting = stepLander({ ...falling, vx: .5 }, flightInput, 'Moon', .1, flightFloor, flightBounds, flightTarget);
  assert.ok(braking.vx < coasting.vx);
});
test('manual landing distinguishes a safe touchdown, hard impact, unknown ground, and a missed zone', () => {
  const touchdown = { ...flightStart, phase: 'flying', y: .015, vy: -.1 };
  const safe = stepLander(touchdown, flightInput, 'Moon', .1, flightFloor, flightBounds, flightTarget);
  assert.equal(safe.phase, 'landed'); assert.ok(safe.y >= 0);
  assert.equal(safe.vy, 0); assert.equal(safe.vx, 0); assert.equal(safe.vz, 0);
  assert.equal(stepLander(safe, { ...flightInput, thrust: true }, 'Moon', .1, flightFloor, flightBounds, flightTarget), safe);
  const hard = stepLander({ ...touchdown, vy: -1 }, flightInput, 'Earth', .1, flightFloor, flightBounds, flightTarget);
  assert.equal(hard.phase, 'crashed'); assert.match(hard.reason, /Descent too fast/);
  const unknown = stepLander(touchdown, flightInput, 'Moon', .1, () => ({ ...flightFloor(), measured: false }), flightBounds, flightTarget);
  assert.equal(unknown.phase, 'crashed'); assert.match(unknown.reason, /No measured/);
  const missed = stepLander({ ...touchdown, x: 2 }, flightInput, 'Moon', .1, flightFloor, flightBounds, flightTarget);
  assert.equal(missed.phase, 'crashed'); assert.match(missed.reason, /Outside/);
});
test('a piloted lander stays within the selected parcel and cannot tunnel below its surface', () => {
  let state = { ...flightStart, phase: 'flying' };
  const bounds = { width: 2, depth: 2, radius: .5 };
  for (let i = 0; i < 600; i++) {
    state = stepLander(state, { ...flightInput, strafe: 1, thrust: true }, 'Moon', 1/60, flightFloor, bounds, flightTarget);
    assert.ok(state.x <= .5 && state.x >= -.5 && state.z <= .5 && state.z >= -.5 && state.y >= 0);
  }
  assert.ok(state.boundaryBlocked);
});
