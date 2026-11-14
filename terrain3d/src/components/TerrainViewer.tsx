import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { TerrainMesh } from "./TerrainMesh";
import type { TerrainData } from "../types/terrain";

export function TerrainViewer({ terrain }: { terrain: TerrainData }) {
  return <section style={{ minWidth: 0 }}>
    <div style={{ height: 350, background: "#101827", borderRadius: 12, overflow: "hidden" }}>
      <Canvas camera={{ position: [9, 9, 13], fov: 45 }}>
        <ambientLight intensity={1.3} />
        <directionalLight position={[5, 12, 8]} intensity={2} />
        <TerrainMesh terrain={terrain} />
        <OrbitControls makeDefault target={[0, 0, 0]} />
        <gridHelper args={[14, 14, "#586778", "#263446"]} position={[0, -0.1, 0]} />
      </Canvas>
    </div>
    <h3>{terrain.name} {terrain.isSynthetic ? "(SYNTHETIC DEMO)" : ""}</h3>
    <small>{terrain.body} · {terrain.width}×{terrain.height} · {terrain.cellSizeMeters} m/cell · vertical exaggeration {terrain.verticalExaggeration ?? 1}× · {terrain.source}</small>
  </section>;
}
