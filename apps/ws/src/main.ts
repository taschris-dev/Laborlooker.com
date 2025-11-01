import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import jwt from 'jsonwebtoken';
import pino from 'pino';
import { envSchema, WSEvent } from '@laborlookers/types';

// Validate environment
const env = envSchema.parse(process.env);

const logger = pino({
  level: env.NODE_ENV === 'development' ? 'debug' : 'info',
  transport: env.NODE_ENV === 'development' 
    ? { target: 'pino-pretty' }
    : undefined,
});

const server = createServer();

const io = new SocketIOServer(server, {
  cors: {
    origin: env.NODE_ENV === 'production' 
      ? ['https://laborlookers.com', 'https://app.laborlookers.com']
      : true,
    credentials: true,
  },
});

// Middleware for JWT authentication
io.use((socket, next) => {
  const token = socket.handshake.auth.token;
  
  if (!token) {
    return next(new Error('Authentication error'));
  }

  try {
    const decoded = jwt.verify(token, env.JWT_SECRET) as { userId: string };
    socket.data.userId = decoded.userId;
    logger.info({ userId: decoded.userId }, 'User connected');
    next();
  } catch (err) {
    logger.error({ error: err }, 'Authentication failed');
    next(new Error('Authentication error'));
  }
});

io.on('connection', (socket) => {
  const userId = socket.data.userId;
  
  logger.info({ userId, socketId: socket.id }, 'User connected to WebSocket');
  
  // Join user to their personal room
  socket.join(`user:${userId}`);
  
  // Handle incoming events
  socket.on('join_room', (room: string) => {
    socket.join(room);
    logger.debug({ userId, room }, 'User joined room');
  });
  
  socket.on('leave_room', (room: string) => {
    socket.leave(room);
    logger.debug({ userId, room }, 'User left room');
  });
  
  socket.on('ping', (data) => {
    socket.emit('pong', data);
  });
  
  socket.on('disconnect', (reason) => {
    logger.info({ userId, reason }, 'User disconnected');
  });
});

// Health check endpoint
server.on('request', (req, res) => {
  if (req.url === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      timestamp: new Date().toISOString(),
      service: 'websocket',
      connectedClients: io.sockets.sockets.size,
    }));
    return;
  }
  
  res.writeHead(404);
  res.end('Not Found');
});

const port = env.PORT || 3002;

server.listen(port, () => {
  logger.info({ port }, '🚀 WebSocket server running');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  server.close(() => {
    logger.info('WebSocket server closed');
    process.exit(0);
  });
});

export { io };
export type { WSEvent };