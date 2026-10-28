// Parse every editor script as an ES module without executing it.
// (`node --check` parses .js as CommonJS and rejects the imports.)
// Run with: node --experimental-vm-modules scripts/check-syntax.mjs
import { readFileSync } from 'node:fs';
import { SourceTextModule } from 'node:vm';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const files = [
  'script.js',
  'modules/state.js',
  'modules/drawing.js',
  'modules/utils.js',
  'modules/plan.js',
];

for (const file of files) {
  const code = readFileSync(join(root, file), 'utf8');
  new SourceTextModule(code); // throws SyntaxError on bad syntax
  console.log(`${file}: OK`);
}
