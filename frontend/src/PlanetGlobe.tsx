import { useEffect, useRef } from "react";

type Phase = "idle" | "out" | "in";
const craters = Array.from({ length: 26 }, (_, i) => ({ longitude: i * 2.39996, latitude: Math.asin(-.85 + (i % 13) / 12 * 1.7), radius: 2 + i % 4 }));
const mix = (a: number[], b: number[], t: number) => `rgb(${a.map((n, i) => Math.round(n + (b[i] - n) * t)).join(",")})`;

/** Project surface details onto a sphere; its silhouette and light stay fixed as it spins. */
export function PlanetGlobe({ body, phase, onPhaseEnd }: { body: string; phase: Phase; onPhaseEnd: () => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const complete = useRef(onPhaseEnd);
  complete.current = onPhaseEnd;
  useEffect(() => {
    const ctx = canvas.current?.getContext("2d");
    if (!ctx) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    let start: number | null = null;
    const paint = (progress: number) => {
      const transition = phase === "out" ? progress / 2 : phase === "in" ? .5 + progress / 2 : 1;
      const toMars = phase === "out" ? body !== "mars" : body === "mars";
      const warm = phase === "idle" ? Number(body === "mars") : toMars ? transition : 1 - transition;
      const angle = phase === "out" ? progress * Math.PI : phase === "in" ? Math.PI + progress * Math.PI : 0;
      ctx.clearRect(0, 0, 128, 128);
      ctx.save(); ctx.beginPath(); ctx.arc(64, 64, 54, 0, 2 * Math.PI); ctx.clip();
      ctx.fillStyle = mix([179, 188, 204], [204, 119, 77], warm); ctx.fillRect(0, 0, 128, 128);
      for (const crater of craters) {
        const longitude = crater.longitude + angle;
        const depth = Math.cos(crater.latitude) * Math.cos(longitude);
        if (depth <= 0) continue;
        const x = 64 + 54 * Math.cos(crater.latitude) * Math.sin(longitude);
        const y = 64 + 54 * Math.sin(crater.latitude);
        ctx.save(); ctx.translate(x, y);
        ctx.rotate(Math.atan2(y - 64, x - 64));
        ctx.scale(Math.max(.06, depth), 1);
        const size = crater.radius * (1 + warm * .35);
        const shade = ctx.createRadialGradient(-size / 3, -size / 3, 0, 0, 0, size);
        shade.addColorStop(0, mix([84, 98, 122], [121, 57, 37], warm));
        shade.addColorStop(.8, mix([145, 158, 180], [173, 87, 53], warm));
        shade.addColorStop(1, mix([207, 213, 221], [219, 139, 91], warm));
        ctx.globalAlpha = .72; ctx.fillStyle = shade;
        ctx.beginPath(); ctx.arc(0, 0, size, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      }
      // Stationary illumination makes the moving details read as an axial rotation.
      const lighting = ctx.createRadialGradient(39, 32, 5, 56, 53, 71);
      lighting.addColorStop(0, "rgba(255,245,225,.35)");
      lighting.addColorStop(.48, "rgba(12,18,35,0)");
      lighting.addColorStop(.83, "rgba(5,10,24,.48)");
      lighting.addColorStop(1, "rgba(3,7,20,.95)");
      ctx.fillStyle = lighting; ctx.fillRect(0, 0, 128, 128); ctx.restore();
    };
    if (phase === "idle") { paint(1); return; }
    const tick = (time: number) => {
      if (start === null) start = time;
      const progress = reduced ? 1 : Math.min(1, (time - start) / 600);
      paint(progress);
      if (progress < 1) frame = requestAnimationFrame(tick);
      else complete.current();
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [body, phase]);
  return <canvas ref={canvas} width="128" height="128" className="planet-globe" aria-hidden="true" />;
}
