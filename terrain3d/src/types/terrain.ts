/** Scalar values mean equal X/Y spacing; objects preserve rectangular samples. */
export type MeterSpacing = number | { x: number; y: number };
export type CelestialBody = "Earth" | "Mars" | "Moon";

export interface ProcessingMetadata {
  /** Required for real data. Use the original product's stable HTTP(S) URL. */
  provenance?: { dataset: string; productId: string; version: string; url: string };
  steps?: string[];
  processedAt?: string;
  software?: string;
}

/** JSON delivery contract. Elevations and all physical distances are in meters. */
export interface TerrainDataJSON {
  id: string;
  name: string;
  body: CelestialBody;
  width: number;
  height: number;
  /** Row-major: index = row * width + column. Null requires validMask[index] = false. */
  heights: (number | null)[];
  cellSizeMeters: MeterSpacing;
  source: string;
  /** Original DEM resolution, independent of output sample spacing. */
  resolutionMeters: MeterSpacing;
  /** Display-only multiplier, default 1. Does not change horizontal spacing. */
  verticalExaggeration?: number;
  dataType: "real" | "synthetic";
  validMask?: boolean[];
  /** Sample-center span: (width - 1) * spacing.x, (height - 1) * spacing.y. */
  horizontalWindowMeters: { width: number; height: number };
  verticalDatum: string;
  /** Explicit CRS identifier or WKT; the viewer does not reproject coordinates. */
  coordinateReferenceSystem: string;
  processingMetadata?: ProcessingMetadata;
}

/** @deprecated Deliver TerrainDataJSON for new integrations. Runtime validation is still required. */
export interface LegacyTerrainData {
  id: string;
  name: string;
  body: CelestialBody;
  width: number;
  height: number;
  cellSizeMeters: MeterSpacing;
  elevationsMeters: number[];
  source: string;
  verticalExaggeration?: number;
  /** Must be explicit at runtime; unlabeled legacy data is rejected. */
  isSynthetic?: boolean;
  dataType?: "real" | "synthetic";
  validMask?: boolean[];
  resolutionMeters?: MeterSpacing;
  horizontalWindowMeters?: { width: number; height: number };
  verticalDatum?: string;
  coordinateReferenceSystem?: string;
  processingMetadata?: ProcessingMetadata;
}

export type TerrainData = TerrainDataJSON | LegacyTerrainData;
export type ValidatedTerrainData = TerrainDataJSON & { verticalExaggeration: number };
