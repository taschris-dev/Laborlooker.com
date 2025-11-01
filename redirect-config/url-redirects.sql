-- URL mapping table for legacy redirects
-- This helps track and manage bulk redirects during migration

CREATE TABLE IF NOT EXISTS url_redirects (
  id SERIAL PRIMARY KEY,
  legacy_path VARCHAR(255) NOT NULL UNIQUE,
  new_path VARCHAR(255) NOT NULL,
  redirect_type INTEGER DEFAULT 301, -- 301 permanent, 302 temporary
  is_active BOOLEAN DEFAULT true,
  hit_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX idx_url_redirects_legacy_path ON url_redirects(legacy_path);
CREATE INDEX idx_url_redirects_active ON url_redirects(is_active);

-- Insert bulk redirect mappings
INSERT INTO url_redirects (legacy_path, new_path, redirect_type) VALUES
-- Authentication redirects
('/login', '/auth/signin', 301),
('/register', '/auth/signup', 301),
('/logout', '/auth/signout', 301),

-- Dashboard redirects
('/dashboard', '/dashboard/overview', 301),
('/dashboard/jobs', '/dashboard/work-requests', 301),
('/dashboard/profile', '/dashboard/profile', 301),
('/dashboard/payments', '/dashboard/payments', 301),

-- Profile redirects
('/profile', '/profiles', 301),
('/contractor', '/professionals', 301),
('/customer', '/customers', 301),

-- Work-related redirects
('/jobs', '/work-requests', 301),
('/work-request', '/work', 301),
('/post-job', '/work-requests/new', 301),
('/find-work', '/work-requests', 301),

-- Support redirects
('/help', '/support', 301),
('/contact', '/support/contact', 301),
('/faq', '/support/faq', 301),

-- Legal redirects
('/terms', '/legal/terms', 301),
('/privacy', '/legal/privacy', 301),
('/cookie-policy', '/legal/cookies', 301),

-- Admin redirects
('/admin', '/admin/dashboard', 301),
('/admin/users', '/admin/users', 301),
('/admin/reports', '/admin/analytics', 301),

-- API redirects
('/api/v1/users', '/api/users', 301),
('/api/v1/work-requests', '/api/work-requests', 301),
('/api/v1/auth', '/api/auth', 301),

-- Static asset redirects
('/static/css', '/assets/css', 301),
('/static/js', '/assets/js', 301),
('/static/images', '/assets/images', 301);

-- Function to get redirect URL
CREATE OR REPLACE FUNCTION get_redirect_url(input_path VARCHAR(255))
RETURNS TABLE(
  redirect_url VARCHAR(255),
  redirect_type INTEGER,
  is_found BOOLEAN
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ur.new_path as redirect_url,
    ur.redirect_type,
    true as is_found
  FROM url_redirects ur
  WHERE ur.legacy_path = input_path 
    AND ur.is_active = true
  LIMIT 1;
  
  -- If no exact match found, return null
  IF NOT FOUND THEN
    RETURN QUERY SELECT NULL::VARCHAR(255), NULL::INTEGER, false;
  END IF;
  
  -- Update hit counter
  UPDATE url_redirects 
  SET hit_count = hit_count + 1,
      updated_at = CURRENT_TIMESTAMP
  WHERE legacy_path = input_path;
  
END;
$$ LANGUAGE plpgsql;

-- View for redirect analytics
CREATE VIEW redirect_analytics AS
SELECT 
  legacy_path,
  new_path,
  hit_count,
  redirect_type,
  created_at,
  updated_at,
  CASE 
    WHEN hit_count = 0 THEN 'Unused'
    WHEN hit_count < 10 THEN 'Low Usage'
    WHEN hit_count < 100 THEN 'Medium Usage'
    ELSE 'High Usage'
  END as usage_category
FROM url_redirects
WHERE is_active = true
ORDER BY hit_count DESC;