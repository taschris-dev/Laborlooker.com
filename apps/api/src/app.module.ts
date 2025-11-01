import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { ThrottlerModule } from '@nestjs/throttler';
import { LoggerModule } from 'nestjs-pino';
import { envSchema } from '@laborlookers/types';
import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { WorkRequestsModule } from './work-requests/work-requests.module';
import { MediaModule } from './media/media.module';
import { HealthModule } from './health/health.module';
import { NotificationsModule } from './notifications/notifications.module';

@Module({
  imports: [
    // Configuration with validation
    ConfigModule.forRoot({
      isGlobal: true,
      validate: (config) => envSchema.parse(config),
      envFilePath: ['.env.local', '.env'],
    }),

    // Logging
    LoggerModule.forRoot({
      pinoHttp: {
        transport: process.env.NODE_ENV === 'development' 
          ? { target: 'pino-pretty' }
          : undefined,
        serializers: {
          req: (req) => ({
            id: req.id,
            method: req.method,
            url: req.url,
            headers: {
              host: req.headers.host,
              'user-agent': req.headers['user-agent'],
              referer: req.headers.referer,
            },
          }),
          res: (res) => ({
            statusCode: res.statusCode,
          }),
        },
      },
    }),

    // Rate limiting
    ThrottlerModule.forRoot([
      {
        ttl: 60000, // 1 minute
        limit: 100, // 100 requests per minute
      },
    ]),

    // Database
    PrismaModule,

    // Feature modules
    AuthModule,
    UsersModule,
    WorkRequestsModule,
    MediaModule,
    HealthModule,
    NotificationsModule,
  ],
})
export class AppModule {}