import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const vitestBin = path.resolve(__dirname, 'node_modules', 'vitest', 'vitest.mjs');

// Filter out CRA-specific options like --watchAll=false so Vitest runs cleanly
const args = process.argv.slice(2).filter((arg) => !arg.startsWith('--watchAll'));
const child = spawn(process.execPath, [vitestBin, 'run', ...args], { stdio: 'inherit' });

child.on('exit', (code) => {
  process.exit(code ?? 0);
});
