# WebSocket Chat Configuration

## Solution: Direct Port Exposure

**Approach:** Expose chat service port directly instead of WebSocket proxying through API gateway.

**Why this is best:**
- ✅ **Easy** - Just port mapping in docker-compose
- ✅ **Low latency** - Direct WebSocket connection, no proxy overhead
- ✅ **Reliable** - No complex WebSocket proxy implementation needed

## Configuration

**docker-compose.yml:**
```yaml
chat-service:
  ports:
    - "8006:8000"  # Direct WebSocket access
```

## Frontend WebSocket Connection

**Connect to chat WebSocket:**
```javascript
// Instead of: ws://localhost:8000/chats/ws/{chat_id}
// Use: ws://localhost:8006/chats/ws/{chat_id}

const ws = new WebSocket(`ws://localhost:8006/chats/ws/${chatId}?ws_token=${wsToken}`);
```

## Testing

**1. Get WebSocket token:**
```bash
curl -X POST http://localhost:8000/ws-token \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**2. Connect to WebSocket:**
```javascript
ws://localhost:8006/chats/ws/1?ws_token=YOUR_WS_TOKEN
```

## Production Deployment

For production, you'd typically:
1. Use Nginx/HAProxy for WebSocket proxying
2. Or expose chat service on different subdomain (e.g., `ws.example.com`)
3. Keep API gateway for HTTP REST endpoints
4. Use separate WebSocket endpoint for real-time connections

This is the standard pattern for microservices with WebSocket support.
