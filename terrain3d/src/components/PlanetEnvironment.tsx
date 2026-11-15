import { Stars } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";

export function PlanetEnvironment({ body, immersive = false, space = false, sunIntensity }: { body: "Earth" | "Mars" | "Moon"; immersive?: boolean; space?: boolean;sunIntensity?:number }) {
  const colors = useMemo(() => ({
    top: new THREE.Color(space ? "#02040c" : body === "Mars" ? "#50352c" : body === "Earth" ? "#3879ae" : "#010207"),
    horizon: new THREE.Color(space ? (body === "Mars" ? "#30241e" : body === "Earth" ? "#142331" : "#070912") : body === "Mars" ? "#d4a579" : body === "Earth" ? "#d3e4df" : "#080b12"),
  }), [body, space]);
  return <>
    {immersive && <>
      {space && <Stars radius={80} depth={40} count={2400} factor={2.5} saturation={0.15} fade speed={0} />}
      <color attach="background" args={[colors.top]} />
      {body !== "Moon" && <fog attach="fog" args={[colors.horizon, space ? 18 : 5, space ? 65 : 24]} />}
      <mesh scale={150} renderOrder={-10}>
        <sphereGeometry args={[1, 32, 24]} />
        <shaderMaterial side={THREE.BackSide} depthWrite={false} uniforms={{ top: { value: colors.top }, horizon: { value: colors.horizon } }}
          vertexShader="varying vec3 vDirection; void main() { vDirection = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }"
          fragmentShader={`uniform vec3 top; uniform vec3 horizon; varying vec3 vDirection; void main() { float h = smoothstep(0.0, 0.7, normalize(vDirection).y); gl_FragColor = vec4(mix(horizon, top, h), 1.0);\n #include <tonemapping_fragment>\n #include <colorspace_fragment>\n }`} />
      </mesh>
      <mesh position={[-24, 15, -65]}>
        <sphereGeometry args={[body === "Moon" ? 0.6 : 1.5, 24, 16]} />
        <meshBasicMaterial color={body === "Mars" ? "#e0e5ec" : "#fff2cf"} fog={false} />
      </mesh>
    </>}
    <hemisphereLight args={[body === "Mars" ? "#efc5a4" : body === "Earth" ? "#d6ebff" : "#b4bbd0", body === "Earth" ? "#44472b" : "#3a2922", body === "Moon" ? 0.35 : 0.85]} />
    <directionalLight position={[-5, 4, -6]} color={body === "Mars" ? "#ffe2c4" : "#fff5e6"} intensity={sunIntensity??(body === "Moon" ? 2.8 : 2.2)} />
  </>;
}
