import React from "react";
import { createRoot } from "react-dom/client";
import { TerrainComparison, type TerrainDataJSON } from "../src";

function provingGround(body:TerrainDataJSON["body"]):TerrainDataJSON {
  const n=161,span=40,spacing=span/(n-1);
  const heights=Array.from({length:n*n},(_,i)=>{
    const x=(i%n)/(n-1)*span-span/2,z=Math.floor(i/n)/(n-1)*span-span/2;
    const ramp=z < -1 && z > -6 ? .35*Math.sin((z+1)/5*Math.PI)**2:0;
    return ramp + .07*Math.exp(-((x-1.1)**2+(z+2)**2)/.05);
  });
  return {id:`rover-lab-${body}`,name:`${body} rover proving ground`,body,width:n,height:n,heights,
    cellSizeMeters:spacing,resolutionMeters:spacing,verticalExaggeration:1,horizontalWindowMeters:{width:span,height:span},
    dataType:"synthetic",source:"Known synthetic ramps and wheel articulation bump; NOT NASA terrain",verticalDatum:"Synthetic zero",coordinateReferenceSystem:"Synthetic local metric frame"};
}
const mars=provingGround("Mars"),earth=provingGround("Earth"),moon=provingGround("Moon");
createRoot(document.getElementById("root")!).render(<React.StrictMode><TerrainComparison target={mars} analog={earth} explorationTerrains={[moon]} /></React.StrictMode>);
