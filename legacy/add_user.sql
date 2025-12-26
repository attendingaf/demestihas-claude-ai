-- Add executive_mene user to users table
INSERT INTO users (id, display_name, role, created_at) 
VALUES ('executive_mene', 'Executive Mene', 'admin', NOW()) 
ON CONFLICT (id) DO NOTHING;

-- Verify insertion
SELECT id, display_name, role, created_at FROM users WHERE id = 'executive_mene';
