import { useEffect, useRef, useState } from "react";
import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

/** Survey satellite with a keyboard/touch-accessible hidden encounter. Excluded from camera bounds. */
export function OrbitingSpacecraft({ altitude, radius, onDiscover, discovered = false }: { altitude: number; radius: number; onDiscover?: () => void; discovered?: boolean }) {
  const ship = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState(false);
  const phase = useRef(0.5);
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(preference.matches);
    update(); preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);
  useFrame((_, delta) => {
    if (!ship.current) return;
    if (!reducedMotion && !hovered && !discovered) phase.current += Math.min(delta, 0.05) * 0.09;
    const t = phase.current;
    ship.current.position.set(Math.cos(t) * radius, altitude + Math.sin(t * 2) * 0.45, -Math.sin(t) * radius * 0.7);
    ship.current.rotation.set(0.15, -t, 0.12);
  });
  return <group ref={ship} scale={0.65} onClick={event => { if (event.delta < 5) { event.stopPropagation(); onDiscover?.(); } }}>
    <Html center zIndexRange={[20, 10]} style={{ pointerEvents: "none" }}>
      <button className="satellite-hit" aria-label="Inspect orbiting satellite" aria-pressed={discovered} title="Inspect satellite"
        onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)} onFocus={() => setHovered(true)} onBlur={() => setHovered(false)}
        onClick={event => { event.stopPropagation(); onDiscover?.(); }}><span aria-hidden="true">⌖</span></button>
    </Html>
    <mesh><cylinderGeometry args={[0.23, 0.28, 0.8, 8]} /><meshStandardMaterial color="#d3d8da" metalness={0.65} roughness={0.4} /></mesh>
    <mesh position={[0, 0.47, 0]}><coneGeometry args={[0.21, 0.22, 8]} /><meshStandardMaterial color="#d7b982" metalness={0.7} roughness={0.3} /></mesh>
    <mesh rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.035, 0.035, 2.8, 6]} /><meshStandardMaterial color="#a3aeb8" metalness={0.8} /></mesh>
    {[-1, 1].map(side => <group key={side} position={[side * 1.05, 0, 0]}>
      <mesh><boxGeometry args={[1.25, 0.04, 0.75]} /><meshStandardMaterial color="#254d80" metalness={0.65} roughness={0.28} /></mesh>
      {[-0.35, 0, 0.35].map(x => <mesh key={x} position={[x, 0.024, 0]}><boxGeometry args={[0.012, 0.008, 0.7]} /><meshBasicMaterial color="#81b9dc" /></mesh>)}
    </group>)}
    <mesh position={[0, -0.5, 0]} rotation={[Math.PI, 0, 0]}><coneGeometry args={[0.09, 0.3, 8]} /><meshBasicMaterial color="#78e2ff" transparent opacity={0.7} toneMapped={false} /></mesh>
  </group>;
}
