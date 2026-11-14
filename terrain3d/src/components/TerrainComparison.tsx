import type { TerrainData } from "../types/terrain";
import { TerrainViewer } from "./TerrainViewer";

export function TerrainComparison({ target, analog }: { target: TerrainData; analog: TerrainData }) {
  return <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
    <TerrainViewer terrain={target} />
    <TerrainViewer terrain={analog} />
  </div>;
}
