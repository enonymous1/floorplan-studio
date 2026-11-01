// Shared plan format (version 1) <-> editor objects.
//
// The plan format is the interchange format with the Python renderer
// (renderer/). Coordinates in a plan are feet, origin bottom-left,
// y increasing upwards. Editor canvas coordinates are pixels,
// origin top-left, y increasing downwards, at PIXELS_PER_FOOT pixels
// per foot. The conversion is a pure scale + Y flip anchored at the
// canvas origin: (x_px, y_px) -> (x_px / 20, -y_px / 20). It is
// lossless in both directions; the renderer centres the plan on the
// page, so the negative y values of an exported canvas plan do not
// matter there.
//
// Room attachment: a door/window segment that lies on a room edge
// (axis-aligned, within tolerance) is attached to the first such
// room, so the renderer can cut a door gap in that wall and draw the
// swing. Segments on no room edge are kept as standalone `openings`
// and rendered as plain segments. Editor-only door fields
// (swingDirection / hingeAtStart) ride along under `editor` so an
// export -> import round trip restores them exactly; the renderer
// ignores them and uses `swing` ("in" by default) instead.

export const PIXELS_PER_FOOT = 20;
export const PLAN_VERSION = 1;

const TOLERANCE_FT = 0.01;

function isNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function isPoint(value) {
  return Array.isArray(value) && value.length === 2 && value.every(isNumber);
}

function isSegment(value) {
  return Array.isArray(value) && value.length === 2 && value.every(isPoint);
}

function isAxisAligned(segment) {
  const [[x1, y1], [x2, y2]] = segment;
  return Math.abs(x1 - x2) < 1e-9 || Math.abs(y1 - y2) < 1e-9;
}

// -0 breaks deepStrictEqual and JSON round trips; normalize it away.
function nz(value) {
  return value === 0 ? 0 : value;
}

function pxToFt(x, y, pixelsPerFoot) {
  return [nz(x / pixelsPerFoot), nz(-y / pixelsPerFoot)];
}

function ftToPx(x, y, pixelsPerFoot) {
  return [nz(x * pixelsPerFoot), nz(-y * pixelsPerFoot)];
}

function rectPxToFt(rect, pixelsPerFoot) {
  return [
    nz(rect.x / pixelsPerFoot),
    nz(-(rect.y + rect.h) / pixelsPerFoot),
    nz(rect.w / pixelsPerFoot),
    nz(rect.h / pixelsPerFoot),
  ];
}

function rectFtToPx(rect, pixelsPerFoot) {
  return {
    x: nz(rect[0] * pixelsPerFoot),
    y: nz(-(rect[1] + rect[3]) * pixelsPerFoot),
    w: nz(rect[2] * pixelsPerFoot),
    h: nz(rect[3] * pixelsPerFoot),
  };
}

function segmentPxToFt(segment, pixelsPerFoot) {
  return segment.map(([x, y]) => pxToFt(x, y, pixelsPerFoot));
}

function segmentFtToPx(segment, pixelsPerFoot) {
  return segment.map(([x, y]) => ftToPx(x, y, pixelsPerFoot));
}

// Validate a parsed plan object. Returns an array of error strings
// (empty when valid). Used by parsePlanJson and by the tests.
export function validatePlan(plan) {
  const errors = [];
  if (!plan || typeof plan !== 'object' || Array.isArray(plan)) {
    return ['Plan must be an object'];
  }
  if (plan.version !== undefined && plan.version !== PLAN_VERSION) {
    errors.push(`Unsupported plan version: ${plan.version} (expected ${PLAN_VERSION})`);
  }
  if (!Array.isArray(plan.rooms)) {
    errors.push("Plan must contain a 'rooms' array");
    return errors;
  }
  const checkOpening = (opening, where) => {
    if (!opening || typeof opening !== 'object') {
      errors.push(`${where} must be an object`);
      return;
    }
    if (!isSegment(opening.pos) || !isAxisAligned(opening.pos)) {
      errors.push(`${where} pos must be a horizontal or vertical [[x1, y1], [x2, y2]] segment`);
    }
    // 'none' is an open passageway: a wall gap with no leaf or arc.
    if (opening.swing !== undefined && opening.swing !== 'in' && opening.swing !== 'out' && opening.swing !== 'none') {
      errors.push(`${where} swing must be 'in', 'out', or 'none'`);
    }
  };
  plan.rooms.forEach((room, i) => {
    if (!room || typeof room !== 'object') {
      errors.push(`Room ${i} must be an object`);
      return;
    }
    if (typeof room.name !== 'string' || !room.name) {
      errors.push(`Room ${i} must have a non-empty 'name'`);
    }
    if (!Array.isArray(room.rect) || room.rect.length !== 4 || !room.rect.every(isNumber)
      || room.rect[2] <= 0 || room.rect[3] <= 0) {
      errors.push(`Room '${room.name}' rect must be [x, y, width, height] with positive size`);
    }
    (room.doors || []).forEach((door, j) => checkOpening(door, `Room '${room.name}' door ${j}`));
    (room.windows || []).forEach((win, j) => checkOpening(win, `Room '${room.name}' window ${j}`));
  });
  if (plan.boundary !== undefined && plan.boundary !== null) {
    if (!Array.isArray(plan.boundary) || plan.boundary.length < 3
      || !plan.boundary.every(isPoint)) {
      errors.push("'boundary' must be a list of at least 3 [x, y] points");
    }
  }
  (plan.walls || []).forEach((wall, i) => {
    if (!wall || !isSegment(wall.pos)) errors.push(`Wall ${i} pos must be [[x1, y1], [x2, y2]]`);
  });
  (plan.openings || []).forEach((opening, i) => {
    if (!opening || (opening.kind !== 'door' && opening.kind !== 'window')) {
      errors.push(`Opening ${i} kind must be 'door' or 'window'`);
    }
    checkOpening(opening, `Opening ${i}`);
  });
  (plan.labels || []).forEach((label, i) => {
    if (!label || typeof label.text !== 'string' || !isPoint(label.point)) {
      errors.push(`Label ${i} must have 'text' and a [x, y] 'point'`);
    }
  });
  (plan.dimensions || []).forEach((dim, i) => {
    if (!dim || !isSegment(dim.pos)) errors.push(`Dimension ${i} pos must be [[x1, y1], [x2, y2]]`);
  });
  (plan.objects || []).forEach((obj, i) => {
    if (!obj || (obj.kind !== 'stairs' && obj.kind !== 'road')
      || !Array.isArray(obj.rect) || obj.rect.length !== 4 || !obj.rect.every(isNumber)) {
      errors.push(`Object ${i} must have kind 'stairs'/'road' and a 4-number rect`);
    }
  });
  return errors;
}

function findRoomForSegment(segment, rooms) {
  const [[x1, y1], [x2, y2]] = segment;
  const horizontal = Math.abs(y1 - y2) < 1e-9;
  for (let index = 0; index < rooms.length; index += 1) {
    const [rx, ry, rw, rh] = rooms[index].rect;
    if (horizontal) {
      const onTop = Math.abs(y1 - (ry + rh)) <= TOLERANCE_FT;
      const onBottom = Math.abs(y1 - ry) <= TOLERANCE_FT;
      if ((onTop || onBottom)
        && Math.min(x1, x2) >= rx - TOLERANCE_FT && Math.max(x1, x2) <= rx + rw + TOLERANCE_FT) {
        return index;
      }
    } else {
      const onLeft = Math.abs(x1 - rx) <= TOLERANCE_FT;
      const onRight = Math.abs(x1 - (rx + rw)) <= TOLERANCE_FT;
      if ((onLeft || onRight)
        && Math.min(y1, y2) >= ry - TOLERANCE_FT && Math.max(y1, y2) <= ry + rh + TOLERANCE_FT) {
        return index;
      }
    }
  }
  return -1;
}

export function editorObjectsToPlan(objects, options = {}) {
  const pixelsPerFoot = options.pixelsPerFoot || PIXELS_PER_FOOT;
  const rooms = [];
  const walls = [];
  const openings = [];
  const labels = [];
  const dimensions = [];
  const planObjects = [];
  const pending = [];

  let roomCount = 0;
  for (const obj of objects || []) {
    if (!obj || typeof obj !== 'object') continue;
    if (obj.type === 'rect') {
      roomCount += 1;
      rooms.push({
        name: typeof obj.name === 'string' && obj.name ? obj.name : `Room ${roomCount}`,
        rect: rectPxToFt(obj, pixelsPerFoot),
        doors: [],
        windows: [],
      });
    } else if (obj.type === 'wall') {
      walls.push({ pos: segmentPxToFt([[obj.x1, obj.y1], [obj.x2, obj.y2]], pixelsPerFoot) });
    } else if (obj.type === 'door' || obj.type === 'window') {
      pending.push(obj);
    } else if (obj.type === 'label') {
      const [x, y] = pxToFt(obj.x, obj.y, pixelsPerFoot);
      labels.push({ text: obj.text || '', point: [x, y], rotation: obj.rotation || 0 });
    } else if (obj.type === 'dim') {
      dimensions.push({
        pos: segmentPxToFt([[obj.x1, obj.y1], [obj.x2, obj.y2]], pixelsPerFoot),
        label: obj.dist || undefined,
      });
    } else if (obj.type === 'stairs' || obj.type === 'road') {
      const entry = { kind: obj.type, rect: rectPxToFt(obj, pixelsPerFoot) };
      if (obj.label) entry.label = obj.label;
      planObjects.push(entry);
    }
    // Unknown object types are ignored: the plan keeps what the
    // renderer understands, and the canvas keeps the rest.
  }

  for (const obj of pending) {
    const pos = segmentPxToFt([[obj.x1, obj.y1], [obj.x2, obj.y2]], pixelsPerFoot);
    const entry = { pos };
    if (obj.type === 'door') {
      if (obj.swing !== undefined) entry.swing = obj.swing;
      if (obj.swingDirection !== undefined || obj.hingeAtStart !== undefined) {
        entry.editor = {
          swingDirection: obj.swingDirection === undefined ? 1 : obj.swingDirection,
          hingeAtStart: obj.hingeAtStart !== false,
        };
      }
    }
    const roomIndex = findRoomForSegment(pos, rooms);
    if (roomIndex >= 0) {
      if (obj.type === 'door') rooms[roomIndex].doors.push(entry);
      else rooms[roomIndex].windows.push(entry);
    } else {
      openings.push({ kind: obj.type, ...entry });
    }
  }

  const plan = { version: PLAN_VERSION };
  if (options.title) plan.title = options.title;
  if (options.address) plan.address = options.address;
  if (options.date) plan.date = options.date;
  if (options.boundary) plan.boundary = options.boundary;
  plan.rooms = rooms;
  if (walls.length) plan.walls = walls;
  if (openings.length) plan.openings = openings;
  if (labels.length) plan.labels = labels;
  if (dimensions.length) plan.dimensions = dimensions;
  if (planObjects.length) plan.objects = planObjects;
  return plan;
}

export function planToEditorObjects(plan, options = {}) {
  const errors = validatePlan(plan);
  if (errors.length) {
    throw new Error(`Invalid plan: ${errors.join('; ')}`);
  }
  const pixelsPerFoot = options.pixelsPerFoot || PIXELS_PER_FOOT;
  const objects = [];
  // A shared door/window is one physical opening, even though a
  // hand-written plan lists it in both rooms (paired, with
  // opposite swings). Without dedupe, importing such a plan
  // put two identical objects on the canvas at the same spot,
  // and exporting then listed the door twice in the first
  // room and not at all in the second. The first listing
  // wins; its swing is the one the canvas object carries.
  const seenSegments = new Set();
  const isNewSegment = (type, x1, y1, x2, y2) => {
    const key = `${type}:${x1},${y1},${x2},${y2}`;
    if (seenSegments.has(key)) return false;
    seenSegments.add(key);
    return true;
  };

  for (const room of plan.rooms) {
    const rect = rectFtToPx(room.rect, pixelsPerFoot);
    const rectObj = { type: 'rect', name: room.name, ...rect };
    objects.push(rectObj);
    for (const door of room.doors || []) {
      const [[x1, y1], [x2, y2]] = segmentFtToPx(door.pos, pixelsPerFoot);
      if (!isNewSegment('door', x1, y1, x2, y2)) continue;
      const doorObj = { type: 'door', x1, y1, x2, y2, swingDirection: 1, hingeAtStart: true };
      if (door.editor) {
        if (door.editor.swingDirection !== undefined) doorObj.swingDirection = door.editor.swingDirection;
        if (door.editor.hingeAtStart !== undefined) doorObj.hingeAtStart = door.editor.hingeAtStart;
      }
      if (door.swing !== undefined) doorObj.swing = door.swing;
      objects.push(doorObj);
    }
    for (const win of room.windows || []) {
      const [[x1, y1], [x2, y2]] = segmentFtToPx(win.pos, pixelsPerFoot);
      if (!isNewSegment('window', x1, y1, x2, y2)) continue;
      objects.push({ type: 'window', x1, y1, x2, y2 });
    }
  }
  for (const wall of plan.walls || []) {
    const [[x1, y1], [x2, y2]] = segmentFtToPx(wall.pos, pixelsPerFoot);
    objects.push({ type: 'wall', x1, y1, x2, y2 });
  }
  for (const opening of plan.openings || []) {
    const [[x1, y1], [x2, y2]] = segmentFtToPx(opening.pos, pixelsPerFoot);
    if (opening.kind === 'door') {
      if (!isNewSegment('door', x1, y1, x2, y2)) continue;
      const doorObj = { type: 'door', x1, y1, x2, y2, swingDirection: 1, hingeAtStart: true };
      if (opening.editor) {
        if (opening.editor.swingDirection !== undefined) doorObj.swingDirection = opening.editor.swingDirection;
        if (opening.editor.hingeAtStart !== undefined) doorObj.hingeAtStart = opening.editor.hingeAtStart;
      }
      if (opening.swing !== undefined) doorObj.swing = opening.swing;
      objects.push(doorObj);
    } else {
      if (!isNewSegment('window', x1, y1, x2, y2)) continue;
      objects.push({ type: 'window', x1, y1, x2, y2 });
    }
  }
  for (const label of plan.labels || []) {
    const [x, y] = ftToPx(label.point[0], label.point[1], pixelsPerFoot);
    objects.push({ type: 'label', text: label.text, x, y, rotation: label.rotation || 0 });
  }
  for (const dim of plan.dimensions || []) {
    const [[x1, y1], [x2, y2]] = segmentFtToPx(dim.pos, pixelsPerFoot);
    const lengthFt = Math.hypot(x2 - x1, y2 - y1) / pixelsPerFoot;
    objects.push({
      type: 'dim', x1, y1, x2, y2,
      dist: dim.label || `${lengthFt.toFixed(2)}'`,
    });
  }
  for (const obj of plan.objects || []) {
    const rect = rectFtToPx(obj.rect, pixelsPerFoot);
    const entry = { type: obj.kind, ...rect };
    if (obj.label) entry.label = obj.label;
    objects.push(entry);
  }

  return {
    objects,
    boundary: plan.boundary ? plan.boundary.map(([x, y]) => [x, y]) : null,
    meta: {
      title: plan.title || null,
      address: plan.address || null,
      date: plan.date || null,
    },
  };
}

export function planToJson(plan) {
  return `${JSON.stringify(plan, null, 2)}\n`;
}

function yamlScalar(value) {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') return String(value);
  const text = String(value);
  // Bare scalars: plain words/numbers/paths. Anything else is
  // single-quoted (single quotes doubled) so PyYAML reads it back.
  if (/^[A-Za-z0-9_][A-Za-z0-9_.\-/]*$/.test(text)
    && !/^(true|false|null|~|yes|no|on|off)$/i.test(text)
    && Number.isNaN(Number(text))) {
    return text;
  }
  return `'${text.replace(/'/g, "''")}'`;
}

function isScalarArray(value) {
  return Array.isArray(value)
    && value.every((v) => v === null || ['string', 'number', 'boolean'].includes(typeof v));
}

function yamlLines(value, indent, lines) {
  const pad = '  '.repeat(indent);
  if (Array.isArray(value)) {
    if (value.length === 0) {
      lines.push(`${pad}[]`);
      return;
    }
    for (const item of value) {
      if (isScalarArray(item)) {
        lines.push(`${pad}- [${item.map(yamlScalar).join(', ')}]`);
      } else if (item !== null && typeof item === 'object') {
        const sub = [];
        yamlLines(item, indent + 1, sub);
        lines.push(`${pad}- ${sub[0].slice((indent + 1) * 2)}`);
        lines.push(...sub.slice(1));
      } else {
        lines.push(`${pad}- ${yamlScalar(item)}`);
      }
    }
    return;
  }
  if (value !== null && typeof value === 'object') {
    if (Object.keys(value).length === 0) {
      lines.push(`${pad}{}`);
      return;
    }
    for (const [key, val] of Object.entries(value)) {
      if (val === undefined) continue;
      if (Array.isArray(val) && val.length === 0) {
        lines.push(`${pad}${key}: []`);
      } else if (isScalarArray(val)) {
        lines.push(`${pad}${key}: [${val.map(yamlScalar).join(', ')}]`);
      } else if (val !== null && typeof val === 'object' && !Array.isArray(val)
        && Object.keys(val).length === 0) {
        lines.push(`${pad}${key}: {}`);
      } else if (Array.isArray(val) || (val !== null && typeof val === 'object')) {
        lines.push(`${pad}${key}:`);
        yamlLines(val, indent + 1, lines);
      } else {
        lines.push(`${pad}${key}: ${yamlScalar(val)}`);
      }
    }
    return;
  }
  lines.push(`${pad}${yamlScalar(value)}`);
}

export function serializePlanYaml(plan) {
  const lines = [];
  yamlLines(plan, 0, lines);
  return `${lines.join('\n')}\n`;
}

export function parsePlanJson(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new Error(`Could not parse plan JSON: ${err.message}`);
  }
  const errors = validatePlan(parsed);
  if (errors.length) {
    throw new Error(`Invalid plan: ${errors.join('; ')}`);
  }
  return parsed;
}
