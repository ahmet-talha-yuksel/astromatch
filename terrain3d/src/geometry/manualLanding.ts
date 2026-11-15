import { CHARACTER_SCALE, SURFACE_GRAVITY } from "./jumpPhysics";

export type LandingPhase = "ready" | "flying" | "landed" | "crashed";
export interface LanderState {
  x: number; y: number; z: number; vx: number; vy: number; vz: number;
  fuel: number; phase: LandingPhase; reason: string; boundaryBlocked: boolean;
}
export interface LanderInput { forward: number; strafe: number; yaw: number; thrust: boolean; brake: boolean }
export interface LandingGround { height: number; measured: boolean; spread: number }
export interface LandingBounds { width: number; depth: number; radius: number }
export const SAFE_DESCENT_MPS = 2.2;
export const SAFE_LATERAL_MPS = 1.4;

/** Deliberately fictional Voyager-inspired craft, using each world's gravity. */
export function stepLander(previous: LanderState, input: LanderInput, body: keyof typeof SURFACE_GRAVITY, seconds: number,
  groundAt: (x: number, z: number) => LandingGround, bounds: LandingBounds, target: { x: number; z: number }): LanderState {
  if (previous.phase === "landed" || previous.phase === "crashed" || !Number.isFinite(seconds) || seconds <= 0) return previous;
  if (previous.phase === "ready" && !(input.forward || input.strafe || input.thrust || input.brake)) return previous;
  const state = { ...previous, phase: "flying" as LandingPhase, boundaryBlocked: false };
  const duration = Math.min(seconds, 0.1), count = Math.ceil(duration * 120), dt = duration / count;
  const length = Math.max(1, Math.hypot(input.forward, input.strafe));
  for (let i = 0; i < count; i++) {
    const thrust = input.thrust && state.fuel > 0;
    const gravity = SURFACE_GRAVITY[body] * CHARACTER_SCALE;
    const acceleration = 3.5 * CHARACTER_SCALE;
    const ax = (input.strafe * Math.cos(input.yaw) - input.forward * Math.sin(input.yaw)) / length * acceleration;
    const az = (-input.forward * Math.cos(input.yaw) - input.strafe * Math.sin(input.yaw)) / length * acceleration;
    state.vx = (state.vx + ax * dt) * Math.exp(-(input.brake ? 3.5 : 0.15) * dt);
    state.vz = (state.vz + az * dt) * Math.exp(-(input.brake ? 3.5 : 0.15) * dt);
    const ay = gravity * (thrust ? 0.9 : -1);
    state.y += state.vy * dt + 0.5 * ay * dt * dt;
    state.vy += ay * dt;
    state.x += state.vx * dt; state.z += state.vz * dt;
    if (thrust) state.fuel = Math.max(0, state.fuel - 3.2 * dt);
    const limitX = Math.max(0, bounds.width / 2 - bounds.radius), limitZ = Math.max(0, bounds.depth / 2 - bounds.radius);
    const x = Math.max(-limitX, Math.min(limitX, state.x)), z = Math.max(-limitZ, Math.min(limitZ, state.z));
    if (x !== state.x) { state.vx = 0; state.boundaryBlocked = true; }
    if (z !== state.z) { state.vz = 0; state.boundaryBlocked = true; }
    state.x = x; state.z = z;
    const ground = groundAt(x, z);
    // A soft ceiling prevents losing the craft or the parcel in deep space.
    if (state.y > ground.height + 100 * CHARACTER_SCALE) { state.y = ground.height + 100 * CHARACTER_SCALE; state.vy = Math.min(0, state.vy); }
    if (state.y > ground.height + 0.008) continue;
    const onTarget = Math.hypot(x - target.x, z - target.z) <= 0.72;
    state.reason = !ground.measured ? "No measured landing ground" : ground.spread > 0.2 ? "Terrain too steep" :
      !onTarget ? "Outside the landing zone" : -state.vy / CHARACTER_SCALE > SAFE_DESCENT_MPS ? "Descent too fast" :
        Math.hypot(state.vx, state.vz) / CHARACTER_SCALE > SAFE_LATERAL_MPS ? "Lateral speed too high" : "Touchdown confirmed";
    state.phase = state.reason === "Touchdown confirmed" ? "landed" : "crashed";
    state.y = ground.height + 0.008;
    state.vx = 0; state.vy = 0; state.vz = 0;
    return state;
  }
  return state;
}
