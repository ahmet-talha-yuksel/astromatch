export { TerrainViewer } from "./components/TerrainViewer";
export { TerrainComparison } from "./components/TerrainComparison";
export type { TerrainComparisonProps } from "./components/TerrainComparison";
export type { TerrainData } from "./types/terrain";
export type { TerrainDataJSON, LegacyTerrainData, ValidatedTerrainData, MeterSpacing, ProcessingMetadata } from "./types/terrain";
export type { TerrainViewerProps, TerrainDisplay } from "./components/TerrainViewer";
export { validateTerrainData, TerrainValidationError } from "./validation/terrain";
export { loadTerrain } from "./loading/loadTerrain";
export { requireCandidateTerrainLink, validateCandidateMetadata, validateSimilarityResult, validateTerrainInput } from "./integration";
export type { CandidateMetadataInput, SimilarityResultInput, ValidatedSimilarityResult } from "./integration";

export type { SurfaceStyle } from "./materials/planetSurface";
