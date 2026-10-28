// Drawing functions
import { state } from './state.js';
import { snapToGrid, getSnappedCoordinates, getRotationHandlePos, getLabelHandlesPos } from './utils.js';

let ctx = null;

export function setDrawingContext(context) {
    ctx = context;
}

export function drawGrid() {
    // Draw grid in world coordinates. The drawing context has already been
    // translated by state.panOffset and scaled by state.scale in `draw()` so
    // we compute world-space bounds and iterate by unscaled grid size.
    // Slightly stronger grid so it's visible on large canvases
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
    // Keep a consistent hairline by compensating for canvas scale
    ctx.lineWidth = 1 / Math.max(1, state.scale);
    const gridSize = state.gridSize; // grid spacing in world pixels

    const canvasWidthWorld = ctx.canvas.width / Math.max(1, state.scale);
    const canvasHeightWorld = ctx.canvas.height / Math.max(1, state.scale);
    const worldLeft = -state.panOffsetX / Math.max(1, state.scale);
    const worldTop = -state.panOffsetY / Math.max(1, state.scale);

    // Extend one extra grid step before/after to avoid edge clipping
    const startGridX = Math.floor((worldLeft - gridSize) / gridSize) * gridSize;
    const startGridY = Math.floor((worldTop - gridSize) / gridSize) * gridSize;
    const endX = Math.ceil((worldLeft + canvasWidthWorld + gridSize) / gridSize) * gridSize;
    const endY = Math.ceil((worldTop + canvasHeightWorld + gridSize) / gridSize) * gridSize;


    for (let x = startGridX; x <= endX; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, worldTop);
        ctx.lineTo(x, worldTop + canvasHeightWorld);
        ctx.stroke();
    }

    for (let y = startGridY; y <= endY; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(worldLeft, y);
        ctx.lineTo(worldLeft + canvasWidthWorld, y);
        ctx.stroke();
    }
}

export function draw() {
    if (!ctx) {
        // Try to recover the context from the shared canvas reference
        if (state.canvas && state.canvas.getContext) {
            ctx = state.canvas.getContext('2d');
            console.warn('drawing.js: ctx was missing; recovered from state.canvas');
        } else {
            console.error('Canvas context not available and no canvas to recover from');
            return;
        }
    }
    ctx.save();
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    // Fill background
    ctx.fillStyle = '#374151'; // gray-700
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.translate(state.panOffsetX, state.panOffsetY);
    ctx.scale(state.scale, state.scale);
    drawGrid();
    
    state.dimensionHitBoxes.length = 0; // Clear hit boxes for redraw
    
    state.objects.forEach(obj => drawObject(obj));

    if (state.showAllDimensions) {
        state.objects.forEach(obj => {
            if (['wall', 'door', 'window', 'dim'].includes(obj.type)) {
                 ctx.save();
                 drawDimensionText(obj.x1, obj.y1, obj.x2, obj.y2, '#fcd34d', obj, 'length');
                 ctx.restore();
            } else if (['rect', 'stairs'].includes(obj.type)) {
                // Draw width dimension
                drawDimensionText(obj.x, obj.y + obj.h/2, obj.x + obj.w, obj.y + obj.h/2, '#fcd34d', obj, 'width');
                // Draw height dimension
                drawDimensionText(obj.x + obj.w/2, obj.y, obj.x + obj.w/2, obj.y + obj.h, '#fcd34d', obj, 'height');
            }
        });
    }

    if (state.selectedObject) {
        highlightObject(state.selectedObject);
        if (!state.showAllDimensions) {
            drawSelectionDetails(state.selectedObject);
        } else if (['wall', 'door', 'dim', 'window'].includes(state.selectedObject.type)) {
            drawResizeHandles(state.selectedObject);
        } else if (['stairs', 'road'].includes(state.selectedObject.type)) {
            drawRectHandles(state.selectedObject);
        } else if (state.selectedObject.type === 'label') {
            drawLabelHandles(state.selectedObject);
        }
    }
    
    if (state.isDrawing && ['wall', 'rect', 'dim', 'door', 'window'].includes(state.currentTool)) {
        ctx.strokeStyle = '#6366f1';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        let currentX = snapToGrid(state.mouseX);
        let currentY = snapToGrid(state.mouseY);
        
        if (['wall', 'door', 'dim', 'window'].includes(state.currentTool)) {
            const snapped = getSnappedCoordinates(currentX, currentY, state.startX, state.startY);
            currentX = snapped.x;
            currentY = snapped.y;
        }
        
        if(state.currentTool === 'rect') {
            const rectW = currentX - state.startX;
            const rectH = currentY - state.startY;
            ctx.strokeRect(state.startX, state.startY, rectW, rectH);
            const width = Math.abs(rectW);
            const height = Math.abs(rectH);
            if (width > 0 || height > 0) {
                const text = `${(width / state.pixelsPerFoot).toFixed(2)}' x ${(height / state.pixelsPerFoot).toFixed(2)}'`;
                ctx.save();
                ctx.setLineDash([]);
                ctx.fillStyle = '#6366f1';
                ctx.font = `${14 / state.scale}px Inter`;
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                ctx.fillText(text, state.mouseX + 10 / state.scale, state.mouseY + 10 / state.scale);
                ctx.restore();
            }
        } else if (state.currentTool === 'dim') {
            drawDimensionPreview(state.startX, state.startY, currentX, currentY);
        } else {
            ctx.beginPath();
            ctx.moveTo(state.startX, state.startY);
            ctx.lineTo(currentX, currentY);
            ctx.stroke();

            if (['wall', 'door', 'window'].includes(state.currentTool)) {
                ctx.save();
                ctx.setLineDash([]);
                drawDimensionText(state.startX, state.startY, currentX, currentY, '#6366f1');
                ctx.restore();
            }
        }
        ctx.setLineDash([]);
    }
    
    ctx.restore();
}

export function drawObject(obj) {
    switch(obj.type) {
        case 'wall':
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 5;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(obj.x1, obj.y1);
            ctx.lineTo(obj.x2, obj.y2);
            ctx.stroke();
            break;
        case 'window':
            ctx.strokeStyle = '#67e8f9';
            ctx.lineWidth = 3;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(obj.x1, obj.y1);
            ctx.lineTo(obj.x2, obj.y2);
            ctx.stroke();
            break;
        case 'rect':
            ctx.strokeStyle = '#a5b4fc';
            ctx.lineWidth = 3;
            ctx.strokeRect(obj.x, obj.y, obj.w, obj.h);
            break;
        case 'door':
            {
                let hingeX, hingeY, latchX, latchY;
                if (obj.hingeAtStart === false) { hingeX = obj.x2; hingeY = obj.y2; latchX = obj.x1; latchY = obj.y1; } 
                else { hingeX = obj.x1; hingeY = obj.y1; latchX = obj.x2; latchY = obj.y2; }
                const len = Math.sqrt(Math.pow(latchX - hingeX, 2) + Math.pow(latchY - hingeY, 2));
                ctx.strokeStyle = 'rgba(252, 165, 165, 0.8)';
                ctx.lineWidth = 2;
                ctx.setLineDash([2, 4]);
                ctx.beginPath();
                ctx.moveTo(obj.x1, obj.y1);
                ctx.lineTo(obj.x2, obj.y2);
                ctx.stroke();
                ctx.setLineDash([]);
                if (len === 0) break;
                const vecX = latchX - hingeX, vecY = latchY - hingeY;
                const endPointX = hingeX - vecY * (obj.swingDirection || 1);
                const endPointY = hingeY + vecX * (obj.swingDirection || 1);
                ctx.strokeStyle = '#fca5a5';
                ctx.lineWidth = 3;
                ctx.lineCap = 'round';
                ctx.beginPath();
                ctx.moveTo(hingeX, hingeY);
                ctx.lineTo(endPointX, endPointY);
                ctx.stroke();
                ctx.lineWidth = 1;
                ctx.strokeStyle = 'rgba(252, 165, 165, 0.7)';
                const startAngle = Math.atan2(latchY - hingeY, latchX - hingeX);
                const endAngle = Math.atan2(endPointY - hingeY, endPointX - hingeX);
                ctx.beginPath();
                const counterClockwise = (obj.swingDirection || 1) === -1;
                ctx.arc(hingeX, hingeY, len, startAngle, endAngle, counterClockwise);
                ctx.stroke();
            }
            break;
        case 'stairs':
            drawStairs(obj);
            break;
        case 'road':
            drawRoad(obj);
            break;
        case 'label':
            ctx.save();
            ctx.font = `${16 / state.scale}px Inter`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.translate(obj.x, obj.y);
            ctx.rotate(obj.rotation * Math.PI / 180);
            ctx.fillStyle = 'white';
            ctx.fillText(obj.text, 0, 0);
            ctx.restore();
            break;
        case 'dim':
            drawDimensionLine(obj.x1, obj.y1, obj.x2, obj.y2, obj.dist);
            break;
    }
}

function drawStairs(obj) {
    ctx.strokeStyle = '#a5b4fc';
    ctx.lineWidth = 2;
    ctx.strokeRect(obj.x, obj.y, obj.w, obj.h);
    const numSteps = Math.max(2, Math.round(Math.max(obj.w, obj.h) / state.pixelsPerFoot));
    const isVertical = obj.h > obj.w;
    
    if (isVertical) {
        const stepHeight = obj.h / numSteps;
        for (let i = 1; i < numSteps; i++) {
            ctx.beginPath();
            ctx.moveTo(obj.x, obj.y + i * stepHeight);
            ctx.lineTo(obj.x + obj.w, obj.y + i * stepHeight);
            ctx.stroke();
        }
    } else { // Horizontal
        const stepWidth = obj.w / numSteps;
        for (let i = 1; i < numSteps; i++) {
            ctx.beginPath();
            ctx.moveTo(obj.x + i * stepWidth, obj.y);
            ctx.lineTo(obj.x + i * stepWidth, obj.y + obj.h);
            ctx.stroke();
        }
    }
}

function drawRoad(obj) {
    ctx.save();
    ctx.fillStyle = '#4b5563'; // Dark Gray
    ctx.fillRect(obj.x, obj.y, obj.w, obj.h);
    ctx.strokeStyle = '#facc15'; // Yellow
    ctx.lineWidth = 3 / state.scale;
    ctx.setLineDash([15 / state.scale, 15 / state.scale]);
    ctx.beginPath();
    if (obj.w < obj.h) { // Vertical
        ctx.moveTo(obj.x + obj.w / 2, obj.y);
        ctx.lineTo(obj.x + obj.w / 2, obj.y + obj.h);
    } else { // Horizontal
        ctx.moveTo(obj.x, obj.y + obj.h / 2);
        ctx.lineTo(obj.x + obj.w, obj.y + obj.h / 2);
    }
    ctx.stroke();
    ctx.setLineDash([]);

    if(obj.label) {
    ctx.font = `bold ${16 / state.scale}px Inter`;
    const textMetrics = ctx.measureText(obj.label);
    const textWidth = textMetrics.width;
    const padding = 10 / state.scale;
    const signWidth = textWidth + (padding * 2);
    const signHeight = (16 / state.scale) + (padding * 2);
        
        const signX = obj.x + (obj.w / 2) - (signWidth / 2);
        const signY = obj.y + (obj.h / 2) - (signHeight / 2);
        
        ctx.fillStyle = '#166534'; // Dark Green
        ctx.fillRect(signX, signY, signWidth, signHeight);
        
        ctx.fillStyle = 'white';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(obj.label, signX + signWidth / 2, signY + signHeight / 2);
    }
    ctx.restore();
}

function highlightObject(obj) {
    ctx.save();
    ctx.strokeStyle = '#34d399';
    ctx.lineWidth = 3;
    ctx.setLineDash([8, 4]);

    switch(obj.type) {
        case 'wall': case 'door': case 'dim': case 'window':
            ctx.beginPath();
            ctx.moveTo(obj.x1, obj.y1);
            ctx.lineTo(obj.x2, obj.y2);
            ctx.stroke();
            break;
        case 'stairs': case 'road': case 'rect':
            ctx.strokeRect(obj.x - 5, obj.y - 5, obj.w + 10, obj.h + 10);
            break;
        case 'label':
            ctx.font = `${16 / state.scale}px Inter`;
            const textWidth = ctx.measureText(obj.text).width;
            const textHeight = 16 / state.scale;
            ctx.translate(obj.x, obj.y);
            ctx.rotate(obj.rotation * Math.PI / 180);
            ctx.strokeRect(-textWidth / 2 - 5, -textHeight / 2 - 5, textWidth + 10, textHeight + 10);
            break;
    }
    ctx.restore();
}

function drawResizeHandles(obj) {
    ctx.fillStyle = '#34d399';
    const scaledHandleSize = (state.handleSize || 8) / state.scale;
    ctx.beginPath();
    ctx.arc(obj.x1, obj.y1, scaledHandleSize, 0, 2 * Math.PI);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(obj.x2, obj.y2, scaledHandleSize, 0, 2 * Math.PI);
    ctx.fill();
}

function drawRectHandles(obj) {
    const scaledHandleSize = (state.handleSize || 8) / state.scale;
    const corners = {
        tl: { x: obj.x, y: obj.y },
        tr: { x: obj.x + obj.w, y: obj.y },
        bl: { x: obj.x, y: obj.y + obj.h },
        br: { x: obj.x + obj.w, y: obj.y + obj.h }
    };

    ctx.fillStyle = '#34d399';
    for (const pos of Object.values(corners)) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, scaledHandleSize * 1.2, 0, 2 * Math.PI);
        ctx.fill();
    }

    const rotationHandlePos = getRotationHandlePos(obj);
    ctx.strokeStyle = '#34d399';
    ctx.lineWidth = 2 / state.scale;
    ctx.beginPath();
    ctx.moveTo(obj.x + obj.w / 2, obj.y + obj.h / 2);
    ctx.lineTo(rotationHandlePos.x, rotationHandlePos.y);
    ctx.stroke();
    
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(rotationHandlePos.x, rotationHandlePos.y, scaledHandleSize, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
}

function drawLabelHandles(obj) {
    const handles = getLabelHandlesPos(obj);
    const scaledHandleSize = (state.handleSize || 8) / state.scale;

    // Rotation handle
    ctx.save();
    ctx.strokeStyle = '#34d399';
    ctx.lineWidth = 2 / state.scale;
    ctx.fillStyle = 'white';
    ctx.translate(handles.rotation.x, handles.rotation.y);
    ctx.beginPath();
    ctx.arc(0, 0, scaledHandleSize, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#34d399';
    ctx.beginPath();
    ctx.arc(0, -scaledHandleSize * 0.6, scaledHandleSize * 0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

function drawSelectionDetails(obj) {
    if (['wall', 'door', 'dim', 'window'].includes(obj.type)) {
        ctx.save();
        drawDimensionText(obj.x1, obj.y1, obj.x2, obj.y2, '#34d399', obj, 'length');
        ctx.restore();
        drawResizeHandles(obj);
    } else if (['rect', 'stairs', 'road'].includes(obj.type)) {
        if(obj.type !== 'road') {
            drawDimensionText(obj.x, obj.y + obj.h/2, obj.x + obj.w, obj.y + obj.h/2, '#34d399', obj, 'width');
            drawDimensionText(obj.x + obj.w/2, obj.y, obj.x + obj.w/2, obj.y + obj.h, '#34d399', obj, 'height');
        }
        if (['stairs', 'road'].includes(obj.type)) {
            drawRectHandles(obj);
        }
    } else if (obj.type === 'label') {
        drawLabelHandles(obj);
    }
}

function drawDimensionLine(x1, y1, x2, y2, text) {
    ctx.strokeStyle = '#fcd34d';
    ctx.fillStyle = '#fcd34d';
    ctx.lineWidth = 1;
    ctx.font = `${12 / state.scale}px Inter`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();

    const angle = Math.atan2(y2 - y1, x2 - x1);
    
    const tickLength = 8;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x1 + tickLength * Math.cos(angle + Math.PI / 2), y1 + tickLength * Math.sin(angle + Math.PI / 2));
    ctx.moveTo(x1, y1);
    ctx.lineTo(x1 + tickLength * Math.cos(angle - Math.PI / 2), y1 + tickLength * Math.sin(angle - Math.PI / 2));
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 + tickLength * Math.cos(angle + Math.PI / 2), y2 + tickLength * Math.sin(angle + Math.PI / 2));
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 + tickLength * Math.cos(angle - Math.PI / 2), y2 + tickLength * Math.sin(angle - Math.PI / 2));
    ctx.stroke();

    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    ctx.save();
    ctx.translate(midX, midY);
    ctx.rotate(angle > Math.PI / 2 || angle < -Math.PI / 2 ? angle + Math.PI : angle);
    ctx.fillText(text, 0, -5 / state.scale);
    ctx.restore();
}

function drawDimensionPreview(x1, y1, x2, y2) {
    const dist = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    const text = `${(dist / state.pixelsPerFoot).toFixed(2)}'`;
    drawDimensionLine(x1, y1, x2, y2, text);
}

function drawDimensionText(x1, y1, x2, y2, color = '#fcd34d', object = null, type = null) {
    let dist, text;
    if (type === 'width') {
        dist = object.w;
        text = `${(dist / state.pixelsPerFoot).toFixed(2)}'`;
    } else if (type === 'height') {
        dist = object.h;
        text = `${(dist / state.pixelsPerFoot).toFixed(2)}'`;
    } else {
        dist = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
        if (dist === 0 && !object) return;
        text = `${(dist / state.pixelsPerFoot).toFixed(2)}'`;
    }
    
    ctx.fillStyle = color;
    ctx.font = `${14 / state.scale}px Inter`;
    ctx.textAlign = 'center';
    
    const midX_orig = (x1 + x2) / 2;
    const midY_orig = (y1 + y2) / 2;
    const angle_orig = Math.atan2(y2 - y1, x2 - x1);

    let finalMidX = midX_orig;
    let finalMidY = midY_orig;
    let finalAngle = angle_orig;
    let finalBaseline = 'bottom';
    let finalYOffset = -8 / state.scale;
    let hitboxY = midY_orig + finalYOffset - (14/state.scale)/2;

    if (type === 'width') {
        finalAngle = 0; // Force horizontal
        finalMidX = object.x + object.w / 2;
        finalMidY = object.y + object.h / 2;
        finalBaseline = 'bottom';
        finalYOffset = -2 / state.scale; 
        hitboxY = finalMidY + finalYOffset - (14/state.scale)/2;
    } else if (type === 'height') {
        finalAngle = 0; // Force horizontal
        finalMidX = object.x + object.w / 2;
        finalMidY = object.y + object.h / 2;
        finalBaseline = 'top';
        finalYOffset = 2 / state.scale;
        hitboxY = finalMidY + finalYOffset + (14/state.scale)/2;
    }
    
    ctx.textBaseline = finalBaseline;

    ctx.save();
    ctx.translate(finalMidX, finalMidY);
    ctx.rotate(finalAngle > Math.PI / 2 || finalAngle < -Math.PI / 2 ? finalAngle + Math.PI : finalAngle);
    ctx.fillText(text, 0, finalYOffset);

    if (object && (state.showAllDimensions || state.selectedObject === object)) {
        const textWidth = ctx.measureText(text).width;
        const textHeight = 14 / state.scale;
        state.dimensionHitBoxes.push({
            object: object,
            type: type,
            x: finalMidX, 
            y: hitboxY, 
            width: textWidth, 
            height: textHeight,
            angle: finalAngle
        });
    }
    ctx.restore();
}