import { useMemo } from "react";
import * as THREE from "three";
import type { TerrainData } from "../types/terrain";

export function TerrainMesh({ terrain }: { terrain: TerrainData }) {
  const geometry = useMemo(() => {
    const { width, height, elevationsMeters, cellSizeMeters } = terrain;
    if (width < 2 || height < 2 || elevationsMeters.length !== width * height ||
        !elevationsMeters.every(Number.isFinite) || cellSizeMeters <= 0) {
      throw new Error("Invalid terrain data");
    }
    const span = Math.max(width - 1, height - 1) * cellSizeMeters;
    const scale = 10 / span;
    const minElevation = Math.min(...elevationsMeters);
    const exaggeration = terrain.verticalExaggeration ?? 1;
    const vertices: number[] = [];
    const colors: number[] = [];
    const indices: number[] = [];
    const maxElevation = Math.max(...elevationsMeters);
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const elevation = elevationsMeters[y * width + x];
        vertices.push((x - (width - 1) / 2) * cellSizeMeters * scale,
          (elevation - minElevation) * scale * exaggeration,
          (y - (height - 1) / 2) * cellSizeMeters * scale);
        const t = maxElevation === minElevation ? 0.5 : (elevation - minElevation) / (maxElevation - minElevation);
        const color = new THREE.Color().setHSL(0.6 - 0.5 * t, 0.45, 0.34 + t * 0.25);
        colors.push(color.r, color.g, color.b);
      }
    }
    for (let y = 0; y < height - 1; y++) {
      for (let x = 0; x < width - 1; x++) {
        const a = y * width + x, b = a + 1, c = a + width, d = c + 1;
        indices.push(a, c, b, b, c, d);
      }
    }
    const mesh = new THREE.BufferGeometry();
    mesh.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    mesh.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    mesh.setIndex(indices);
    mesh.computeVertexNormals();
    return mesh;
  }, [terrain]);
  return <mesh geometry={geometry}><meshStandardMaterial vertexColors side={THREE.DoubleSide} roughness={0.9} /></mesh>;
}
