// Utility functions
import { state } from './state.js';

export function getSnappedCoordinates(currentX, currentY, startX, startY) {
    const dx = Math.abs(currentX - startX);
    const dy = Math.abs(currentY - startY);
    return dx > dy ? { x: currentX, y: startY } : { x: startX, y: currentY };
}

export function pointToSegmentDistance(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.sqrt(Math.pow(px - x1, 2) + Math.pow(py - y1, 2));
    let t = ((px - x1) * dx + (py - y1) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    return Math.sqrt(Math.pow(px - (x1 + t * dx), 2) + Math.pow(py - (y1 + t * dy), 2));
}

export function snapToGrid(value) {
    const gs = state.gridSize || 10;
    return Math.round(value / gs) * gs;
}

export function getHandleAt(x, y, obj) {
    if (!obj || !['wall', 'door', 'dim', 'window'].includes(obj.type)) return null;
    const tolerance = (state.handleSize || 8) / state.scale;
    if (Math.sqrt(Math.pow(x - obj.x1, 2) + Math.pow(y - obj.y1, 2)) < tolerance) return 'start';
    if (Math.sqrt(Math.pow(x - obj.x2, 2) + Math.pow(y - obj.y2, 2)) < tolerance) return 'end';
    return null;
}

export function getRectCornerHandleAt(x, y, obj) {
    const tolerance = ((state.handleSize || 8) * 1.5) / state.scale;
    const corners = {
        tl: { x: obj.x, y: obj.y }, tr: { x: obj.x + obj.w, y: obj.y },
        bl: { x: obj.x, y: obj.y + obj.h }, br: { x: obj.x + obj.w, y: obj.y + obj.h }
    };
    for (const [name, pos] of Object.entries(corners)) {
        if (Math.sqrt(Math.pow(x - pos.x, 2) + Math.pow(y - pos.y, 2)) < tolerance) return name;
    }
    return null;
}

export function getRotationHandlePos(obj) {
    return { x: obj.x + obj.w / 2, y: obj.y - (30 / state.scale) };
}

export function getLabelHandlesPos(obj) {
    const ctx = state.ctx || (state.canvas ? state.canvas.getContext('2d') : null);
    const scale = state.scale || 1;
    if (ctx) ctx.font = `${16 / scale}px Inter`;
    const textWidth = ctx ? ctx.measureText(obj.text).width : (obj.text.length * 8);
    const textHeight = 16 / scale;
    const halfW = textWidth / 2;
    const halfH = textHeight / 2;

    const rotationHandleDist = 20 / scale;

    let rotHandleLocal = { x: 0, y: -halfH - rotationHandleDist };
    
    const angleRad = obj.rotation * Math.PI / 180;
    const cosA = Math.cos(angleRad);
    const sinA = Math.sin(angleRad);

    const rotatePoint = (p) => ({
        x: p.x * cosA - p.y * sinA,
        y: p.x * sinA + p.y * cosA
    });

    const rotHandleRotated = rotatePoint(rotHandleLocal);

    return {
        rotation: { x: obj.x + rotHandleRotated.x, y: obj.y + rotHandleRotated.y }
    };
}

export function getAnchorForHandle(handle, rect) {
    const anchors = {
        br: { x: rect.x, y: rect.y }, tl: { x: rect.x + rect.w, y: rect.y + rect.h },
        bl: { x: rect.x + rect.w, y: rect.y }, tr: { x: rect.x, y: rect.y + rect.h }
    };
    return anchors[handle];
}

export function getObjectAt(x, y, objects) {
    for (let i = objects.length - 1; i >= 0; i--) {
        if (isPointOnObject(x, y, objects[i])) return objects[i];
    }
    return null;
}

export function isPointOnObject(x, y, obj) {
    const tolerance = 10 / (state.scale || 1);
    switch(obj.type) {
        case 'wall': case 'dim': case 'window':
            return pointToSegmentDistance(x, y, obj.x1, obj.y1, obj.x2, obj.y2) < tolerance;
        case 'door': {
            let hingeX, hingeY;
            if (obj.hingeAtStart === false) { hingeX = obj.x2; hingeY = obj.y2; } 
            else { hingeX = obj.x1; hingeY = obj.y1; }
            const len = Math.sqrt(Math.pow(obj.x2 - obj.x1, 2) + Math.pow(obj.y2 - obj.y1, 2));
            const angle = Math.atan2(obj.y2-obj.y1, obj.x2-obj.x1);
            const endPointX = hingeX + len * Math.cos(angle - Math.PI/2 * (obj.swingDirection || 1));
            const endPointY = hingeY + len * Math.sin(angle - Math.PI/2 * (obj.swingDirection || 1));
            return pointToSegmentDistance(x, y, obj.x1, obj.y1, obj.x2, obj.y2) < tolerance || pointToSegmentDistance(x, y, hingeX, hingeY, endPointX, endPointY) < tolerance;
        }
        case 'stairs': case 'road': case 'rect':
            return x >= obj.x - tolerance && x <= obj.x + obj.w + tolerance && y >= obj.y - tolerance && y <= obj.y + obj.h + tolerance;
        case 'label': {
            const ctx = state.ctx || (state.canvas ? state.canvas.getContext('2d') : null);
            const scale = state.scale || 1;
            if (ctx) ctx.font = `${16 / scale}px Inter`;
            const textWidth = ctx ? ctx.measureText(obj.text).width : (obj.text.length * 8);
            const textHeight = 16 / scale;
            const halfW = textWidth / 2;
            const halfH = textHeight / 2;

            let localX = x - obj.x;
            let localY = y - obj.y;

            const angleRad = -obj.rotation * Math.PI / 180;
            const cosA = Math.cos(angleRad);
            const sinA = Math.sin(angleRad);
            const rotatedX = localX * cosA - localY * sinA;
            const rotatedY = localX * sinA + localY * cosA;

            return rotatedX >= -halfW - tolerance && rotatedX <= halfW + tolerance &&
                   rotatedY >= -halfH - tolerance && rotatedY <= halfH + tolerance;
        }
        default: return false;
    }
}