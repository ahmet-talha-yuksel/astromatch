import { forwardRef, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

function Joint({ position, radius = 0.11 }: { position: [number, number, number]; radius?: number }) {
  return <mesh position={position}><sphereGeometry args={[radius, 12, 10]} /><meshStandardMaterial color="#34424b" roughness={0.9} /></mesh>;
}

export const ExplorerAvatar = forwardRef<THREE.Group, { moving: React.MutableRefObject<boolean>; airborne?: React.MutableRefObject<boolean>; visible: boolean }>(function ExplorerAvatar({ moving, airborne, visible }, ref) {
  const legs = [useRef<THREE.Group>(null), useRef<THREE.Group>(null)];
  const arms = [useRef<THREE.Group>(null), useRef<THREE.Group>(null)];
  const torso = useRef<THREE.Group>(null);
  const gait = useRef(0);
  useFrame((_, delta) => {
    gait.current += Math.min(delta, 0.05) * (moving.current ? 10 : 2);
    const flying = airborne?.current ?? false;
    const swing = moving.current && !flying ? Math.sin(gait.current) * 0.43 : 0;
    legs.forEach((leg, i) => { if (leg.current) leg.current.rotation.x = THREE.MathUtils.damp(leg.current.rotation.x, (flying ? (i ? 0.2 : -0.3) : swing * (i ? -1 : 1)), 14, delta); });
    arms.forEach((arm, i) => { if (arm.current) arm.current.rotation.x = THREE.MathUtils.damp(arm.current.rotation.x, (flying ? -0.6 : swing * (i ? 1 : -1) * 0.7), 14, delta); });
    if (torso.current) torso.current.position.y = flying ? 0 : moving.current ? Math.abs(Math.sin(gait.current)) * 0.025 : Math.sin(gait.current) * 0.006;
  });
  return <group ref={ref} visible={visible}>
    <group scale={0.14}>
      <group ref={torso}>
        <mesh position={[0, 0.88, 0]} scale={[1, 1, 0.8]}><capsuleGeometry args={[0.24, 0.3, 8, 16]} /><meshStandardMaterial color="#e9e9df" roughness={0.68} /></mesh>
        <mesh position={[0, 0.63, 0]}><cylinderGeometry args={[0.235, 0.22, 0.09, 16]} /><meshStandardMaterial color="#455865" /></mesh>
        <mesh position={[0, 1.14, 0]} rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.19, 0.045, 8, 24]} /><meshStandardMaterial color="#667681" metalness={0.5} /></mesh>
        <group position={[0, 1.36, 0]} scale={[1, 1.05, 0.96]}>
          <mesh><sphereGeometry args={[0.3, 32, 24]} /><meshStandardMaterial color="#f4f0df" roughness={0.27} metalness={0.2} /></mesh>
          {/* Sphere azimuth -π/2 faces forward (-Z), matching the chest and boots. */}
          <mesh><sphereGeometry args={[0.307, 32, 20, -Math.PI / 2 - 0.98, 1.96, 0.53, 1.97]} /><meshStandardMaterial color="#45535c" roughness={0.55} /></mesh>
          <mesh><sphereGeometry args={[0.31, 32, 20, -Math.PI / 2 - 0.91, 1.82, 0.6, 1.82]} /><meshStandardMaterial color="#bb9850" metalness={0.88} roughness={0.18} /></mesh>
          {[-1, 1].map(side => <mesh key={side} position={[side * 0.3, -0.02, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.07, 0.07, 0.045, 12]} /><meshStandardMaterial color="#657984" metalness={0.55} /></mesh>)}
        </group>
        <mesh position={[0, 0.94, -0.215]}><boxGeometry args={[0.28, 0.21, 0.065]} /><meshStandardMaterial color="#344954" roughness={0.55} /></mesh>
        {[-0.075, 0, 0.075].map((x, i) => <mesh key={x} position={[x, 0.95, -0.253]}><sphereGeometry args={[0.018, 8, 6]} /><meshBasicMaterial color={i === 0 ? "#e69b5e" : "#74e6c5"} /></mesh>)}
        <mesh position={[0, 0.82, -0.218]}><boxGeometry args={[0.23, 0.025, 0.015]} /><meshStandardMaterial color="#de8c43" /></mesh>
        <mesh position={[0, 0.94, 0.25]}><boxGeometry args={[0.43, 0.55, 0.24]} /><meshStandardMaterial color="#d0d8d5" roughness={0.65} /></mesh>
        <mesh position={[0, 0.95, 0.38]}><boxGeometry args={[0.25, 0.35, 0.025]} /><meshStandardMaterial color="#415863" /></mesh>
        {[-1, 1].map(side => <group key={side}>
          <mesh position={[side * 0.185, 0.95, 0.35]}><capsuleGeometry args={[0.065, 0.3, 6, 10]} /><meshStandardMaterial color="#aebec0" metalness={0.4} /></mesh>
          <mesh position={[side * 0.19, 1.25, 0.27]}><boxGeometry args={[0.055, 0.045, 0.07]} /><meshStandardMaterial color="#de884a" /></mesh>
        </group>)}
        {arms.map((arm, i) => <group key={i} ref={arm} position={[(i ? 1 : -1) * 0.3, 1.04, 0]} rotation={[0, 0, (i ? 1 : -1) * 0.08]}>
          <Joint position={[0, 0, 0]} radius={0.12} />
          <mesh position={[0, -0.14, 0]}><capsuleGeometry args={[0.1, 0.12, 6, 12]} /><meshStandardMaterial color="#e1e3db" /></mesh>
          <Joint position={[0, -0.3, 0]} radius={0.095} />
          <mesh position={[0, -0.39, -0.02]}><capsuleGeometry args={[0.09, 0.1, 6, 12]} /><meshStandardMaterial color="#e9e9df" /></mesh>
          <mesh position={[0, -0.47, -0.02]}><cylinderGeometry args={[0.095, 0.095, 0.05, 12]} /><meshStandardMaterial color="#dc894c" /></mesh>
          <mesh position={[0, -0.55, -0.025]} scale={[0.085, 0.1, 0.09]}><sphereGeometry args={[1, 12, 10]} /><meshStandardMaterial color="#879796" /></mesh>
        </group>)}
      </group>
      {legs.map((leg, i) => <group key={i} ref={leg} position={[(i ? 1 : -1) * 0.13, 0.58, 0]}>
        <mesh position={[0, -0.11, 0]}><capsuleGeometry args={[0.108, 0.1, 6, 12]} /><meshStandardMaterial color="#dfe4dd" /></mesh>
        <Joint position={[0, -0.27, 0]} radius={0.1} />
        <mesh position={[0, -0.27, -0.07]}><boxGeometry args={[0.15, 0.12, 0.08]} /><meshStandardMaterial color="#a6b4b6" /></mesh>
        <mesh position={[0, -0.38, 0]}><capsuleGeometry args={[0.095, 0.1, 6, 12]} /><meshStandardMaterial color="#dce0d8" /></mesh>
        <mesh position={[0, -0.51, -0.06]}><boxGeometry args={[0.2, 0.12, 0.32]} /><meshStandardMaterial color="#485a62" roughness={0.85} /></mesh>
        <mesh position={[0, -0.56, -0.06]}><boxGeometry args={[0.21, 0.025, 0.33]} /><meshStandardMaterial color="#25343c" /></mesh>
      </group>)}
    </group>
  </group>;
});
