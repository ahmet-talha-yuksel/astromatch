import type * as Rapier from "@dimforge/rapier3d-compat";
import * as THREE from "three";
import type { ValidatedTerrainData } from "../types/terrain";
import { createTerrainGeometry } from "./terrainGeometry";
import { parcelSegmentIsValid, type ParcelPosition } from "./surfaceNavigation";
import { vehicleGround, type SurfaceWorld } from "./explorerVehicles";
import { SURFACE_GRAVITY } from "./jumpPhysics";

export const ROVER_STEP = 1 / 120;
export const MER_REFERENCE = {
  massKg: 185, wheelRadiusM: 0.131, wheelWidthM: 0.215, maxSpeedMps: 0.05,
  source: "https://robotics.jpl.nasa.gov/media/documents/fmwi-rankin-2022-0225-final.pdf",
  speedSource: "https://atmos.nmsu.edu/data_and_services/atmospheres_data/MARS/MER/spirit/logs/MER2_INSTHOST.pdf",
} as const;
// Layout, elastic suspension and motor torque are explicit engineering approximations.
export const WHEEL_MOUNTS = [-1, 1].flatMap(side => [-0.62, 0, 0.62].map(z => ({ x: side * 0.68, y: 0.04, z })));
export const ROVER_REST = 0.36;
export const ROVER_FOOTPRINT_M = 1.05;
export type RoverProfile = "mer" | "training";
export interface RoverInput { throttle: number; steer: number; brake: boolean; creep: boolean; grip: number; tractionControl: boolean; profile: RoverProfile }
export interface RoverWheel { x: number; y: number; z: number; steering: number; rotation: number; contact: boolean; loadN: number; compression: number }
export interface RoverSnapshot {
  position: THREE.Vector3; rotation: THREE.Quaternion; wheels: RoverWheel[]; speed: number; pitch: number; roll: number;
  steer: number; contacts: number; traction: number; distance: number; boundaryBlocked: boolean; overturned: boolean;
}
let backend: Promise<typeof Rapier> | null = null;
export function loadRoverBackend() {
  backend ??= import("@dimforge/rapier3d-compat").then(async api => { await api.init(); return api; });
  return backend;
}

/** Source DEM triangles, rigid chassis and six independent ray-cast wheel contacts. */
export class RoverPhysics {
  readonly physics: Rapier.World;
  readonly body: Rapier.RigidBody;
  readonly vehicle: Rapier.DynamicRayCastVehicleController;
  private steering = 0;
  private driveTarget = 0;
  private distance = 0;
  private blockedUntil = 0;
  private ticks = 0;
  private traction = 0;
  private lastSafe: THREE.Vector3;
  private previous: THREE.Vector3;
  private previousRotation: THREE.Quaternion;
  private wheelAngles = Array(6).fill(0) as number[];
  private released = false;
  private readonly radius: number;

  constructor(private api: typeof Rapier, readonly terrain: ValidatedTerrainData, readonly world: SurfaceWorld,
    readonly sceneScale: number, spawn: ParcelPosition, heading = 0) {
    this.radius = ROVER_FOOTPRINT_M * sceneScale;
    this.physics = new api.World({ x: 0, y: -SURFACE_GRAVITY[terrain.body], z: 0 });
    this.physics.timestep = ROVER_STEP; this.physics.numSolverIterations = 8;
    const geometry = createTerrainGeometry(terrain, { verticalExaggeration: 1 });
    const source = geometry.getAttribute("position").array;
    const vertices = new Float32Array(source.length);
    for (let i = 0; i < source.length; i++) vertices[i] = source[i] / sceneScale;
    const indices = new Uint32Array(geometry.index!.array); geometry.dispose();
    this.physics.createCollider(api.ColliderDesc.trimesh(vertices, indices).setFriction(0.8).setRestitution(0));
    const sample = vehicleGround(terrain, world, spawn, this.radius);
    if (!sample.measured || sample.height === null) { this.physics.free(); throw new Error("The rover needs a measured footprint"); }
    const y = sample.height / sceneScale + 0.55;
    this.body = this.physics.createRigidBody(api.RigidBodyDesc.dynamic()
      .setTranslation((spawn.u - 0.5) * world.width / sceneScale, y, (spawn.v - 0.5) * world.depth / sceneScale)
      .setRotation({ x: 0, y: Math.sin(heading / 2), z: 0, w: Math.cos(heading / 2) })
      .setAngularDamping(0.25).setLinearDamping(0.015).setCcdEnabled(true).setCanSleep(false));
    this.physics.createCollider(api.ColliderDesc.cuboid(0.47, 0.16, 0.56).setMass(MER_REFERENCE.massKg)
      .setTranslation(0, -0.025, 0).setFriction(0.6).setRestitution(0.02), this.body);
    this.vehicle = this.physics.createVehicleController(this.body);
    this.vehicle.indexUpAxis = 1; this.vehicle.setIndexForwardAxis = 2;
    WHEEL_MOUNTS.forEach((point, i) => {
      this.vehicle.addWheel(point, { x: 0, y: -1, z: 0 }, { x: 1, y: 0, z: 0 }, ROVER_REST, MER_REFERENCE.wheelRadiusM);
      this.vehicle.setWheelSuspensionStiffness(i, 17);
      this.vehicle.setWheelSuspensionCompression(i, 4.2); this.vehicle.setWheelSuspensionRelaxation(i, 5.2);
      this.vehicle.setWheelMaxSuspensionTravel(i, 0.22); this.vehicle.setWheelMaxSuspensionForce(i, 2400);
      this.vehicle.setWheelFrictionSlip(i, 0.75); this.vehicle.setWheelSideFrictionStiffness(i, 1);
    });
    this.lastSafe = new THREE.Vector3().copy(this.body.translation());
    this.previous = this.lastSafe.clone(); this.previousRotation = new THREE.Quaternion().copy(this.body.rotation()).normalize();
    // Prime scene queries before the first wheel update.
    this.physics.step();
  }

  reset(spawn: ParcelPosition, heading: number) {
    const sample = vehicleGround(this.terrain, this.world, spawn, this.radius);
    if (!sample.measured || sample.height === null) return;
    this.body.setTranslation({ x: (spawn.u - 0.5) * this.world.width / this.sceneScale,
      y: sample.height / this.sceneScale + 0.48, z: (spawn.v - 0.5) * this.world.depth / this.sceneScale }, true);
    this.body.setRotation({ x: 0, y: Math.sin(heading / 2), z: 0, w: Math.cos(heading / 2) }, true);
    this.body.setLinvel({ x: 0, y: 0, z: 0 }, true); this.body.setAngvel({ x: 0, y: 0, z: 0 }, true);
    this.lastSafe.copy(this.body.translation()); this.previous.copy(this.lastSafe); this.previousRotation.copy(this.body.rotation()).normalize();
    this.steering = 0; this.driveTarget = 0; this.blockedUntil = 0;
  }

  step(input: RoverInput) {
    if (this.released) return;
    this.ticks++;
    this.previous.copy(this.body.translation()); this.previousRotation.copy(this.body.rotation()).normalize();
    const orientation = new THREE.Quaternion().copy(this.body.rotation()).normalize();
    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(orientation);
    const speed = new THREE.Vector3().copy(this.body.linvel()).dot(forward);
    const maxSpeed = input.profile === "mer" ? MER_REFERENCE.maxSpeedMps : input.creep ? 0.3 : 1.8;
    const desired = input.throttle * maxSpeed;
    const reference = input.profile === "mer";
    // Pass through a controlled stop before reversing. The old speed threshold
    // alternated full braking and motor force, especially on downhill terrain.
    const reversing = desired * speed < 0 && Math.abs(speed) > (reference ? .003 : .03);
    const target = input.brake || reversing ? 0 : desired;
    const slowing = target === 0 || Math.abs(target) < Math.abs(this.driveTarget);
    const ramp = reference ? .12 : slowing ? 1.3 : .9;
    this.driveTarget += THREE.MathUtils.clamp(target - this.driveTarget, -ramp * ROVER_STEP, ramp * ROVER_STEP);
    const parking = input.throttle === 0 && Math.abs(speed) < (reference ? .005 : .025) && Math.abs(this.driveTarget) < .01;
    const braking = input.brake || parking;
    if (braking) this.driveTarget = 0;
    const targetSteer = input.steer * 0.48 / (1 + Math.abs(speed) * 0.2);
    this.steering += (targetSteer - this.steering) * (1 - Math.exp(-ROVER_STEP * 5));
    const gravity = SURFACE_GRAVITY[this.terrain.body];
    const gradeCompensation=MER_REFERENCE.massKg*gravity*forward.y/6;
    // Continuous motor feedback also slows an overspeed vehicle. Releasing the
    // throttle gives progressive engine braking, then hill hold at rest.
    const acceleration = THREE.MathUtils.clamp((this.driveTarget - speed) * (reference ? 8 : 4.5), -1.4, 1.4);
    const requested = braking ? 0 : THREE.MathUtils.clamp(acceleration * MER_REFERENCE.massKg / 6 + gradeCompensation, -90, 90);
    this.traction = 0;
    for (let i = 0; i < 6; i++) {
      const load = this.normalLoad(i);
      const available = Math.max(0.1, load * input.grip);
      const utilization = Math.abs(requested) / available;
      this.traction = Math.max(this.traction, utilization);
      const force = input.tractionControl ? THREE.MathUtils.clamp(requested, -available * 0.95, available * 0.95) : requested;
      const row = i % 3, side = i < 3 ? -1 : 1;
      // Four-wheel steering; inside front/rear wheels have the tighter angle.
      const angle = row === 1 ? 0 : (row === 0 ? 1 : -0.6) * this.steering * (1 + side * this.steering * 0.3);
      this.vehicle.setWheelSteering(i, angle);
      this.vehicle.setWheelFrictionSlip(i, input.grip);
      this.vehicle.setWheelEngineForce(i, force);
      this.vehicle.setWheelBrake(i, (braking ? 350 : 0) * ROVER_STEP);
    }
    this.vehicle.updateVehicle(ROVER_STEP, this.api.QueryFilterFlags.EXCLUDE_DYNAMIC);
    this.physics.step();
    const position = new THREE.Vector3().copy(this.body.translation());
    const from = { u: this.lastSafe.x * this.sceneScale / this.world.width + 0.5, v: this.lastSafe.z * this.sceneScale / this.world.depth + 0.5 };
    const to = { u: position.x * this.sceneScale / this.world.width + 0.5, v: position.z * this.sceneScale / this.world.depth + 0.5 };
    const sample = vehicleGround(this.terrain, this.world, to, this.radius);
    if (!sample.measured || !parcelSegmentIsValid(this.terrain, from, to)) {
      // Explicit parcel/data geofence, separate from contact dynamics.
      this.body.setTranslation(this.lastSafe, true);
      this.body.setLinvel({ x: 0, y: 0, z: 0 }, true);
      this.driveTarget = 0;
      this.blockedUntil = this.ticks + 25;
    } else {
      this.distance += Math.hypot(position.x - this.lastSafe.x, position.z - this.lastSafe.z);
      this.lastSafe.copy(position);
    }
    for (let i = 0; i < 6; i++) this.wheelAngles[i] = this.vehicle.wheelRotation(i) ?? this.wheelAngles[i];
  }

  snapshot(alpha = 1): RoverSnapshot {
    const current = new THREE.Vector3().copy(this.body.translation());
    const rotation = new THREE.Quaternion().copy(this.body.rotation()).normalize();
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(rotation);
    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(rotation);
    const pitch = Math.asin(THREE.MathUtils.clamp(forward.y, -1, 1)) * 180 / Math.PI;
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(rotation);
    const roll = Math.atan2(right.y, up.y) * 180 / Math.PI;
    const wheels = WHEEL_MOUNTS.map((mount, i) => {
      const length = this.vehicle.wheelSuspensionLength(i) ?? ROVER_REST;
      return { ...mount, y: mount.y - length, steering: this.vehicle.wheelSteering(i) ?? 0,
        rotation: this.wheelAngles[i], contact: this.vehicle.wheelIsInContact(i), loadN: this.normalLoad(i),
        compression: (ROVER_REST - length) / 0.22 };
    });
    return { position: this.previous.clone().lerp(current, alpha).multiplyScalar(this.sceneScale),
      rotation: this.previousRotation.clone().slerp(rotation, alpha), wheels,
      speed: new THREE.Vector3().copy(this.body.linvel()).dot(forward), pitch, roll, steer: this.steering * 180 / Math.PI,
      contacts: wheels.filter(wheel => wheel.contact).length, traction: this.traction, distance: this.distance,
      boundaryBlocked: this.ticks < this.blockedUntil, overturned: up.y < 0.35 };
  }

  private normalLoad(i:number) {
    if(!this.vehicle.wheelIsInContact(i)) return 0;
    const force=this.vehicle.wheelSuspensionForce(i)??0;
    // If no fresh solver force is available, show the elastic support estimate.
    return force>0?force:Math.max(0,ROVER_REST-(this.vehicle.wheelSuspensionLength(i)??ROVER_REST))*17*MER_REFERENCE.massKg;
  }

  dispose() { if (!this.released) { this.released = true; this.physics.free(); } }
}
