// State management as a single mutable object
export const state = {
    showAllDimensions: false,
    currentTool: 'wall',
    isDrawing: false,
    isDragging: false,
    objects: [],
    selectedObject: null,
    startX: undefined,
    startY: undefined,
    mouseX: undefined,
    mouseY: undefined,
    panOffsetX: 0,
    panOffsetY: 0,
    scale: 1,
    gridSize: 20, // Represents 1 foot
    pixelsPerFoot: 20,
    isResizing: false,
    resizingHandle: null, // 'start' or 'end' or corner for rects
    handleSize: 8, // pixels
    lastLabelCoords: { x: 0, y: 0 },
    editingTarget: null,
    history: [[]], // Array of object states
    historyIndex: 0, // Pointer to the current state in history
    currentObjectType: null,
    originalObjectStateOnResize: null,
    pendingObject: null,
    dimensionHitBoxes: [],

    // Imported plan data that has no canvas object: the exterior
    // boundary (feet, bottom-left origin) and plan metadata. Kept so
    // an imported plan re-exports with its boundary intact.
    planBoundary: null,
    planMeta: { title: null, address: null, date: null },

    // Canvas and context
    canvas: null,
    ctx: null,
    container: null,

    initCanvas(canv, cont) {
        this.canvas = canv;
        this.ctx = canv.getContext('2d');
        this.container = cont;
    }
};