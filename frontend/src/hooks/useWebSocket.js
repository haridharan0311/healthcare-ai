import { useState, useEffect, useRef } from 'react';
import { WS_BASE } from '../api';

export default function useWebSocket(endpoint) {
  const [data, setData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);

  useEffect(() => {
    let timeout;
    function connect() {
      if (ws.current) {
        ws.current.close();
      }

      const socket = new WebSocket(`${WS_BASE}${endpoint}`);
      ws.current = socket;

      socket.onopen = () => {
        setIsConnected(true);
        setError(null);
        console.log(`[WebSocket] Connected to ${endpoint}`);
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setData(parsed);
        } catch (e) {
          console.error('[WebSocket] Message parsing error', e);
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        console.log(`[WebSocket] Disconnected from ${endpoint}, retrying in 3s...`);
        timeout = setTimeout(connect, 3000); // Reconnect
      };

      socket.onerror = (err) => {
        setError('WebSocket encountered an error');
        console.error(`[WebSocket] Error on ${endpoint}`, err);
        socket.close();
      };
    }

    connect();

    return () => {
      clearTimeout(timeout);
      if (ws.current) {
        ws.current.onclose = null; // Prevent reconnect on explicit unmount
        ws.current.close();
      }
    };
  }, [endpoint]);

  return { data, isConnected, error };
}
