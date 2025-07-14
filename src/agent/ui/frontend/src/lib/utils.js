import { clsx } from "clsx";

export function cn(...inputs) {
  return clsx(inputs);
}

export function generateId() {
  return Math.random().toString(36).substring(2, 15);
}

export function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function isValidWebSocketState(ws) {
  return ws && ws.readyState === WebSocket.OPEN;
}