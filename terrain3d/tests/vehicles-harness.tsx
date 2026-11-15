import React from "react";
import { createRoot } from "react-dom/client";
import { TerrainComparison } from "../src";
import { synthetic } from "../demo/terrains";

const target = synthetic("Mars flight practice", "Mars");
const analog = synthetic("Earth flight practice", "Earth");
const moon = synthetic("Moon flight practice", "Moon");
createRoot(document.getElementById("root")!).render(<React.StrictMode>
  <TerrainComparison target={target} analog={analog} explorationTerrains={[moon]} />
</React.StrictMode>);
