import { PrismaClient } from '@prisma/client';
import pino from 'pino';

const logger = pino();
const prisma = new PrismaClient();

export class AnalyticsService {
  async trackEvent(event: string, userId?: string, data: Record<string, any> = {}) {
    logger.info({ event, userId, data }, 'Tracking analytics event');

    try {
      // Store event in analytics table
      await prisma.analyticsEvent.create({
        data: {
          event,
          userId,
          data: JSON.stringify(data),
          timestamp: new Date(),
          sessionId: data.sessionId || null,
          ipAddress: data.ipAddress || null,
          userAgent: data.userAgent || null,
        }
      });

      // Update user activity if userId provided
      if (userId) {
        await prisma.user.update({
          where: { id: userId },
          data: { lastActiveAt: new Date() }
        });
      }

      // Update real-time metrics
      await this.updateRealTimeMetrics(event, data);

      logger.debug({ event, userId }, 'Analytics event tracked successfully');
    } catch (error) {
      logger.error({ event, userId, error }, 'Failed to track analytics event');
      throw error;
    }
  }

  async updateMetrics(data: Record<string, any>) {
    logger.info({ data }, 'Updating analytics metrics');

    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      // Update daily metrics
      const dailyMetrics = await prisma.dailyMetrics.upsert({
        where: { date: today },
        update: {
          activeUsers: data.activeUsers || 0,
          newSignups: data.newSignups || 0,
          workRequestsCreated: data.workRequestsCreated || 0,
          workRequestsCompleted: data.workRequestsCompleted || 0,
          messagesExchanged: data.messagesExchanged || 0,
          totalRevenue: data.totalRevenue || 0,
          updatedAt: new Date(),
        },
        create: {
          date: today,
          activeUsers: data.activeUsers || 0,
          newSignups: data.newSignups || 0,
          workRequestsCreated: data.workRequestsCreated || 0,
          workRequestsCompleted: data.workRequestsCompleted || 0,
          messagesExchanged: data.messagesExchanged || 0,
          totalRevenue: data.totalRevenue || 0,
        }
      });

      logger.debug({ date: today, metrics: dailyMetrics }, 'Daily metrics updated');
    } catch (error) {
      logger.error({ data, error }, 'Failed to update metrics');
      throw error;
    }
  }

  async generateReport(data: { type: string; startDate: Date; endDate: Date; userId?: string }) {
    logger.info({ data }, 'Generating analytics report');

    try {
      const { type, startDate, endDate, userId } = data;

      let report: any = {};

      switch (type) {
        case 'user_activity':
          report = await this.generateUserActivityReport(startDate, endDate, userId);
          break;
        
        case 'platform_overview':
          report = await this.generatePlatformOverviewReport(startDate, endDate);
          break;
        
        case 'revenue':
          report = await this.generateRevenueReport(startDate, endDate);
          break;
        
        default:
          throw new Error(`Unknown report type: ${type}`);
      }

      // Store report in database
      await prisma.analyticsReport.create({
        data: {
          type,
          startDate,
          endDate,
          userId,
          data: JSON.stringify(report),
          generatedAt: new Date(),
        }
      });

      logger.info({ type, startDate, endDate }, 'Analytics report generated successfully');
      return report;

    } catch (error) {
      logger.error({ data, error }, 'Failed to generate report');
      throw error;
    }
  }

  private async updateRealTimeMetrics(event: string, data: any) {
    const now = new Date();
    const hourKey = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}-${now.getHours()}`;

    try {
      switch (event) {
        case 'user_signup':
          await this.incrementMetric('signups', hourKey);
          break;
        
        case 'work_request_created':
          await this.incrementMetric('work_requests', hourKey);
          break;
        
        case 'message_sent':
          await this.incrementMetric('messages', hourKey);
          break;
        
        case 'page_view':
          await this.incrementMetric('page_views', hourKey);
          break;
      }
    } catch (error) {
      logger.error({ event, error }, 'Failed to update real-time metrics');
    }
  }

  private async incrementMetric(metric: string, timeKey: string) {
    await prisma.realTimeMetrics.upsert({
      where: { 
        metric_timeKey: {
          metric,
          timeKey
        }
      },
      update: {
        value: { increment: 1 },
        updatedAt: new Date(),
      },
      create: {
        metric,
        timeKey,
        value: 1,
      }
    });
  }

  private async generateUserActivityReport(startDate: Date, endDate: Date, userId?: string) {
    const whereClause = {
      timestamp: {
        gte: startDate,
        lte: endDate,
      },
      ...(userId && { userId }),
    };

    const events = await prisma.analyticsEvent.groupBy({
      by: ['event'],
      where: whereClause,
      _count: {
        event: true,
      },
      orderBy: {
        _count: {
          event: 'desc',
        },
      },
    });

    const totalEvents = await prisma.analyticsEvent.count({
      where: whereClause,
    });

    const uniqueUsers = await prisma.analyticsEvent.findMany({
      where: whereClause,
      select: { userId: true },
      distinct: ['userId'],
    }).then(results => results.filter(r => r.userId).length);

    return {
      events,
      totalEvents,
      uniqueUsers,
      dateRange: { startDate, endDate },
    };
  }

  private async generatePlatformOverviewReport(startDate: Date, endDate: Date) {
    const metrics = await prisma.dailyMetrics.findMany({
      where: {
        date: {
          gte: startDate,
          lte: endDate,
        },
      },
      orderBy: { date: 'asc' },
    });

    const totals = metrics.reduce((acc, metric) => ({
      activeUsers: acc.activeUsers + metric.activeUsers,
      newSignups: acc.newSignups + metric.newSignups,
      workRequestsCreated: acc.workRequestsCreated + metric.workRequestsCreated,
      workRequestsCompleted: acc.workRequestsCompleted + metric.workRequestsCompleted,
      messagesExchanged: acc.messagesExchanged + metric.messagesExchanged,
      totalRevenue: acc.totalRevenue + metric.totalRevenue,
    }), {
      activeUsers: 0,
      newSignups: 0,
      workRequestsCreated: 0,
      workRequestsCompleted: 0,
      messagesExchanged: 0,
      totalRevenue: 0,
    });

    return {
      metrics,
      totals,
      averages: {
        activeUsers: totals.activeUsers / metrics.length,
        newSignups: totals.newSignups / metrics.length,
        workRequestsCreated: totals.workRequestsCreated / metrics.length,
        workRequestsCompleted: totals.workRequestsCompleted / metrics.length,
        messagesExchanged: totals.messagesExchanged / metrics.length,
        dailyRevenue: totals.totalRevenue / metrics.length,
      },
      dateRange: { startDate, endDate },
    };
  }

  private async generateRevenueReport(startDate: Date, endDate: Date) {
    const transactions = await prisma.transaction.findMany({
      where: {
        createdAt: {
          gte: startDate,
          lte: endDate,
        },
        status: 'COMPLETED',
      },
      include: {
        workRequest: {
          select: {
            title: true,
            category: true,
          },
        },
      },
    });

    const totalRevenue = transactions.reduce((sum, tx) => sum + tx.amount, 0);
    const platformFee = transactions.reduce((sum, tx) => sum + (tx.platformFee || 0), 0);

    const byCategory = transactions.reduce((acc, tx) => {
      const category = tx.workRequest?.category || 'unknown';
      acc[category] = (acc[category] || 0) + tx.amount;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalRevenue,
      platformFee,
      netRevenue: totalRevenue - platformFee,
      transactionCount: transactions.length,
      averageTransactionValue: totalRevenue / transactions.length || 0,
      revenueByCategory: byCategory,
      dateRange: { startDate, endDate },
    };
  }
}