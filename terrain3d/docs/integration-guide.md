# Integration guide

```tsx
<TerrainComparison target={validatedMars} analog={validatedEarth} />
```

Validate boundary inputs with the public adapters:

```ts
import { validateTerrainInput, validateSimilarityResult, validateCandidateMetadata } from "./terrain3d/src";
const terrain = validateTerrainInput(payload);
const result = validateSimilarityResult(optionalEngineResult);
const candidate = validateCandidateMetadata(candidatePayload);
```

Adapters preserve IDs and explanations; they do not calculate scores, discover
candidates, fetch DEMs, reproject coordinates or alter the terrain contract.

From `terrain3d/` run:

```text
npm install
npm test
npm run build
python -m pytest converter/tests
npm run dev -- --host 0.0.0.0 --port 5174
python tests/browser_check.py
```

The browser command requires Playwright and Chrome. The demo fixtures are explicitly
synthetic and must not be presented as NASA data or as a real ranking.

