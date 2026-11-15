import { forwardRef, useLayoutEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { MER_REFERENCE, WHEEL_MOUNTS, type RoverSnapshot } from "../geometry/roverPhysics";

export const RoverModel = forwardRef<THREE.Group, { scale: number; snapshot: React.MutableRefObject<RoverSnapshot | null>; visible: boolean }>(function RoverModel({ scale, snapshot, visible }, ref) {
  const contents=useRef<THREE.Group>(null);
  useLayoutEffect(()=>{contents.current?.traverse(node=>{if(node instanceof THREE.Mesh){node.castShadow=true;node.receiveShadow=true;}});},[]);
  return <group ref={ref} visible={visible}>
    <group ref={contents} scale={scale}>
      <mesh><boxGeometry args={[0.98, 0.32, 1.14]} /><meshStandardMaterial color="#d3d8d1" roughness={0.5} metalness={0.18} /></mesh>
      <mesh position={[0, -0.13, 0]}><boxGeometry args={[0.86, 0.11, 1.02]} /><meshStandardMaterial color="#46535b" metalness={0.3} roughness={0.65} /></mesh>
      <mesh position={[0, 0.20, 0.02]}><boxGeometry args={[0.58, 0.13, 0.7]} /><meshStandardMaterial color="#d3b477" metalness={0.45} roughness={0.45} /></mesh>
      {[-1, 1].map(side => <group key={side} position={[side * 0.6, 0.28, 0.05]}>
        <mesh><boxGeometry args={[0.66, 0.035, 1.12]} /><meshStandardMaterial color="#8b9a9e" metalness={0.4} /></mesh>
        {Array.from({ length: 3 }, (_, row) => Array.from({ length: 6 }, (_, col) => <mesh key={`${row}-${col}`} position={[(row - 1) * 0.205, 0.02, (col - 2.5) * 0.176]}>
          <boxGeometry args={[0.19, 0.008, 0.161]} /><meshStandardMaterial color={col % 2 ? "#1b3045" : "#263d52"} metalness={0.28} roughness={0.32} />
        </mesh>))}
      </group>)}
      <mesh position={[0.16, 0.73, -0.2]}><cylinderGeometry args={[0.036, 0.045, 0.86, 12]} /><meshStandardMaterial color="#b4bfc1" metalness={0.5} /></mesh>
      <mesh position={[0.16, 1.17, -0.2]}><boxGeometry args={[0.4, 0.15, 0.16]} /><meshStandardMaterial color="#d9ded6" roughness={0.45} /></mesh>
      {[-1, 1].map(side => <group key={side} position={[0.16 + side * 0.13, 1.17, -0.29]} rotation={[Math.PI/2,0,0]}>
        <mesh><cylinderGeometry args={[0.047, 0.052, 0.06, 16]} /><meshStandardMaterial color="#35434b" /></mesh>
        <mesh position={[0, 0.035, 0]} rotation={[-Math.PI/2,0,0]}><circleGeometry args={[0.031, 18]} /><meshStandardMaterial color="#375d71" metalness={0.5} roughness={0.15} /></mesh>
      </group>)}
      <mesh position={[-0.19, 0.42, 0.31]}><cylinderGeometry args={[0.045, 0.075, 0.36, 10]} /><meshStandardMaterial color="#e5e5d7" /></mesh>
      <mesh position={[-0.19, 0.62, 0.31]} rotation={[-0.3,0,0.2]}><cylinderGeometry args={[0.16, 0.16, 0.025, 24]} /><meshStandardMaterial color="#dce3de" metalness={0.25} /></mesh>
      <mesh position={[0.3, 0.61, 0.48]}><cylinderGeometry args={[0.006, 0.006, 0.8, 6]} /><meshStandardMaterial color="#c3cdcb" /></mesh>
      <mesh position={[0, 0.015, -0.59]}><boxGeometry args={[0.75, 0.11, 0.08]} /><meshStandardMaterial color="#aab7bb" metalness={0.3} /></mesh>
      {[-1, 1].map(side => <mesh key={side} position={[side * 0.25, 0.02, -0.64]} rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[0.035, 0.035, 0.025, 12]} /><meshStandardMaterial color="#273d49" /></mesh>)}
      <mesh position={[-0.17, -0.14, -0.72]} rotation={[0.4,0,-0.2]}><boxGeometry args={[0.11, 0.1, 0.4]} /><meshStandardMaterial color="#829399" metalness={0.45} /></mesh>
      <mesh position={[-0.22, -0.19, -0.92]} rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[0.075, 0.075, 0.12, 12]} /><meshStandardMaterial color="#ba9a65" metalness={0.5} /></mesh>
      {WHEEL_MOUNTS.map((mount, i) => <SuspendedWheel key={i} index={i} mount={mount} snapshot={snapshot} />)}
    </group>
  </group>;
});

function SuspendedWheel({ index, mount, snapshot }: { index: number; mount: { x: number; y: number; z: number }; snapshot: React.MutableRefObject<RoverSnapshot | null> }) {
  const carrier = useRef<THREE.Group>(null), tire = useRef<THREE.Group>(null), arm = useRef<THREE.Mesh>(null), shock = useRef<THREE.Mesh>(null);
  const treads = useRef<THREE.InstancedMesh>(null);
  const from = new THREE.Vector3(Math.sign(mount.x) * 0.45, -0.06, mount.z * 0.65);
  useLayoutEffect(() => {
    const object = new THREE.Object3D();
    for (let i = 0; i < 25; i++) {
      const angle = i / 25 * Math.PI * 2;
      const treadCenter = MER_REFERENCE.wheelRadiusM - 0.0045;
      object.position.set(0, Math.cos(angle) * treadCenter, Math.sin(angle) * treadCenter);
      object.rotation.set(angle, 0, 0); object.updateMatrix();
      treads.current?.setMatrixAt(i, object.matrix);
    }
    if (treads.current) treads.current.instanceMatrix.needsUpdate = true;
  }, []);
  useFrame(() => {
    const wheel = snapshot.current?.wheels[index];
    if (!wheel || !carrier.current) return;
    carrier.current.position.set(wheel.x, wheel.y, wheel.z);
    carrier.current.rotation.y = wheel.steering;
    if (tire.current) tire.current.rotation.x = wheel.rotation;
    const endpoint = new THREE.Vector3(wheel.x, wheel.y, wheel.z), direction = endpoint.clone().sub(from);
    for (const [mesh, offset] of [[arm.current, 0], [shock.current, 0.06]] as const) {
      if (!mesh) continue;
      mesh.position.copy(from).add(endpoint).multiplyScalar(0.5); mesh.position.y += offset;
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), direction.clone().normalize()); mesh.scale.y = direction.length();
    }
  });
  return <>
    <mesh ref={arm}><cylinderGeometry args={[0.024,0.024,1,8]} /><meshStandardMaterial color="#86979c" metalness={0.4} /></mesh>
    <mesh ref={shock}><cylinderGeometry args={[0.014,0.014,1,8]} /><meshStandardMaterial color="#c4ad77" metalness={0.55} /></mesh>
    <group ref={carrier} position={[mount.x, mount.y - 0.36, mount.z]}>
      <group ref={tire}>
        <mesh rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[MER_REFERENCE.wheelRadiusM-.007, MER_REFERENCE.wheelRadiusM-.007, MER_REFERENCE.wheelWidthM, 32,1,true]} /><meshStandardMaterial color="#858c8b" side={THREE.DoubleSide} roughness={0.7} metalness={0.25} /></mesh>
        <instancedMesh ref={treads} args={[undefined,undefined,25]}><boxGeometry args={[0.222,0.009,0.018]} /><meshStandardMaterial color="#b3bcb7" roughness={0.65} metalness={0.2} /></instancedMesh>
        {[-1,1].map(side => <group key={side} position={[side * 0.106,0,0]} rotation={[0,0,Math.PI/2]}>
          <mesh rotation={[Math.PI/2,0,0]}><torusGeometry args={[0.118,0.008,6,28]} /><meshStandardMaterial color="#b3bdb8" metalness={0.3} /></mesh>
          <mesh><cylinderGeometry args={[0.037,0.037,0.025,16]} /><meshStandardMaterial color="#6b797c" /></mesh>
          {[0,1,2,3,4,5].map(spoke => <mesh key={spoke} rotation={[0,spoke*Math.PI/3,0]}><boxGeometry args={[0.018,0.011,0.215]} /><meshStandardMaterial color="#b5bfbb" metalness={0.3} /></mesh>)}
        </group>)}
      </group>
    </group>
  </>;
}
