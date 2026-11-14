import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bounds, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { MOUSE } from "three";
import { useEffect, useMemo, useRef, useState } from "react";
import { TerrainMesh } from "./TerrainMesh";
import type { TerrainData, ValidatedTerrainData } from "../types/terrain";
import { spacingAxes, validateTerrainData } from "../validation/terrain";
import { loadTerrain } from "../loading/loadTerrain";

export type TerrainViewerProps =
  | { terrain: TerrainData; terrainUrl?: never; display?: TerrainDisplay }
  | { terrainUrl: string; terrain?: never; display?: TerrainDisplay };
export interface TerrainDisplay { exaggeration?: number; colorMode?: "elevation" | "neutral"; elevationOffset?: number; colorRange?: { min: number; max: number }; worldSpanMeters?: number; syncKey?: string; syncEnabled?: boolean }
type TerrainState = { terrain: ValidatedTerrainData; error?: never } | { terrain?: never; error: string };
type ColorMode = "elevation" | "neutral";
function errorMessage(error: unknown): string { return error instanceof Error ? error.message : String(error); }

export function TerrainViewer(props: TerrainViewerProps) {
  if (props.terrainUrl !== undefined) return <TerrainUrlViewer key={props.terrainUrl} url={props.terrainUrl} display={props.display} />;
  return <TerrainObjectViewer terrain={props.terrain} display={props.display} />;
}
function TerrainObjectViewer({ terrain, display }: { terrain: TerrainData; display?: TerrainDisplay }) {
  const state = useMemo<TerrainState>(() => { try { return { terrain: validateTerrainData(terrain) }; } catch (e) { return { error: errorMessage(e) }; } }, [terrain]);
  return state.terrain ? <TerrainScene terrain={state.terrain} display={display} /> : <p role="alert">{state.error}</p>;
}
function TerrainUrlViewer({ url, display }: { url: string; display?: TerrainDisplay }) {
  const [state, setState] = useState<TerrainState | null>(null);
  useEffect(() => { const controller = new AbortController(); let active = true;
    loadTerrain(url, controller.signal).then(t => { if (active) setState({ terrain: t }); }, e => { if (active) setState({ error: errorMessage(e) }); });
    return () => { active = false; controller.abort(); };
  }, [url]);
  if (!state) return <p role="status">Loading terrain…</p>;
  return state.terrain ? <TerrainScene terrain={state.terrain} display={display} /> : <p role="alert">{url}: {state.error}</p>;
}

function TerrainScene({ terrain, display }: { terrain: ValidatedTerrainData; display?: TerrainDisplay }) {
  const [localExaggeration, setExaggeration] = useState(terrain.verticalExaggeration);
  const [localColorMode, setColorMode] = useState<ColorMode>("elevation");
  const exaggeration = display?.exaggeration ?? localExaggeration;
  const colorMode = display?.colorMode ?? localColorMode;
  const [cameraAction, setCameraAction] = useState("perspective");
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const spacing = spacingAxes(terrain.cellSizeMeters);
  const valid = terrain.heights.filter((h): h is number => h !== null);
  const min = Math.min(...valid), max = Math.max(...valid);
  return <section style={{ minWidth: 0 }}>
    <div className="terrain-canvas">
      <Canvas camera={{ position: [9, 9, 13], fov: 45 }} style={{ touchAction: "none" }}>
        <ambientLight intensity={1.3} /><directionalLight position={[5, 12, 8]} intensity={2} />
        <CameraControls terrain={terrain} action={cameraAction} syncKey={display?.syncKey} syncEnabled={display?.syncEnabled} displayWorldSpanMeters={display?.worldSpanMeters} />
        <Bounds key={terrain.id} fit observe margin={1.6}><TerrainMesh terrain={terrain} verticalExaggeration={exaggeration} colorMode={colorMode} elevationOffset={display?.elevationOffset} colorRange={display?.colorRange} worldSpanMeters={display?.worldSpanMeters} onInspect={point => { const next = pointToInspection(point, terrain, display?.worldSpanMeters); setInspection(previous => sameInspection(previous, next) ? previous : next); }} /></Bounds>
        <gridHelper args={[14, 14, "#586778", "#263446"]} position={[0, -0.1, 0]} />
      </Canvas>
    </div>
    <div className="viewer-tools" aria-label={`${terrain.name} camera controls`}>
      <button title="Restore the default camera position" aria-label="Reset Camera" onClick={() => setCameraAction("reset")}><span aria-hidden="true">↺</span> Reset</button>
      <button title="View terrain from directly above" aria-label="Top View" onClick={() => setCameraAction("top")}><span aria-hidden="true">⊙</span> Top</button>
      <button title="Return to an angled perspective" aria-label="Perspective View" onClick={() => setCameraAction("perspective")}><span aria-hidden="true">◈</span> Perspective</button>
      <button title="Fit the complete terrain in view" aria-label="Fit Terrain" onClick={() => setCameraAction("fit")}><span aria-hidden="true">⌗</span> Fit</button>
      {!display && <label>Color mode <select value={colorMode} onChange={e => setColorMode(e.target.value as ColorMode)}><option value="elevation">Elevation gradient</option><option value="neutral">Neutral shaded</option></select></label>}
    </div>
    <label style={{ display: "block", marginTop: 7 }}>Vertical exaggeration: <output>{exaggeration.toFixed(1)}×</output>
      {!display && <input aria-label="Vertical exaggeration" type="range" min="0.5" max="5" step="0.1" value={exaggeration} onChange={e => setExaggeration(Number(e.target.value))} />}
    </label>
    <small>Visualization setting only; measured elevations are unchanged. Left-drag rotates · Right-drag pans · Scroll zooms</small>
    <div aria-label="Elevation legend" style={{ marginTop: 6 }}><small>Elevation (m): {min.toFixed(2)} <span style={{ color: "#d98845" }}>━━━━</span> {max.toFixed(2)}</small></div>
    <div className="terrain-summary"><div><strong>{terrain.name}</strong><span>{terrain.body} · {terrain.dataType === "synthetic" ? "Synthetic dataset" : "Real dataset"}</span></div><div className="synthetic-chip">{terrain.dataType === "synthetic" ? "SYNTHETIC" : "REAL"}</div></div><h3 className="sr-only">{terrain.name} {terrain.dataType === "synthetic" ? "(SYNTHETIC DEMO — NOT NASA DATA)" : "(REAL DATA)"}</h3>
    <div className="terrain-stats"><div><small>Elevation range</small><strong>{min.toFixed(2)} to {max.toFixed(2)} m</strong></div><div><small>Relief</small><strong>{(max - min).toFixed(2)} m</strong></div><div><small>Valid data</small><strong>{(100 * valid.length / (terrain.width * terrain.height)).toFixed(2)}%</strong></div></div>
    {inspection && <div role="status"><strong>Elevation inspection</strong>: {inspection.elevation.toFixed(2)} m · local coordinates X {inspection.x.toFixed(2)} m, Y {inspection.y.toFixed(2)} m · {terrain.name} · {terrain.body}</div>}
    <Metadata terrain={terrain} spacing={spacing} exaggeration={exaggeration} valid={valid.length} />
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

function CameraControls({ terrain, action, syncKey, syncEnabled, displayWorldSpanMeters }: { terrain: ValidatedTerrainData; action: string; syncKey?: string; syncEnabled?: boolean; displayWorldSpanMeters?: number }) {
  const controls = useRef<any>(null); const syncApplying = useRef(false); const { camera, gl } = useThree();
  const spacing = spacingAxes(terrain.cellSizeMeters); const span = Math.max((terrain.width - 1) * spacing.x, (terrain.height - 1) * spacing.y); const normalizedSpan = span * (10 / (displayWorldSpanMeters ?? span)); const distance = Math.max(8, Math.min(40, normalizedSpan * 1.65));
  const publishInspectionState = () => {
    if (!window.location.pathname.startsWith("/tests/") || !controls.current) return;
    const states = ((window as Window & { __terrain3dCameraStates?: Record<string, { position: number[]; target: number[] }> }).__terrain3dCameraStates ??= {});
    states[terrain.id] = { position: camera.position.toArray(), target: controls.current.target.toArray() };
  };
  const setView = (mode: string) => { const target = new THREE.Vector3(0, 0, 0); const position = mode === "top" ? new THREE.Vector3(0, distance, 0.001) : new THREE.Vector3(distance * 0.7, distance * 0.7, distance); camera.position.copy(position); camera.lookAt(target); if (controls.current) { controls.current.target.copy(target); controls.current.minDistance = Math.max(2, distance * 0.15); controls.current.maxDistance = distance * 8; controls.current.update(); } };
  useEffect(() => { setView(action); }, [action, terrain.id]);
  useEffect(() => { const timer = window.setTimeout(publishInspectionState, 250); return () => window.clearTimeout(timer); }, [terrain.id]);
  useFrame(publishInspectionState);
  useEffect(() => {
    if (!syncEnabled || !syncKey) return;
    const receive = (event: Event) => { const detail = (event as CustomEvent<{ key: string; source: string; position: number[]; target: number[] }>).detail; if (detail.key !== syncKey || detail.source === terrain.id) return; syncApplying.current = true; camera.position.fromArray(detail.position); camera.lookAt(new THREE.Vector3().fromArray(detail.target)); if (controls.current) { controls.current.target.fromArray(detail.target); controls.current.update(); } syncApplying.current = false; };
    window.addEventListener("terrain-camera-sync", receive); return () => window.removeEventListener("terrain-camera-sync", receive);
  }, [syncEnabled, syncKey, terrain.id, camera]);
  return <OrbitControls ref={controls} onChange={() => { publishInspectionState(); if (syncEnabled && syncKey && !syncApplying.current && controls.current) window.dispatchEvent(new CustomEvent("terrain-camera-sync", { detail: { key: syncKey, source: terrain.id, position: camera.position.toArray(), target: controls.current.target.toArray() } })); }} domElement={gl.domElement} makeDefault enabled enableRotate enablePan enableZoom enableDamping dampingFactor={0.08} minDistance={Math.max(2, distance * 0.15)} maxDistance={distance * 8} screenSpacePanning mouseButtons={{ LEFT: MOUSE.ROTATE, MIDDLE: MOUSE.DOLLY, RIGHT: MOUSE.PAN }} />;
}
