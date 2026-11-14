import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { TerrainComparison, type TerrainDataJSON } from "../src";

function Harness() {
  const [data, setData] = useState<[TerrainDataJSON, TerrainDataJSON] | null>(null);
  useEffect(() => { Promise.all([fetch("/terrain/mars_demo.json").then(r => r.json()), fetch("/terrain/earth_demo.json").then(r => r.json())]).then(value => setData(value as [TerrainDataJSON, TerrainDataJSON])); }, []);
  return data ? <TerrainComparison target={data[0]} analog={data[1]} /> : <p role="status">Loading comparison</p>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><Harness /></React.StrictMode>);
