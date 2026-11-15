import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { ValidatedTerrainData } from "../types/terrain";
import { findSurfaceSpawn, type ParcelPosition } from "../geometry/surfaceNavigation";
import { findRoverSpawn, type SurfaceWorld } from "../geometry/explorerVehicles";
import { loadRoverBackend, RoverPhysics, ROVER_STEP, type RoverInput, type RoverProfile, type RoverSnapshot } from "../geometry/roverPhysics";
import { RoverModel } from "./RoverModel";

export interface RoverTelemetry { loading: boolean; error?: string; speed: number; pitch: number; roll: number; contacts: number; traction: number; distance: number; steer: number; loads: number[]; suspension: number[]; boundaryBlocked: boolean; overturned: boolean }
export function RoverVehicle({ terrain, world, sceneScale, held, angles, location, player, view, active, paused, returnRevision, profile, timeScale, grip, tractionControl, onTelemetry, marker, parcelStatus }: {
  terrain: ValidatedTerrainData; world: SurfaceWorld; sceneScale: number; held: React.MutableRefObject<Set<string>>;
  angles: React.MutableRefObject<{ yaw: number; pitch: number }>; location: React.MutableRefObject<ParcelPosition | null>;
  player: React.MutableRefObject<THREE.Vector3>; view: "third" | "first"; active: boolean; paused: boolean; returnRevision: number;
  profile: RoverProfile; timeScale: number; grip: number; tractionControl: boolean; onTelemetry: (value: RoverTelemetry) => void;
  marker: React.RefObject<HTMLSpanElement>; parcelStatus: React.RefObject<HTMLSpanElement>;
}) {
  const { camera } = useThree();
  const simulation = useRef<RoverPhysics | null>(null), root = useRef<THREE.Group>(null), snapshot = useRef<RoverSnapshot | null>(null);
  const accumulator = useRef(0), report = useRef(0), snap = useRef(true), heading = useRef(angles.current.yaw);
  const startup = useRef({ spawn: location.current ?? findSurfaceSpawn(terrain), heading: angles.current.yaw });
  const sun=useRef<THREE.DirectionalLight>(null), fill=useRef<THREE.DirectionalLight>(null), sunTarget=useMemo(()=>new THREE.Object3D(),[]);
  useEffect(() => {
    let disposed = false, owned: RoverPhysics | null = null;
    const spawn = findRoverSpawn(terrain, world, startup.current.spawn, sceneScale);
    onTelemetry({ loading: true, speed: 0,pitch:0,roll:0,contacts:0,traction:0,distance:0,steer:0,loads:[],suspension:[],boundaryBlocked:false,overturned:false });
    loadRoverBackend().then(api => {
      if (disposed) return;
      if (!spawn) throw new Error("Not enough measured terrain for the rover");
      owned = new RoverPhysics(api, terrain, world, sceneScale, spawn, startup.current.heading);
      simulation.current = owned; accumulator.current = 0; snap.current = true;
    }).catch(error => {
      if (!disposed) onTelemetry({ loading:false,error:String(error),speed:0,pitch:0,roll:0,contacts:0,traction:0,distance:0,steer:0,loads:[],suspension:[],boundaryBlocked:false,overturned:false });
    });
    return () => { disposed = true; owned?.dispose(); simulation.current = null; };
  }, [terrain, world, sceneScale, onTelemetry]);
  useEffect(() => {
    const spawn = findRoverSpawn(terrain, world, findSurfaceSpawn(terrain), sceneScale);
    if (spawn) simulation.current?.reset(spawn, heading.current);
    accumulator.current = 0; snap.current = true;
  }, [returnRevision]);
  useEffect(() => { snap.current = true; accumulator.current = 0; }, [active, paused, view]);
  useFrame((_, delta) => {
    const sim = simulation.current;
    if (!sim || !root.current) return;
    const pressed = (...keys: string[]) => keys.some(key => held.current.has(key));
    const input: RoverInput = { throttle: Number(pressed("KeyW","ArrowUp")) - Number(pressed("KeyS","ArrowDown")),
      steer: Number(pressed("KeyA","ArrowLeft")) - Number(pressed("KeyD","ArrowRight")), brake: pressed("Space"),
      creep: pressed("ShiftLeft","ShiftRight"), grip, tractionControl, profile };
    if (active && !paused) {
      accumulator.current += Math.min(delta,0.1) * timeScale;
      for (let count=0; accumulator.current+1e-10 >= ROVER_STEP && count < 240; count++) { sim.step(input); accumulator.current = Math.max(0,accumulator.current-ROVER_STEP); }
    } else accumulator.current = 0;
    const pose = sim.snapshot(active && !paused ? Math.min(1,accumulator.current / ROVER_STEP) : 1);
    snapshot.current = pose; root.current.position.copy(pose.position); root.current.quaternion.copy(pose.rotation);
    sunTarget.position.copy(pose.position);
    sun.current?.position.copy(pose.position).add(new THREE.Vector3(-4,6,-5).multiplyScalar(sceneScale));
    player.current.copy(pose.position);
    location.current = { u: pose.position.x / world.width + 0.5, v: pose.position.z / world.depth + 0.5 };
    if (!active) return;
    const bodyForward = new THREE.Vector3(0,0,-1).applyQuaternion(pose.rotation);
    const bodyYaw = Math.atan2(-bodyForward.x, -bodyForward.z);
    const orbitYaw = bodyYaw + angles.current.yaw - startup.current.heading;
    const target = pose.position.clone().add(new THREE.Vector3(0,0.45 * sceneScale,0));
    if (view === "third") {
      const orbitPitch = Math.max(0.12,-angles.current.pitch), distance = 5.8 * sceneScale;
      const desired = target.clone().add(new THREE.Vector3(Math.sin(orbitYaw)*Math.cos(orbitPitch),Math.sin(orbitPitch),Math.cos(orbitYaw)*Math.cos(orbitPitch)).multiplyScalar(distance));
      for (let i=1;i<=20;i++) {
        const t=i/20, x=THREE.MathUtils.lerp(target.x,desired.x,t), z=THREE.MathUtils.lerp(target.z,desired.z,t);
        const ground = world.at(x/world.width+.5,z/world.depth+.5);
        if (ground !== null) desired.y=Math.max(desired.y,target.y+(ground+.12*sceneScale-target.y)/t);
      }
      camera.position.lerp(desired,snap.current?1:1-Math.exp(-delta*9)); camera.lookAt(target);
    } else {
      camera.position.copy(new THREE.Vector3(.16,1.17,-.2).multiplyScalar(sceneScale).applyQuaternion(pose.rotation).add(pose.position));
      const look = new THREE.Quaternion().setFromEuler(new THREE.Euler(angles.current.pitch, angles.current.yaw-startup.current.heading,0,"YXZ"));
      camera.quaternion.copy(pose.rotation).multiply(look);
    }
    snap.current=false;
    fill.current?.position.copy(camera.position).add(new THREE.Vector3(0,2*sceneScale,0));
    camera.near=Math.max(1e-7,sceneScale*.015); camera.updateProjectionMatrix();
    if (marker.current) { marker.current.style.left=`${(location.current.u+2)*20}%`;marker.current.style.top=`${(location.current.v+2)*20}%`; }
    if (parcelStatus.current) parcelStatus.current.textContent=pose.boundaryBlocked?"Geofence · measured terrain only":"Rover inside selected parcel";
    report.current+=delta;
    if (report.current>.1) {
      onTelemetry({loading:false,speed:pose.speed,pitch:pose.pitch,roll:pose.roll,contacts:pose.contacts,traction:pose.traction,distance:pose.distance,
        steer:pose.steer,loads:pose.wheels.map(w=>w.loadN),suspension:pose.wheels.map(w=>w.compression),boundaryBlocked:pose.boundaryBlocked,overturned:pose.overturned});
      report.current=0;
    }
    if (window.location.pathname.startsWith("/tests/")) {
      (window as Window & {__terrain3dPov?:unknown}).__terrain3dPov={body:terrain.body,vehicle:"rover",id:terrain.id,view,position:camera.position.toArray(),
        player:pose.position.toArray(),location:location.current,heading:[angles.current.yaw,angles.current.pitch],grounded:pose.contacts>0,
        speed:pose.speed,pitch:pose.pitch,roll:pose.roll,contacts:pose.contacts,wheels:pose.wheels,boundaryBlocked:pose.boundaryBlocked,paused,timeScale};
    }
  });
  return <>
    <RoverModel ref={root} scale={sceneScale} snapshot={snapshot} visible={active && view === "third"} />
    <primitive object={sunTarget} />
    <directionalLight ref={fill} target={sunTarget} visible={active} intensity={0.7} color="#c4d7ef" />
    <directionalLight ref={sun} target={sunTarget} visible={active} intensity={2.2} color={terrain.body==="Mars"?"#ffe0be":"#fff5e6"} castShadow
      shadow-mapSize-width={1024} shadow-mapSize-height={1024} shadow-camera-near={sceneScale*.1} shadow-camera-far={sceneScale*15}
      shadow-camera-left={-3*sceneScale} shadow-camera-right={3*sceneScale} shadow-camera-top={3*sceneScale} shadow-camera-bottom={-3*sceneScale}
      shadow-normalBias={sceneScale*.003} shadow-bias={-.00005} />
  </>;
}
