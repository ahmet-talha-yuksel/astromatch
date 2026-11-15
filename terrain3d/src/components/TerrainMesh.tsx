import { useEffect, useMemo } from "react";
import * as THREE from "three";
import type { TerrainData } from "../types/terrain";
import { NoDataOverlay } from "./NoDataOverlay";
import { createVisualFillGeometry } from "../geometry/visualInterpolation";
import { createTerrainGeometry } from "../geometry/terrainGeometry";
import { createPlanetTextures, isPlanetSurface, type SurfaceStyle } from "../materials/planetSurface";

export function TerrainMesh({ terrain, verticalExaggeration, colorMode, elevationOffset, colorRange, worldSpanMeters, onInspect, onHoverChange, highlighted = false, fillMissing = false, meterScale }: {
  terrain: TerrainData; verticalExaggeration?: number; colorMode?: SurfaceStyle;
  elevationOffset?: number; colorRange?: { min: number; max: number }; worldSpanMeters?: number;
  onInspect?: (point: THREE.Vector3) => void; onHoverChange?: (hovered: boolean) => void; highlighted?: boolean; fillMissing?: boolean;
  meterScale?:number;
}) {
  const planet = colorMode === "surface" ? terrain.body : colorMode && isPlanetSurface(colorMode) ? colorMode : null;
  const geometryMode = colorMode === "neutral" ? "neutral" : "elevation";
  const geometry = useMemo(() => (fillMissing ? createVisualFillGeometry : createTerrainGeometry)(terrain, { verticalExaggeration, colorMode: geometryMode, elevationOffset, colorRange, worldSpanMeters }), [terrain, verticalExaggeration, geometryMode, elevationOffset, colorRange, worldSpanMeters, fillMissing]);
  useEffect(() => () => { geometry.dispose(); }, [geometry]);
  return <><mesh geometry={geometry} receiveShadow onPointerOver={() => onHoverChange?.(true)} onPointerMove={event => onInspect?.(event.point)} onPointerOut={() => { onHoverChange?.(false); onInspect?.(new THREE.Vector3(NaN, NaN, NaN)); }}>
    <SurfaceMaterial style={planet ?? geometryMode} highlighted={highlighted} showEstimates={fillMissing} meterScale={meterScale} />
  </mesh>{!fillMissing && <NoDataOverlay terrain={terrain} verticalExaggeration={verticalExaggeration} elevationOffset={elevationOffset} worldSpanMeters={worldSpanMeters} />}</>;
}

export function SurfaceMaterial({ style, highlighted = false, dimmed = false, showEstimates = false, meterScale }: { style: SurfaceStyle; highlighted?: boolean; dimmed?: boolean; showEstimates?: boolean; meterScale?:number }) {
  const planet = isPlanetSurface(style) ? style : null;
  const geometryMode = style;
  const textures = useMemo(() => planet ? createPlanetTextures(planet) : null, [planet]);
  useEffect(() => () => { textures?.map.dispose(); textures?.bumpMap.dispose(); textures?.soilMap?.dispose(); textures?.rockMap?.dispose(); }, [textures]);
  return <meshStandardMaterial color={dimmed ? "#899296" : "#ffffff"} emissive="#4be6c2" emissiveIntensity={highlighted ? 0.16 : 0} key={`${planet??geometryMode}-${meterScale??"overview"}`} vertexColors={!planet} map={textures?.map ?? null} bumpMap={textures?.bumpMap ?? null} bumpScale={meterScale?meterScale*.004:.002} onBeforeCompile={shader => {
      if (showEstimates) {
        shader.vertexShader = `attribute float visualEstimate; varying float vVisualEstimate;\n${shader.vertexShader}`
          .replace("#include <begin_vertex>", "#include <begin_vertex>\nvVisualEstimate = visualEstimate;");
        shader.fragmentShader = `varying float vVisualEstimate;\n${shader.fragmentShader}`
          .replace("#include <color_fragment>", "#include <color_fragment>\ndiffuseColor.rgb *= mix(vec3(1.0), vec3(1.08, 1.03, 0.94), clamp(vVisualEstimate, 0.0, 1.0));");
      }
      if (!planet) return;
      if(meterScale) {
        shader.uniforms.simMeterScale={value:meterScale};
        shader.vertexShader=`uniform float simMeterScale; varying vec2 vSimMeters;\n${shader.vertexShader}`.replace("#include <begin_vertex>","#include <begin_vertex>\nvSimMeters=transformed.xz/simMeterScale;");
        shader.fragmentShader=`varying vec2 vSimMeters;\n${shader.fragmentShader}`.replace("#include <map_fragment>",`
          vec3 macroColor=texture2D(map,vMapUv).rgb;
          float grain=texture2D(bumpMap,vSimMeters*1.25).r;
          vec3 microColor=texture2D(map,vSimMeters*.3).rgb;
          diffuseColor.rgb*=mix(macroColor,microColor,.28)*(.8+grain*.4);
        `).replace("#include <bumpmap_pars_fragment>",THREE.ShaderChunk.bumpmap_pars_fragment.split("vBumpMapUv").join("(vSimMeters*1.25)"));
        return;
      }
      if (planet === "Earth") {
        shader.uniforms.earthSoilMap = { value: textures?.soilMap };
        shader.uniforms.earthRockMap = { value: textures?.rockMap };
        shader.vertexShader = `varying vec3 vEarthNormal; varying vec3 vEarthPosition;\n${shader.vertexShader}`
          .replace("#include <beginnormal_vertex>", "#include <beginnormal_vertex>\nvEarthNormal = objectNormal;")
          .replace("#include <begin_vertex>", "#include <begin_vertex>\nvEarthPosition = transformed;");
        shader.fragmentShader = `varying vec3 vEarthNormal; varying vec3 vEarthPosition; uniform sampler2D earthSoilMap; uniform sampler2D earthRockMap;\n${shader.fragmentShader}`
          .replace("#include <map_fragment>", `
            // Geometric slope selects rock; a broad world-space mask breaks up tiling.
            float slope = 1.0 - abs(normalize(vEarthNormal).y);
            vec2 macroUv = vEarthPosition.xz * 0.075 + vec2(0.47, 0.11);
            float patches = texture2D(bumpMap, macroUv).r;
            float rockWeight = smoothstep(0.075, 0.25, slope + (patches - 0.5) * 0.035) * (0.65 + patches * 0.35);
            float soilWeight = smoothstep(0.51, 0.64, patches) * (1.0 - rockWeight * 0.6);
            vec3 grass = texture2D(map, vMapUv).rgb;
            float detail = texture2D(bumpMap, vMapUv * 28.0).r;
            grass *= 0.8 + detail * 0.4;
            vec3 soil = texture2D(earthSoilMap, vMapUv * 1.7 + vec2(0.23, 0.41)).rgb;
            vec3 rock = texture2D(earthRockMap, vMapUv * 0.9).rgb;
            diffuseColor.rgb *= mix(mix(grass, soil, soilWeight), rock, rockWeight);
          `)
          .replace("#include <bumpmap_pars_fragment>", THREE.ShaderChunk.bumpmap_pars_fragment.split("vBumpMapUv").join("(vBumpMapUv * 28.0)"));
        return;
      }
      shader.fragmentShader = shader.fragmentShader.replace("#include <map_fragment>", THREE.ShaderChunk.map_fragment.replace(
        "diffuseColor *= sampledDiffuseColor;",
        "vec3 detail = texture2D(map, vMapUv * 32.0 + vec2(0.17, 0.39)).rgb; diffuseColor *= sampledDiffuseColor; diffuseColor.rgb *= 0.65 + detail * 0.9;"
      )).replace("#include <bumpmap_pars_fragment>", THREE.ShaderChunk.bumpmap_pars_fragment.split("vBumpMapUv").join("(vBumpMapUv * 24.0)"));
    }} customProgramCacheKey={() => `${planet === "Earth" ? "earth-layered-v1" : "planet-detail-v1"}-${showEstimates ? "estimated" : "source"}-${meterScale?"meter-detail":"overview"}`} side={THREE.DoubleSide} roughness={0.96} />;
}
