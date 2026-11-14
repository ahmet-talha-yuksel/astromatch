import React from "react";
import { createRoot } from "react-dom/client";
import { TerrainComparison, type TerrainData } from "../src";
import "./style.css";

function synthetic(name: string, body: TerrainData["body"], offset: number): TerrainData {
  const width = 64, height = 64;
  const elevationsMeters = Array.from({ length: width * height }, (_, i) => {
    const x = (i % width - width / 2) / 10;
    const y = (Math.floor(i / width) - height / 2) / 10;
    return 250 * Math.exp(-((x - offset) ** 2 + y ** 2) / 5) +
      70 * Math.sin(x * 1.7 + offset) * Math.cos(y * 1.3);
  });
  return { id: name, name, body, width, height, cellSizeMeters: 100,
    elevationsMeters, source: "Procedurally generated demo (NOT NASA)", isSynthetic: true };
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode><main>
    <h1>AstroMatch AI — Terrain3D Module</h1>
    <p>Standalone integration demo. Both surfaces are synthetic; replace with processed DEM data.</p>
    <TerrainComparison target={synthetic("Mars target demo", "Mars", 0)}
      analog={synthetic("Earth analog demo", "Earth", 1)} />
  </main></React.StrictMode>
);
