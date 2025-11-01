import { z } from 'zod';

// === Environment Configuration ===
export const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  PORT: z.coerce.number().default(3000),
  
  // Database
  DATABASE_URL: z.string(),
  REDIS_URL: z.string(),
  
  // Auth
  JWT_SECRET: z.string(),
  JWT_REFRESH_SECRET: z.string(),
  
  // File Storage (Cloudflare R2)
  R2_ACCESS_KEY_ID: z.string(),
  R2_SECRET_ACCESS_KEY: z.string(),
  R2_ENDPOINT: z.string(),
  R2_BUCKET: z.string(),
  CDN_BASE_URL: z.string(),
  
  // OAuth
  GOOGLE_CLIENT_ID: z.string().optional(),
  GOOGLE_CLIENT_SECRET: z.string().optional(),
  APPLE_CLIENT_ID: z.string().optional(),
  APPLE_CLIENT_SECRET: z.string().optional(),
  
  // Observability
  SENTRY_DSN: z.string().optional(),
  OTLP_ENDPOINT: z.string().optional(),
  
  // Email
  SMTP_HOST: z.string().optional(),
  SMTP_PORT: z.coerce.number().optional(),
  SMTP_USER: z.string().optional(),
  SMTP_PASS: z.string().optional(),
  
  // DocuSign (from existing system)
  DOCUSIGN_INTEGRATION_KEY: z.string().optional(),
  DOCUSIGN_USER_ID: z.string().optional(),
  DOCUSIGN_ACCOUNT_ID: z.string().optional(),
});

export type Env = z.infer<typeof envSchema>;

// === User Types ===
export const accountTypeSchema = z.enum(['customer', 'professional', 'job_seeker', 'networking']);
export type AccountType = z.infer<typeof accountTypeSchema>;

export const userSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  accountType: accountTypeSchema,
  emailVerified: z.boolean(),
  approved: z.boolean(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export type User = z.infer<typeof userSchema>;

// === Auth Types ===
export const registerRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(15).regex(/^(?=.*[A-Z].*[A-Z])(?=.*[!@_\-.]).+$/, 
    'Password must have 2+ uppercase letters and 1 symbol (!@_-.)'),
  accountType: accountTypeSchema,
});

export const loginRequestSchema = z.object({
  email: z.string().email(),
  password: z.string(),
});

export const authResponseSchema = z.object({
  user: userSchema,
  accessToken: z.string(),
  refreshToken: z.string(),
});

// === Work Request Types ===
export const workRequestStatusSchema = z.enum(['pending', 'assigned', 'scheduled', 'completed', 'cancelled']);

export const workRequestSchema = z.object({
  id: z.string(),
  customerId: z.string(),
  contractorId: z.string().optional(),
  serviceCategories: z.array(z.string()),
  geographicArea: z.string(),
  status: workRequestStatusSchema,
  description: z.string(),
  customerName: z.string(),
  customerContact: z.string(),
  scheduledDate: z.date().optional(),
  completedDate: z.date().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export type WorkRequest = z.infer<typeof workRequestSchema>;

// === Profile Types ===
export const professionalProfileSchema = z.object({
  id: z.string(),
  userId: z.string(),
  businessName: z.string(),
  contactName: z.string(),
  phone: z.string().optional(),
  location: z.string().optional(),
  geographicArea: z.string().optional(),
  serviceRadius: z.number().optional(),
  billingPlan: z.string().optional(),
  commissionRate: z.number().optional(),
  services: z.array(z.string()),
  workHours: z.record(z.string()),
  licenseVerified: z.boolean(),
  insuranceVerified: z.boolean(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export const customerProfileSchema = z.object({
  id: z.string(),
  userId: z.string(),
  firstName: z.string(),
  lastName: z.string(),
  phone: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  zipCode: z.string().optional(),
  geographicArea: z.string().optional(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

// === Rating Types ===
export const ratingSchema = z.object({
  id: z.string(),
  raterId: z.string(),
  rateeId: z.string(),
  rating: z.number().min(1).max(5),
  comment: z.string().optional(),
  workRequestId: z.string().optional(),
  transactionType: z.string(),
  createdAt: z.date(),
});

// === Message Types ===
export const messageSchema = z.object({
  id: z.string(),
  senderId: z.string(),
  recipientId: z.string(),
  subject: z.string(),
  content: z.string(),
  messageType: z.enum(['direct', 'work_request', 'invoice', 'system']),
  priority: z.enum(['low', 'normal', 'high', 'urgent']),
  status: z.enum(['sent', 'delivered', 'read']),
  sentAt: z.date(),
  deliveredAt: z.date().optional(),
  readAt: z.date().optional(),
});

// === API Response Types ===
export const apiResponseSchema = z.object({
  success: z.boolean(),
  data: z.unknown().optional(),
  error: z.string().optional(),
  message: z.string().optional(),
});

export const paginatedResponseSchema = <T extends z.ZodType>(itemSchema: T) =>
  z.object({
    success: z.boolean(),
    data: z.object({
      items: z.array(itemSchema),
      total: z.number(),
      page: z.number(),
      limit: z.number(),
      totalPages: z.number(),
    }),
    error: z.string().optional(),
  });

// === File Upload Types ===
export const presignedUploadResponseSchema = z.object({
  uploadUrl: z.string(),
  fileUrl: z.string(),
  fileKey: z.string(),
  expiresIn: z.number(),
});

// === WebSocket Event Types ===
export const wsEventSchema = z.object({
  type: z.string(),
  payload: z.unknown(),
  timestamp: z.date(),
  userId: z.string().optional(),
});

export type WSEvent = z.infer<typeof wsEventSchema>;

// === Health Check Types ===
export const healthCheckSchema = z.object({
  status: z.enum(['ok', 'error']),
  timestamp: z.date(),
  uptime: z.number(),
  version: z.string().optional(),
  dependencies: z.record(z.object({
    status: z.enum(['ok', 'error']),
    responseTime: z.number().optional(),
    error: z.string().optional(),
  })).optional(),
});

export type HealthCheck = z.infer<typeof healthCheckSchema>;