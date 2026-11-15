import { useEffect, useMemo } from "react";
import { createContextGeometry, type explorationWorld } from "../geometry/explorationWorld";
import type { ValidatedTerrainData } from "../types/terrain";
import type { SurfaceStyle } from "../materials/planetSurface";
import { SurfaceMaterial } from "./TerrainMesh";

export function ExplorationContext({ terrain, world, appearance, overview = false, highlighted = false }: { terrain: ValidatedTerrainData; world: ReturnType<typeof explorationWorld>; appearance?: SurfaceStyle; overview?: boolean; highlighted?: boolean }) {
  const geometry = useMemo(() => createContextGeometry(world), [world]);
  const boundary = useMemo(() => {
    const points: number[] = [];
    const segment = (u: number, v: number, nu: number, nv: number) => {
      const y = world.at(u, v), next = world.at(nu, nv);
      if (y === null || next === null) return;
      points.push((u - 0.5) * world.width, y + 0.025, (v - 0.5) * world.depth,
        (nu - 0.5) * world.width, next + 0.025, (nv - 0.5) * world.depth);
    };
    for (let x = 0; x < terrain.width - 1; x++) {
      segment(x / (terrain.width - 1), 0, (x + 1) / (terrain.width - 1), 0);
      segment(x / (terrain.width - 1), 1, (x + 1) / (terrain.width - 1), 1);
    }
    for (let z = 0; z < terrain.height - 1; z++) {
      segment(0, z / (terrain.height - 1), 0, (z + 1) / (terrain.height - 1));
      segment(1, z / (terrain.height - 1), 1, (z + 1) / (terrain.height - 1));
    }
    return new Float32Array(points);
  }, [terrain, world]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <group>
    <mesh geometry={geometry}><SurfaceMaterial style={appearance ?? terrain.body} dimmed={overview} /></mesh>
    <lineSegments renderOrder={5}>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[boundary, 3]} /></bufferGeometry>
      <lineBasicMaterial color={highlighted ? "#e0fff2" : "#7bffdd"} toneMapped={false} depthTest={false} transparent opacity={highlighted ? 1 : 0.85} />
    </lineSegments>
    {[[0, 0], [1, 0], [0, 1], [1, 1]].map(([u, v]) => {
      const y = world.at(u, v);
      return y === null ? null : <group key={`${u}-${v}`} position={[(u - 0.5) * world.width, y, (v - 0.5) * world.depth]}>
        <mesh position={[0, 0.4, 0]}><cylinderGeometry args={[0.008, 0.008, 0.8, 6]} /><meshBasicMaterial color="#7bffdd" transparent opacity={0.65} toneMapped={false} /></mesh>
        <mesh position={[0, 0.81, 0]}><octahedronGeometry args={[0.045]} /><meshBasicMaterial color="#b5ffe7" toneMapped={false} /></mesh>
      </group>;
    })}
  </group>;
}
