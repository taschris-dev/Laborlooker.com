-- Initialize database with required extensions and basic data

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create initial admin user (you can change these values)
-- This will be created after Prisma migrations are run

-- You can add any initial data or custom functions here
-- This file is automatically executed when the PostgreSQL container starts