"""
Frontend WebSocket Integration Guide

Requirement 6: Live Updates - WebSocket support for frontend.

This file documents how to integrate WebSocket live updates in the React frontend.

Installation:
    The following files should be added to frontend/src/:
    - hooks/useWebSocket.js - React hook for WebSocket connections
    - components/LiveDataProvider.jsx - Context provider for shared WebSocket connections
    - utils/websocketConfig.js - Configuration and helpers

After adding these files, update your components to use real-time data.
"""

# File: frontend/src/hooks/useWebSocket.js
"""
import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Custom React Hook for WebSocket connections
 * 
 * Features:
 *   - Automatic reconnection with exponential backoff
 *   - Message queuing while disconnected
 *   - Automatic heartbeat/ping to detect connection loss
 *   - Error recovery
 * 
 * Usage:
 *   const [data, sendMessage, connected, error] = useWebSocket(
 *     'ws://localhost:8000/ws/disease-trends/'
 *   );
 * 
 * @param {string} url - WebSocket URL
 * @param {Object} options - Configuration options
 * @returns {Array} [data, sendMessage, connected, error]
 */
export function useWebSocket(url, options = {}) {
  const {
    maxReconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    onMessage = null,
    onConnect = null,
    onDisconnect = null,
    onError = null,
  } = options;
  
  const wsRef = useRef(null);
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [reconnectCount, setReconnectCount] = useState(0);
  const messageQueueRef = useRef([]);
  const heartbeatTimerRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  
  /**
   * Send message through WebSocket
   * Queues message if not connected
   */
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      // Queue message for later
      messageQueueRef.current.push(message);
      console.warn('WebSocket not connected, message queued');
    }
  }, []);
  
  /**
   * Process queued messages
   */
  const flushMessageQueue = useCallback(() => {
    while (messageQueueRef.current.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
      const message = messageQueueRef.current.shift();
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);
  
  /**
   * Start heartbeat to detect connection loss
   */
  const startHeartbeat = useCallback(() => {
    heartbeatTimerRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        sendMessage({ action: 'ping' });
      }
    }, heartbeatInterval);
  }, [heartbeatInterval, sendMessage]);
  
  /**
   * Stop heartbeat
   */
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
    }
  }, []);
  
  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (wsRef.current !== null) {
      return; // Already connecting/connected
    }
    
    try {
      if (typeof WebSocket === 'undefined') {
        throw new Error('WebSocket not supported in this browser');
      }
      
      wsRef.current = new WebSocket(url);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected:', url);
        setConnected(true);
        setError(null);
        setReconnectCount(0);
        
        // Flush queued messages
        flushMessageQueue();
        
        // Start heartbeat
        startHeartbeat();
        
        // Send initial subscription
        sendMessage({ action: 'subscribe' });
        
        if (onConnect) {
          onConnect();
        }
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setData(message);
          
          if (message.type === 'pong') {
            // Heartbeat response, ignore
            return;
          }
          
          if (onMessage) {
            onMessage(message);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
      
      wsRef.current.onerror = (event) => {
        const errorMsg = 'WebSocket error occurred';
        console.error(errorMsg, event);
        setError(errorMsg);
        
        if (onError) {
          onError(errorMsg);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected:', url);
        stopHeartbeat();
        wsRef.current = null;
        setConnected(false);
        
        if (onDisconnect) {
          onDisconnect();
        }
        
        // Attempt reconnection
        if (reconnectCount < maxReconnectAttempts) {
          const delay = reconnectInterval * (2 ** reconnectCount); // Exponential backoff
          console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectCount + 1}/${maxReconnectAttempts})`);
          
          setReconnectCount(prev => prev + 1);
          reconnectTimerRef.current = setTimeout(connect, delay);
        } else {
          const finalError = 'WebSocket disconnected - max reconnection attempts reached';
          setError(finalError);
          
          if (onError) {
            onError(finalError);
          }
        }
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
      setError(e.message);
      
      if (onError) {
        onError(e.message);
      }
    }
  }, [url, onConnect, onDisconnect, onError, onMessage, flushMessageQueue, startHeartbeat, stopHeartbeat, sendMessage, reconnectCount, maxReconnectAttempts, reconnectInterval]);
  
  /**
   * Setup connection on mount
   */
  useEffect(() => {
    connect();
    
    return () => {
      // Cleanup on unmount
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      stopHeartbeat();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect, stopHeartbeat]);
  
  return [data, sendMessage, connected, error];
}

export default useWebSocket;
"""

# File: frontend/src/components/LiveDataProvider.jsx
"""
import React, { createContext, useContext, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

/**
 * Context provider for shared WebSocket connections
 * 
 * Prevents multiple WebSocket connections for the same endpoint
 * Shares data across multiple components
 * 
 * Usage:
 *   <LiveDataProvider>
 *     <YourComponent />
 *   </LiveDataProvider>
 *   
 *   In component:
 *   const { diseaseTrends, spikeAlerts, restock } = useLiveData();
 */
const LiveDataContext = createContext();

export function LiveDataProvider({ children }) {
  const [diseaseTrends, sendDiseaseTrendMsg, diseaseTrendsConnected] = useWebSocket(
    'ws://localhost:8000/ws/disease-trends/'
  );
  
  const [spikeAlerts, sendSpikeAlertMsg, spikeAlertsConnected] = useWebSocket(
    'ws://localhost:8000/ws/spike-alerts/'
  );
  
  const [restockData, sendRestockMsg, restockConnected] = useWebSocket(
    'ws://localhost:8000/ws/restock/'
  );
  
  const value = {
    // Disease trends data and controls
    diseaseTrends,
    sendDiseaseTrendMsg,
    diseaseTrendsConnected,
    
    // Spike alerts data and controls
    spikeAlerts,
    sendSpikeAlertMsg,
    spikeAlertsConnected,
    
    // Restock data and controls
    restockData,
    sendRestockMsg,
    restockConnected,
    
    // Overall connection status
    isConnected: diseaseTrendsConnected && spikeAlertsConnected && restockConnected,
  };
  
  return (
    <LiveDataContext.Provider value={value}>
      {children}
    </LiveDataContext.Provider>
  );
}

export function useLiveData() {
  const context = useContext(LiveDataContext);
  if (!context) {
    throw new Error('useLiveData must be used within LiveDataProvider');
  }
  return context;
}

export default LiveDataProvider;
"""

# File: frontend/src/utils/websocketConfig.js
"""
/**
 * WebSocket configuration and helpers
 * 
 * Centralized configuration for WebSocket connections
 */

// Determine correct WebSocket URL based on environment
export const getWebSocketBaseUrl = () => {
  if (typeof window === 'undefined') {
    return 'ws://localhost:8000'; // Server-side rendering
  }
  
  const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  return protocol + window.location.host;
};

export const WEBSOCKET_ENDPOINTS = {
  DISEASE_TRENDS: `${getWebSocketBaseUrl()}/ws/disease-trends/`,
  SPIKE_ALERTS: `${getWebSocketBaseUrl()}/ws/spike-alerts/`,
  RESTOCK: `${getWebSocketBaseUrl()}/ws/restock/`,
};

/**
 * Message types sent by server
 */
export const MESSAGE_TYPES = {
  TREND_UPDATE: 'trend_update',
  SPIKE_ALERTS: 'spike_alerts',
  RESTOCK_UPDATE: 'restock_update',
  ERROR: 'error',
  PONG: 'pong',
};

/**
 * Message types sent to server
 */
export const CLIENT_ACTIONS = {
  SUBSCRIBE: 'subscribe',
  PING: 'ping',
  REFRESH: 'refresh',
};

/**
 * Format WebSocket error message for display
 */
export const formatWebSocketError = (error) => {
  if (typeof error === 'string') {
    return error;
  }
  return error?.message || 'Unknown WebSocket error';
};

/**
 * Connect with fallback to polling (for compatibility)
 */
export const useWebSocketWithFallback = (wsUrl, fallbackApiUrl) => {
  // Try WebSocket first
  // If fails, fallback to HTTP polling
  // Useful for older browsers or network restrictions
  
  return {
    // Implementation would check WebSocket support
    // and fallback to polling if needed
  };
};
"""

# File: frontend/src/components/DashboardWithLiveData.jsx (Example Usage)
"""
import React, { useEffect, useState } from 'react';
import { useLiveData } from '../context/LiveDataProvider';

export function DashboardWithLiveData() {
  const { diseaseTrends, spikeAlerts, isConnected } = useLiveData();
  const [trends, setTrends] = useState([]);
  
  // Update trends when new data arrives
  useEffect(() => {
    if (diseaseTrends?.data) {
      setTrends(diseaseTrends.data);
    }
  }, [diseaseTrends]);
  
  return (
    <div>
      <div className="connection-status">
        {isConnected ? '🟢 Live Data Active' : '🔴 Offline'}
      </div>
      
      <div className="trends-container">
        {trends?.map(trend => (
          <div key={trend.disease_name} className="trend-card">
            <h3>{trend.disease_name}</h3>
            <p>Trend Score: {trend.trend_score}</p>
            <p>Total Cases: {trend.total_cases}</p>
          </div>
        ))}
      </div>
      
      {spikeAlerts?.data && (
        <div className="spike-alerts">
          <h2>⚠️ Active Spikes</h2>
          {spikeAlerts.data.map(spike => (
            <div key={spike.disease_name} className="spike-alert">
              {spike.disease_name} - {spike.today_count} cases
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default DashboardWithLiveData;
"""

# File: frontend/src/App.jsx (Update main component)
"""
import React from 'react';
import { LiveDataProvider } from './components/LiveDataProvider';
import DashboardWithLiveData from './components/DashboardWithLiveData';

function App() {
  return (
    <LiveDataProvider>
      <div className="app">
        <DashboardWithLiveData />
      </div>
    </LiveDataProvider>
  );
}

export default App;
"""
