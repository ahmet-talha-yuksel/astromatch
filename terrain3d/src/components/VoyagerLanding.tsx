import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { ValidatedTerrainData } from "../types/terrain";
import { CHARACTER_SCALE } from "../geometry/jumpPhysics";
import { findLandingSite, LANDER_RADIUS, LANDING_FOOTPRINT, vehicleGround, type LandingSite, type SurfaceWorld } from "../geometry/explorerVehicles";
import { stepLander, type LanderState, type LandingPhase } from "../geometry/manualLanding";
import type { ParcelPosition } from "../geometry/surfaceNavigation";
import { VoyagerCraft } from "./VoyagerCraft";

export interface FlightTelemetry {
  phase: LandingPhase | "unavailable"; altitude: number; verticalSpeed: number; lateralSpeed: number;
  fuel: number; thrust: boolean; reason: string; boundaryBlocked: boolean;
}

export function VoyagerLanding({ terrain, world, origin, angles, held, active, paused, onTelemetry }: {
  terrain: ValidatedTerrainData; world: SurfaceWorld; origin: React.MutableRefObject<ParcelPosition | null>;
  angles: React.MutableRefObject<{ yaw: number; pitch: number }>; held: React.MutableRefObject<Set<string>>;
  active: boolean; paused: boolean; onTelemetry: (telemetry: FlightTelemetry) => void;
}) {
  const { camera, size } = useThree();
  const site = useMemo(() => findLandingSite(terrain, world, origin.current ?? { u: 0.5, v: 0.68 }, angles.current.yaw), [terrain, world]);
  const initial = useMemo<LanderState | null>(() => site ? {
    x: site.x, y: site.y + 45 * CHARACTER_SCALE, z: site.z,
    vx: 0, vy: 0, vz: 0, fuel: 100, phase: "ready", reason: "Hold Space to take control", boundaryBlocked: false,
  } : null, [site]);
  const state = useRef(initial), craft = useRef<THREE.Group>(null), thrust = useRef(false);
  const dust = useRef<THREE.Points>(null), snap = useRef(true), reportTime = useRef(0), elapsed = useRef(0);
  const particlePositions = useMemo(() => new Float32Array(90 * 3), []);
  const previousPhase = useRef<LandingPhase | null>(null);
  useEffect(() => {
    state.current = initial; snap.current = true;
    if (!site) onTelemetry({ phase: "unavailable", altitude: 0, verticalSpeed: 0, lateralSpeed: 0, fuel: 0, thrust: false, reason: "No measured, level landing area in this parcel", boundaryBlocked: false });
  }, [initial, site, onTelemetry]);
  useEffect(() => () => {
    if (window.location.pathname.startsWith("/tests/")) delete (window as Window & { __terrain3dLanding?: unknown }).__terrain3dLanding;
  }, []);
  useEffect(() => {
    if (!active && window.location.pathname.startsWith("/tests/")) delete (window as Window & { __terrain3dLanding?: unknown }).__terrain3dLanding;
  }, [active]);
  useFrame((_, delta) => {
    if (!site || !state.current || !craft.current) return;
    const dt = Math.min(delta, 0.05); elapsed.current += dt;
    const pressed = (...keys: string[]) => keys.some(key => held.current.has(key));
    const input = { forward: Number(pressed("KeyW", "ArrowUp")) - Number(pressed("KeyS", "ArrowDown")),
      strafe: Number(pressed("KeyD", "ArrowRight")) - Number(pressed("KeyA", "ArrowLeft")),
      yaw: angles.current.yaw, thrust: pressed("Space"), brake: pressed("ShiftLeft", "ShiftRight") };
    const groundAt = (x: number, z: number) => {
      const sample = vehicleGround(terrain, world, { u: x / world.width + 0.5, v: z / world.depth + 0.5 }, LANDING_FOOTPRINT);
      return { ...sample, height: sample.height ?? site.y };
    };
    if (active&&!paused) state.current = stepLander(state.current, input, terrain.body, dt, groundAt, { width: world.width, depth: world.depth, radius: LANDER_RADIUS }, site);
    const ship = state.current, ground = groundAt(ship.x, ship.z);
    thrust.current = active && !paused && ship.phase === "flying" && input.thrust && ship.fuel > 0;
    craft.current.position.set(ship.x, ship.y, ship.z);
    craft.current.rotation.x = THREE.MathUtils.damp(craft.current.rotation.x, ship.phase === "flying" ? input.forward * 0.08 : ship.phase === "crashed" ? 0.12 : 0, 6, dt);
    craft.current.rotation.z = THREE.MathUtils.damp(craft.current.rotation.z, ship.phase === "flying" ? -input.strafe * 0.08 : ship.phase === "crashed" ? -0.15 : 0, 6, dt);
    if (dust.current) {
      dust.current.position.set(ship.x, ground.height + 0.025, ship.z);
      const strength = thrust.current ? Math.max(0, 1 - (ship.y - ground.height) / 2) : 0;
      dust.current.visible = strength > 0;
      for (let i = 0; i < 90; i++) {
        const age = (i / 90 + elapsed.current * 0.5) % 1, angle = i * 2.39996;
        const radius = 0.12 + age * 0.9;
        particlePositions[i * 3] = Math.cos(angle) * radius;
        particlePositions[i * 3 + 1] = Math.sin(age * Math.PI) * 0.1;
        particlePositions[i * 3 + 2] = Math.sin(angle) * radius;
      }
      dust.current.geometry.getAttribute("position").needsUpdate = true;
      (dust.current.material as THREE.PointsMaterial).opacity = strength * 0.45;
    }
    if (!active) return;
    const height = Math.max(0, ship.y - ground.height);
    const mobile = size.width < 600;
    const framing = mobile ? 0.8 : 0.5;
    const focus = new THREE.Vector3((ship.x + site.x) / 2, ship.y * framing + site.y * (1 - framing) + 0.28, (ship.z + site.z) / 2);
    const orbit = THREE.MathUtils.clamp(-angles.current.pitch + 0.3, 0.3, 1.1);
    const distance = Math.max(2.8, height * 0.8 + 2) * (mobile ? 1.15 + 0.35 * Math.min(1, height / 4) : 1);
    const desired = focus.clone().add(new THREE.Vector3(Math.sin(input.yaw) * Math.cos(orbit), Math.sin(orbit), Math.cos(input.yaw) * Math.cos(orbit)).multiplyScalar(distance));
    const floor = world.at(desired.x / world.width + 0.5, desired.z / world.depth + 0.5);
    if (floor !== null) desired.y = Math.max(desired.y, floor + 0.15);
    camera.position.lerp(desired, snap.current ? 1 : 1 - Math.exp(-dt * 7)); camera.lookAt(focus); snap.current = false;
    reportTime.current += dt;
    if (reportTime.current > 0.1 || previousPhase.current !== ship.phase) {
      onTelemetry({ phase: ship.phase, altitude: ship.phase === "landed" || ship.phase === "crashed" ? 0 : height / CHARACTER_SCALE, verticalSpeed: ship.vy / CHARACTER_SCALE,
        lateralSpeed: Math.hypot(ship.vx, ship.vz) / CHARACTER_SCALE, fuel: ship.fuel, thrust: thrust.current,
        reason: ship.reason, boundaryBlocked: ship.boundaryBlocked });
      reportTime.current = 0; previousPhase.current = ship.phase;
    }
    if (window.location.pathname.startsWith("/tests/")) {
      (window as Window & { __terrain3dLanding?: unknown }).__terrain3dLanding = { body: terrain.body, ...ship, ground, site, active, altitude: height / CHARACTER_SCALE, thrust: thrust.current };
    }
  });
  if (!site) return null;
  return <>
    <LandingZone site={site} world={world} />
    <group ref={craft}><VoyagerCraft thrust={thrust} /></group>
    <points ref={dust} frustumCulled={false}>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[particlePositions, 3]} /></bufferGeometry>
      <pointsMaterial color={terrain.body === "Mars" ? "#c99566" : terrain.body === "Moon" ? "#b4b2ac" : "#aaa88b"} size={0.025} transparent opacity={0} depthWrite={false} />
    </points>
  </>;
}

function LandingZone({ site, world }: { site: LandingSite; world: SurfaceWorld }) {
  const points = useMemo(() => {
    const positions: number[] = [];
    for (let i = 0; i < 64; i++) {
      if (i % 4 === 0) continue;
      for (const angle of [i / 64 * Math.PI * 2, (i + 1) / 64 * Math.PI * 2]) {
        const x = site.x + Math.cos(angle) * 0.72, z = site.z + Math.sin(angle) * 0.72;
        positions.push(x, (world.at(x / world.width + 0.5, z / world.depth + 0.5) ?? site.y) + 0.018, z);
      }
    }
    return new Float32Array(positions);
  }, [site, world]);
  return <group>
    <lineSegments><bufferGeometry><bufferAttribute attach="attributes-position" args={[points, 3]} /></bufferGeometry><lineBasicMaterial color="#9effdd" toneMapped={false} /></lineSegments>
    {[[-0.1, 0.1], [0.1, -0.1]].map(([x,z], i) => <mesh key={i} position={[site.x + x, site.y + 0.025, site.z + z]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[0.13,0.04]} /><meshBasicMaterial color="#8df1d1" side={THREE.DoubleSide} toneMapped={false} /></mesh>)}
  </group>;
}
