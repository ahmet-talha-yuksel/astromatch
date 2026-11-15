import { defineConfig } from "vite";
import { searchForWorkspaceRoot } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
export default defineConfig({
  plugins: [react()],
  optimizeDeps: { include: ["@dimforge/rapier3d-compat"] },
  resolve: { dedupe: ["react", "react-dom", "three", "@react-three/fiber", "@react-three/drei", "@dimforge/rapier3d-compat"] },
  server: { fs: { allow: [searchForWorkspaceRoot(process.cwd()), fileURLToPath(new URL("../terrain3d", import.meta.url))] } },
});
