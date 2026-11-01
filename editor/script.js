import { state } from './modules/state.js';
import { draw } from './modules/drawing.js';
import { getObjectAt, snapToGrid, getSnappedCoordinates, getHandleAt, getRectCornerHandleAt, getRotationHandlePos, getLabelHandlesPos, getAnchorForHandle } from './modules/utils.js';
import { setDrawingContext } from './modules/drawing.js';
import { editorObjectsToPlan, planToEditorObjects, parsePlanJson, planToJson, serializePlanYaml } from './modules/plan.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize canvas
    const canvasElement = document.getElementById('floorPlanCanvas');
    const containerElement = document.getElementById('canvas-container');

    if (!canvasElement) {
        console.error('Canvas element not found');
        return;
    }

    // Initialize and wire up drawing context
    state.initCanvas(canvasElement, containerElement);
    setDrawingContext(state.ctx);

    // Console debugging aid only. No module reads window globals:
    // drawing.js and utils.js import `state` directly, so the old
    // syncGlobals shim (window.gridSize/scale/handleSize/...) was
    // dead code and has been removed.
    window.state = state;

    // --- Plan persistence (localStorage) and import/export ---
    // The autosaved value is a shared-format plan, the same shape the
    // renderer reads, so a saved canvas can be rendered directly.
    const AUTOSAVE_KEY = 'floorplan-autosave-v1';
    function currentPlan() {
        return editorObjectsToPlan(state.objects, {
            boundary: state.planBoundary,
            title: state.planMeta.title || undefined,
            address: state.planMeta.address || undefined,
            date: state.planMeta.date || undefined,
        });
    }
    function noteAutosaveProblem(message) {
        const el = document.getElementById('autosave-status');
        if (el) el.textContent = message;
    }
    function persistPlan() {
        try { localStorage.setItem(AUTOSAVE_KEY, planToJson(currentPlan())); }
        catch (e) {
            // Never alert() on the autosave path (it fires during
            // ordinary editing); a footer note + console warning do.
            console.warn('floorplan-studio: autosave failed:', e);
            noteAutosaveProblem('Autosave unavailable — exports still work');
        }
    }
    function restorePlan() {
        try {
            const raw = localStorage.getItem(AUTOSAVE_KEY);
            if (!raw) return;
            const { objects, boundary, meta } = planToEditorObjects(parsePlanJson(raw));
            if (objects.length === 0) return;
            state.objects = objects;
            state.planBoundary = boundary;
            state.planMeta = meta;
            state.history = [JSON.parse(JSON.stringify(objects))];
            state.historyIndex = 0;
        } catch (e) {
            // Corrupt or old save: start empty, but say so instead
            // of silently presenting an empty canvas.
            console.warn('floorplan-studio: saved plan could not be restored:', e);
            noteAutosaveProblem('Saved plan could not be restored — starting empty');
        }
    }
    function downloadFile(filename, text, type) {
        const blob = new Blob([text], { type });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    // --- Initialization ---
    function resizeCanvas() {
        const buffer = 1000;
        if (!state.container) return;
        state.canvas.width = state.container.clientWidth + buffer;
        state.canvas.height = state.container.clientHeight + buffer;
        state.panOffsetX = state.panOffsetX === 0 ? -buffer / 2 : state.panOffsetX;
        state.panOffsetY = state.panOffsetY === 0 ? -buffer / 2 : state.panOffsetY;
        draw();
    }

    restorePlan();
    resizeCanvas();
    // A restored autosave has the same off-centre problem as a
    // fresh load (plan y is negative in canvas pixels), so
    // centre it too; with nothing restored, keep the default
    // view for drawing from scratch.
    if (state.objects.length) {
        centerViewOnPlan();
        draw();
    }
    // Footer scale label from the single source (state), not a
    // hardcoded string in index.html that could drift from it.
    const scaleInfo = document.getElementById('scale-info');
    if (scaleInfo) scaleInfo.textContent = `Scale: ${state.pixelsPerFoot}px = 1ft`;
    window.addEventListener('resize', resizeCanvas);

// --- Event Handling ---
function getMousePos(evt) {
    const rect = state.canvas.getBoundingClientRect();
    return {
        x: (evt.clientX - rect.left - state.panOffsetX) / state.scale,
        y: (evt.clientY - rect.top - state.panOffsetY) / state.scale
    };
}

function updateCoords(evt) {
    const pos = getMousePos(evt);
    const worldX = snapToGrid(pos.x);
    const worldY = snapToGrid(pos.y);
    document.getElementById('coords').textContent = `X: ${(worldX / state.pixelsPerFoot).toFixed(1)}', Y: ${(worldY / state.pixelsPerFoot).toFixed(1)}'`;
}

// Mouse events
state.canvas.addEventListener('mousedown', e => {
    const pos = getMousePos(e);
    state.mouseX = pos.x;
    state.mouseY = pos.y;
    state.startX = snapToGrid(state.mouseX);
    state.startY = snapToGrid(state.mouseY);
    
    if (e.button === 1 || e.ctrlKey) {
        state.isDragging = true;
        return;
    }

    switch (state.currentTool) {
        case 'select':
            state.isResizing = false;
            state.resizingHandle = null;
            
            if (state.selectedObject) {
                 if (['wall', 'door', 'dim', 'window'].includes(state.selectedObject.type)) {
                    state.resizingHandle = getHandleAt(state.mouseX, state.mouseY, state.selectedObject);
                } else if (['stairs', 'road'].includes(state.selectedObject.type)) {
                    const rotationHandlePos = getRotationHandlePos(state.selectedObject);
                    const distToRotateHandle = Math.sqrt(Math.pow(state.mouseX - rotationHandlePos.x, 2) + Math.pow(state.mouseY - rotationHandlePos.y, 2));
                    if (distToRotateHandle < (state.handleSize * 1.5) / state.scale) {
                        [state.selectedObject.w, state.selectedObject.h] = [state.selectedObject.h, state.selectedObject.w];
                        saveState();
                        draw();
                        return;
                    }
                    state.resizingHandle = getRectCornerHandleAt(state.mouseX, state.mouseY, state.selectedObject);
                } else if (state.selectedObject.type === 'label') {
                    const handles = getLabelHandlesPos(state.selectedObject);
                    const distToRotate = Math.sqrt(Math.pow(state.mouseX - handles.rotation.x, 2) + Math.pow(state.mouseY - handles.rotation.y, 2));
                    if (distToRotate < (state.handleSize * 1.5) / state.scale) {
                        state.selectedObject.rotation = (state.selectedObject.rotation + 90) % 360;
                        saveState();
                        draw();
                        return;
                    }
                }

                if (state.resizingHandle) {
                    state.isResizing = true;
                    state.isDrawing = true;
                    state.originalObjectStateOnResize = JSON.parse(JSON.stringify(state.selectedObject));
                    return;
                }
            }
            const objectUnderCursor = getObjectAt(state.mouseX, state.mouseY, state.objects);
            
            if (state.selectedObject && objectUnderCursor === state.selectedObject && state.selectedObject.type === 'door') {
                const hingePoint = state.selectedObject.hingeAtStart !== false ? {x: state.selectedObject.x1, y: state.selectedObject.y1} : {x: state.selectedObject.x2, y: state.selectedObject.y2};
                const latchPoint = state.selectedObject.hingeAtStart !== false ? {x: state.selectedObject.x2, y: state.selectedObject.y2} : {x: state.selectedObject.x1, y: state.selectedObject.y1};
                const distToHinge = Math.sqrt(Math.pow(state.mouseX - hingePoint.x, 2) + Math.pow(state.mouseY - hingePoint.y, 2));
                const distToLatch = Math.sqrt(Math.pow(state.mouseX - latchPoint.x, 2) + Math.pow(state.mouseY - latchPoint.y, 2));

                if (distToHinge < distToLatch) {
                    state.selectedObject.hingeAtStart = !state.selectedObject.hingeAtStart;
                } else {
                    state.selectedObject.swingDirection *= -1;
                }
                saveState();
                draw();
            }

            state.selectedObject = objectUnderCursor;
            state.isDrawing = state.selectedObject !== null;
            break;
        case 'placeObject': {
            const newObj = { type: state.currentObjectType };
            if (state.currentObjectType === 'stairs') {
                newObj.w = 3 * state.pixelsPerFoot; newObj.h = 10 * state.pixelsPerFoot;
                newObj.x = snapToGrid(state.mouseX) - newObj.w / 2;
                newObj.y = snapToGrid(state.mouseY) - newObj.h / 2;
                state.objects.push(newObj);
                saveState();
            } else if (state.currentObjectType === 'road') {
                newObj.w = 12 * state.pixelsPerFoot; newObj.h = 24 * state.pixelsPerFoot;
                newObj.x = snapToGrid(state.mouseX) - newObj.w / 2;
                newObj.y = snapToGrid(state.mouseY) - newObj.h / 2;
                state.objects.push(newObj);
                state.pendingObject = newObj;
                openLabelModal('Enter Road Name', 'Provide a name for the road (e.g., Main St).', 'Road Name');
            }
            break;
        }
        case 'eraser':
            const objectToDelete = getObjectAt(state.mouseX, state.mouseY, state.objects);
            if(objectToDelete) {
                state.objects = state.objects.filter(o => o !== objectToDelete);
                saveState();
            }
            break;
        case 'label':
            state.lastLabelCoords = { x: state.mouseX, y: state.mouseY };
            openLabelModal('Enter Label Text', 'Type the desired text for your label below.', '');
            break;
        default:
            state.isDrawing = true;
    }
    draw();
});

state.canvas.addEventListener('mousemove', e => {
    const pos = getMousePos(e);
    updateCoords(e);
    
    if (state.currentTool === 'select') {
        let cursorSet = false;
         if (state.selectedObject) {
            const rotationHandlePos = ['stairs', 'road'].includes(state.selectedObject.type) ? getRotationHandlePos(state.selectedObject) : null;
            if(rotationHandlePos && Math.sqrt(Math.pow(pos.x - rotationHandlePos.x, 2) + Math.pow(pos.y - rotationHandlePos.y, 2)) < (state.handleSize * 1.5) / state.scale) {
                state.canvas.style.cursor = 'pointer';
                cursorSet = true;
            } else if (state.selectedObject.type === 'label') {
                const labelHandles = getLabelHandlesPos(state.selectedObject);
                const distToRotate = Math.sqrt(Math.pow(pos.x - labelHandles.rotation.x, 2) + Math.pow(pos.y - labelHandles.rotation.y, 2));
                if(distToRotate < (state.handleSize*1.5)/state.scale) {
                    state.canvas.style.cursor = 'pointer';
                    cursorSet = true;
                }
            } else {
                const cornerHandle = ['stairs', 'road'].includes(state.selectedObject.type) ? getRectCornerHandleAt(pos.x, pos.y, state.selectedObject) : null;
                if(cornerHandle) {
                   const cursors = { tl: 'nwse-resize', br: 'nwse-resize', tr: 'nesw-resize', bl: 'nesw-resize'};
                   state.canvas.style.cursor = cursors[cornerHandle];
                   cursorSet = true;
                }
            }
         }
         if(!cursorSet) {
            state.canvas.style.cursor = getObjectAt(pos.x, pos.y, state.objects) ? 'pointer' : 'move';
         }
    }

    if (state.isDragging) {
        state.panOffsetX += e.movementX;
        state.panOffsetY += e.movementY;
        draw();
        return;
    }
    
    if (!state.isDrawing) return;

    state.mouseX = pos.x;
    state.mouseY = pos.y;

    if (state.currentTool === 'select' && state.selectedObject) {
        if (state.isResizing) {
            const currentX = snapToGrid(state.mouseX);
            const currentY = snapToGrid(state.mouseY);
            if (['wall', 'door', 'dim', 'window'].includes(state.selectedObject.type)) {
                if (state.resizingHandle === 'start') {
                    const snapped = getSnappedCoordinates(currentX, currentY, state.selectedObject.x2, state.selectedObject.y2);
                    state.selectedObject.x1 = snapped.x; state.selectedObject.y1 = snapped.y;
                } else {
                    const snapped = getSnappedCoordinates(currentX, currentY, state.selectedObject.x1, state.selectedObject.y1);
                    state.selectedObject.x2 = snapped.x; state.selectedObject.y2 = snapped.y;
                }
                if(state.selectedObject.type === 'dim') {
                     const dist = Math.sqrt(Math.pow(state.selectedObject.x2 - state.selectedObject.x1, 2) + Math.pow(state.selectedObject.y2 - state.selectedObject.y1, 2));
                     state.selectedObject.dist = `${(dist / state.pixelsPerFoot).toFixed(2)}'`;
                }
            } else if (['stairs', 'road'].includes(state.selectedObject.type)) {
                const anchor = getAnchorForHandle(state.resizingHandle, state.originalObjectStateOnResize);
                state.selectedObject.x = Math.min(anchor.x, currentX);
                state.selectedObject.y = Math.min(anchor.y, currentY);
                state.selectedObject.w = Math.abs(currentX - anchor.x);
                state.selectedObject.h = Math.abs(currentY - anchor.y);
            }
        } else { // Move logic
            const dx = state.mouseX - state.startX;
            const dy = state.mouseY - state.startY;

            if (['rect', 'label', 'stairs', 'road'].includes(state.selectedObject.type)) {
                state.selectedObject.x += dx;
                state.selectedObject.y += dy;
            } else {
                state.selectedObject.x1 += dx;
                state.selectedObject.y1 += dy;
                state.selectedObject.x2 += dx;
                state.selectedObject.y2 += dy;
            }
            state.startX = state.mouseX;
            state.startY = state.mouseY;
        }
    }
    
    draw();
});

state.canvas.addEventListener('mouseup', e => {
    state.isDragging = false;
    if (state.isResizing) {
        state.isResizing = false;
        state.originalObjectStateOnResize = null;
    }
    if (!state.isDrawing) return;
    
    let actionTaken = false;
    const originalStartX = state.startX;
    const originalStartY = state.startY;

    state.isDrawing = false;
    const endX = snapToGrid(state.mouseX);
    const endY = snapToGrid(state.mouseY);

    if (state.currentTool === 'select' && state.selectedObject) {
        actionTaken = true; 
    } else {
        switch (state.currentTool) {
            case 'wall': case 'window': case 'door': case 'rect': case 'dim': {
                const snapped = getSnappedCoordinates(endX, endY, originalStartX, originalStartY);
                if (snapped.x !== originalStartX || snapped.y !== originalStartY) {
                    actionTaken = true;
                    if (state.currentTool === 'wall') state.objects.push({ type: 'wall', x1: originalStartX, y1: originalStartY, x2: snapped.x, y2: snapped.y });
                    else if (state.currentTool === 'window') state.objects.push({ type: 'window', x1: originalStartX, y1: originalStartY, x2: snapped.x, y2: snapped.y });
                    else if (state.currentTool === 'door') state.objects.push({ type: 'door', x1: originalStartX, y1: originalStartY, x2: snapped.x, y2: snapped.y, swingDirection: 1, hingeAtStart: true });
                    else if (state.currentTool === 'rect') state.objects.push({ type: 'rect', x: Math.min(originalStartX, endX), y: Math.min(originalStartY, endY), w: Math.abs(endX - originalStartX), h: Math.abs(endY - originalStartY) });
                    else if (state.currentTool === 'dim') {
                        const dist = Math.sqrt(Math.pow(snapped.x - originalStartX, 2) + Math.pow(snapped.y - originalStartY, 2));
                        state.objects.push({ type: 'dim', x1: originalStartX, y1: originalStartY, x2: snapped.x, y2: snapped.y, dist: `${(dist / state.pixelsPerFoot).toFixed(2)}'` });
                    }
                }
                break;
            }
            case 'select':
                if (!state.selectedObject) state.selectedObject = null;
                break;
        }
    }

    if (actionTaken) saveState();
    draw();
});

state.canvas.addEventListener('dblclick', e => {
    const pos = getMousePos(e);
    if (state.showAllDimensions) {
        for (const hitBox of state.dimensionHitBoxes) {
            const dx = pos.x - hitBox.x;
            const dy = pos.y - hitBox.y;
            const angle = -hitBox.angle;
            const rotatedX = dx * Math.cos(angle) - dy * Math.sin(angle);
            const rotatedY = dx * Math.sin(angle) + dy * Math.cos(angle);
            
            if (Math.abs(rotatedX) < hitBox.width / 2 && Math.abs(rotatedY) < hitBox.height / 2) {
                createDimensionEditor(hitBox);
                return;
            }
        }
    }

    const objectToEdit = getObjectAt(pos.x, pos.y, state.objects);
    if (objectToEdit) {
        if (objectToEdit.type === 'label') {
            state.editingTarget = { obj: objectToEdit, prop: 'text' };
            openLabelModal('Edit Label Text', 'Update the text for your label.', state.editingTarget.obj[state.editingTarget.prop]);
        } else if (objectToEdit.type === 'road') {
            state.editingTarget = { obj: objectToEdit, prop: 'label' };
            openLabelModal('Edit Road Name', 'Update the name for the road.', state.editingTarget.obj[state.editingTarget.prop] || '');
        }
    }
});

state.canvas.addEventListener('wheel', e => {
    e.preventDefault();
    const zoomIntensity = 0.1;
    const wheel = e.deltaY < 0 ? 1 : -1;
    const zoom = Math.exp(wheel * zoomIntensity);
    const newScale = Math.max(0.1, Math.min(5, state.scale * zoom));
    const mousePos = getMousePos(e);
    state.panOffsetX -= mousePos.x * state.scale * (zoom - 1);
    state.panOffsetY -= mousePos.y * state.scale * (zoom - 1);
    state.scale = newScale;
    document.getElementById('zoom-level').textContent = `Zoom: ${Math.round(state.scale * 100)}%`;
    draw();
});

// --- Tool and UI Functions ---
function setActiveTool(tool) {
    state.currentTool = tool;
    if (tool !== 'select') state.selectedObject = null;
    if (tool !== 'placeObject') state.currentObjectType = null;
    document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`${tool}-tool`);
    if (activeBtn) activeBtn.classList.add('active');
    state.canvas.classList.remove('custom-cursor-eraser');
    state.canvas.style.cursor = 'crosshair';
    if (tool === 'select') state.canvas.style.cursor = 'move';
    if (tool === 'label') state.canvas.style.cursor = 'text';
    if (tool === 'eraser') state.canvas.classList.add('custom-cursor-eraser');
    draw();
}

// --- Dimension Editor ---
function createDimensionEditor(hitBox) {
    const existingEditor = document.getElementById('dimension-editor');
    if (existingEditor) existingEditor.remove();

    const input = document.createElement('input');
    input.type = 'text';
    input.id = 'dimension-editor';
    
    const canvasRect = state.canvas.getBoundingClientRect();
    
    const worldX = hitBox.x, worldY = hitBox.y;
    const screenX = (worldX * state.scale + state.panOffsetX) + canvasRect.left;
    const screenY = (worldY * state.scale + state.panOffsetY) + canvasRect.top;

    let currentValue;
    if(hitBox.type === 'width') currentValue = hitBox.object.w / state.pixelsPerFoot;
    else if (hitBox.type === 'height') currentValue = hitBox.object.h / state.pixelsPerFoot;
    else currentValue = Math.sqrt(Math.pow(hitBox.object.x2 - hitBox.object.x1, 2) + Math.pow(hitBox.object.y2 - hitBox.object.y1, 2)) / state.pixelsPerFoot;

    input.value = currentValue.toFixed(2);
    
    input.style.left = `${screenX - (hitBox.width * state.scale)/2 - 5}px`;
    input.style.top = `${screenY - (hitBox.height * state.scale) - 5}px`;
    input.style.width = `${hitBox.width * state.scale + 10}px`;
    input.style.height = `${hitBox.height * state.scale + 10}px`;
    input.style.fontSize = `${14 * state.scale}px`;

    document.body.appendChild(input);
    input.focus();
    input.select();

    const applyChange = () => {
        if (!input.parentNode) return; // FIX: Check if node is still in DOM

        const newValue = parseFloat(input.value);
        if (!isNaN(newValue) && newValue > 0) {
            const newPixelValue = newValue * state.pixelsPerFoot;
            const obj = hitBox.object;

            if (hitBox.type === 'length') {
                const dx = obj.x2 - obj.x1;
                const dy = obj.y2 - obj.y1;
                const currentLength = Math.sqrt(dx*dx + dy*dy);
                if (currentLength > 0) {
                    const ratio = newPixelValue / currentLength;
                    obj.x2 = obj.x1 + dx * ratio;
                    obj.y2 = obj.y1 + dy * ratio;
                    if (obj.type === 'dim') obj.dist = `${newValue.toFixed(2)}'`;
                }
            } else if (hitBox.type === 'width') {
                obj.w = newPixelValue;
            } else if (hitBox.type === 'height') {
                obj.h = newPixelValue;
            }

            saveState();
            draw();
        }
        input.remove();
    };

    input.addEventListener('blur', applyChange);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyChange();
        } else if (e.key === 'Escape') {
             if (input.parentNode) {
               input.remove();
            }
        }
    });
}

// --- Modal Logic ---
const labelModal = document.getElementById('label-modal');
const labelModalTitle = document.getElementById('label-modal-title');
const labelModalSubtitle = document.getElementById('label-modal-subtitle');
const labelInput = document.getElementById('label-input');
const cancelLabelBtn = document.getElementById('cancel-label');
const confirmLabelBtn = document.getElementById('confirm-label');

// Modal helpers: toggle both 'hidden' and 'flex' to avoid utility-class conflicts
function showModal(el) {
    if (!el) return;
    el.classList.remove('hidden');
    el.classList.add('flex');
}
function hideModal(el) {
    if (!el) return;
    el.classList.add('hidden');
    el.classList.remove('flex');
}

function openLabelModal(title, subtitle, value) {
    labelModalTitle.textContent = title;
    labelModalSubtitle.textContent = subtitle;
    labelInput.value = value;
    showModal(labelModal);
    labelInput.focus();
    labelInput.select();
}

const clearModal = document.getElementById('clear-modal');
const cancelClearBtn = document.getElementById('cancel-clear');
const confirmClearBtn = document.getElementById('confirm-clear');

document.getElementById('clear-canvas').addEventListener('click', () => {
    showModal(clearModal);
});
cancelClearBtn.addEventListener('click', () => {
    hideModal(clearModal);
});
confirmClearBtn.addEventListener('click', () => {
    if (state.objects.length > 0) { state.objects = []; state.selectedObject = null; saveState(); }
    hideModal(clearModal);
    draw();
});
clearModal.addEventListener('click', (e) => { if (e.target === clearModal) hideModal(clearModal); });

cancelLabelBtn.addEventListener('click', () => {
    if(state.pendingObject) {
        state.objects = state.objects.filter(o => o !== state.pendingObject);
        state.pendingObject = null;
    }
    state.editingTarget = null;
    hideModal(labelModal);
    draw();
});

confirmLabelBtn.addEventListener('click', () => {
    const text = labelInput.value;
    if (state.pendingObject) {
        if (text) state.pendingObject.label = text;
        saveState();
        state.pendingObject = null;
    } else if (state.editingTarget) {
        if(text || state.editingTarget.obj.type !== 'label') {
            state.editingTarget.obj[state.editingTarget.prop] = text;
        } else {
             state.objects = state.objects.filter(o => o !== state.editingTarget.obj);
        }
        saveState();
        state.editingTarget = null;
    } else if (text) {
        state.objects.push({type: 'label', text: text, x: state.lastLabelCoords.x, y: state.lastLabelCoords.y, rotation: 0});
        saveState();
    }
    hideModal(labelModal);
    draw();
});
labelModal.addEventListener('click', (e) => { if (e.target === labelModal) cancelLabelBtn.click(); });
labelInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') confirmLabelBtn.click();
    if (e.key === 'Escape') cancelLabelBtn.click();
});

document.getElementById('show-dims-toggle').addEventListener('change', e => { state.showAllDimensions = e.target.checked; draw(); });

const objectLibraryModal = document.getElementById('object-library-modal');
document.getElementById('close-object-library').addEventListener('click', () => hideModal(objectLibraryModal));
objectLibraryModal.addEventListener('click', e => {
    if (e.target === objectLibraryModal) hideModal(objectLibraryModal);
    const objectBtn = e.target.closest('.object-btn');
    if (objectBtn) {
        state.currentObjectType = objectBtn.dataset.objectType;
        setActiveTool('placeObject');
        hideModal(objectLibraryModal);
    }
});

// --- History (Undo/Redo) Logic ---
const undoBtn = document.getElementById('undo-btn');
const redoBtn = document.getElementById('redo-btn');
// History is a full deep copy per action, so it must be bounded:
// a long session otherwise grows memory linearly with no ceiling.
const MAX_HISTORY = 100;
function saveState() {
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push(JSON.parse(JSON.stringify(state.objects)));
    if (state.history.length > MAX_HISTORY) state.history.shift();
    state.historyIndex = state.history.length - 1;
    updateButtonStates();
    persistPlan();
}
function undo() {
    if (state.historyIndex > 0) {
        state.historyIndex--;
        state.objects = JSON.parse(JSON.stringify(state.history[state.historyIndex]));
        state.selectedObject = null;
        draw();
        updateButtonStates();
        persistPlan();
    }
}
function redo() {
    if (state.historyIndex < state.history.length - 1) {
        state.historyIndex++;
        state.objects = JSON.parse(JSON.stringify(state.history[state.historyIndex]));
        state.selectedObject = null;
        draw();
        updateButtonStates();
        persistPlan();
    }
}
function updateButtonStates() {
    undoBtn.disabled = state.historyIndex <= 0;
    redoBtn.disabled = state.historyIndex >= state.history.length - 1;
}
undoBtn.addEventListener('click', undo);
redoBtn.addEventListener('click', redo);

// --- Event Listeners ---
document.getElementById('toolbar').addEventListener('click', e => {
    const button = e.target.closest('button');
    if (!button) return;
    if (['export-json-btn', 'export-yaml-btn', 'import-btn', 'load-sample-btn', 'clear-canvas', 'undo-btn', 'redo-btn'].includes(button.id)) return;
    const tool = button.id.replace('-tool', '');
    if (tool === 'objects') {
        if (allowModalOpen) showModal(document.getElementById('object-library-modal'));
    }
    else if (['select', 'wall', 'rect', 'door', 'window', 'label', 'dim', 'eraser'].includes(tool)) setActiveTool(tool);
});

window.addEventListener('keydown', e => {
    const keyMap = { 'v': 'select', 'w': 'wall', 'r': 'rect', 'd': 'door', 'i':'window', 'o':'objects', 't': 'label', 'm': 'dim', 'e': 'eraser' };
    if (document.activeElement.tagName === 'INPUT') return;
    if (keyMap[e.key] === 'objects') {
        if (allowModalOpen) showModal(document.getElementById('object-library-modal'));
    } else if (keyMap[e.key]) setActiveTool(keyMap[e.key]);
    
    if(e.key === 'Delete' || e.key === 'Backspace') {
        if(state.selectedObject) {
            state.objects = state.objects.filter(o => o !== state.selectedObject);
            state.selectedObject = null;
            saveState();
            draw();
        }
    }
    if (e.ctrlKey && e.key === 'Backspace') document.getElementById('clear-canvas').click();
    if (e.ctrlKey) {
        if (e.key === 'z') { e.preventDefault(); undo(); } 
        else if (e.key === 'y') { e.preventDefault(); redo(); }
    }
});

// Ensure any modals are hidden on initial load (robust against unexpected state)
const objModal = document.getElementById('object-library-modal');
const lblModal = document.getElementById('label-modal');
const clrModal = document.getElementById('clear-modal');
if (objModal) hideModal(objModal);
if (lblModal) hideModal(lblModal);
if (clrModal) hideModal(clrModal);

// Prevent accidental modal openings during initial page load / focus changes.
// We'll enable modal openings after a short delay once the UI has settled.
let allowModalOpen = false;
setTimeout(() => { allowModalOpen = true; }, 300);

// --- Plan import / export ---
document.getElementById('export-json-btn').addEventListener('click', () => {
    downloadFile('floor-plan.json', planToJson(currentPlan()), 'application/json');
});
document.getElementById('export-yaml-btn').addEventListener('click', () => {
    downloadFile('floor-plan.yaml', serializePlanYaml(currentPlan()), 'text/yaml');
});
// Centre the view on the current canvas contents, zooming out
// (never in) if they do not fit. Loaded plans need this:
// plan coordinates are feet, y up, so a plan becomes canvas
// pixels with y from -height to 0 (north is negative), while
// the editor's initial view shows world x/y from 500 onwards
// (pan -500, scroll 0). Without centring, a loaded plan sits
// entirely above the viewport — out of sight, not just off-centre.
// Scroll is reset to 0 first, because pan is measured from
// the canvas origin, not from the scrolled position.
function centerViewOnPlan() {
    if (!state.container) return;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const include = (x1, y1, x2, y2) => {
        minX = Math.min(minX, x1, x2); maxX = Math.max(maxX, x1, x2);
        minY = Math.min(minY, y1, y2); maxY = Math.max(maxY, y1, y2);
    };
    for (const obj of state.objects || []) {
        if (!obj || typeof obj !== 'object') continue;
        if (typeof obj.x1 === 'number' && typeof obj.x2 === 'number'
            && typeof obj.y1 === 'number' && typeof obj.y2 === 'number') {
            include(obj.x1, obj.y1, obj.x2, obj.y2);
        } else if (typeof obj.x === 'number' && typeof obj.y === 'number'
            && typeof obj.w === 'number' && typeof obj.h === 'number') {
            include(obj.x, obj.y, obj.x + obj.w, obj.y + obj.h);
        } else if (typeof obj.x === 'number' && typeof obj.y === 'number') {
            include(obj.x, obj.y, obj.x, obj.y);
        }
    }
    // No canvas objects (a plan with only a boundary): fall back
    // to the boundary, converted feet -> canvas pixels (y flip).
    if (minX === Infinity && Array.isArray(state.planBoundary) && state.planBoundary.length) {
        const ppf = state.pixelsPerFoot;
        for (const [bx, by] of state.planBoundary) {
            include(bx * ppf, -by * ppf, bx * ppf, -by * ppf);
        }
    }
    if (minX === Infinity) return;
    const vw = state.container.clientWidth;
    const vh = state.container.clientHeight;
    if (!vw || !vh) return;
    const margin = 40;
    const bw = Math.max(maxX - minX, 1);
    const bh = Math.max(maxY - minY, 1);
    // Fit, but never zoom in past the current scale: a small
    // plan at 100% stays at 100%, a large plan zooms out just
    // enough to fit with a margin. Scale limits match the
    // wheel-zoom handler (0.1–5).
    const fitScale = Math.min((vw - 2 * margin) / bw, (vh - 2 * margin) / bh);
    const newScale = Math.max(0.1, Math.min(5, Math.min(state.scale, fitScale)));
    state.scale = newScale;
    state.container.scrollLeft = 0;
    state.container.scrollTop = 0;
    state.panOffsetX = vw / 2 - ((minX + maxX) / 2) * newScale;
    state.panOffsetY = vh / 2 - ((minY + maxY) / 2) * newScale;
    const zoomEl = document.getElementById('zoom-level');
    if (zoomEl) zoomEl.textContent = `Zoom: ${Math.round(newScale * 100)}%`;
}
// Shared by Import and Load sample: replacing the canvas with a
// plan JSON, resetting history to it, centring the view on it,
// and autosaving it. (Like Import, this discards the previous
// canvas — export first if you want to keep it; Undo cannot
// reach back past a load.)
function loadPlanFromJson(text) {
    const { objects, boundary, meta } = planToEditorObjects(parsePlanJson(text));
    state.objects = objects;
    state.selectedObject = null;
    state.planBoundary = boundary;
    state.planMeta = meta;
    state.history = [JSON.parse(JSON.stringify(objects))];
    state.historyIndex = 0;
    centerViewOnPlan();
    updateButtonStates();
    persistPlan();
    draw();
}
const importFileInput = document.getElementById('import-file');
document.getElementById('import-btn').addEventListener('click', () => importFileInput.click());
importFileInput.addEventListener('change', () => {
    const file = importFileInput.files && importFileInput.files[0];
    if (!file) return;
    if (/\.ya?ml$/i.test(file.name)) {
        // The editor exports YAML but imports JSON only. Say so
        // with a path forward instead of a dead-end parse error.
        // (A real YAML import, e.g. via js-yaml, is follow-up work.)
        alert('That file is YAML. Convert it first, then import the JSON:\n'
            + 'floorplan convert plan.yaml plan.json');
        importFileInput.value = '';
        return;
    }
    file.text().then(loadPlanFromJson).catch((err) => {
        alert(`Could not import that plan: ${err.message}`);
    }).finally(() => { importFileInput.value = ''; });
});
// The bundled sample: editor/sample-plan.json is a copy of
// examples/floor_plan.json, kept identical by a CI contract
// check, so it ships inside the Pages artifact (which uploads
// only editor/) and works wherever the editor is served.
// A relative fetch, so it resolves under a Pages subpath too;
// opening the editor from a file:// URL cannot fetch, and the
// alert says so with the Import fallback.
document.getElementById('load-sample-btn').addEventListener('click', () => {
    fetch('sample-plan.json').then((res) => {
        if (!res.ok) throw new Error(`sample plan not found (${res.status})`);
        return res.text();
    }).then(loadPlanFromJson).catch((err) => {
        alert(`Could not load the sample plan: ${err.message}\n\n`
            + 'If you opened the editor from a file, run a local server instead, '
            + 'or use Import JSON with examples/floor_plan.json from the repo.');
    });
});

setActiveTool('wall');
updateButtonStates();
});