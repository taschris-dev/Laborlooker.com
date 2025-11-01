import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { HealthCheck } from '@laborlookers/types';

@Injectable()
export class HealthService {
  constructor(private prisma: PrismaService) {}

  async check(): Promise<HealthCheck> {
    const startTime = Date.now();
    
    try {
      // Check database connectivity
      const dbStart = Date.now();
      await this.prisma.$queryRaw`SELECT 1`;
      const dbResponseTime = Date.now() - dbStart;

      return {
        status: 'ok',
        timestamp: new Date(),
        uptime: process.uptime(),
        version: process.env.npm_package_version,
        dependencies: {
          database: {
            status: 'ok',
            responseTime: dbResponseTime,
          },
        },
      };
    } catch (error) {
      return {
        status: 'error',
        timestamp: new Date(),
        uptime: process.uptime(),
        dependencies: {
          database: {
            status: 'error',
            error: error instanceof Error ? error.message : 'Unknown error',
          },
        },
      };
    }
  }
}