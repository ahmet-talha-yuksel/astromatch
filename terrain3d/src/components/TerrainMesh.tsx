import { useMemo } from "react";
import * as THREE from "three";
import type { TerrainData } from "../types/terrain";
import { createTerrainGeometry } from "../geometry/terrainGeometry";

export function TerrainMesh({ terrain, verticalExaggeration, colorMode, elevationOffset, colorRange, worldSpanMeters, onInspect }: {
  terrain: TerrainData; verticalExaggeration?: number; colorMode?: "elevation" | "neutral";
  elevationOffset?: number; colorRange?: { min: number; max: number }; worldSpanMeters?: number;
  onInspect?: (point: THREE.Vector3) => void;
}) {
  const geometry = useMemo(() => createTerrainGeometry(terrain, { verticalExaggeration, colorMode, elevationOffset, colorRange, worldSpanMeters }), [terrain, verticalExaggeration, colorMode, elevationOffset, colorRange, worldSpanMeters]);
  return <mesh geometry={geometry} onPointerMove={event => onInspect?.(event.point)} onPointerOut={() => onInspect?.(new THREE.Vector3(NaN, NaN, NaN))}>
    <meshStandardMaterial vertexColors side={THREE.DoubleSide} roughness={0.9} />
  </mesh>;
}
