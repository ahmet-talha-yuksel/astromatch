// Approximate surface gravities, m/s² (NASA NSSDC planetary fact sheets):
// https://nssdc.gsfc.nasa.gov/planetary/factsheet/{earthfact,marsfact,moonfact}.html
export const SURFACE_GRAVITY = { Earth: 9.8, Mars: 3.73, Moon: 1.62 } as const;
// Match the illustrative astronaut's 0.14 scene units per character meter.
// This is intentionally independent of DEM normalization and display exaggeration.
export const CHARACTER_SCALE = 0.14;
export const JUMP_SPEED = 3.6 * CHARACTER_SCALE;
export interface JumpState { y: number; velocity: number; grounded: boolean }
export const groundedJump = (y: number): JumpState => ({ y, velocity: 0, grounded: true });
export function launchJump(state: JumpState): JumpState {
  return state.grounded ? { ...state, velocity: JUMP_SPEED, grounded: false } : state;
}
export function stepJump(state: JumpState, body: keyof typeof SURFACE_GRAVITY, seconds: number, ground: number): JumpState {
  if (state.grounded) return groundedJump(ground);
  if (!Number.isFinite(seconds) || seconds <= 0) return state;
  const dt = seconds, gravity = SURFACE_GRAVITY[body] * CHARACTER_SCALE;
  const y = state.y + state.velocity * dt - 0.5 * gravity * dt * dt;
  return y <= ground ? groundedJump(ground) : { y, velocity: state.velocity - gravity * dt, grounded: false };
}
