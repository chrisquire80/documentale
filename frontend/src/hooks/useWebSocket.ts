import { useEffect, useState, useRef } from 'react';

const BASE_WS_URL = (import.meta.env.VITE_API_URL as string)?.replace('http', 'ws') || 'ws://localhost:8000';

export function useWebSocket() {
    const [lastMessage, setLastMessage] = useState<any>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) return;

        let reconnectTimeout: ReturnType<typeof setTimeout>;

        const connect = () => {
            const ws = new WebSocket(`${BASE_WS_URL}/ws/${token}`);

            ws.onopen = () => {
                console.log('WebSocket connected for live notifications');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setLastMessage(data);
                } catch (e) {
                    console.error('Failed to parse WS message', e);
                }
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected. Reconnecting in 3s...');
                reconnectTimeout = setTimeout(connect, 3000);
            };

            ws.onerror = (err) => {
                console.error('WebSocket error', err);
                ws.close();
            };

            wsRef.current = ws;
        };

        connect();

        return () => {
            clearTimeout(reconnectTimeout);
            if (wsRef.current) {
                // Remove onclose to prevent auto-reconnect when unmounting
                wsRef.current.onclose = null;
                wsRef.current.close();
            }
        };
    }, []);

    return { lastMessage };
}
