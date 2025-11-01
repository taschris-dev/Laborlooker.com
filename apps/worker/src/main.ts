import { Worker, Job } from 'bullmq';
import IORedis from 'ioredis';
import { PrismaClient } from '@prisma/client';
import pino from 'pino';
import { envSchema } from '@laborlookers/types';
import { EmailService } from './services/email.service';
import { ModerationService } from './services/moderation.service';
import { AnalyticsService } from './services/analytics.service';
import { NotificationService } from './services/notification.service';

// Validate environment
const env = envSchema.parse(process.env);

const logger = pino({
  level: env.NODE_ENV === 'development' ? 'debug' : 'info',
  transport: env.NODE_ENV === 'development' 
    ? { target: 'pino-pretty' }
    : undefined,
});

// Initialize Redis connection
const connection = new IORedis({
  host: env.REDIS_HOST || 'localhost',
  port: parseInt(env.REDIS_PORT || '6379'),
  maxRetriesPerRequest: 3,
  retryDelayOnFailover: 100,
});

// Initialize Prisma
const prisma = new PrismaClient();

// Initialize services
const emailService = new EmailService();
const moderationService = new ModerationService();
const analyticsService = new AnalyticsService();
const notificationService = new NotificationService();

// Job types
interface EmailJobData {
  type: 'welcome' | 'verification' | 'password-reset' | 'work-request-notification' | 'rating-reminder';
  to: string;
  userId?: string;
  workRequestId?: string;
  data: Record<string, any>;
}

interface ModerationJobData {
  type: 'profile-review' | 'work-request-review' | 'message-review';
  resourceId: string;
  resourceType: 'user' | 'work_request' | 'message';
}

interface AnalyticsJobData {
  type: 'track-event' | 'update-metrics' | 'generate-report';
  event?: string;
  userId?: string;
  data: Record<string, any>;
}

interface NotificationJobData {
  type: 'push-notification' | 'websocket-broadcast' | 'sms';
  userId: string;
  message: string;
  data?: Record<string, any>;
}

// Email worker
const emailWorker = new Worker(
  'email',
  async (job: Job<EmailJobData>) => {
    logger.info({ jobId: job.id, type: job.data.type }, 'Processing email job');
    
    try {
      switch (job.data.type) {
        case 'welcome':
          await emailService.sendWelcomeEmail(job.data.to, job.data.data);
          break;
        case 'verification':
          await emailService.sendVerificationEmail(job.data.to, job.data.data);
          break;
        case 'password-reset':
          await emailService.sendPasswordResetEmail(job.data.to, job.data.data);
          break;
        case 'work-request-notification':
          await emailService.sendWorkRequestNotification(job.data.to, job.data.data);
          break;
        case 'rating-reminder':
          await emailService.sendRatingReminder(job.data.to, job.data.data);
          break;
        default:
          throw new Error(`Unknown email job type: ${job.data.type}`);
      }
      
      logger.info({ jobId: job.id, type: job.data.type }, 'Email job completed');
    } catch (error) {
      logger.error({ jobId: job.id, error }, 'Email job failed');
      throw error;
    }
  },
  { connection, concurrency: 5 }
);

// Moderation worker
const moderationWorker = new Worker(
  'moderation',
  async (job: Job<ModerationJobData>) => {
    logger.info({ jobId: job.id, type: job.data.type }, 'Processing moderation job');
    
    try {
      const result = await moderationService.reviewContent(
        job.data.resourceId,
        job.data.resourceType,
        job.data.type
      );
      
      if (result.requiresAction) {
        // Update database with moderation result
        await prisma.moderationLog.create({
          data: {
            resourceId: job.data.resourceId,
            resourceType: job.data.resourceType,
            action: result.action,
            reason: result.reason,
            confidence: result.confidence,
          },
        });
        
        // Take automated action if confidence is high
        if (result.confidence > 0.8) {
          await moderationService.takeAutomatedAction(
            job.data.resourceId,
            job.data.resourceType,
            result.action
          );
        }
      }
      
      logger.info({ jobId: job.id, result }, 'Moderation job completed');
    } catch (error) {
      logger.error({ jobId: job.id, error }, 'Moderation job failed');
      throw error;
    }
  },
  { connection, concurrency: 3 }
);

// Analytics worker
const analyticsWorker = new Worker(
  'analytics',
  async (job: Job<AnalyticsJobData>) => {
    logger.info({ jobId: job.id, type: job.data.type }, 'Processing analytics job');
    
    try {
      switch (job.data.type) {
        case 'track-event':
          await analyticsService.trackEvent(job.data.event!, job.data.userId, job.data.data);
          break;
        case 'update-metrics':
          await analyticsService.updateMetrics(job.data.data);
          break;
        case 'generate-report':
          await analyticsService.generateReport(job.data.data);
          break;
        default:
          throw new Error(`Unknown analytics job type: ${job.data.type}`);
      }
      
      logger.info({ jobId: job.id, type: job.data.type }, 'Analytics job completed');
    } catch (error) {
      logger.error({ jobId: job.id, error }, 'Analytics job failed');
      throw error;
    }
  },
  { connection, concurrency: 10 }
);

// Notification worker
const notificationWorker = new Worker(
  'notification',
  async (job: Job<NotificationJobData>) => {
    logger.info({ jobId: job.id, type: job.data.type }, 'Processing notification job');
    
    try {
      switch (job.data.type) {
        case 'push-notification':
          await notificationService.sendPushNotification(job.data.userId, job.data.message, job.data.data);
          break;
        case 'websocket-broadcast':
          await notificationService.broadcastToUser(job.data.userId, job.data.message, job.data.data);
          break;
        case 'sms':
          await notificationService.sendSMS(job.data.userId, job.data.message);
          break;
        default:
          throw new Error(`Unknown notification job type: ${job.data.type}`);
      }
      
      logger.info({ jobId: job.id, type: job.data.type }, 'Notification job completed');
    } catch (error) {
      logger.error({ jobId: job.id, error }, 'Notification job failed');
      throw error;
    }
  },
  { connection, concurrency: 15 }
);

// Error handling for all workers
[emailWorker, moderationWorker, analyticsWorker, notificationWorker].forEach(worker => {
  worker.on('completed', (job) => {
    logger.debug({ queue: worker.name, jobId: job.id }, 'Job completed');
  });
  
  worker.on('failed', (job, err) => {
    logger.error({ queue: worker.name, jobId: job?.id, error: err }, 'Job failed');
  });
  
  worker.on('error', (err) => {
    logger.error({ queue: worker.name, error: err }, 'Worker error');
  });
});

// Health check server
import { createServer } from 'http';

const server = createServer((req, res) => {
  if (req.url === '/health' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      timestamp: new Date().toISOString(),
      service: 'worker',
      workers: {
        email: emailWorker.isRunning(),
        moderation: moderationWorker.isRunning(),
        analytics: analyticsWorker.isRunning(),
        notification: notificationWorker.isRunning(),
      },
    }));
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

const port = env.PORT || 3003;
server.listen(port, () => {
  logger.info({ port }, '🚀 Worker service running');
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  
  await Promise.all([
    emailWorker.close(),
    moderationWorker.close(),
    analyticsWorker.close(),
    notificationWorker.close(),
  ]);
  
  await prisma.$disconnect();
  await connection.quit();
  
  server.close(() => {
    logger.info('Worker service closed');
    process.exit(0);
  });
});

export { emailWorker, moderationWorker, analyticsWorker, notificationWorker };