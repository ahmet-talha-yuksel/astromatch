// Compile only the testable TypeScript modules; use Node's built-in test runner.
const { spawnSync } = require('node:child_process');
const { mkdirSync, writeFileSync, rmSync } = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = path.join(root, '.test-build');
let status = 1;
try {
  const compile = spawnSync(process.execPath, [path.join(root, 'node_modules/typescript/bin/tsc'), '-p', path.join(__dirname, 'tsconfig.json')], { stdio: 'inherit', cwd: root });
  if (compile.status === 0) {
    mkdirSync(output, { recursive: true });
    writeFileSync(path.join(output, 'package.json'), '{"type":"commonjs"}');
    status = spawnSync(process.execPath, ['--test', path.join(__dirname, 'terrain.test.cjs'), path.join(__dirname,'rover.test.cjs')], { stdio: 'inherit', cwd: root }).status ?? 1;
  }
} finally {
  rmSync(output, { recursive: true, force: true });
}
process.exitCode = status;
