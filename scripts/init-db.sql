-- Stratum AI Database Initialization Script
-- This script runs only on first database initialization

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application user with appropriate permissions (for production)
-- GRANT ALL PRIVILEGES ON DATABASE stratum_ai TO stratum;
