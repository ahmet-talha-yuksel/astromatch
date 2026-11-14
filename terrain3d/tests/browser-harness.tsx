import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { TerrainViewer } from "../src";

function Harness() {
  const [url, setUrl] = useState("/terrain/mars_demo.json");
  return <main>
    <label>Terrain URL <input value={url} onChange={event => setUrl(event.target.value)} /></label>
    <TerrainViewer terrainUrl={url} />
  </main>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><Harness /></React.StrictMode>);
