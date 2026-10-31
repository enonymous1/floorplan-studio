// Write a golden plan JSON built with plan.js, for the CI contract job:
// the Python renderer must render what the editor exports. The objects
// below exercise a room, an attached door (on the room's bottom edge
// after the canvas Y flip), and a standalone wall.
//
// Usage: node scripts/export-golden.mjs [output-path]
// Defaults to golden-plan.json in the current working directory.
import { writeFileSync } from 'node:fs';
import { editorObjectsToPlan } from '../modules/plan.js';

const objects = [
  { type: 'rect', name: 'Room 1', x: 0, y: 0, w: 400, h: 300 },
  {
    type: 'door', x1: 200, y1: 300, x2: 260, y2: 300,
    swingDirection: 1, hingeAtStart: true, swing: 'in',
  },
  { type: 'wall', x1: 400, y1: 0, x2: 400, y2: 300 },
];

const plan = editorObjectsToPlan(objects, { title: 'Golden Plan' });
const out = process.argv[2] || 'golden-plan.json';
writeFileSync(out, `${JSON.stringify(plan, null, 2)}\n`);
console.log(out);
