import { useState, useEffect } from 'react';

/**
 * Printer count, slicing progress, print status, window visibility. Subscribes to printer_list, slicing_progress, print_status_update, request_print_window.
 * @param {object} socket - Socket.IO client
 * @param {function} setElementPositions - From layout (optional)
 * @param {function} clampToViewport - From layout (optional)
 */
export function usePrinterState(socket, setElementPositions, clampToViewport) {
    const [slicingStatus, setSlicingStatus] = useState({ active: false, percent: 0, message: '' });
    const [activePrintStatus, setActivePrintStatus] = useState(null);
    const [printerCount, setPrinterCount] = useState(0);
    const [showPrinterWindow, setShowPrinterWindow] = useState(false);

    useEffect(() => {
        if (!socket) return;
        socket.on('printer_list', (data) => {
            const list = Array.isArray(data) ? data : (data && data.printers) || [];
            const showBadge = Array.isArray(data) ? true : !!(data && data.badge);
            setPrinterCount(showBadge ? list.length : 0);
        });
        socket.on('request_print_window', () => {
            setShowPrinterWindow(true);
            if (setElementPositions && clampToViewport) {
                const size = { w: 380, h: 380 };
                const clamped = clampToViewport({ x: window.innerWidth / 2, y: window.innerHeight / 2 }, size);
                setElementPositions(prev => ({ ...prev, printer: clamped }));
            }
        });
        socket.on('slicing_progress', (data) => {
            setSlicingStatus({
                active: data.percent < 100,
                percent: data.percent,
                message: data.message || ''
            });
        });
        socket.on('print_status_update', (data) => {
            if (data.state && data.state.toLowerCase().includes('print')) {
                setActivePrintStatus({
                    printer: data.printer,
                    progress_percent: data.progress_percent,
                    time_elapsed: data.time_elapsed,
                    state: data.state
                });
            } else if (data.state && ['idle', 'standby', 'complete'].includes(data.state.toLowerCase())) {
                setActivePrintStatus(null);
            }
        });
        return () => {
            socket.off('printer_list');
            socket.off('request_print_window');
            socket.off('slicing_progress');
            socket.off('print_status_update');
        };
    }, [socket, setElementPositions, clampToViewport]);

    return { slicingStatus, setSlicingStatus, activePrintStatus, setActivePrintStatus, printerCount, setPrinterCount, showPrinterWindow, setShowPrinterWindow };
}
