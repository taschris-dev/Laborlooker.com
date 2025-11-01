import { PrismaClient } from '@prisma/client';
import pino from 'pino';

const logger = pino();
const prisma = new PrismaClient();

export class ModerationService {
  async reviewContent(resourceId: string, resourceType: 'user' | 'work_request' | 'message', moderationType: string) {
    logger.info({ resourceId, resourceType, moderationType }, 'Starting content moderation');

    try {
      let content = '';
      let metadata: any = {};

      // Fetch content based on resource type
      switch (resourceType) {
        case 'user':
          const user = await prisma.user.findUnique({
            where: { id: resourceId },
            include: { profile: true }
          });
          if (user?.profile) {
            content = `${user.profile.bio || ''} ${user.profile.skills || ''}`.trim();
            metadata = { userId: user.id, email: user.email };
          }
          break;

        case 'work_request':
          const workRequest = await prisma.workRequest.findUnique({
            where: { id: resourceId }
          });
          if (workRequest) {
            content = `${workRequest.title} ${workRequest.description}`.trim();
            metadata = { workRequestId: workRequest.id, ownerId: workRequest.ownerId };
          }
          break;

        case 'message':
          const message = await prisma.message.findUnique({
            where: { id: resourceId }
          });
          if (message) {
            content = message.content;
            metadata = { messageId: message.id, senderId: message.senderId };
          }
          break;
      }

      if (!content) {
        logger.warn({ resourceId, resourceType }, 'No content found for moderation');
        return { requiresAction: false, confidence: 0, action: null, reason: 'No content found' };
      }

      // Simple content moderation rules
      const moderationResult = this.analyzeContent(content);
      
      logger.info({ 
        resourceId, 
        resourceType, 
        result: moderationResult 
      }, 'Content moderation completed');

      return moderationResult;

    } catch (error) {
      logger.error({ resourceId, resourceType, error }, 'Content moderation failed');
      throw error;
    }
  }

  private analyzeContent(content: string) {
    const lowercaseContent = content.toLowerCase();
    
    // Define moderation rules
    const profanityWords = [
      'spam', 'scam', 'fake', 'fraud', 'illegal', 'drugs', 
      'violence', 'harassment', 'discriminat', 'hate'
    ];
    
    const suspiciousPatterns = [
      /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, // Credit card patterns
      /\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b/, // SSN patterns
      /password\s*[:=]\s*\w+/i, // Password exposure
      /bitcoin|crypto|investment.*guaranteed/i, // Crypto scams
    ];

    let score = 0;
    let flags: string[] = [];

    // Check for profanity
    for (const word of profanityWords) {
      if (lowercaseContent.includes(word)) {
        score += 0.3;
        flags.push(`Contains inappropriate word: ${word}`);
      }
    }

    // Check for suspicious patterns
    for (const pattern of suspiciousPatterns) {
      if (pattern.test(content)) {
        score += 0.4;
        flags.push(`Contains suspicious pattern: ${pattern.source}`);
      }
    }

    // Check for excessive caps
    const capsRatio = (content.match(/[A-Z]/g) || []).length / content.length;
    if (capsRatio > 0.5 && content.length > 20) {
      score += 0.2;
      flags.push('Excessive use of capital letters');
    }

    // Check for repetitive content
    const words = content.split(/\s+/);
    const uniqueWords = new Set(words);
    if (words.length > 10 && uniqueWords.size / words.length < 0.3) {
      score += 0.3;
      flags.push('Repetitive content detected');
    }

    // Determine action based on score
    let action = null;
    let requiresAction = false;

    if (score >= 0.8) {
      action = 'suspend';
      requiresAction = true;
    } else if (score >= 0.5) {
      action = 'flag_for_review';
      requiresAction = true;
    } else if (score >= 0.3) {
      action = 'monitor';
      requiresAction = true;
    }

    return {
      requiresAction,
      confidence: Math.min(score, 1),
      action,
      reason: flags.join('; ') || 'Content appears acceptable',
      flags,
      score
    };
  }

  async takeAutomatedAction(resourceId: string, resourceType: 'user' | 'work_request' | 'message', action: string) {
    logger.info({ resourceId, resourceType, action }, 'Taking automated moderation action');

    try {
      switch (action) {
        case 'suspend':
          if (resourceType === 'user') {
            await prisma.user.update({
              where: { id: resourceId },
              data: { 
                isActive: false,
                suspendedAt: new Date(),
                suspensionReason: 'Automated moderation - content violation'
              }
            });
          } else if (resourceType === 'work_request') {
            await prisma.workRequest.update({
              where: { id: resourceId },
              data: { status: 'SUSPENDED' }
            });
          }
          break;

        case 'flag_for_review':
          // Create admin notification for manual review
          await prisma.adminNotification.create({
            data: {
              type: 'MODERATION_REVIEW',
              title: `Content flagged for review`,
              message: `${resourceType} ${resourceId} requires manual review`,
              metadata: { resourceId, resourceType, action },
              priority: 'HIGH'
            }
          });
          break;

        case 'monitor':
          // Add to monitoring list
          await prisma.moderationWatch.create({
            data: {
              resourceId,
              resourceType,
              reason: 'Automated flagging - suspicious content',
              watchUntil: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) // 7 days
            }
          });
          break;
      }

      logger.info({ resourceId, resourceType, action }, 'Automated action completed');
    } catch (error) {
      logger.error({ resourceId, resourceType, action, error }, 'Failed to take automated action');
      throw error;
    }
  }
}