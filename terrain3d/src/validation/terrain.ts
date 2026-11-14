import type { MeterSpacing, ProcessingMetadata, ValidatedTerrainData } from "../types/terrain";

export class TerrainValidationError extends Error {
  constructor(message: string) {
    super(`Invalid terrain: ${message}`);
    this.name = "TerrainValidationError";
  }
}

function fail(message: string): never { throw new TerrainValidationError(message); }
function record(value: unknown, field: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${field} must be an object`);
  return value as Record<string, unknown>;
}
function text(value: unknown, field: string): string {
  if (typeof value !== "string" || !value.trim()) fail(`${field} must be a non-empty string`);
  return value;
}
function positive(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) fail(`${field} must be finite and greater than zero`);
  return value;
}
function spacing(value: unknown, field: string): MeterSpacing {
  if (typeof value === "number") return positive(value, field);
  const axes = record(value, field);
  return { x: positive(axes.x, `${field}.x`), y: positive(axes.y, `${field}.y`) };
}
export function spacingAxes(value: MeterSpacing): { x: number; y: number } {
  return typeof value === "number" ? { x: value, y: value } : value;
}
function dimension(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 2) fail(`${field} must be an integer >= 2`);
  return value;
}
function processing(value: unknown, real: boolean): ProcessingMetadata | undefined {
  if (value === undefined && !real) return undefined;
  const input = record(value, "processingMetadata (required for real data)");
  const result: ProcessingMetadata = {};
  if (input.provenance !== undefined || real) {
    const p = record(input.provenance, "processingMetadata.provenance (required for real data)");
    const url = text(p.url, "provenance.url");
    try {
      const parsed = new URL(url);
      if (!["https:", "http:"].includes(parsed.protocol)) fail("provenance.url must be an HTTP(S) product or DOI URL");
    } catch { fail("provenance.url must be an absolute HTTP(S) product or DOI URL"); }
    result.provenance = {
      dataset: text(p.dataset, "provenance.dataset"), productId: text(p.productId, "provenance.productId"),
      version: text(p.version, "provenance.version"), url,
    };
  }
  if (input.steps !== undefined) {
    if (!Array.isArray(input.steps)) fail("processingMetadata.steps must be an array of strings");
    result.steps = Array.from(input.steps, (s, i) => text(s, `processingMetadata.steps[${i}]`));
  }
  if (input.software !== undefined) result.software = text(input.software, "processingMetadata.software");
  if (input.processedAt !== undefined) {
    const date = text(input.processedAt, "processingMetadata.processedAt");
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$/.test(date) || !Number.isFinite(Date.parse(date)) ||
        new Date(date).toISOString().slice(0, 10) !== date.slice(0, 10)) fail("processingMetadata.processedAt must be a valid UTC ISO timestamp");
    result.processedAt = date;
  }
  return result;
}

/** Validate untrusted JSON and normalize legacy aliases. Throws TerrainValidationError. */
export function validateTerrainData(value: unknown): ValidatedTerrainData {
  const input = record(value, "root");
  const id = text(input.id, "id");
  const name = text(input.name, "name");
  const source = text(input.source, "source");
  const body = input.body;
  if (body !== "Earth" && body !== "Mars" && body !== "Moon") fail("body must be Earth, Mars or Moon");
  const width = dimension(input.width, "width"), height = dimension(input.height, "height");
  const count = width * height;
  if (!Number.isSafeInteger(count)) fail("width * height exceeds the safe integer range");
  const cellSizeMeters = spacing(input.cellSizeMeters, "cellSizeMeters");
  const { x, y } = spacingAxes(cellSizeMeters);
  if (input.isSynthetic !== undefined && typeof input.isSynthetic !== "boolean") fail("isSynthetic must be boolean");
  const dataType = input.dataType === undefined ? (input.isSynthetic === true ? "synthetic" : input.isSynthetic === false ? "real" : undefined) : input.dataType;
  if (dataType !== "real" && dataType !== "synthetic") fail('dataType must explicitly be "real" or "synthetic" (legacy: isSynthetic)');
  if (input.isSynthetic !== undefined && input.isSynthetic !== (dataType === "synthetic")) fail("dataType conflicts with isSynthetic");
  const legacySynthetic = input.heights === undefined && input.elevationsMeters !== undefined && dataType === "synthetic";
  const rawHeights = input.heights === undefined ? input.elevationsMeters : input.heights;
  if (!Array.isArray(rawHeights) || rawHeights.length !== count) fail(`heights must be an array of width * height (${count}) samples`);
  if (input.heights !== undefined && input.elevationsMeters !== undefined) {
    const old = input.elevationsMeters;
    if (!Array.isArray(old) || old.length !== count || rawHeights.some((h, i) => h !== old[i])) fail("heights conflicts with elevationsMeters");
  }
  let validMask: boolean[] | undefined;
  if (input.validMask !== undefined) {
    if (!Array.isArray(input.validMask) || input.validMask.length !== count) fail(`validMask must contain ${count} booleans`);
    validMask = Array.from(input.validMask, (v, i) => {
      if (typeof v !== "boolean") fail(`validMask[${i}] must be boolean`);
      return v;
    });
  }
  let validCount = 0, minElevation = Infinity, maxElevation = -Infinity;
  const heights = Array.from(rawHeights, (h, i): number | null => {
    const valid = validMask?.[i] ?? true;
    if (h === null && !valid) return null;
    if (typeof h !== "number" || !Number.isFinite(h)) fail(`heights[${i}] must be finite meters; null is allowed only with validMask[${i}] = false`);
    if (valid) {
      validCount++;
      minElevation = Math.min(minElevation, h);
      maxElevation = Math.max(maxElevation, h);
    }
    return valid ? h : null; // Masked numeric sentinels never become elevations.
  });
  if (!validCount) fail("at least one valid elevation sample is required");
  const resolutionMeters = spacing(input.resolutionMeters === undefined && legacySynthetic ? cellSizeMeters : input.resolutionMeters, "resolutionMeters");
  const verticalExaggeration = input.verticalExaggeration === undefined ? 1 : positive(input.verticalExaggeration, "verticalExaggeration");
  const expected = { width: (width - 1) * x, height: (height - 1) * y };
  positive(expected.width, "computed horizontal width");
  positive(expected.height, "computed horizontal height");
  const window = record(input.horizontalWindowMeters === undefined && legacySynthetic ? expected : input.horizontalWindowMeters, "horizontalWindowMeters");
  const horizontalWindowMeters = { width: positive(window.width, "horizontalWindowMeters.width"), height: positive(window.height, "horizontalWindowMeters.height") };
  for (const axis of ["width", "height"] as const) {
    if (Math.abs(horizontalWindowMeters[axis] - expected[axis]) > Math.max(1e-6, expected[axis] * 1e-6)) fail(`horizontalWindowMeters.${axis} must equal the sample-center span ${expected[axis]} meters`);
  }
  const scale = 10 / Math.max(expected.width, expected.height);
  // Leave headroom for area-weighted normal accumulation in float32 buffers.
  const displayHeight = (maxElevation - minElevation) * scale * verticalExaggeration;
  if (!Number.isFinite(scale) || !Number.isFinite(displayHeight) || displayHeight > 1e30) fail("elevation range / spacing / verticalExaggeration exceeds safe GPU float32 range");
  let hasTriangle = false;
  for (let row = 0; row < height - 1 && !hasTriangle; row++) {
    for (let column = 0; column < width - 1 && !hasTriangle; column++) {
      const a = row * width + column, b = a + 1, c = a + width, d = c + 1;
      hasTriangle = heights[b] !== null && heights[c] !== null && (heights[a] !== null || heights[d] !== null);
    }
  }
  if (!hasTriangle) fail("valid samples do not form any terrain triangles");
  const verticalDatum = text(input.verticalDatum === undefined && legacySynthetic ? "Synthetic local elevation reference" : input.verticalDatum, "verticalDatum");
  const coordinateReferenceSystem = text(input.coordinateReferenceSystem === undefined && legacySynthetic ? "Synthetic local metric grid" : input.coordinateReferenceSystem, "coordinateReferenceSystem");
  const processingMetadata = processing(input.processingMetadata, dataType === "real");
  return { id, name, body, width, height, heights, cellSizeMeters, source, resolutionMeters,
    verticalExaggeration, dataType, validMask, horizontalWindowMeters, verticalDatum,
    coordinateReferenceSystem, processingMetadata };
}
