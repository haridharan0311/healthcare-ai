"""
WebSocket URL Routing for Channels

Maps WebSocket endpoints to consumer handlers for real-time data streaming.

Layer: API (WebSocket Layer)
Usage in asgi.py:
    from analytics.routing import websocket_urlpatterns
    
    application = ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

Endpoints:
    ws://localhost:8000/ws/disease-trends/ - Disease trend live updates
    ws://localhost:8000/ws/spike-alerts/ - Spike detection alerts
    ws://localhost:8000/ws/restock/ - Restock suggestions
    ws://localhost:8000/ws/inventory/ - Inventory level changes
"""

from django.urls import path
from .consumers import (
    DiseaseTrendConsumer, SpikeAlertConsumer,
    RestockConsumer
)


websocket_urlpatterns = [
    # ─── Disease Trends: Real-time disease case trends ────────────────────────
    path(
        'ws/disease-trends/',
        DiseaseTrendConsumer.as_asgi(),
        name='ws_disease_trends'
    ),
    # Usage: Connect to ws://localhost:8000/ws/disease-trends/
    # Receive: {type: "trend_update", data: [...], timestamp: "..."}
    
    # ─── Spike Alerts: Real-time spike detection notifications ────────────────
    path(
        'ws/spike-alerts/',
        SpikeAlertConsumer.as_asgi(),
        name='ws_spike_alerts'
    ),
    # Usage: Connect to ws://localhost:8000/ws/spike-alerts/
    # Receive: {type: "spike_alerts", data: [...], timestamp: "..."}
    
    # ─── Restock: Real-time inventory restock suggestions ────────────────────
    path(
        'ws/restock/',
        RestockConsumer.as_asgi(),
        name='ws_restock'
    ),
    # Usage: Connect to ws://localhost:8000/ws/restock/
    # Receive: {type: "restock_update", data: [...], timestamp: "..."}
]


"""
Example WebSocket Client (JavaScript):

    class AnalyticsWebSocket {
        constructor(url) {
            this.url = url;
            this.ws = null;
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;
        }
        
        connect() {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('Connected to', this.url);
                this.reconnectAttempts = 0;
                this.ws.send(JSON.stringify({action: 'subscribe'}));
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('Received:', data);
                this.handleMessage(data);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            this.ws.onclose = () => {
                console.log('Disconnected from', this.url);
                this.reconnect();
            };
        }
        
        reconnect() {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = 1000 * (2 ** this.reconnectAttempts); // Exponential backoff
                setTimeout(() => this.connect(), delay);
            }
        }
        
        handleMessage(data) {
            // Override in subclass
            console.log('Message:', data);
        }
        
        send(action) {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({action}));
            }
        }
        
        close() {
            if (this.ws) {
                this.ws.close();
            }
        }
    }
    
    // Usage:
    const diseaseWs = new AnalyticsWebSocket('ws://localhost:8000/ws/disease-trends/');
    diseaseWs.handleMessage = (data) => {
        console.log('Disease trends:', data.data);
        // Update UI with new trends
    };
    diseaseWs.connect();

Example React Hook (useWebSocket):

    import { useEffect, useState } from 'react';
    
    export function useWebSocket(url) {
        const [data, setData] = useState(null);
        const [connected, setConnected] = useState(false);
        const wsRef = useRef(null);
        
        useEffect(() => {
            const ws = new WebSocket(url);
            wsRef.current = ws;
            
            ws.onopen = () => setConnected(true);
            ws.onmessage = (e) => setData(JSON.parse(e.data));
            ws.onclose = () => setConnected(false);
            
            return () => ws.close();
        }, [url]);
        
        const send = (message) => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify(message));
            }
        };
        
        return [data, send, connected];
    }
    
    // Usage in component:
    const [trends, sendMessage, connected] = useWebSocket('ws://localhost:8000/ws/disease-trends/');
    
    return (
        <div>
            <p>Status: {connected ? 'Connected' : 'Disconnected'}</p>
            <p>Trends: {JSON.stringify(trends?.data)}</p>
        </div>
    );
"""
