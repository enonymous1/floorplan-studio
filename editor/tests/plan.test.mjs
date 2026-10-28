import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  editorObjectsToPlan,
  parsePlanJson,
  planToEditorObjects,
  serializePlanYaml,
  validatePlan,
} from '../modules/plan.js';

const room = { type: 'rect', x: 0, y: 0, w: 400, h: 300 };

test('rect exports with Y flip: feet, bottom-left origin', () => {
  const plan = editorObjectsToPlan([room]);
  assert.deepEqual(plan.rooms[0].rect, [0, -15, 20, 15]);
  assert.equal(plan.rooms[0].name, 'Room 1');
});

test('named rect keeps its name', () => {
  const plan = editorObjectsToPlan([{ ...room, name: 'Kitchen' }]);
  assert.equal(plan.rooms[0].name, 'Kitchen');
});

test('door on a room edge attaches to the room', () => {
  // Bottom edge of the room in canvas pixels is y=300.
  const door = { type: 'door', x1: 200, y1: 300, x2: 260, y2: 300, swingDirection: -1, hingeAtStart: false };
  const plan = editorObjectsToPlan([room, door]);
  assert.equal(plan.rooms[0].doors.length, 1);
  assert.deepEqual(plan.rooms[0].doors[0].pos, [[10, -15], [13, -15]]);
  assert.deepEqual(plan.rooms[0].doors[0].editor, { swingDirection: -1, hingeAtStart: false });
  assert.equal(plan.openings, undefined);
});

test('window on the top edge attaches; door off any edge becomes an opening', () => {
  const win = { type: 'window', x1: 40, y1: 0, x2: 160, y2: 0 };
  const stray = { type: 'door', x1: 800, y1: 800, x2: 860, y2: 800, swingDirection: 1, hingeAtStart: true };
  const plan = editorObjectsToPlan([room, win, stray]);
  assert.equal(plan.rooms[0].windows.length, 1);
  assert.deepEqual(plan.rooms[0].windows[0].pos, [[2, 0], [8, 0]]);
  assert.equal(plan.openings.length, 1);
  assert.equal(plan.openings[0].kind, 'door');
});

test('walls, labels, dimensions and objects survive export', () => {
  const objects = [
    { type: 'wall', x1: 0, y1: 0, x2: 0, y2: 200 },
    { type: 'label', text: 'Hall', x: 100, y: 100, rotation: 0 },
    { type: 'dim', x1: 0, y1: 0, x2: 400, y2: 0, dist: "20.00'" },
    { type: 'stairs', x: 0, y: 0, w: 60, h: 200 },
    { type: 'road', x: 0, y: 0, w: 240, h: 480, label: 'Main St' },
  ];
  const plan = editorObjectsToPlan(objects);
  assert.deepEqual(plan.walls, [{ pos: [[0, 0], [0, -10]] }]);
  assert.deepEqual(plan.labels, [{ text: 'Hall', point: [5, -5], rotation: 0 }]);
  assert.deepEqual(plan.dimensions, [{ pos: [[0, 0], [20, 0]], label: "20.00'" }]);
  assert.deepEqual(plan.objects, [
    { kind: 'stairs', rect: [0, -10, 3, 10] },
    { kind: 'road', rect: [0, -24, 12, 24], label: 'Main St' },
  ]);
});

test('export -> import -> export round trip is exact', () => {
  const objects = [
    { ...room, name: 'Living Room' },
    { type: 'door', x1: 200, y1: 300, x2: 260, y2: 300, swingDirection: -1, hingeAtStart: false },
    { type: 'window', x1: 40, y1: 0, x2: 160, y2: 0 },
    { type: 'wall', x1: 0, y1: 0, x2: 0, y2: 200 },
    { type: 'label', text: 'Hall', x: 100, y: 100, rotation: 90 },
    { type: 'stairs', x: 0, y: 0, w: 60, h: 200 },
  ];
  const plan = editorObjectsToPlan(objects, { boundary: [[0, -15], [20, -15], [20, 0], [0, 0]], title: 'Test' });
  const { objects: back, boundary, meta } = planToEditorObjects(plan);
  assert.deepEqual(boundary, [[0, -15], [20, -15], [20, 0], [0, 0]]);
  assert.equal(meta.title, 'Test');
  assert.deepEqual(editorObjectsToPlan(back, { boundary, title: meta.title }), plan);
});

test('YAML serializer produces parseable, readable YAML', () => {
  const plan = {
    version: 1,
    title: 'Residential Floor Plan',
    boundary: [[0, 0], [32, 0], [32, 27], [0, 27]],
    rooms: [{
      name: 'Living Room',
      rect: [0, 0, 20, 15],
      doors: [{ pos: [[10, 0], [13, 0]], swing: 'in' }],
      windows: [{ pos: [[2, 15], [8, 15]] }],
    }],
  };
  const yaml = serializePlanYaml(plan);
  assert.match(yaml, /^version: 1\n/);
  assert.match(yaml, /name: 'Living Room'\n/);
  assert.match(yaml, /rect: \[0, 0, 20, 15\]\n/);
  assert.match(yaml, /- \[10, 0\]/);
  assert.match(yaml, /swing: in\n/);
});

test('parsePlanJson rejects bad plans', () => {
  assert.throws(() => parsePlanJson('{"version": 2, "rooms": []}'), /Unsupported plan version/);
  assert.throws(() => parsePlanJson('{"rooms": "nope"}'), /rooms/);
  assert.throws(() => parsePlanJson('{bad json'), /Could not parse/);
  const diagonal = {
    version: 1,
    rooms: [{ name: 'R', rect: [0, 0, 10, 10], doors: [{ pos: [[0, 0], [3, 3]] }], windows: [] }],
  };
  assert.ok(validatePlan(diagonal).some((e) => e.includes('horizontal or vertical')));
  assert.deepEqual(validatePlan({ version: 1, rooms: [] }), []);
});
