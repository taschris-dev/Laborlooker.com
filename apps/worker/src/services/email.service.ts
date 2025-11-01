import nodemailer from 'nodemailer';
import fs from 'fs/promises';
import path from 'path';
import Handlebars from 'handlebars';
import pino from 'pino';
import { envSchema } from '@laborlookers/types';

const env = envSchema.parse(process.env);
const logger = pino();

export class EmailService {
  private transporter: nodemailer.Transporter;
  private templates: Map<string, HandlebarsTemplateDelegate> = new Map();

  constructor() {
    this.transporter = nodemailer.createTransporter({
      host: env.SMTP_HOST || 'smtp.gmail.com',
      port: parseInt(env.SMTP_PORT || '587'),
      secure: false,
      auth: {
        user: env.SMTP_USER,
        pass: env.SMTP_PASS,
      },
    });

    this.loadTemplates();
  }

  private async loadTemplates() {
    try {
      const templatesPath = path.join(__dirname, '../templates');
      const templateFiles = [
        'welcome.hbs',
        'verification.hbs',
        'password-reset.hbs',
        'work-request-notification.hbs',
        'rating-reminder.hbs',
      ];

      for (const file of templateFiles) {
        try {
          const templateContent = await fs.readFile(
            path.join(templatesPath, file),
            'utf-8'
          );
          const templateName = file.replace('.hbs', '');
          this.templates.set(templateName, Handlebars.compile(templateContent));
        } catch (error) {
          logger.warn({ template: file }, 'Template not found, using fallback');
        }
      }
    } catch (error) {
      logger.error({ error }, 'Failed to load email templates');
    }
  }

  private async sendEmail(to: string, subject: string, html: string) {
    try {
      const result = await this.transporter.sendMail({
        from: `"LaborLookers" <${env.SMTP_FROM || env.SMTP_USER}>`,
        to,
        subject,
        html,
      });

      logger.info({ to, subject, messageId: result.messageId }, 'Email sent successfully');
      return result;
    } catch (error) {
      logger.error({ to, subject, error }, 'Failed to send email');
      throw error;
    }
  }

  async sendWelcomeEmail(to: string, data: { name: string; verificationUrl?: string }) {
    const template = this.templates.get('welcome');
    const html = template 
      ? template(data)
      : `
        <h1>Welcome to LaborLookers, ${data.name}!</h1>
        <p>Thank you for joining our platform. We're excited to help you connect with opportunities.</p>
        ${data.verificationUrl ? `<p><a href="${data.verificationUrl}">Verify your email</a></p>` : ''}
      `;

    return this.sendEmail(to, 'Welcome to LaborLookers!', html);
  }

  async sendVerificationEmail(to: string, data: { name: string; verificationUrl: string }) {
    const template = this.templates.get('verification');
    const html = template 
      ? template(data)
      : `
        <h1>Verify your email address</h1>
        <p>Hi ${data.name},</p>
        <p>Please click the link below to verify your email address:</p>
        <p><a href="${data.verificationUrl}">Verify Email</a></p>
        <p>This link will expire in 24 hours.</p>
      `;

    return this.sendEmail(to, 'Verify your email address', html);
  }

  async sendPasswordResetEmail(to: string, data: { name: string; resetUrl: string }) {
    const template = this.templates.get('password-reset');
    const html = template 
      ? template(data)
      : `
        <h1>Reset your password</h1>
        <p>Hi ${data.name},</p>
        <p>You requested a password reset. Click the link below to set a new password:</p>
        <p><a href="${data.resetUrl}">Reset Password</a></p>
        <p>This link will expire in 1 hour. If you didn't request this, please ignore this email.</p>
      `;

    return this.sendEmail(to, 'Reset your password', html);
  }

  async sendWorkRequestNotification(to: string, data: { 
    recipientName: string;
    senderName: string;
    workTitle: string;
    workUrl: string;
    type: 'new_request' | 'status_update' | 'message';
  }) {
    const template = this.templates.get('work-request-notification');
    
    let subject = '';
    switch (data.type) {
      case 'new_request':
        subject = `New work request: ${data.workTitle}`;
        break;
      case 'status_update':
        subject = `Work request update: ${data.workTitle}`;
        break;
      case 'message':
        subject = `New message about: ${data.workTitle}`;
        break;
    }

    const html = template 
      ? template(data)
      : `
        <h1>${subject}</h1>
        <p>Hi ${data.recipientName},</p>
        <p>${data.senderName} has updated the work request "${data.workTitle}".</p>
        <p><a href="${data.workUrl}">View Work Request</a></p>
      `;

    return this.sendEmail(to, subject, html);
  }

  async sendRatingReminder(to: string, data: { 
    name: string;
    workTitle: string;
    ratingUrl: string;
    otherPartyName: string;
  }) {
    const template = this.templates.get('rating-reminder');
    const html = template 
      ? template(data)
      : `
        <h1>Rate your recent work experience</h1>
        <p>Hi ${data.name},</p>
        <p>How was your experience working on "${data.workTitle}" with ${data.otherPartyName}?</p>
        <p>Your feedback helps maintain quality on our platform.</p>
        <p><a href="${data.ratingUrl}">Leave a Rating</a></p>
      `;

    return this.sendEmail(to, 'Rate your recent work experience', html);
  }
}