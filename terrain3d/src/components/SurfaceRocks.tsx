import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import type { ValidatedTerrainData } from "../types/terrain";
import { findSurfaceSpawn, surfaceElevation } from "../geometry/surfaceNavigation";

/** Instanced decorative stones. They do not modify or supplement the source DEM. */
export function SurfaceRocks({ terrain, exaggeration }: { terrain: ValidatedTerrainData; exaggeration: number }) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const stones = useMemo(() => {
    const span = Math.max(terrain.horizontalWindowMeters.width, terrain.horizontalWindowMeters.height);
    const scale = 10 / span;
    let min = Infinity;
    for (const height of terrain.heights) if (height !== null) min = Math.min(min, height);
    const spawn = findSurfaceSpawn(terrain);
    const random = (i: number) => { const n = Math.sin(i * 127.1 + 35.7) * 43758.5453; return n - Math.floor(n); };
    const result: { position: THREE.Vector3; scale: THREE.Vector3; rotation: THREE.Euler }[] = [];
    for (let i = 0; i < 650; i++) {
      // More small stones near the initial landing make the ground scale legible.
      const local = i < 400;
      const u = local ? spawn.u + (random(i * 5) - 0.5) * 0.16 : random(i * 5);
      const v = local ? spawn.v + (random(i * 5 + 1) - 0.5) * 0.16 : random(i * 5 + 1);
      const height = surfaceElevation(terrain, u, v);
      if (height === null || Math.hypot(u - spawn.u, v - spawn.v) < 0.003) continue;
      const size = local ? 0.0015 + random(i * 5 + 2) ** 3 * 0.009 : 0.005 + random(i * 5 + 2) ** 4 * 0.025;
      result.push({ position: new THREE.Vector3((u - 0.5) * terrain.horizontalWindowMeters.width * scale,
        (height - min) * scale * exaggeration + size * 0.15, (v - 0.5) * terrain.horizontalWindowMeters.height * scale),
        scale: new THREE.Vector3(size, size * (0.4 + random(i * 5 + 3) * 0.5), size * 0.85),
        rotation: new THREE.Euler(random(i) * 2, random(i + 1) * 6, random(i + 2)) });
    }
    return result;
  }, [terrain, exaggeration]);
  useLayoutEffect(() => {
    const object = new THREE.Object3D();
    stones.forEach((stone, i) => { object.position.copy(stone.position); object.scale.copy(stone.scale); object.rotation.copy(stone.rotation); object.updateMatrix(); mesh.current?.setMatrixAt(i, object.matrix); });
    if (mesh.current) { mesh.current.instanceMatrix.needsUpdate = true; mesh.current.computeBoundingSphere(); }
  }, [stones]);
  return <instancedMesh ref={mesh} args={[undefined, undefined, stones.length]}>
    <icosahedronGeometry args={[1, 1]} />
    <meshStandardMaterial color={terrain.body === "Mars" ? "#78604d" : terrain.body === "Earth" ? "#77776a" : "#77787a"} roughness={1} flatShading />
  </instancedMesh>;
}
