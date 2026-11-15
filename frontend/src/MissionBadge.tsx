import { useState } from "react";
import { PlanetGlobe } from "./PlanetGlobe";

export function MissionBadge({ body, onToggle, disabled = false }: { body: string; onToggle: () => void; disabled?: boolean }) {
  const [phase, setPhase] = useState<"idle" | "out" | "in">("idle");
  const [discovered, setDiscovered] = useState(false);
  const mars = body === "mars";
  return <button type="button" className={`mission-badge phase-${phase} ${discovered ? "discovered" : ""}`}
    disabled={disabled || phase !== "idle"} onClick={() => { setDiscovered(false); setPhase("out"); }}
    aria-label={mars ? "Switch to Moon" : "Switch to Mars"} aria-busy={phase !== "idle"}>
    <PlanetGlobe body={body} phase={phase} onPhaseEnd={() => {
      if (phase === "out") { onToggle(); setPhase("in"); }
      if (phase === "in") { setPhase("idle"); setDiscovered(true); }
    }} />
    <span className="mission-copy"><span className="mission-eyebrow">{mars ? "MARS MISSION" : "LUNAR MISSION"}</span>
      <strong>{mars ? "Following the red planet" : "Tracing silent craters"}</strong>
      <span className="mission-secret">{phase !== "idle" ? "Changing course…" : mars ? "Tap to explore the Moon ↻" : "Tap to explore Mars ↻"}</span>
    </span>
    {discovered && <span className="mission-easter" aria-live="polite">
      <svg viewBox="0 0 78 32" aria-hidden="true">
        {mars ? <g stroke="currentColor" fill="none" strokeWidth="1.6"><path d="M20 22H58M27 19L29 11H48L52 19M40 11V4H47M34 15H44"/><circle cx="28" cy="25" r="3"/><circle cx="40" cy="25" r="3"/><circle cx="52" cy="25" r="3"/><path d="M2 29H20" strokeDasharray="3 3"/></g> : <g stroke="currentColor" strokeWidth="1.7" fill="none"><circle cx="26" cy="7" r="5"/><path d="M22 13H30L32 23H21ZM22 15L15 19M30 15L41 12M23 23L20 30M29 23L33 30M42 4V30M42 4H56L52 9L56 13H42"/><path d="M3 27L6 25M10 30L13 28M62 29L65 27" strokeWidth="2.6"/></g>}
      </svg><span>{mars ? "A little rover is on its way." : "One small step left a mark."}</span>
    </span>}
  </button>;
}

export function ScoreRing({ score, color, label }: { score: number; color: string; label: string }) {
  const percent = Math.max(0, Math.min(100, score));
  return <span className="score-ring" role="img" aria-label={`Topographic similarity: ${label}%`}>
    <svg viewBox="0 0 64 64" aria-hidden="true"><circle className="ring-track" cx="32" cy="32" r="27" /><circle className="ring-fill" cx="32" cy="32" r="27" pathLength="100" stroke={color} strokeDasharray="100" strokeDashoffset={100 - percent} /></svg>
    <strong style={{ color }}>{label}<small>%</small></strong>
  </span>;
}
