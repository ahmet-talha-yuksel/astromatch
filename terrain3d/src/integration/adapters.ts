import type { TerrainData } from "../types/terrain";
import { validateTerrainData, TerrainValidationError } from "../validation/terrain";

export interface SimilarityResultInput {
  synthetic?: boolean;
  target_id: string;
  candidate_id: string;
  total_similarity: number;
  criterion_similarity?: Record<string, number>;
  normalized_weights?: Record<string, number>;
  missing_data?: string[];
  source?: { label?: string };
  [key: string]: unknown;
}

export interface ValidatedSimilarityResult extends SimilarityResultInput {
  target_id: string;
  candidate_id: string;
  total_similarity: number;
}

export interface CandidateMetadataInput {
  id: string;
  name?: string;
  lat?: number;
  lon?: number;
  terrainId?: string;
  terrain_id?: string;
  [key: string]: unknown;
}

export function validateSimilarityResult(input: unknown): ValidatedSimilarityResult {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new TerrainValidationError("Invalid similarity result: expected an object");
  const result = input as Record<string, unknown>;
  for (const field of ["target_id", "candidate_id"]) {
    if (typeof result[field] !== "string" || !(result[field] as string).trim()) throw new TerrainValidationError(`Invalid similarity result: ${field}`);
  }
  if (typeof result.total_similarity !== "number" || !Number.isFinite(result.total_similarity) || result.total_similarity < 0 || result.total_similarity > 1) {
    throw new TerrainValidationError("Invalid similarity result: total_similarity must be a finite number in [0, 1]");
  }
  for (const field of ["criterion_similarity", "normalized_weights"]) {
    if (result[field] !== undefined) {
      const values = result[field];
      if (!values || typeof values !== "object" || Array.isArray(values) || Object.values(values as Record<string, unknown>).some(value => typeof value !== "number" || !Number.isFinite(value) || (field === "criterion_similarity" && (value < 0 || value > 1)))) {
        throw new TerrainValidationError(`Invalid similarity result: ${field}`);
      }
    }
  }
  if (result.missing_data !== undefined && (!Array.isArray(result.missing_data) || result.missing_data.some(value => typeof value !== "string"))) throw new TerrainValidationError("Invalid similarity result: missing_data");
  return result as ValidatedSimilarityResult;
}

export function validateCandidateMetadata(input: unknown): CandidateMetadataInput {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new TerrainValidationError("Invalid candidate: expected an object");
  const candidate = input as Record<string, unknown>;
  if (typeof candidate.id !== "string" || !candidate.id.trim()) throw new TerrainValidationError("Invalid candidate: id");
  for (const field of ["lat", "lon"]) if (candidate[field] !== undefined && (typeof candidate[field] !== "number" || !Number.isFinite(candidate[field] as number))) throw new TerrainValidationError(`Invalid candidate: ${field}`);
  return candidate as CandidateMetadataInput;
}

export function requireCandidateTerrainLink(input: unknown, availableTerrainIds: Iterable<string>): string {
  const candidate = validateCandidateMetadata(input);
  const terrainId = candidate.terrainId ?? candidate.terrain_id;
  if (typeof terrainId !== "string" || !terrainId.trim()) throw new TerrainValidationError(`Candidate ${candidate.id} has no terrain link`);
  if (!new Set(availableTerrainIds).has(terrainId)) throw new TerrainValidationError(`Candidate ${candidate.id} references unavailable terrain ${terrainId}`);
  return terrainId;
}

export function validateTerrainInput(input: unknown): ReturnType<typeof validateTerrainData> { return validateTerrainData(input as TerrainData); }

