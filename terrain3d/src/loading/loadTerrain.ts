import { validateTerrainData } from "../validation/terrain";
import type { ValidatedTerrainData } from "../types/terrain";

/** Native fetch only. Propagates aborts and field-specific validation errors. */
export async function loadTerrain(url: string, signal?: AbortSignal): Promise<ValidatedTerrainData> {
  if (!url.trim()) throw new Error("Terrain URL must be non-empty");
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`Terrain request failed: HTTP ${response.status} ${response.statusText}`);
  let json: unknown;
  try { json = await response.json(); }
  catch (error) {
    if (signal?.aborted) throw error;
    throw new Error("Terrain response is not valid JSON");
  }
  return validateTerrainData(json);
}
