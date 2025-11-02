-- LaborLooker PostgreSQL Extensions Setup
-- Run these commands in Railway's PostgreSQL console

-- ============================================================================
-- ESSENTIAL EXTENSIONS FOR LABORLOOKER PLATFORM
-- ============================================================================

-- 1. UUID Generation (CRITICAL - for secure IDs, referral links, payment tokens)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Advanced Encryption (CRITICAL - for data security, password hashing)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 3. Fuzzy Text Search (HIGH - for intelligent search, typo tolerance)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 4. Key-Value Storage (HIGH - for user preferences, metadata)
CREATE EXTENSION IF NOT EXISTS hstore;

-- 5. Advanced Indexing (MEDIUM - for performance optimization)
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- 6. Query Performance Monitoring (MEDIUM - for optimization)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 7. Geographic Data (HIGH - for location-based matching)
-- Note: PostGIS might not be available on all Railway plans
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- LABORLOOKER-SPECIFIC OPTIMIZED INDEXES
-- ============================================================================

-- User Authentication & Account Management
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_verified 
ON "user" (email, email_verified);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_account_type 
ON "user" (account_type, approved);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created 
ON "user" (created_at DESC);

-- Job Posting Optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_postings_status_budget 
ON job_posting (status, budget, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_postings_category 
ON job_posting (category, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_postings_location 
ON job_posting (location, status);

-- Professional Profile Search (requires pg_trgm)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_professional_business_name_trgm 
ON professional_profile USING GIN (business_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_professional_specialties_trgm 
ON professional_profile USING GIN (specialties gin_trgm_ops);

-- Customer Profile Optimization  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customer_company_trgm 
ON customer_profile USING GIN (billing_company gin_trgm_ops);

-- Networking & Referrals
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_referral_links_active 
ON referral_link (is_active, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_referral_links_user 
ON referral_link (user_id, is_active);

-- Swipe System Optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_swipe_actions_swiper 
ON swipe_action (swiper_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_swipe_actions_target 
ON swipe_action (target_id, swipe_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_swipe_matches_users 
ON swipe_match (user1_id, user2_id, status);

-- Payment & Invoice Tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_status_due 
ON invoice (status, due_date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contractor_invoice_status 
ON contractor_invoice (status, created_at DESC);

-- Campaign & Lead Management
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_campaign_user_status 
ON campaign (user_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lead_campaign_status 
ON lead (campaign_id, status, created_at DESC);

-- Work Request Optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_work_request_professional 
ON work_request (professional_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_work_request_customer 
ON work_request (customer_id, status, created_at DESC);

-- ============================================================================
-- VERIFY EXTENSIONS INSTALLATION
-- ============================================================================

-- Check installed extensions
SELECT extname, extversion 
FROM pg_extension 
WHERE extname IN (
    'uuid-ossp', 'pgcrypto', 'pg_trgm', 'hstore', 
    'btree_gin', 'pg_stat_statements', 'postgis'
)
ORDER BY extname;

-- ============================================================================
-- EXAMPLE USAGE FOR LABORLOOKER FEATURES
-- ============================================================================

-- Example 1: Generate secure referral link
-- INSERT INTO referral_link (user_id, link_code, created_at, is_active)
-- VALUES (123, uuid_generate_v4(), NOW(), true);

-- Example 2: Fuzzy contractor search (find "plumer" when searching for "plumber")
-- SELECT business_name, similarity(business_name, 'plumer') as score
-- FROM professional_profile 
-- WHERE business_name % 'plumer'
-- ORDER BY score DESC;

-- Example 3: Store user preferences with HSTORE
-- UPDATE "user" SET preferences = hstore(ARRAY[
--     'notification_frequency', 'daily',
--     'max_distance', '25',
--     'preferred_contact', 'email'
-- ]) WHERE id = 123;

-- Example 4: Encrypt sensitive data
-- INSERT INTO secure_data (user_id, encrypted_ssn)
-- VALUES (123, crypt('123-45-6789', gen_salt('bf')));

-- ============================================================================
-- PERFORMANCE MONITORING QUERIES
-- ============================================================================

-- Monitor slow queries (requires pg_stat_statements)
-- SELECT query, calls, total_time, mean_time, rows
-- FROM pg_stat_statements 
-- ORDER BY mean_time DESC 
-- LIMIT 10;

-- ============================================================================
-- MAINTENANCE COMMANDS
-- ============================================================================

-- Update statistics for better query planning
ANALYZE;

-- Rebuild indexes if needed (run during maintenance windows)
-- REINDEX DATABASE railway;

-- ============================================================================
-- NOTES FOR RAILWAY DEPLOYMENT
-- ============================================================================

/*
1. Run these commands in Railway's PostgreSQL console or via railway connect
2. Some extensions (like PostGIS) may not be available on all Railway plans
3. CONCURRENTLY indexes can be created without downtime
4. Monitor extension usage with pg_stat_statements
5. Consider upgrading Railway plan if PostGIS is needed for location features
*/