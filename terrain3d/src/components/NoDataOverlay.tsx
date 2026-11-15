import { useEffect, useMemo } from "react";
import * as THREE from "three";
import type { TerrainData } from "../types/terrain";
import { createNoDataGeometry } from "../geometry/noDataGeometry";

/** Unlit hatching explains missing samples without adding inspectable/walkable elevations. */
export function NoDataOverlay({ terrain, verticalExaggeration, elevationOffset, worldSpanMeters }: {
  terrain: TerrainData; verticalExaggeration?: number; elevationOffset?: number; worldSpanMeters?: number;
}) {
  const geometry = useMemo(() => createNoDataGeometry(terrain, { verticalExaggeration, elevationOffset, worldSpanMeters }), [terrain, verticalExaggeration, elevationOffset, worldSpanMeters]);
  useEffect(() => () => geometry?.dispose(), [geometry]);
  const uniforms = useMemo(() => ({ base: { value: new THREE.Color("#59594f") }, ink: { value: new THREE.Color("#b6b09b") } }), []);
  if (!geometry) return null;
  return <mesh geometry={geometry} raycast={() => {}} name="nodata-reference-overlay">
    <shaderMaterial side={THREE.DoubleSide} uniforms={uniforms}
      vertexShader={`varying vec2 vFootprint;
        void main() { vFootprint = position.xz; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`}
      fragmentShader={`uniform vec3 base; uniform vec3 ink; varying vec2 vFootprint;
        void main() {
          float phase = (vFootprint.x + vFootprint.y) * 16.0;
          float stripe = abs(fract(phase) - 0.5);
          float aa = min(0.2, fwidth(phase));
          float hatch = 1.0 - smoothstep(0.05, 0.05 + max(aa, 0.001), stripe);
          gl_FragColor = vec4(mix(base, ink, hatch * 0.7), 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`} />
  </mesh>;
}
