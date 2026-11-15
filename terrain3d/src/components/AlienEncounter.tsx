import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { explorationWorld } from "../geometry/explorationWorld";

export function AlienEncounter({ world }: { world: ReturnType<typeof explorationWorld> }) {
  const visitor = useRef<THREE.Group>(null), arm = useRef<THREE.Group>(null);
  const age = useRef(0), reducedMotion = useRef(false);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => { reducedMotion.current = preference.matches; };
    update(); preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);
  const height = world.at(0.88, 0.72) ?? 0;
  useFrame((_, delta) => {
    age.current += Math.min(delta, 0.05);
    const reduced = reducedMotion.current;
    if (visitor.current) visitor.current.scale.setScalar(reduced ? 1 : THREE.MathUtils.smoothstep(age.current, 0, 1));
    if (arm.current) arm.current.rotation.z = reduced ? -0.9 : -0.9 + Math.sin(age.current * 5) * 0.3;
  });
  return <group position={[world.width * 0.38, height + 0.8, world.depth * 0.22]}>
    <mesh scale={[1, 0.25, 1]}><sphereGeometry args={[0.7, 32, 16]} /><meshStandardMaterial color="#91a9ab" metalness={0.8} roughness={0.23} /></mesh>
    <mesh position={[0, 0.05, 0]} rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.57, 0.035, 8, 32]} /><meshBasicMaterial color="#97ffe0" toneMapped={false} /></mesh>
    <group ref={visitor} position={[0, 0.17, 0]}>
      <mesh position={[0, 0.32, 0]} scale={[0.2, 0.34, 0.16]}><sphereGeometry args={[1, 16, 16]} /><meshStandardMaterial color="#79bc79" roughness={0.65} /></mesh>
      <mesh position={[0, 0.77, 0]} scale={[0.34, 0.4, 0.27]}><sphereGeometry args={[1, 24, 20]} /><meshStandardMaterial color="#a8de8e" roughness={0.55} /></mesh>
      {[-1, 1].map(side => <group key={side}>
        <mesh position={[side * 0.145, 0.81, 0.23]} rotation={[0, side * 0.28, side * -0.25]} scale={[0.11, 0.16, 0.045]}><sphereGeometry args={[1, 16, 12]} /><meshStandardMaterial color="#081e23" roughness={0.15} metalness={0.25} /></mesh>
        <mesh position={[side * 0.11, 0.04, 0]}><capsuleGeometry args={[0.05, 0.22, 5, 8]} /><meshStandardMaterial color="#6fa56f" /></mesh>
      </group>)}
      <group ref={arm} position={[-0.2, 0.48, 0]}>
        <mesh position={[-0.11, 0.15, 0]} rotation={[0, 0, 0.4]}><capsuleGeometry args={[0.045, 0.3, 5, 8]} /><meshStandardMaterial color="#86c67f" /></mesh>
        <mesh position={[-0.18, 0.34, 0]} scale={[0.07, 0.09, 0.035]}><sphereGeometry args={[1, 12, 10]} /><meshStandardMaterial color="#a8de8e" /></mesh>
      </group>
      <mesh position={[0.25, 0.3, 0]} rotation={[0, 0, 0.3]}><capsuleGeometry args={[0.045, 0.3, 5, 8]} /><meshStandardMaterial color="#86c67f" /></mesh>
    </group>
  </group>;
}
