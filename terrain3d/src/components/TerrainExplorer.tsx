import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import * as THREE from "three";
import type { ValidatedTerrainData } from "../types/terrain";
import { findSurfaceSpawn, moveWithinParcel } from "../geometry/surfaceNavigation";
import { interpolateTerrainForDisplay } from "../geometry/visualInterpolation";
import { SURFACE_GRAVITY, groundedJump, launchJump, stepJump } from "../geometry/jumpPhysics";
import { TerrainMesh } from "./TerrainMesh";
import { SurfaceRocks } from "./SurfaceRocks";
import { explorationWorld } from "../geometry/explorationWorld";
import { ExplorationContext } from "./ExplorationContext";
import { ExplorerAvatar } from "./ExplorerAvatar";
import { PlanetEnvironment } from "./PlanetEnvironment";

type Body = "Earth" | "Mars" | "Moon";
type HeldKeys = React.MutableRefObject<Set<string>>;
const bodies: Body[] = ["Earth", "Mars", "Moon"];

export function TerrainExplorer({ terrain, destinations, exaggeration, onClose, showParcelUi = true, fillMissing = true }: {
  terrain: ValidatedTerrainData; destinations: ValidatedTerrainData[]; exaggeration: number; onClose: () => void; showParcelUi?: boolean; fillMissing?: boolean;
}) {
  const [active, setActive] = useState(terrain);
  const [speed, setSpeed] = useState(1);
  const [transition, setTransition] = useState(0);
  const [view, setView] = useState<"third" | "first">("third");
  const [returnRevision, setReturnRevision] = useState(0);
  const marker = useRef<HTMLSpanElement>(null);
  const parcelStatus = useRef<HTMLSpanElement>(null);
  const [fillGaps, setFillGaps] = useState(fillMissing);
  const visualTerrain = useMemo(() => fillGaps ? interpolateTerrainForDisplay(active).terrain : active, [active, fillGaps]);
  const world = useMemo(() => explorationWorld(visualTerrain, exaggeration), [visualTerrain, exaggeration]);
  const jumpRequest = useRef(0);
  const missingPercent = useMemo(() => 100 * active.heights.filter(h => h === null).length / active.heights.length, [active]);
  const held = useRef(new Set<string>());
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const worlds = useMemo(() => bodies.map(body => ({ body, terrain: [terrain, ...destinations].find(t => t.body === body) })), [terrain, destinations]);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    close.current?.focus();
    const focusFrame = requestAnimationFrame(() => {
      const canvas = dialog.current?.querySelector("canvas");
      if (canvas) { canvas.tabIndex = 0; canvas.focus({ preventScroll: true }); }
    });
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); onClose(); }
      if (event.key !== "Tab") return;
      const elements = dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input, select, [tabindex="0"]');
      if (!elements?.length) return;
      const first = elements[0], last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", keyboard);
    return () => { cancelAnimationFrame(focusFrame); document.body.style.overflow = overflow; document.removeEventListener("keydown", keyboard); previous?.focus(); held.current.clear(); };
  }, [onClose]);
  const changeWorld = (next: ValidatedTerrainData) => {
    if (next.id === active.id) return;
    held.current.clear(); setActive(next); setTransition(value => value + 1);
  };
  const touchButton = (key: string, label: string, symbol: string) => <button type="button" aria-label={label}
    onPointerDown={e => { e.preventDefault(); e.currentTarget.setPointerCapture(e.pointerId); held.current.add(key); }}
    onPointerUp={() => held.current.delete(key)} onPointerCancel={() => held.current.delete(key)} onLostPointerCapture={() => held.current.delete(key)}>{symbol}</button>;
  return createPortal(<div ref={dialog} className={`terrain-explorer planet-${active.body.toLowerCase()}`} role="dialog" aria-modal="true" aria-label="Planet terrain explorer">
    <Canvas camera={{ fov: 68, near: 0.0005, far: 300 }} dpr={[1, 1.5]} style={{ touchAction: "none" }}>
      <PlanetEnvironment key={active.body} body={active.body} immersive space />
      <TerrainMesh terrain={active} fillMissing={fillGaps} colorMode={active.body} verticalExaggeration={exaggeration} />
      <ExplorationContext terrain={active} world={world} />
      <SurfaceRocks terrain={active} exaggeration={exaggeration} />
      <ExplorerCamera terrain={active} world={world} held={held} jumpRequest={jumpRequest} speed={speed} view={view} returnRevision={returnRevision} marker={marker} parcelStatus={parcelStatus} />
    </Canvas>
    <div key={transition} className="explorer-transition" aria-hidden="true" />
    <header className="explorer-header">
      <div><span className="explorer-eyebrow">PLANET EXPLORER / {view === "third" ? "THIRD PERSON" : "FIRST PERSON"}</span><h2>{active.body}<span> / {active.name}</span></h2></div>
      <button ref={close} type="button" className="explorer-exit" onClick={onClose}>Exit POV <kbd>Esc</kbd></button>
    </header>
    <nav className="explorer-worlds" aria-label="POV destination">
      {worlds.map(world => <button type="button" key={world.body} disabled={!world.terrain} aria-pressed={active.body === world.body}
        title={world.terrain ? `Explore ${world.terrain.name}` : `No ${world.body} terrain loaded`}
        onClick={() => world.terrain && changeWorld(world.terrain)}><span className={`planet-dot ${world.body.toLowerCase()}`} />{world.body}</button>)}
    </nav>
    <div className="explorer-gravity" aria-label="Surface gravity"><strong>{SURFACE_GRAVITY[active.body].toFixed(2)} m/s²</strong><span>Gravity · {(SURFACE_GRAVITY[active.body] / SURFACE_GRAVITY.Earth).toFixed(2)}g</span></div>
    {showParcelUi && <aside className="explorer-parcel" aria-label="Selected parcel map">
      <div className="parcel-map"><span className="parcel-selected" /><span ref={marker} className="parcel-player" /></div>
      <strong><i /> Selected parcel</strong><span ref={parcelStatus}>Inside selected parcel</span>
      <small>Movement stays inside this parcel</small>
      {missingPercent > 0 && <small className="explorer-nodata">{fillGaps ? "Estimated fill" : "No elevation data"}: {missingPercent.toFixed(2)}%. Not walkable.</small>}
      <button onClick={() => setReturnRevision(value => value + 1)}>Return to parcel</button>
    </aside>}
    {missingPercent > 0 && showParcelUi === false && <div className="explorer-nodata-note" role="note">{fillGaps ? "Estimated fill" : "No elevation data"}: {missingPercent.toFixed(2)}% · Not walkable</div>}
    <div className="explorer-bottom">
      <div className="explorer-instructions"><strong>{view === "third" ? (showParcelUi ? "Explore the selected parcel." : "Explore the surface.") : "Walk the surface."}</strong><span>Drag to look · WASD / arrows to move · Shift to move faster · Space to jump</span>
        <label>Camera <select aria-label="Explorer camera" value={view} onChange={event => setView(event.target.value as "third" | "first")}><option value="third">Third person</option><option value="first">First person</option></select></label>
        {missingPercent > 0 && <button className="explorer-fill-toggle" aria-label="Fill missing terrain (visual only)" aria-pressed={fillGaps} onClick={() => setFillGaps(value => !value)}>{fillGaps ? "Show measured gaps" : "Fill gaps (visual estimate)"}</button>}
        <label>Travel speed <select aria-label="POV travel speed" value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value={0.25}>Slow</option><option value={1}>Explore</option><option value={3}>Fast</option></select></label>
        <small>{active.dataType === "synthetic" ? "SYNTHETIC TERRAIN" : "REAL DEM"} · Artistic environment · Relief {exaggeration.toFixed(1)}×</small>
        <span className="sr-only" role="status">Exploring {active.body}: {active.name}</span>
      </div>
      <div className="explorer-dpad" aria-label="Touch movement controls">
        {touchButton("KeyW", "Move forward", "↑")}<div>{touchButton("KeyA", "Move left", "←")}{touchButton("KeyS", "Move backward", "↓")}{touchButton("KeyD", "Move right", "→")}</div>
        <button className="explorer-jump" aria-label="Jump" onClick={() => { jumpRequest.current++; }}>↟ Jump <kbd>Space</kbd></button>
      </div>
    </div>
  </div>, document.body);
}

function ExplorerCamera({ terrain, world, held, jumpRequest, speed, view, returnRevision, marker, parcelStatus }: {
  terrain: ValidatedTerrainData; world: ReturnType<typeof explorationWorld>; held: HeldKeys; jumpRequest: React.MutableRefObject<number>; speed: number;
  view: "third" | "first"; returnRevision: number;
  marker: React.RefObject<HTMLSpanElement>; parcelStatus: React.RefObject<HTMLSpanElement>;
}) {
  const { camera, gl } = useThree();
  const avatar = useRef<THREE.Group>(null);
  const moving = useRef(false);
  const airborne = useRef(false);
  const jump = useRef(groundedJump(0));
  const consumedJump = useRef(0);
  const jumpElapsed = useRef(0);
  const player = useRef(new THREE.Vector3());
  const angles = useRef({ yaw: 0, pitch: -0.4 });
  const location = useRef<{ u: number; v: number } | null>(null);
  const snap = useRef(true);
  const placePlayer = (u: number, v: number, reset = false) => {
    if (u < 0 || u > 1 || v < 0 || v > 1) return false;
    const height = world.at(u, v);
    if (height === null || (!reset && !jump.current.grounded && height > jump.current.y + 1e-8)) return false;
    if (reset) { jump.current = groundedJump(height); airborne.current = false; consumedJump.current = jumpRequest.current; jumpElapsed.current = 0; }
    location.current = { u, v };
    player.current.set((u - 0.5) * world.width, height, (v - 0.5) * world.depth);
    return true;
  };
  useEffect(() => {
    const current = location.current;
    if (!current || !placePlayer(current.u, current.v, true)) { const spawn = findSurfaceSpawn(terrain); placePlayer(spawn.u, spawn.v, true); }
    snap.current = true;
  }, [terrain, world]);
  useEffect(() => {
    const spawn = findSurfaceSpawn(terrain); placePlayer(spawn.u, spawn.v, true); snap.current = true;
  }, [returnRevision]);
  useEffect(() => { snap.current = true; }, [view]);
  useEffect(() => {
    const canvas = gl.domElement;
    let pointer: number | null = null, lastX = 0, lastY = 0;
    const down = (event: PointerEvent) => { if (pointer !== null) return; pointer = event.pointerId; lastX = event.clientX; lastY = event.clientY; canvas.setPointerCapture(pointer); canvas.focus({ preventScroll: true }); };
    const move = (event: PointerEvent) => {
      if (event.pointerId !== pointer) return;
      angles.current.yaw -= (event.clientX - lastX) * 0.004;
      angles.current.pitch = THREE.MathUtils.clamp(angles.current.pitch - (event.clientY - lastY) * 0.004, -1.15, 0.45);
      lastX = event.clientX; lastY = event.clientY;
    };
    const up = () => { pointer = null; };
    canvas.tabIndex = 0;
    canvas.setAttribute("aria-label", "Terrain view. WASD to move, Space to jump.");
    const keys = new Set(["KeyW", "KeyA", "KeyS", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "ShiftLeft", "ShiftRight"]);
    const keydown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLElement && /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)) return;
      if (event.code === "Space") {
        // Preserve native activation for focused buttons and other UI controls.
        if (event.target instanceof HTMLElement && event.target.closest("button, a, [contenteditable=true]")) return;
        event.preventDefault();
        if (!event.repeat && !held.current.has("Space")) jumpRequest.current++;
        held.current.add("Space"); return;
      }
      if (keys.has(event.code)) { event.preventDefault(); canvas.focus({ preventScroll: true }); held.current.add(event.code); }
    };
    const keyup = (event: KeyboardEvent) => { held.current.delete(event.code); };
    const clear = () => { held.current.clear(); consumedJump.current = jumpRequest.current; pointer = null; };
    canvas.addEventListener("pointerdown", down); canvas.addEventListener("pointermove", move);
    canvas.addEventListener("pointerup", up); canvas.addEventListener("pointercancel", up); canvas.addEventListener("lostpointercapture", up);
    window.addEventListener("keydown", keydown); window.addEventListener("keyup", keyup); window.addEventListener("blur", clear);
    document.addEventListener("visibilitychange", clear);
    return () => {
      canvas.removeEventListener("pointerdown", down); canvas.removeEventListener("pointermove", move);
      canvas.removeEventListener("pointerup", up); canvas.removeEventListener("pointercancel", up); canvas.removeEventListener("lostpointercapture", up);
      window.removeEventListener("keydown", keydown); window.removeEventListener("keyup", keyup); window.removeEventListener("blur", clear);
      document.removeEventListener("visibilitychange", clear); clear();
    };
  }, [gl, held]);
  useFrame((_, delta) => {
    if (consumedJump.current !== jumpRequest.current) {
      consumedJump.current = jumpRequest.current;
      if (jump.current.grounded) { jump.current = launchJump(jump.current); jumpElapsed.current = 0; }
    }
    let boundaryBlocked = false;
    const pressed = (...codes: string[]) => codes.some(code => held.current.has(code));
    const forward = Number(pressed("KeyW", "ArrowUp")) - Number(pressed("KeyS", "ArrowDown"));
    const strafe = Number(pressed("KeyD", "ArrowRight")) - Number(pressed("KeyA", "ArrowLeft"));
    moving.current = !!(forward || strafe);
    if (moving.current && location.current) {
      const yaw = angles.current.yaw;
      let travel = Math.min(delta, 0.05) * 0.55 * speed * (pressed("ShiftLeft", "ShiftRight") ? 2.5 : 1) / Math.hypot(forward, strafe);
      // Small substeps prevent stepping across a narrow NoData hole at high speed.
      const cell = Math.min(world.width / (terrain.width - 1), world.depth / (terrain.height - 1));
      travel = Math.min(travel, cell * 12);
      const steps = Math.max(1, Math.ceil(travel / (cell * 0.2)));
      for (let i = 0; i < steps; i++) {
        const du = (strafe * Math.cos(yaw) - forward * Math.sin(yaw)) * travel / steps / world.width;
        const dv = (-forward * Math.cos(yaw) - strafe * Math.sin(yaw)) * travel / steps / world.depth;
        const current = location.current;
        const next = moveWithinParcel(terrain, current, du, dv, { u: Math.min(0.05, 0.05 / world.width), v: Math.min(0.05, 0.05 / world.depth) });
        if (!next || !placePlayer(next.u, next.v)) { boundaryBlocked = true; break; }
        if (Math.abs(next.u - current.u - du) > 1e-10 || Math.abs(next.v - current.v - dv) > 1e-10) boundaryBlocked = true;
      }
    }
    const ground = location.current ? world.at(location.current.u, location.current.v) : null;
    if (ground !== null) {
      const dt = Math.min(delta, 0.1);
      if (!jump.current.grounded) jumpElapsed.current += dt;
      jump.current = stepJump(jump.current, terrain.body, dt, ground);
      player.current.y = jump.current.y;
    }
    airborne.current = !jump.current.grounded;
    const target = player.current.clone().add(new THREE.Vector3(0, view === "third" ? 0.16 : Math.max(1.7 * world.scale, 0.003), 0));
    if (view === "third") {
      const { yaw, pitch } = angles.current;
      const desired = target.clone().add(new THREE.Vector3(Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch)).multiplyScalar(1.15));
      // Keep the camera above intervening ridges, including after crossing a parcel edge.
      for (let i = 1; i <= 20; i++) {
        const t = i / 20;
        const x = THREE.MathUtils.lerp(target.x, desired.x, t), z = THREE.MathUtils.lerp(target.z, desired.z, t);
        const ground = world.at(x / world.width + 0.5, z / world.depth + 0.5);
        if (ground !== null) desired.y = Math.max(desired.y, target.y + (ground + 0.08 - target.y) / t);
      }
      camera.position.lerp(desired, snap.current ? 1 : 1 - Math.exp(-delta * 10));
      const floor = world.at(camera.position.x / world.width + 0.5, camera.position.z / world.depth + 0.5);
      if (floor !== null) camera.position.y = Math.max(camera.position.y, floor + 0.06);
      camera.lookAt(target);
    } else {
      camera.position.copy(target);
      camera.rotation.set(angles.current.pitch, angles.current.yaw, 0, "YXZ");
    }
    snap.current = false;
    if (avatar.current) {
      avatar.current.position.copy(player.current);
      if (moving.current) avatar.current.rotation.y = angles.current.yaw + Math.atan2(-strafe, forward);
    }
    if (location.current) {
      const { u, v } = location.current;
      if (marker.current) { marker.current.style.left = `${(u + 2) * 20}%`; marker.current.style.top = `${(v + 2) * 20}%`; }
      if (parcelStatus.current) parcelStatus.current.textContent = boundaryBlocked ? "Parcel boundary · Turn back" : "Inside selected parcel";
    }
    if (window.location.pathname.startsWith("/tests/")) {
      (window as Window & { __terrain3dPov?: unknown }).__terrain3dPov = { body: terrain.body, id: terrain.id, position: camera.position.toArray(), rotation: camera.rotation.toArray(), location: location.current, view, heading: [angles.current.yaw, angles.current.pitch], player: player.current.toArray(), grounded: jump.current.grounded, verticalVelocity: jump.current.velocity, jumpElapsed: jumpElapsed.current, ground, gravity: SURFACE_GRAVITY[terrain.body], boundaryBlocked };
    }
  });
  return <ExplorerAvatar ref={avatar} moving={moving} airborne={airborne} visible={view === "third"} />;
}
