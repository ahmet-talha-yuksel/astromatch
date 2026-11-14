export interface TerrainData {
  id: string;
  name: string;
  body: "Earth" | "Mars" | "Moon";
  width: number;
  height: number;
  cellSizeMeters: number;
  elevationsMeters: number[];
  source: string;
  verticalExaggeration?: number;
  isSynthetic?: boolean;
}
