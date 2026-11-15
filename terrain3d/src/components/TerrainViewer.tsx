import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { MOUSE } from "three";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TerrainMesh } from "./TerrainMesh";
import { ExplorationContext } from "./ExplorationContext";
import { OrbitingSpacecraft } from "./OrbitingSpacecraft";
import { keepOverviewAboveGround } from "../geometry/overviewCollision";
import { AlienEncounter } from "./AlienEncounter";
import { explorationWorld } from "../geometry/explorationWorld";
import { TerrainExplorer } from "./TerrainExplorer";
import { PlanetEnvironment } from "./PlanetEnvironment";
import { isPlanetSurface, type SurfaceStyle } from "../materials/planetSurface";
import "./explorer.css";
import type { TerrainData, ValidatedTerrainData } from "../types/terrain";
import { spacingAxes, validateTerrainData } from "../validation/terrain";
import { loadTerrain } from "../loading/loadTerrain";

export type TerrainViewerProps = (
  | { terrain: TerrainData; terrainUrl?: never; display?: TerrainDisplay }
  | { terrainUrl: string; terrain?: never; display?: TerrainDisplay }) & { explorationTerrains?: TerrainData[] };
export interface TerrainDisplay { exaggeration?: number; colorMode?: SurfaceStyle; elevationOffset?: number; colorRange?: { min: number; max: number }; worldSpanMeters?: number; syncKey?: string; syncEnabled?: boolean }
type TerrainState = { terrain: ValidatedTerrainData; error?: never } | { terrain?: never; error: string };
type ColorMode = SurfaceStyle;
function errorMessage(error: unknown): string { return error instanceof Error ? error.message : String(error); }

export function TerrainViewer(props: TerrainViewerProps) {
  if (props.terrainUrl !== undefined) return <TerrainUrlViewer key={props.terrainUrl} url={props.terrainUrl} display={props.display} explorationTerrains={props.explorationTerrains} />;
  return <TerrainObjectViewer terrain={props.terrain} display={props.display} explorationTerrains={props.explorationTerrains} />;
}
function TerrainObjectViewer({ terrain, display, explorationTerrains }: { terrain: TerrainData; display?: TerrainDisplay; explorationTerrains?: TerrainData[] }) {
  const state = useMemo<TerrainState>(() => { try { return { terrain: validateTerrainData(terrain) }; } catch (e) { return { error: errorMessage(e) }; } }, [terrain]);
  return state.terrain ? <TerrainScene key={state.terrain.id} terrain={state.terrain} display={display} explorationTerrains={explorationTerrains} /> : <p role="alert">{state.error}</p>;
}
function TerrainUrlViewer({ url, display, explorationTerrains }: { url: string; display?: TerrainDisplay; explorationTerrains?: TerrainData[] }) {
  const [state, setState] = useState<TerrainState | null>(null);
  useEffect(() => { const controller = new AbortController(); let active = true;
    loadTerrain(url, controller.signal).then(t => { if (active) setState({ terrain: t }); }, e => { if (active) setState({ error: errorMessage(e) }); });
    return () => { active = false; controller.abort(); };
  }, [url]);
  if (!state) return <p role="status">Loading terrain…</p>;
  return state.terrain ? <TerrainScene key={state.terrain.id} terrain={state.terrain} display={display} explorationTerrains={explorationTerrains} /> : <p role="alert">{url}: {state.error}</p>;
}

function TerrainScene({ terrain, display, explorationTerrains }: { terrain: ValidatedTerrainData; display?: TerrainDisplay; explorationTerrains?: TerrainData[] }) {
  const [localExaggeration, setExaggeration] = useState(terrain.verticalExaggeration);
  const [localColorMode, setColorMode] = useState<ColorMode>("surface");
  const [pov, setPov] = useState(false);
  const closePov = useCallback(() => setPov(false), []);
  const destinations = useMemo(() => {
    try { return { terrains: (explorationTerrains ?? []).map(validateTerrainData), error: "" }; }
    catch (error) { return { terrains: [], error: errorMessage(error) }; }
  }, [explorationTerrains]);
  const exaggeration = display?.exaggeration ?? localExaggeration;
  const colorMode = display?.colorMode ?? localColorMode;
  const surfaceBody = colorMode === "surface" ? terrain.body : isPlanetSurface(colorMode) ? colorMode : null;
  const [cameraAction, setCameraAction] = useState({ mode: "perspective", revision: 0 });
  const [alien, setAlien] = useState(false);
  const [parcelHovered, setParcelHovered] = useState(false);
  const context = useMemo(() => explorationWorld(terrain, exaggeration, { worldSpanMeters: display?.worldSpanMeters, elevationOffset: display?.elevationOffset }), [terrain, exaggeration, display?.worldSpanMeters, display?.elevationOffset]);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const spacing = spacingAxes(terrain.cellSizeMeters);
  const { min, max, validCount } = useMemo(() => {
    let min = Infinity, max = -Infinity, validCount = 0;
    for (const value of terrain.heights) {
      if (value === null) continue;
      min = Math.min(min, value); max = Math.max(max, value); validCount++;
    }
    return { min, max, validCount };
  }, [terrain]);
  const requestView = (mode: string) => setCameraAction(previous => ({ mode, revision: previous.revision + 1 }));
  return <section style={{ minWidth: 0 }}>
    <div className="terrain-canvas">
      <Canvas camera={{ position: [9, 9, 13], fov: 45 }} style={{ touchAction: "none" }}>
        <PlanetEnvironment key={surfaceBody ?? terrain.body} body={surfaceBody ?? terrain.body} immersive space />
        <CameraControls world={context} terrain={terrain} action={cameraAction} relief={max - min} exaggeration={exaggeration} elevationOffset={display?.elevationOffset ?? 0} syncKey={display?.syncKey} syncEnabled={display?.syncEnabled} displayWorldSpanMeters={display?.worldSpanMeters} />
        <TerrainMesh terrain={terrain} highlighted={parcelHovered} onHoverChange={setParcelHovered} verticalExaggeration={exaggeration} colorMode={colorMode} elevationOffset={display?.elevationOffset} colorRange={display?.colorRange} worldSpanMeters={display?.worldSpanMeters} onInspect={point => { const next = pointToInspection(point, terrain, display?.worldSpanMeters); setInspection(previous => sameInspection(previous, next) ? previous : next); }} />
        <ExplorationContext terrain={terrain} world={context} appearance={surfaceBody ?? terrain.body} overview highlighted={parcelHovered} />
        <OrbitingSpacecraft onDiscover={() => setAlien(value => !value)} discovered={alien} altitude={(max - min + (display?.elevationOffset ?? 0)) * context.scale * exaggeration + 3} radius={Math.max(context.width, context.depth) * 0.85 + 1} />
        {alien && <AlienEncounter world={context} />}
      </Canvas>
      <button className="overview-parcel" data-hovered={parcelHovered} aria-label={`Focus selected parcel: ${terrain.name}`}
        onMouseEnter={() => setParcelHovered(true)} onMouseLeave={() => setParcelHovered(false)} onFocus={() => setParcelHovered(true)} onBlur={() => setParcelHovered(false)} onClick={() => requestView("fit")}>
        <span className="overview-parcel-dot" /><span><strong>Selected parcel</strong><small>{terrain.name}</small></span><span aria-hidden="true">⌗</span>
      </button>
      {alien && <div className="alien-message" role="status"><span>UNKNOWN SIGNAL / 👽</span><strong>Greetings, Earthling. Nice parcel!</strong><button aria-label="Dismiss alien" onClick={() => setAlien(false)}>×</button></div>}
      <span className="overview-context-note">24 generated parcels · Decorative surroundings</span>
    </div>
    <div className="viewer-tools" aria-label={`${terrain.name} camera controls`}>
      <button title="Restore the default camera position" aria-label="Reset Camera" onClick={() => requestView("reset")}><span aria-hidden="true">↺</span> Reset</button>
      <button title="View terrain from directly above" aria-label="Top View" onClick={() => requestView("top")}><span aria-hidden="true">⊙</span> Top</button>
      <button title="Return to an angled perspective" aria-label="Perspective View" onClick={() => requestView("perspective")}><span aria-hidden="true">◈</span> Perspective</button>
      <button title="Fit the complete terrain in view" aria-label="Fit Terrain" onClick={() => requestView("fit")}><span aria-hidden="true">⌗</span> Fit</button>
      <button className="pov-launch" aria-label="Enter POV" onClick={() => setPov(true)}><span aria-hidden="true">◎</span> POV · Explore surface</button>
      {!display && <label>Surface <select value={colorMode} onChange={e => setColorMode(e.target.value as ColorMode)}><option value="surface">Planet surface</option><option value="Mars">Mars regolith</option><option value="Moon">Lunar regolith</option><option value="Earth">Earth terrain</option><option value="elevation">Elevation gradient</option><option value="neutral">Neutral shaded</option></select></label>}
    </div>
    {destinations.error && <p role="alert">POV destinations: {destinations.error}</p>}
    {surfaceBody && <p className="surface-disclaimer">{surfaceBody} surface · Artistic material; elevation data unchanged.</p>}
    {pov && <TerrainExplorer terrain={terrain} destinations={destinations.terrains} exaggeration={exaggeration} onClose={closePov} />}
    <label style={{ display: "block", marginTop: 7 }}>Vertical exaggeration: <output>{exaggeration.toFixed(1)}×</output>
      {!display && <input aria-label="Vertical exaggeration" type="range" min="0.5" max="5" step="0.1" value={exaggeration} onChange={e => setExaggeration(Number(e.target.value))} />}
    </label>
    <small>Visualization setting only; measured elevations are unchanged. Left-drag rotates · Right-drag pans · Scroll zooms</small>
    <div aria-label="Elevation legend" style={{ marginTop: 6 }}><small>Elevation (m): {min.toFixed(2)} <span style={{ color: "#d98845" }}>━━━━</span> {max.toFixed(2)}</small></div>
    <div className="terrain-summary"><div><strong>{terrain.name}</strong><span>{terrain.body} · {terrain.dataType === "synthetic" ? "Synthetic dataset" : "Real dataset"}</span></div><div className="synthetic-chip">{terrain.dataType === "synthetic" ? "SYNTHETIC" : "REAL"}</div></div><h3 className="sr-only">{terrain.name} {terrain.dataType === "synthetic" ? "(SYNTHETIC DEMO — NOT NASA DATA)" : "(REAL DATA)"}</h3>
    <div className="terrain-stats"><div><small>Elevation range</small><strong>{min.toFixed(2)} to {max.toFixed(2)} m</strong></div><div><small>Relief</small><strong>{(max - min).toFixed(2)} m</strong></div><div><small>Valid data</small><strong>{(100 * validCount / (terrain.width * terrain.height)).toFixed(2)}%</strong></div></div>
    {inspection && <div role="status"><strong>Elevation inspection</strong>: {inspection.elevation.toFixed(2)} m · local coordinates X {inspection.x.toFixed(2)} m, Y {inspection.y.toFixed(2)} m · {terrain.name} · {terrain.body}</div>}
    <Metadata terrain={terrain} spacing={spacing} exaggeration={exaggeration} valid={validCount} />
  </section>;
}

function Metadata({ terrain, spacing, exaggeration, valid }: { terrain: ValidatedTerrainData; spacing: { x: number; y: number }; exaggeration: number; valid: number }) {
  const provenance = terrain.processingMetadata?.provenance;
  return <details className="terrain-metadata"><summary>Scientific details</summary><div className="metadata-grid"><small>
    Terrain: {terrain.name}<br />Body: {terrain.body}<br />Data type: {terrain.dataType === "synthetic" ? "SYNTHETIC DEMO — NOT NASA DATA" : "Real dataset"}<br />Source: {terrain.source || "Not provided"}<br />Source resolution: {formatSpacing(terrain.resolutionMeters)} m<br />Display spacing: {spacing.x} × {spacing.y} m<br />Window: {terrain.horizontalWindowMeters.width} × {terrain.horizontalWindowMeters.height} m<br />Vertical datum: {terrain.verticalDatum || "Not provided"}<br />CRS: {terrain.coordinateReferenceSystem || "Not provided"}<br />Valid data: {(100 * valid / (terrain.width * terrain.height)).toFixed(2)}%<br />Vertical exaggeration: {exaggeration.toFixed(1)}×<br />{provenance ? <>Dataset: {provenance.dataset}<br />Product: {provenance.productId} · Version: {provenance.version}<br />Provenance: {provenance.url}</> : terrain.dataType === "real" ? "Provenance: Not provided" : null}
  </small></div></details>;
}
function formatSpacing(value: number | { x: number; y: number }): string { return typeof value === "number" ? `${value}` : `${value.x} × ${value.y}`; }
type Inspection = { elevation: number; x: number; y: number };
function sameInspection(a: Inspection | null, b: Inspection | null): boolean { return a === b || (!!a && !!b && a.elevation === b.elevation && a.x === b.x && a.y === b.y); }
function pointToInspection(point: THREE.Vector3, terrain: ValidatedTerrainData, worldSpanMeters?: number): Inspection | null {
  if (!Number.isFinite(point.x) || !Number.isFinite(point.z)) return null;
  const s = spacingAxes(terrain.cellSizeMeters); const scale = 10 / (worldSpanMeters ?? Math.max((terrain.width - 1) * s.x, (terrain.height - 1) * s.y));
  const col = Math.round(point.x / (s.x * scale) + (terrain.width - 1) / 2), row = Math.round(point.z / (s.y * scale) + (terrain.height - 1) / 2);
  if (row < 0 || col < 0 || row >= terrain.height || col >= terrain.width) return null;
  const elevation = terrain.heights[row * terrain.width + col]; if (elevation === null) return null;
  return { elevation, x: (col - (terrain.width - 1) / 2) * s.x, y: (row - (terrain.height - 1) / 2) * s.y };
}

function CameraControls({ world, terrain, action, relief, exaggeration, elevationOffset, syncKey, syncEnabled, displayWorldSpanMeters }: { world: ReturnType<typeof explorationWorld>; terrain: ValidatedTerrainData; action: { mode: string; revision: number }; relief: number; exaggeration: number; elevationOffset: number; syncKey?: string; syncEnabled?: boolean; displayWorldSpanMeters?: number }) {
  const controls = useRef<any>(null); const syncApplying = useRef(false); const { camera, gl, size } = useThree();
  const spacing = spacingAxes(terrain.cellSizeMeters); const span = Math.max((terrain.width - 1) * spacing.x, (terrain.height - 1) * spacing.y);
  const publishInspectionState = () => {
    if (!window.location.pathname.startsWith("/tests/") || !controls.current) return;
    const states = ((window as Window & { __terrain3dCameraStates?: Record<string, { position: number[]; target: number[] }> }).__terrain3dCameraStates ??= {});
    states[terrain.id] = { position: camera.position.toArray(), target: controls.current.target.toArray() };
  };
  const setView = (mode: string) => {
    // Clear pending orbit/pan damping before applying an explicit camera command.
    if (controls.current) {
      controls.current.enableDamping = false;
      controls.current.update();
      controls.current.enableDamping = true;
    }
    const scale = 10 / (displayWorldSpanMeters ?? span);
    const height = relief * scale * exaggeration;
    const target = new THREE.Vector3(0, (relief / 2 + elevationOffset) * scale * exaggeration, 0);
    const radius = Math.hypot(terrain.horizontalWindowMeters.width * scale, height, terrain.horizontalWindowMeters.height * scale) / 2;
    const verticalFov = THREE.MathUtils.degToRad((camera as THREE.PerspectiveCamera).fov);
    const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * size.width / size.height);
    const fitDistance = Math.max(2, radius / Math.sin(Math.min(verticalFov, horizontalFov) / 2) * 1.15);
    const direction = mode === "top" ? new THREE.Vector3(0, 1, 0.0001) : mode === "fit" ? camera.position.clone().sub(controls.current?.target ?? target).normalize() : new THREE.Vector3(0.7, 0.7, 1).normalize();
    camera.position.copy(target).addScaledVector(direction, fitDistance);
    camera.near = Math.max(0.001, fitDistance / 1000);
    camera.far = Math.max(1000, fitDistance * 20);
    camera.updateProjectionMatrix();
    camera.lookAt(target);
    if (controls.current) {
      controls.current.target.copy(target);
      controls.current.minDistance = Math.max(0.1, radius * 0.1);
      controls.current.maxDistance = fitDistance * 8;
      controls.current.update();
    }
  };
  useEffect(() => { setView(action.mode); }, [action, terrain, displayWorldSpanMeters, size.width, size.height]);
  useEffect(() => { const timer = window.setTimeout(publishInspectionState, 250); return () => window.clearTimeout(timer); }, [terrain.id]);
  const guardCamera = () => {
    keepOverviewAboveGround(camera.position, world, Math.max(0.15, camera.near * 2));
    if (controls.current) camera.lookAt(controls.current.target);
  };
  useFrame(() => { guardCamera(); publishInspectionState(); });
  useEffect(() => {
    if (!syncEnabled || !syncKey) return;
    const receive = (event: Event) => { const detail = (event as CustomEvent<{ key: string; source: string; position: number[]; target: number[] }>).detail; if (detail.key !== syncKey || detail.source === terrain.id) return; syncApplying.current = true; camera.position.fromArray(detail.position); camera.lookAt(new THREE.Vector3().fromArray(detail.target)); if (controls.current) { controls.current.target.fromArray(detail.target); controls.current.update(); } syncApplying.current = false; };
    window.addEventListener("terrain-camera-sync", receive); return () => window.removeEventListener("terrain-camera-sync", receive);
  }, [syncEnabled, syncKey, terrain.id, camera]);
  return <OrbitControls ref={controls} maxPolarAngle={Math.PI / 2 - 0.08} onChange={() => { guardCamera(); publishInspectionState(); if (syncEnabled && syncKey && !syncApplying.current && controls.current) window.dispatchEvent(new CustomEvent("terrain-camera-sync", { detail: { key: syncKey, source: terrain.id, position: camera.position.toArray(), target: controls.current.target.toArray() } })); }} domElement={gl.domElement} makeDefault enabled enableRotate enablePan enableZoom enableDamping dampingFactor={0.08} screenSpacePanning={false} mouseButtons={{ LEFT: MOUSE.ROTATE, MIDDLE: MOUSE.DOLLY, RIGHT: MOUSE.PAN }} />;
}
