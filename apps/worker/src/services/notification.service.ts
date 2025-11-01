import pino from 'pino';
import { io } from '../main';

const logger = pino();

export class NotificationService {
  async sendPushNotification(userId: string, message: string, data?: Record<string, any>) {
    logger.info({ userId, message }, 'Sending push notification');

    try {
      // In a real implementation, you would integrate with services like:
      // - Firebase Cloud Messaging (FCM)
      // - Apple Push Notification Service (APNs)
      // - Web Push API
      
      // For now, we'll simulate the push notification
      logger.info({ userId, message, data }, 'Push notification sent (simulated)');
      
      // Also broadcast via WebSocket as fallback
      await this.broadcastToUser(userId, message, { 
        ...data, 
        type: 'push_notification' 
      });

    } catch (error) {
      logger.error({ userId, message, error }, 'Failed to send push notification');
      throw error;
    }
  }

  async broadcastToUser(userId: string, message: string, data?: Record<string, any>) {
    logger.info({ userId, message }, 'Broadcasting to user via WebSocket');

    try {
      // Broadcast to user's personal room
      io.to(`user:${userId}`).emit('notification', {
        message,
        timestamp: new Date().toISOString(),
        ...data,
      });

      logger.debug({ userId, message }, 'WebSocket broadcast sent');
    } catch (error) {
      logger.error({ userId, message, error }, 'Failed to broadcast to user');
      throw error;
    }
  }

  async sendSMS(userId: string, message: string) {
    logger.info({ userId, message }, 'Sending SMS notification');

    try {
      // In a real implementation, you would integrate with services like:
      // - Twilio
      // - AWS SNS
      // - Nexmo/Vonage
      
      // For now, we'll simulate the SMS
      logger.info({ userId, message }, 'SMS notification sent (simulated)');

    } catch (error) {
      logger.error({ userId, message, error }, 'Failed to send SMS');
      throw error;
    }
  }

  async broadcastToRoom(room: string, message: string, data?: Record<string, any>) {
    logger.info({ room, message }, 'Broadcasting to room via WebSocket');

    try {
      io.to(room).emit('broadcast', {
        message,
        timestamp: new Date().toISOString(),
        ...data,
      });

      logger.debug({ room, message }, 'Room broadcast sent');
    } catch (error) {
      logger.error({ room, message, error }, 'Failed to broadcast to room');
      throw error;
    }
  }

  async notifyWorkRequestUpdate(workRequestId: string, type: 'status_change' | 'new_message' | 'new_application', data: any) {
    logger.info({ workRequestId, type }, 'Notifying work request update');

    try {
      // Broadcast to work request room
      await this.broadcastToRoom(`work_request:${workRequestId}`, 
        `Work request ${type.replace('_', ' ')}`, 
        { workRequestId, type, ...data }
      );

      // Send individual notifications to relevant users
      if (data.notifyUsers && Array.isArray(data.notifyUsers)) {
        for (const userId of data.notifyUsers) {
          await this.broadcastToUser(
            userId,
            `Update on your work request`,
            { workRequestId, type, ...data }
          );
        }
      }

    } catch (error) {
      logger.error({ workRequestId, type, error }, 'Failed to notify work request update');
      throw error;
    }
  }

  async notifyNewMessage(conversationId: string, senderId: string, recipientId: string, message: string) {
    logger.info({ conversationId, senderId, recipientId }, 'Notifying new message');

    try {
      // Notify recipient
      await this.broadcastToUser(recipientId, 'New message received', {
        conversationId,
        senderId,
        messagePreview: message.substring(0, 100),
        type: 'new_message'
      });

      // Broadcast to conversation room
      await this.broadcastToRoom(`conversation:${conversationId}`, 'New message', {
        senderId,
        messagePreview: message.substring(0, 100),
        type: 'new_message'
      });

    } catch (error) {
      logger.error({ conversationId, senderId, recipientId, error }, 'Failed to notify new message');
      throw error;
    }
  }

  async notifySystemAlert(level: 'info' | 'warning' | 'error', title: string, message: string, targetUsers?: string[]) {
    logger.info({ level, title, targetUsers }, 'Sending system alert');

    try {
      const alertData = {
        level,
        title,
        message,
        timestamp: new Date().toISOString(),
        type: 'system_alert'
      };

      if (targetUsers && targetUsers.length > 0) {
        // Send to specific users
        for (const userId of targetUsers) {
          await this.broadcastToUser(userId, title, alertData);
        }
      } else {
        // Broadcast to all connected users
        io.emit('system_alert', alertData);
      }

      logger.info({ level, title, targetCount: targetUsers?.length || 'all' }, 'System alert sent');
    } catch (error) {
      logger.error({ level, title, error }, 'Failed to send system alert');
      throw error;
    }
  }
}