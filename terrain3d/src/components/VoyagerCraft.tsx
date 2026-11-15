import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

function Strut({ from, to, radius = 0.018, color = "#a8b4b8" }: { from: [number, number, number]; to: [number, number, number]; radius?: number; color?: string }) {
  const { position, quaternion, length } = useMemo(() => {
    const a = new THREE.Vector3(...from), b = new THREE.Vector3(...to), direction = b.clone().sub(a);
    return { position: a.clone().add(b).multiplyScalar(0.5), length: direction.length(), quaternion: new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize()) };
  }, [from[0], from[1], from[2], to[0], to[1], to[2]]);
  return <mesh position={position} quaternion={quaternion}><cylinderGeometry args={[radius, radius, length, 8]} /><meshStandardMaterial color={color} metalness={0.4} roughness={0.5} /></mesh>;
}

/** Recognizable antenna, instrument booms and Golden Record; fictional landing legs. */
export function VoyagerCraft({ thrust, damaged = false }: { thrust: React.MutableRefObject<boolean>; damaged?: boolean }) {
  const exhaust = useRef<THREE.Group>(null), time = useRef(0);
  const profile = useMemo(() => Array.from({ length: 20 }, (_, i) => {
    const r = i / 19 * 0.68;
    return new THREE.Vector2(r, 0.26 * (r / 0.68) ** 2);
  }), []);
  useFrame((_, delta) => {
    time.current += delta;
    if (exhaust.current) { exhaust.current.visible = thrust.current; exhaust.current.scale.y = 0.8 + Math.sin(time.current * 38) * 0.16; }
  });
  return <group scale={0.55} rotation={[damaged ? 0.12 : 0, 0.3, damaged ? -0.15 : 0]}>
    <mesh position={[0, 0.44, 0]}><cylinderGeometry args={[0.31, 0.37, 0.3, 10]} /><meshStandardMaterial color="#bc9150" metalness={0.55} roughness={0.42} /></mesh>
    <mesh position={[0, 0.615, 0]}><cylinderGeometry args={[0.34, 0.34, 0.05, 10]} /><meshStandardMaterial color="#35404a" metalness={0.4} /></mesh>
    <mesh position={[0, 0.69, 0]}><cylinderGeometry args={[0.12, 0.2, 0.17, 12]} /><meshStandardMaterial color="#abb1b1" metalness={0.45} /></mesh>
    <group position={[0, 0.76, 0]} rotation={[0.15, 0, -0.12]}>
      <mesh><latheGeometry args={[profile, 48]} /><meshStandardMaterial color="#e8ece7" side={THREE.DoubleSide} metalness={0.22} roughness={0.4} /></mesh>
      <mesh position={[0, 0.26, 0]} rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.68, 0.017, 8, 48]} /><meshStandardMaterial color="#c0ccd0" metalness={0.6} /></mesh>
      {[0, 2.094, 4.189].map(angle => <Strut key={angle} from={[Math.sin(angle) * 0.54, 0.16, Math.cos(angle) * 0.54]} to={[0, 0.62, 0]} radius={0.009} />)}
      <mesh position={[0, 0.62, 0]}><cylinderGeometry args={[0.045, 0.08, 0.14, 12]} /><meshStandardMaterial color="#a6adaf" metalness={0.5} /></mesh>
    </group>
    {[0.5, 2.594, 4.689].map(angle => <group key={angle}>
      <Strut from={[Math.sin(angle) * 0.25, 0.4, Math.cos(angle) * 0.25]} to={[Math.sin(angle) * 0.67, 0.045, Math.cos(angle) * 0.67]} radius={0.024} />
      <Strut from={[Math.sin(angle) * 0.18, 0.28, Math.cos(angle) * 0.18]} to={[Math.sin(angle) * 0.62, 0.12, Math.cos(angle) * 0.62]} radius={0.012} color="#c6a76e" />
      <mesh position={[Math.sin(angle) * 0.67, 0.025, Math.cos(angle) * 0.67]}><cylinderGeometry args={[0.12, 0.14, 0.04, 12]} /><meshStandardMaterial color="#77888d" metalness={0.5} /></mesh>
    </group>)}
    <Strut from={[0.22, 0.47, 0.12]} to={[1.25, 0.55, 0.2]} radius={0.025} />
    <Strut from={[0.2, 0.32, 0.05]} to={[1.15, 0.52, 0.2]} radius={0.012} />
    {[0, 1, 2].map(i => <group key={i} position={[0.95 + i * 0.17, 0.55, 0.2]} rotation={[0, 0, Math.PI / 2]}>
      <mesh><cylinderGeometry args={[0.075, 0.075, 0.15, 12]} /><meshStandardMaterial color="#333e47" metalness={0.35} /></mesh>
      {[0, 1, 2].map(fin => <mesh key={fin} position={[0, -0.05 + fin * 0.05, 0]}><cylinderGeometry args={[0.11, 0.11, 0.012, 12]} /><meshStandardMaterial color="#53616a" /></mesh>)}
    </group>)}
    <Strut from={[-0.2, 0.52, 0]} to={[-0.92, 0.58, -0.2]} radius={0.018} />
    <mesh position={[-0.9, 0.58, -0.2]}><boxGeometry args={[0.22, 0.17, 0.15]} /><meshStandardMaterial color="#333f49" metalness={0.4} /></mesh>
    <Strut from={[-0.1, 0.52, 0.15]} to={[-0.85, 1.1, 0.7]} radius={0.008} />
    <mesh position={[0, 0.46, 0.36]}><circleGeometry args={[0.12, 32]} /><meshStandardMaterial color="#dfb95d" metalness={0.65} roughness={0.3} side={THREE.DoubleSide} /></mesh>
    {[0.06, 0.09, 0.12].map(radius => <mesh key={radius} position={[0, 0.46, 0.365]}><torusGeometry args={[radius, 0.002, 4, 32]} /><meshStandardMaterial color="#9a7133" /></mesh>)}
    <group ref={exhaust}>
      {[-1, 1].map(side => <mesh key={side} position={[side * 0.18, -0.18, 0]} rotation={[Math.PI, 0, 0]}>
        <coneGeometry args={[0.1, 0.65, 20]} /><meshBasicMaterial color="#83d9ff" transparent opacity={0.45} toneMapped={false} depthWrite={false} />
      </mesh>)}
    </group>
  </group>;
}
