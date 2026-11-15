import type { TerrainDataJSON } from "../src";

// Explicitly synthetic landscapes for demonstrating the renderer, not measured DEMs.
export function synthetic(name: string, body: TerrainDataJSON["body"]): TerrainDataJSON {
  const width = 144, height = 144, span = 6300;
  const random = (i: number) => { const n = Math.sin(i * 127.1 + 311.7) * 43758.5453; return n - Math.floor(n); };
  const craters = Array.from({ length: body === "Moon" ? 19 : 5 }, (_, i) => ({
    x: (random(i * 3) - 0.5) * 5.8, y: (random(i * 3 + 1) - 0.5) * 5.8,
    radius: 0.22 + random(i * 3 + 2) * 0.6,
  }));
  const heights = Array.from({ length: width * height }, (_, i) => {
    const x = (i % width / (width - 1) - 0.5) * 6.3;
    const y = (Math.floor(i / width) / (height - 1) - 0.5) * 6.3;
    const detail = 11 * Math.sin(x * 18 + Math.sin(y * 9)) * Math.cos(y * 15) + 5 * Math.sin(x * 41) * Math.cos(y * 36);
    if (body === "Earth") return 280 * Math.exp(-((x + 0.5) ** 2 + (y + 0.7) ** 2) / 3)
      + 140 * Math.sin(x * 2.2 + Math.sin(y * 1.4)) * Math.cos(y * 1.7) + 45 * Math.sin(x * 5.2) * Math.cos(y * 4.1) + detail;
    let h = body === "Mars" ? 190 * Math.exp(-((x - 0.6) ** 2 + (y + 0.7) ** 2) / 2)
      + 80 * Math.sin(x * 2.6 + y * 0.4) * Math.cos(y * 1.8) + 25 * Math.sin(x * 7 + y * 2) : 30 * Math.sin(x * 2) * Math.cos(y * 2.7);
    for (const crater of craters) {
      const d = Math.hypot(x - crater.x, y - crater.y) / crater.radius;
      h += crater.radius * (100 * Math.exp(-((d - 1) ** 2) * 32) - 210 * Math.max(0, 1 - d * d));
    }
    return h + detail * (body === "Moon" ? 0.7 : 1);
  });
  const spacing = span / (width - 1);
  return { id: name, name, body, width, height, cellSizeMeters: spacing, heights,
    source: "Procedurally generated landscape demo (NOT NASA)", dataType: "synthetic", resolutionMeters: spacing,
    horizontalWindowMeters: { width: span, height: span }, verticalDatum: "Synthetic local elevation reference", coordinateReferenceSystem: "Synthetic local metric grid" };
}
