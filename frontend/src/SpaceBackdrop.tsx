import { useEffect, useRef, useState, type CSSProperties } from "react";

type Meteor = { id: number; x: number; y: number; dx: number; dy: number; angle: number; duration: number; length: number };
const random = (min: number, max: number) => min + Math.random() * (max - min);

/** Decorative, bounded animation; never participates in terrain camera events. */
export function SpaceBackdrop({ enabled }: { enabled: boolean }) {
  const [meteors, setMeteors] = useState<Meteor[]>([]);
  const [running, setRunning] = useState(false);
  const sequence = useRef(0);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let timer: number | undefined;
    const expirations = new Set<number>();
    const spawn = () => {
      const id = sequence.current++;
      const angle = random(130, 155);
      const distance = random(220, 520);
      const meteor = {
        id, x: random(22, 104),
        // Alternate visible sky above the panels with the wider background.
        y: id % 2 === 0 ? random(7, 24) : random(18, 85),
        dx: Math.cos(angle * Math.PI / 180) * distance,
        dy: Math.sin(angle * Math.PI / 180) * distance,
        angle, duration: random(1.6, 2.8), length: random(85, 180),
      };
      setMeteors(current => [...current.slice(-7), meteor]);
      const expiry = window.setTimeout(() => {
        setMeteors(current => current.filter(item => item.id !== id));
        expirations.delete(expiry);
      }, meteor.duration * 1000 + 100);
      expirations.add(expiry);
    };
    const tick = () => {
      spawn();
      if (Math.random() > 0.6) spawn();
      timer = window.setTimeout(tick, random(650, 1250));
    };
    const sync = () => {
      window.clearTimeout(timer);
      expirations.forEach(window.clearTimeout);
      expirations.clear();
      setMeteors([]);
      const active = enabled && !preference.matches && !document.hidden;
      setRunning(active);
      if (active) { spawn(); tick(); }
    };
    sync();
    preference.addEventListener("change", sync);
    document.addEventListener("visibilitychange", sync);
    return () => {
      window.clearTimeout(timer);
      expirations.forEach(window.clearTimeout);
      preference.removeEventListener("change", sync);
      document.removeEventListener("visibilitychange", sync);
    };
  }, [enabled]);

  return <div className={`starfield ${running ? "" : "space-paused"}`} aria-hidden="true">
    <div className="space-glow" />
    <div className="stars stars-far" /><div className="stars stars-near" />
    {meteors.map(meteor => <span key={meteor.id} className="meteor" style={{
      left: `${meteor.x}%`, top: `${meteor.y}%`, width: meteor.length,
      "--dx": `${meteor.dx}px`, "--dy": `${meteor.dy}px`, "--angle": `${meteor.angle}deg`,
      animationDuration: `${meteor.duration}s`,
    } as CSSProperties} />)}
    {running && <div className="apollo-flight">
      <div className="apollo-craft">
        <svg viewBox="0 0 320 82" width="210" height="54" fill="none">
          <defs>
            <linearGradient id="rocket-metal" x1="0" y1="12" x2="0" y2="70" gradientUnits="userSpaceOnUse"><stop stopColor="#6d809d" /><stop offset=".42" stopColor="#f1f5ff" /><stop offset="1" stopColor="#7185a5" /></linearGradient>
            <linearGradient id="rocket-plume"><stop stopColor="#88baff" stopOpacity="0" /><stop offset=".65" stopColor="#a6cdff" stopOpacity=".45" /><stop offset="1" stopColor="#fff" /></linearGradient>
          </defs>
          {/* Stylized Saturn V / Apollo tribute, decorative rather than a scale model. */}
          <path className="rocket-exhaust" d="M0 41L80 31V51Z" fill="url(#rocket-plume)" />
          <path d="M76 27L88 30V52L76 55Z" fill="#596e90" />
          <path d="M85 22H210L243 29V53L210 60H85Z" fill="url(#rocket-metal)" />
          <path d="M88 22L71 10H101L119 22M88 60L71 72H101L119 60" fill="#8596b3" />
          <path d="M107 22H119V60H107ZM173 22H183V60H173Z" fill="#172844" />
          <path d="M210 22L243 29V53L210 60Z" stroke="#b6c6e0" />
          <path d="M243 29H265L287 41L265 53H243Z" fill="url(#rocket-metal)" />
          <path d="M287 41H311" stroke="#cbdcf6" strokeWidth="2" />
          <path d="M286 35L299 41L286 47" stroke="#cbdcf6" />
          <path d="M135 26H148V33H135Z" fill="#fc3d21" />
          <text x="128" y="46" fill="#152843" fontSize="8" fontFamily="monospace" letterSpacing="1">USA</text>
          <path d="M88 26H100M88 30H100M88 34H100M88 38H100M88 42H100M88 46H100M88 50H100M88 54H100" stroke="#415574" strokeWidth="1" />
        </svg>
        <span className="apollo-caption">APOLLO 11 <i /> 1969</span>
      </div>
    </div>}
  </div>;
}
