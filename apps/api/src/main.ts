import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { ConfigService } from '@nestjs/config';
import helmet from 'helmet';
import compression from 'compression';
import { AppModule } from './app.module';
import { Logger } from 'nestjs-pino';

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bufferLogs: true,
  });

  // Get config service
  const configService = app.get(ConfigService);
  const port = configService.get('PORT', 3000);
  const nodeEnv = configService.get('NODE_ENV', 'development');

  // Use Pino logger
  app.useLogger(app.get(Logger));

  // Security middleware
  app.use(helmet({
    contentSecurityPolicy: nodeEnv === 'production',
    crossOriginEmbedderPolicy: false,
  }));

  // Compression
  app.use(compression());

  // CORS
  app.enableCors({
    origin: nodeEnv === 'production' 
      ? ['https://laborlookers.com', 'https://app.laborlookers.com']
      : true,
    credentials: true,
  });

  // Global validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: {
        enableImplicitConversion: true,
      },
    }),
  );

  // Global prefix
  app.setGlobalPrefix('api/v1');

  // Swagger documentation
  if (nodeEnv !== 'production') {
    const config = new DocumentBuilder()
      .setTitle('LaborLookers API')
      .setDescription('The LaborLookers platform API')
      .setVersion('1.0')
      .addBearerAuth()
      .build();
    
    const document = SwaggerModule.createDocument(app, config);
    SwaggerModule.setup('api', app, document);
  }

  await app.listen(port, '0.0.0.0');
  
  const logger = app.get(Logger);
  logger.log(`🚀 Application is running on: http://0.0.0.0:${port}`);
  if (nodeEnv !== 'production') {
    logger.log(`📚 API Documentation: http://0.0.0.0:${port}/api`);
  }
}

bootstrap();