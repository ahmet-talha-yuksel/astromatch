import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

export type Terrain = {
  id: string;
  width: number;
  height: number;
  cell_size_m: [number, number];
  heights: (number | null)[];
  source: string | null;
  data_status: string;
};

type CameraMessage = { source: string; position: number[]; target: number[] };

function Surface({ terrain, relief, earth }: { terrain: Terrain; relief: number; earth: boolean }) {
  const geometry = useMemo(() => {
    const { width, height, heights } = terrain;
    const vertices = new Float32Array(width * height * 3);
    const colors = new Float32Array(width * height * 3);
    const valid = heights.filter((h): h is number => h !== null);
    const middle = valid.length ? (Math.min(...valid) + Math.max(...valid)) / 2 : 0;
    const horizontal = Math.max((width - 1) * terrain.cell_size_m[0], (height - 1) * terrain.cell_size_m[1]);
    const sx = 10 * terrain.cell_size_m[0] / horizontal;
    const sz = 10 * terrain.cell_size_m[1] / horizontal;
    const low = new THREE.Color(earth ? "#245e55" : "#654e4c");
    const high = new THREE.Color(earth ? "#b1cf9d" : "#e6b492");
    const color = new THREE.Color();
    for (let row = 0; row < height; row++) for (let col = 0; col < width; col++) {
      const i = row * width + col;
      const h = heights[i];
      vertices[i * 3] = (col - (width - 1) / 2) * sx;
      vertices[i * 3 + 1] = h === null ? 0 : (h - middle) * 2 / relief;
      vertices[i * 3 + 2] = (row - (height - 1) / 2) * sz;
      color.copy(low).lerp(high, h === null ? 0 : Math.max(0, Math.min(1, 0.5 + (h - middle) / relief)));
      colors.set(color.toArray(), i * 3);
    }
    const faces: number[] = [];
    for (let row = 0; row < height - 1; row++) for (let col = 0; col < width - 1; col++) {
      const a = row * width + col, b = a + 1, c = a + width, d = c + 1;
      if (heights[a] !== null && heights[b] !== null && heights[c] !== null) faces.push(a, c, b);
      if (heights[b] !== null && heights[c] !== null && heights[d] !== null) faces.push(b, c, d);
    }
    const mesh = new THREE.BufferGeometry();
    mesh.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
    mesh.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    mesh.setIndex(faces);
    mesh.computeVertexNormals();
    return mesh;
  }, [terrain, relief, earth]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <mesh geometry={geometry} rotation={[0, 0, 0]}><meshStandardMaterial vertexColors side={THREE.DoubleSide} roughness={0.9} /></mesh>;
}

function SyncedControls({ id }: { id: string }) {
  const controls = useRef<any>(null);
  const applying = useRef(false);
  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(9, 8, 10);
    controls.current?.target.set(0, 0, 0);
    controls.current?.update();
  }, [id, camera]);
  useEffect(() => {
    const receive = (event: Event) => {
      const message = (event as CustomEvent<CameraMessage>).detail;
      if (message.source === id || !controls.current) return;
      applying.current = true;
      camera.position.fromArray(message.position);
      controls.current.target.fromArray(message.target);
      controls.current.update();
      applying.current = false;
    };
    window.addEventListener("astromatch-camera", receive);
    return () => window.removeEventListener("astromatch-camera", receive);
  }, [id, camera]);
  return <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.08} minDistance={4} maxDistance={35}
    onChange={() => {
      if (applying.current || !controls.current) return;
      window.dispatchEvent(new CustomEvent<CameraMessage>("astromatch-camera", {
        detail: { source: id, position: camera.position.toArray(), target: controls.current.target.toArray() },
      }));
    }} />;
}

export function TerrainPane({ terrain, relief, earth }: { terrain: Terrain | null; relief: number; earth: boolean }) {
  if (!terrain) return <div className="terrain-empty">Bu bölge için 3D yükseklik haritası bulunamadı.</div>;
  return <div className="terrain-canvas" aria-label={`${terrain.id} 3D arazi görünümü`}>
    <Canvas camera={{ position: [9, 8, 10], fov: 42 }}>
      <color attach="background" args={[earth ? "#102b2a" : "#2a2527"]} />
      <ambientLight intensity={1.5} />
      <directionalLight position={[3, 8, 5]} intensity={2.4} />
      <Surface terrain={terrain} relief={relief} earth={earth} />
      <SyncedControls id={terrain.id} />
    </Canvas>
  </div>;
}

export function terrainRelief(terrain: Terrain | null): number {
  if (!terrain) return 0;
  const valid = terrain.heights.filter((h): h is number => h !== null);
  return valid.length ? Math.max(...valid) - Math.min(...valid) : 0;
}
