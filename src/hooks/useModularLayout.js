import { useState, useEffect, useRef, useCallback } from 'react';

const DEFAULT_POSITIONS = {
    video: { x: 40, y: 80 },
    visualizer: { x: 0, y: 0 },
    chat: { x: 0, y: 0 },
    cad: { x: 0, y: 0 },
    browser: { x: 0, y: 0 },
    kasa: { x: 0, y: 0 },
    printer: { x: 0, y: 0 },
    memory: { x: 0, y: 0 },
    tools: { x: 0, y: 0 }
};

const DEFAULT_SIZES = {
    visualizer: { w: 550, h: 350 },
    chat: { w: 550, h: 220 },
    tools: { w: 500, h: 80 },
    cad: { w: 400, h: 400 },
    browser: { w: 550, h: 380 },
    video: { w: 320, h: 180 },
    kasa: { w: 300, h: 380 },
    printer: { w: 380, h: 380 },
    memory: { w: 420, h: 440 }
};

/**
 * Modular layout: positions, sizes, z-index, drag handlers, clampToViewport, getZIndex, bringToFront, updateElementPosition.
 */
export function useModularLayout() {
    const [elementPositions, setElementPositions] = useState(() => ({
        ...DEFAULT_POSITIONS,
        visualizer: { x: typeof window !== 'undefined' ? window.innerWidth / 2 : 400, y: (typeof window !== 'undefined' ? window.innerHeight : 600) / 2 - 150 },
        chat: { x: typeof window !== 'undefined' ? window.innerWidth / 2 : 400, y: (typeof window !== 'undefined' ? window.innerHeight : 600) / 2 + 100 },
        cad: { x: (typeof window !== 'undefined' ? window.innerWidth : 800) / 2 + 300, y: (typeof window !== 'undefined' ? window.innerHeight : 600) / 2 },
        browser: { x: (typeof window !== 'undefined' ? window.innerWidth : 800) / 2 - 300, y: (typeof window !== 'undefined' ? window.innerHeight : 600) / 2 },
        kasa: { x: (typeof window !== 'undefined' ? window.innerWidth : 800) / 2 + 350, y: (typeof window !== 'undefined' ? window.innerHeight : 600) / 2 - 100 },
        printer: { x: (typeof window !== 'undefined' ? window.innerWidth : 800) / 2 - 350, y: (typeof window !== 'undefined' ? window.innerHeight : 600) / 2 - 100 },
        memory: { x: (typeof window !== 'undefined' ? window.innerWidth : 800) / 2, y: (typeof window !== 'undefined' ? window.innerHeight : 600) / 2 - 50 },
        tools: { x: (typeof window !== 'undefined' ? window.innerWidth : 800) / 2, y: (typeof window !== 'undefined' ? window.innerHeight : 600) - 100 }
    }));
    const [elementSizes, setElementSizes] = useState(DEFAULT_SIZES);
    const [zIndexOrder, setZIndexOrder] = useState(['visualizer', 'chat', 'tools', 'video', 'cad', 'browser', 'kasa', 'printer', 'memory']);
    const [activeDragElement, setActiveDragElement] = useState(null);
    const [isModularMode, setIsModularMode] = useState(false);
    const elementPositionsRef = useRef(elementPositions);
    const isModularModeRef = useRef(false);
    const dragOffsetRef = useRef({ x: 0, y: 0 });
    const isDraggingRef = useRef(false);
    const activeDragElementRef = useRef(null);
    const lastActiveDragElementRef = useRef(null);

    useEffect(() => {
        elementPositionsRef.current = elementPositions;
    }, [elementPositions]);
    useEffect(() => {
        isModularModeRef.current = isModularMode;
    }, [isModularMode]);

    useEffect(() => {
        const centerElements = () => {
            const width = window.innerWidth;
            const height = window.innerHeight;
            const toolsCenterY = height - 100;
            const gap = 20;
            let vizH = 400;
            let chatH = 250;
            const topBarHeight = 60;
            const totalNeeded = topBarHeight + vizH + gap + chatH + gap + 140;
            if (height < totalNeeded) {
                const available = height - topBarHeight - 140 - (gap * 2);
                vizH = available * 0.6;
                chatH = available * 0.4;
            }
            const vizY = topBarHeight + (vizH / 2);
            const chatY = topBarHeight + vizH + gap;
            setElementSizes(prev => ({
                ...prev,
                visualizer: { w: Math.min(600, width * 0.8), h: vizH },
                chat: { w: Math.min(600, width * 0.9), h: chatH }
            }));
            setElementPositions(prev => ({
                ...prev,
                visualizer: { x: width / 2, y: vizY },
                chat: { x: width / 2, y: chatY },
                tools: { x: width / 2, y: toolsCenterY }
            }));
        };
        centerElements();
        window.addEventListener('resize', centerElements);
        return () => window.removeEventListener('resize', centerElements);
    }, []);

    const clampToViewport = useCallback((pos, size) => {
        const margin = 10;
        const topBarHeight = 60;
        const width = window.innerWidth;
        const height = window.innerHeight;
        return {
            x: Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, pos.x)),
            y: Math.max(size.h / 2 + margin + topBarHeight, Math.min(height - size.h / 2 - margin, pos.y))
        };
    }, []);

    const getZIndex = useCallback((id) => {
        const baseZ = 30;
        const index = zIndexOrder.indexOf(id);
        return baseZ + (index >= 0 ? index : 0);
    }, [zIndexOrder]);

    const bringToFront = useCallback((id) => {
        setZIndexOrder(prev => {
            const filtered = prev.filter(el => el !== id);
            return [...filtered, id];
        });
    }, []);

    const updateElementPosition = useCallback((id, dx, dy) => {
        setElementPositions(prev => {
            const currentPos = prev[id];
            if (!currentPos) return prev;
            const size = elementSizes[id] || { w: 100, h: 100 };
            let newX = currentPos.x + dx;
            let newY = currentPos.y + dy;
            const width = window.innerWidth;
            const height = window.innerHeight;
            const margin = 0;
            if (id === 'chat') {
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));
            } else if (id === 'video') {
                newX = Math.max(margin, Math.min(width - size.w - margin, newX));
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));
            } else {
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                newY = Math.max(size.h / 2 + margin, Math.min(height - size.h / 2 - margin, newY));
            }
            return { ...prev, [id]: { x: newX, y: newY } };
        });
    }, [elementSizes]);

    const handleMouseDown = useCallback((e, id) => {
        const fixedElements = ['visualizer', 'chat', 'video', 'tools'];
        if (fixedElements.includes(id)) return;
        bringToFront(id);
        const tagName = e.target.tagName.toLowerCase();
        if (tagName === 'input' || tagName === 'button' || tagName === 'textarea' || tagName === 'canvas' || e.target.closest('button')) return;
        const isDragHandle = e.target.closest('[data-drag-handle]');
        if (!isDragHandle && !isModularModeRef.current) return;
        const elPos = elementPositions[id];
        if (!elPos) return;
        dragOffsetRef.current = { x: e.clientX - elPos.x, y: e.clientY - elPos.y };
        setActiveDragElement(id);
        activeDragElementRef.current = id;
        isDraggingRef.current = true;
        const handleMouseDrag = (ev) => {
            if (!isDraggingRef.current || !activeDragElementRef.current) return;
            const id = activeDragElementRef.current;
            const size = elementSizes[id] || { w: 100, h: 100 };
            const rawNewX = ev.clientX - dragOffsetRef.current.x;
            const rawNewY = ev.clientY - dragOffsetRef.current.y;
            const width = window.innerWidth;
            const height = window.innerHeight;
            const margin = 0;
            let newX = rawNewX, newY = rawNewY;
            if (id === 'chat') {
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));
            } else if (id === 'video') {
                newX = Math.max(margin, Math.min(width - size.w - margin, newX));
                newY = Math.max(margin, Math.min(height - size.h - margin, newY));
            } else {
                newX = Math.max(size.w / 2 + margin, Math.min(width - size.w / 2 - margin, newX));
                newY = Math.max(size.h / 2 + margin, Math.min(height - size.h / 2 - margin, newY));
            }
            setElementPositions(prev => ({ ...prev, [id]: { x: newX, y: newY } }));
        };
        const handleMouseUp = () => {
            isDraggingRef.current = false;
            setActiveDragElement(null);
            activeDragElementRef.current = null;
            lastActiveDragElementRef.current = null;
            window.removeEventListener('mousemove', handleMouseDrag);
            window.removeEventListener('mouseup', handleMouseUp);
        };
        window.addEventListener('mousemove', handleMouseDrag);
        window.addEventListener('mouseup', handleMouseUp);
    }, [elementPositions, elementSizes, bringToFront]);

    return {
        elementPositions,
        setElementPositions,
        elementSizes,
        setElementSizes,
        zIndexOrder,
        setZIndexOrder,
        activeDragElement,
        setActiveDragElement,
        elementPositionsRef,
        activeDragElementRef,
        lastActiveDragElementRef,
        isModularMode,
        setIsModularMode,
        clampToViewport,
        getZIndex,
        bringToFront,
        updateElementPosition,
        handleMouseDown
    };
}
