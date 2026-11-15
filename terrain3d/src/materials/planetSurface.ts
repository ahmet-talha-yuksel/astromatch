import * as THREE from "three";

export type SurfaceStyle = "elevation" | "neutral" | "surface" | "Earth" | "Mars" | "Moon";
export const isPlanetSurface = (style: SurfaceStyle): style is "Earth" | "Mars" | "Moon" =>
  style === "Earth" || style === "Mars" || style === "Moon";

export interface PlanetTextures {
  map: THREE.DataTexture;
  bumpMap: THREE.DataTexture;
  soilMap?: THREE.DataTexture;
  rockMap?: THREE.DataTexture;
}

// Periodic value noise: repeatable materials without downloads or visible tile seams.
function hash(x: number, y: number) {
  const n = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return n - Math.floor(n);
}
function noise(u: number, v: number, frequency: number) {
  const x = u * frequency, y = v * frequency;
  const ix = Math.floor(x), iy = Math.floor(y);
  const sx = x - ix, sy = y - iy;
  const a = sx * sx * (3 - 2 * sx), b = sy * sy * (3 - 2 * sy);
  const sample = (dx: number, dy: number) => hash((ix + dx) % frequency, (iy + dy) % frequency);
  return THREE.MathUtils.lerp(THREE.MathUtils.lerp(sample(0, 0), sample(1, 0), a),
    THREE.MathUtils.lerp(sample(0, 1), sample(1, 1), a), b);
}

// Keep the generated pixels, while each material owns/disposes its GPU textures.
let earthPixels: { grass: Uint8Array<ArrayBuffer>; soil: Uint8Array<ArrayBuffer>; rock: Uint8Array<ArrayBuffer>; bump: Uint8Array<ArrayBuffer> } | undefined;
function createEarthTextures(): PlanetTextures {
  const size = 512;
  if (!earthPixels) {
    const grass = new Uint8Array(size * size * 4), soil = new Uint8Array(size * size * 4);
    const rock = new Uint8Array(size * size * 4), bump = new Uint8Array(size * size * 4);
    const green = new THREE.Color("#345b31"), meadow = new THREE.Color("#7c9550"), straw = new THREE.Color("#a5a16b");
    const earth = new THREE.Color("#513d2d"), sand = new THREE.Color("#b29b77");
    const slate = new THREE.Color("#646b65"), stone = new THREE.Color("#b6b4a1");
    const color = new THREE.Color();
    const write = (pixels: Uint8Array, i: number) => {
      color.convertLinearToSRGB();
      pixels[i] = color.r * 255; pixels[i + 1] = color.g * 255; pixels[i + 2] = color.b * 255; pixels[i + 3] = 255;
    };
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const u = x / size, v = y / size, i = (y * size + x) * 4;
      const patch = noise(u, v, 4), clump = noise(u, v, 16), fine = noise(u, v, 64);
      const blades = noise(u * 4, v, 128), grain = hash(x, y);
      color.copy(green).lerp(meadow, clump * 0.65 + fine * 0.35);
      color.lerp(straw, THREE.MathUtils.smoothstep(patch, 0.5, 0.84) * 0.65);
      color.multiplyScalar(0.8 + blades * 0.28 + grain * 0.12); write(grass, i);
      const pebble = THREE.MathUtils.smoothstep(fine, 0.65, 0.85);
      color.copy(earth).lerp(sand, clump * 0.6 + fine * 0.4).lerp(stone, pebble * 0.7);
      color.multiplyScalar(0.84 + grain * 0.26); write(soil, i);
      const fissure = 1 - THREE.MathUtils.smoothstep(Math.abs(clump - 0.5), 0.012, 0.045);
      color.copy(slate).lerp(stone, patch * 0.25 + fine * 0.75);
      color.multiplyScalar((0.9 + grain * 0.18) * (1 - fissure * 0.28)); write(rock, i);
      bump[i] = bump[i + 1] = bump[i + 2] = (patch * 0.3 + clump * 0.3 + blades * 0.2 + fine * 0.15 + grain * 0.05) * 255;
      bump[i + 3] = 255;
    }
    earthPixels = { grass, soil, rock, bump };
  }
  const texture = (pixels: Uint8Array<ArrayBuffer>, color: boolean) => {
    const result = new THREE.DataTexture(pixels, size, size);
    if (color) result.colorSpace = THREE.SRGBColorSpace;
    result.wrapS = result.wrapT = THREE.RepeatWrapping;
    result.repeat.set(3, 3);
    result.magFilter = THREE.LinearFilter;
    result.minFilter = THREE.LinearMipmapLinearFilter;
    result.generateMipmaps = true;
    result.anisotropy = 8;
    result.needsUpdate = true;
    return result;
  };
  return { map: texture(earthPixels.grass, true), soilMap: texture(earthPixels.soil, true), rockMap: texture(earthPixels.rock, true), bumpMap: texture(earthPixels.bump, false) };
}

/** Artistic regolith/soil, not satellite imagery or an additional elevation dataset. */
export function createPlanetTextures(body: "Earth" | "Mars" | "Moon"): PlanetTextures {
  if (body === "Earth") return createEarthTextures();
  const size = 512;
  const pixels = new Uint8Array(size * size * 4);
  const relief = new Uint8Array(size * size * 4);
  const low = new THREE.Color(body === "Mars" ? "#613a28" : "#47464a");
  const high = new THREE.Color(body === "Mars" ? "#cd9966" : "#aaa79e");
  const color = new THREE.Color();
  const craters = Array.from({ length: body === "Moon" ? 34 : 10 }, (_, i) => ({
    x: hash(i, 11), y: hash(i, 28), r: 0.012 + hash(i, 19) * (body === "Moon" ? 0.085 : 0.025),
  }));
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const u = x / size, v = y / size;
    const coarse = noise(u, v, 8), medium = noise(u, v, 32), fine = noise(u, v, 128);
    const grain = hash(x, y);
    let value = coarse * 0.48 + medium * 0.29 + fine * 0.16 + grain * 0.07;
    let bump = value;
    for (const crater of craters) {
      const dx = Math.min(Math.abs(u - crater.x), 1 - Math.abs(u - crater.x));
      const dy = Math.min(Math.abs(v - crater.y), 1 - Math.abs(v - crater.y));
      const d = Math.hypot(dx, dy) / crater.r;
      if (d < 1.4) {
        const rim = Math.exp(-((d - 1) ** 2) * 65) * 0.16;
        const bowl = Math.max(0, 1 - d * d) * 0.18;
        value += rim - bowl; bump += rim - bowl;
      }
    }
    if (body === "Mars") value += Math.sin(u * Math.PI * 48 + coarse * 7) * 0.025;
    color.copy(low).lerp(high, THREE.MathUtils.clamp(value * 1.25, 0, 1));
    const i = (y * size + x) * 4;
    // Encode color in sRGB; Three decodes it for physically based lighting.
    color.convertLinearToSRGB();
    pixels[i] = color.r * 255; pixels[i + 1] = color.g * 255; pixels[i + 2] = color.b * 255; pixels[i + 3] = 255;
    relief[i] = relief[i + 1] = relief[i + 2] = THREE.MathUtils.clamp(bump, 0, 1) * 255; relief[i + 3] = 255;
  }
  const map = new THREE.DataTexture(pixels, size, size);
  const bumpMap = new THREE.DataTexture(relief, size, size);
  map.colorSpace = THREE.SRGBColorSpace;
  for (const texture of [map, bumpMap]) {
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(7, 7);
    texture.magFilter = THREE.LinearFilter;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.generateMipmaps = true;
    texture.anisotropy = 8;
    texture.needsUpdate = true;
  }
  return { map, bumpMap };
}
