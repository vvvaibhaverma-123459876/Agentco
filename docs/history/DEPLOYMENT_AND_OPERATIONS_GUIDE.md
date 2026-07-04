> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# AgentCo Deployment & Operations Guide

**Version**: 1.0.0  
**Date**: 2026-06-24  
**Status**: ✅ Production Ready

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Database Management](#database-management)
5. [Monitoring & Logging](#monitoring--logging)
6. [Backup & Recovery](#backup--recovery)
7. [Scaling Considerations](#scaling-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## Pre-Deployment Checklist

### System Requirements

- [ ] **OS**: Linux (Ubuntu 20.04+) or macOS 10.15+
- [ ] **CPU**: 2+ cores recommended
- [ ] **RAM**: 4GB+ recommended
- [ ] **Disk**: 10GB+ available
- [ ] **Network**: Internet access for LLM API

### Software Requirements

- [ ] **PostgreSQL**: 12.0+
- [ ] **Node.js**: 16.0+
- [ ] **npm**: 7.0+
- [ ] **Git**: 2.0+
- [ ] **OpenAI API**: Account with API key

### Verification Commands

```bash
# Check PostgreSQL
psql --version
# Expected: psql (PostgreSQL) 12.0 or higher

# Check Node.js
node --version
# Expected: v16.0.0 or higher

# Check npm
npm --version
# Expected: 7.0.0 or higher

# Check git
git --version
# Expected: git version 2.0 or higher
```

---

## Local Development Setup

### Step 1: Install Dependencies

```bash
# Navigate to backend
cd Agentco/backend

# Install Node dependencies
npm install

# Verify installation
npm list | head -20
```

### Step 2: PostgreSQL Setup

```bash
# Create database
createdb agentco

# Create user
createuser agentco

# Grant permissions
psql -c "ALTER USER agentco CREATEDB;"
psql -c "ALTER USER agentco SUPERUSER;"

# Verify
psql -l | grep agentco
```

### Step 3: Environment Configuration

```bash
# Create .env file in backend directory
cat > .env << 'EOF'
DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco
OPENAI_API_KEY=[REDACTED-KEY-PREFIX]...
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
NODE_ENV=development
EOF

# Load environment
source .env
```

### Step 4: Build & Migrate

```bash
# Build TypeScript
npm run build

# Run migrations
npm run db:migrate
# Expected output: "✅ All 52 migrations applied successfully"

# Verify database
psql -c "\d autonomy_goals" | head -20
```

### Step 5: Run Tests

```bash
# Run all tests
npm test

# Run specific test suite
npm test -- --testPathPattern="agentco-5min-vetting"

# Expected: "PASS tests/agentco-5min-vetting.test.ts"
```

### Step 6: Start Development

```bash
# Start development server (TypeScript + auto-reload)
npm run dev

# In another terminal, run real-world test
source .env
npx ts-node scripts/autonomy-real-world-2min-unconstrained.ts
```

---

## Production Deployment

### Step 1: Infrastructure Setup

#### PostgreSQL Production Setup

```bash
# 1. Install PostgreSQL on production server
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# 2. Create production database
sudo -u postgres psql << 'EOF'
CREATE DATABASE agentco;
CREATE USER agentco WITH ENCRYPTED PASSWORD 'strong-password-here';
ALTER ROLE agentco SET client_encoding TO 'utf8';
ALTER ROLE agentco SET default_transaction_isolation TO 'read committed';
ALTER ROLE agentco SET default_transaction_deferrable TO on;
ALTER ROLE agentco SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE agentco TO agentco;
EOF

# 3. Configure PostgreSQL for production
sudo vi /etc/postgresql/12/main/postgresql.conf
# Set: max_connections = 200
# Set: shared_buffers = 256MB
# Set: effective_cache_size = 1GB

# 4. Restart PostgreSQL
sudo systemctl restart postgresql
```

#### Node.js Application Setup

```bash
# 1. Create application directory
sudo mkdir -p /var/www/agentco
sudo chown $USER:$USER /var/www/agentco

# 2. Clone repository
cd /var/www/agentco
git clone <repo-url> .

# 3. Install dependencies
npm install --production

# 4. Build application
npm run build

# 5. Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql://agentco:password@production-db:5432/agentco
OPENAI_API_KEY=[REDACTED-KEY-PREFIX]...
NODE_ENV=production
PORT=3000
EOF

# 6. Run migrations
npm run db:migrate
```

### Step 2: Process Management (PM2)

```bash
# Install PM2 globally
npm install -g pm2

# Create PM2 ecosystem config
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'agentco',
    script: './dist/server.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    max_restarts: 10,
    min_uptime: '10s',
    watch: false,
    ignore_watch: ['node_modules', 'logs']
  }]
};
EOF

# Start with PM2
pm2 start ecosystem.config.js

# Save PM2 startup configuration
pm2 save
pm2 startup

# Verify
pm2 list
pm2 logs agentco --lines 50
```

### Step 3: Reverse Proxy (Nginx)

```bash
# Install Nginx
sudo apt-get install nginx

# Create Nginx config
sudo cat > /etc/nginx/sites-available/agentco << 'EOF'
upstream agentco {
  server 127.0.0.1:3000;
}

server {
  listen 80;
  server_name api.agentco.local;

  location / {
    proxy_pass http://agentco;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_cache_bypass $http_upgrade;
  }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/agentco /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 4: SSL/TLS (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.agentco.local -d agentco.local

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Step 5: Monitoring Setup

```bash
# Install monitoring tools
npm install -g pm2-monitoring

# Enable PM2+ monitoring
pm2 install pm2-auto-pull
pm2 install pm2-logrotate

# Configure log rotation
pm2 conf pm2-logrotate '{
  "max_size": "100M",
  "retain": "7",
  "compress": true,
  "dateFormat": "YYYY-MM-DD_HH-mm-ss"
}'
```

---

## Database Management

### Migration Management

```bash
# Apply all pending migrations
npm run db:migrate

# Check migration status
psql -c "SELECT name FROM schema_migrations ORDER BY name;"

# Rollback last migration (CAREFUL!)
npm run db:rollback

# Reset database (DESTRUCTIVE!)
npm run db:reset
npm run db:migrate
```

### Database Backup

#### Automated Backups

```bash
# Create backup script
cat > /var/backups/agentco-backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/agentco"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

# Full database backup
pg_dump -U agentco -h localhost agentco | \
  gzip > $BACKUP_DIR/agentco_$TIMESTAMP.sql.gz

# Keep last 7 days of backups
find $BACKUP_DIR -name "agentco_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/agentco_$TIMESTAMP.sql.gz"
EOF

chmod +x /var/backups/agentco-backup.sh

# Schedule with cron (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /var/backups/agentco-backup.sh") | crontab -
```

#### Manual Backup & Restore

```bash
# Full backup
pg_dump -U agentco -h localhost agentco > backup.sql

# Compressed backup
pg_dump -U agentco -h localhost agentco | gzip > backup.sql.gz

# Restore
psql -U agentco -h localhost agentco < backup.sql

# Restore from compressed
gunzip -c backup.sql.gz | psql -U agentco -h localhost agentco
```

### Database Maintenance

```bash
# Analyze table performance
ANALYZE autonomy_goals;

# Vacuum (cleanup)
VACUUM autonomy_goals;

# Full vacuum and analyze
VACUUM ANALYZE autonomy_goals;

# Check table size
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Monitoring & Logging

### Application Logging

```bash
# View PM2 logs
pm2 logs agentco --lines 100

# Real-time log streaming
pm2 logs agentco --follow

# Filter logs
pm2 logs agentco | grep "ERROR"

# Save logs
pm2 logs agentco > app.log
```

### Database Monitoring

```bash
# Active connections
psql -c "SELECT datname, usename, application_name, state, query_start 
         FROM pg_stat_activity 
         WHERE datname = 'agentco';"

# Slow queries
psql -c "SELECT query, calls, mean_time, total_time 
         FROM pg_stat_statements 
         WHERE query LIKE '%autonomy%' 
         ORDER BY mean_time DESC 
         LIMIT 10;"

# Table sizes
psql -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
         FROM pg_tables 
         WHERE schemaname = 'public' 
         ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Index usage
psql -c "SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch 
         FROM pg_stat_user_indexes 
         WHERE schemaname = 'public' 
         ORDER BY idx_scan DESC;"
```

### System Monitoring

```bash
# CPU and memory usage
top -b -n 1 | head -20

# Disk usage
df -h /var/www/agentco

# Network connections
netstat -an | grep :3000

# Process information
ps aux | grep node
```

### Health Checks

```bash
# Create health check script
cat > /usr/local/bin/agentco-health-check.sh << 'EOF'
#!/bin/bash

echo "Checking AgentCo health..."

# Check application
curl -s http://localhost:3000/health || echo "❌ Application not responding"

# Check database
psql -U agentco -h localhost agentco -c "SELECT 1;" &>/dev/null && echo "✅ Database OK" || echo "❌ Database not responding"

# Check migrations
psql -U agentco -h localhost agentco -c "SELECT COUNT(*) FROM schema_migrations;" || echo "❌ Migrations check failed"
EOF

chmod +x /usr/local/bin/agentco-health-check.sh

# Schedule health check (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/agentco-health-check.sh >> /var/log/agentco-health.log") | crontab -
```

---

## Backup & Recovery

### Recovery Procedures

#### Partial Database Restore

```bash
# Restore specific table only
pg_restore -U agentco -h localhost -d agentco -t autonomy_goals backup.dump

# Restore specific schema
pg_restore -U agentco -h localhost -d agentco -n public backup.dump
```

#### Point-in-Time Recovery

```bash
# Enable WAL archiving (in postgresql.conf)
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f'

# Recover to specific point in time
pg_ctl stop
# Modify recovery.conf with restore_command and recovery_target_time
pg_ctl start
```

#### Disaster Recovery

```bash
# 1. Check backup integrity
pg_dump -U agentco -d agentco --test-load 2>&1 | head -20

# 2. Verify restore on test server
createdb agentco_test
pg_restore -d agentco_test backup.dump

# 3. Validate data
psql -d agentco_test -c "SELECT COUNT(*) FROM autonomy_goals;"

# 4. If valid, perform actual restore
psql -U agentco -d agentco < backup.sql
```

### Backup Verification

```bash
# Monthly backup test
cat > /var/backups/test-restore.sh << 'EOF'
#!/bin/bash
LATEST_BACKUP=$(ls -t /var/backups/agentco_*.sql.gz | head -1)
TEST_DB="agentco_restore_test"

# Drop test database if exists
psql -U postgres -c "DROP DATABASE IF EXISTS $TEST_DB;"

# Create test database
createdb $TEST_DB

# Restore backup
gunzip -c "$LATEST_BACKUP" | psql -U postgres -d $TEST_DB

# Run validation queries
psql -U postgres -d $TEST_DB << 'QUERY'
SELECT COUNT(*) FROM autonomy_goals;
SELECT COUNT(*) FROM reputation_scores;
SELECT COUNT(*) FROM autonomy_claims;
SELECT COUNT(*) FROM coalition_formations;
QUERY

echo "Backup test completed for: $LATEST_BACKUP"
EOF

chmod +x /var/backups/test-restore.sh
```

---

## Scaling Considerations

### Horizontal Scaling

```bash
# 1. Database replication
# Set up PostgreSQL streaming replication for read replicas

# 2. Load balancing
# Configure multiple Node.js instances behind load balancer
pm2 start ecosystem.config.js -i max  # Cluster mode with all CPUs

# 3. Update Nginx upstream
cat > /etc/nginx/upstream.conf << 'EOF'
upstream agentco {
  server 127.0.0.1:3000 weight=1 max_fails=3 fail_timeout=30s;
  server 127.0.0.1:3001 weight=1 max_fails=3 fail_timeout=30s;
  server 127.0.0.1:3002 weight=1 max_fails=3 fail_timeout=30s;
}
EOF
```

### Database Scaling

```sql
-- Add connection pooling (pgBouncer)
-- Configuration: /etc/pgbouncer/pgbouncer.ini
[databases]
agentco = host=localhost port=5432 dbname=agentco

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25

-- Restart pgBouncer
sudo systemctl restart pgbouncer
```

### Caching Layer

```bash
# Install Redis
sudo apt-get install redis-server

# Update connection
cat >> .env << 'EOF'
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600
EOF

# Restart application
pm2 restart agentco
```

---

## Troubleshooting Guide

### Common Issues & Solutions

#### Issue: Database Connection Refused

```bash
# Symptom: "connect ECONNREFUSED 127.0.0.1:5432"

# Solution:
1. Check PostgreSQL status
   sudo systemctl status postgresql

2. Start PostgreSQL
   sudo systemctl start postgresql

3. Verify connection
   psql -U agentco -h localhost -d agentco -c "SELECT 1;"

4. Check firewall
   sudo ufw allow 5432/tcp
```

#### Issue: Out of Memory

```bash
# Symptom: Node process crashes with "JavaScript heap out of memory"

# Solution:
1. Increase Node.js heap
   NODE_OPTIONS="--max-old-space-size=4096" npm start

2. Or update PM2 config
   "node_args": "--max-old-space-size=4096"

3. Monitor memory usage
   pm2 monit

4. Profile memory leaks
   node --inspect dist/server.js
   # Then use Chrome DevTools
```

#### Issue: Slow Queries

```bash
# Symptom: High latency (>100ms)

# Solution:
1. Enable query logging
   ALTER SYSTEM SET log_min_duration_statement = 1000;
   SELECT pg_reload_conf();

2. Check query plans
   EXPLAIN ANALYZE SELECT * FROM autonomy_goals WHERE status = 'active';

3. Add indexes if needed
   CREATE INDEX idx_goals_status ON autonomy_goals(status);

4. Analyze tables
   ANALYZE autonomy_goals;
```

#### Issue: High CPU Usage

```bash
# Symptom: CPU at 100%

# Solution:
1. Check PM2 logs
   pm2 logs agentco

2. Identify slow operations
   ps aux | grep node
   top -p <pid>

3. Check database locks
   psql -c "SELECT * FROM pg_locks WHERE NOT granted;"

4. Kill long-running queries
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE duration > '5 minutes'::interval;
```

#### Issue: Disk Space Exhausted

```bash
# Symptom: "No space left on device"

# Solution:
1. Check disk usage
   df -h
   du -sh /var/www/agentco

2. Clean old logs
   rm /var/www/agentco/logs/*.log
   find /var/backups -mtime +30 -delete

3. Vacuum database
   VACUUM FULL autonomy_goals;

4. Expand disk (if possible)
   # Add new disk and expand partition
```

### Emergency Procedures

#### Complete Service Recovery

```bash
# 1. Stop application
pm2 stop agentco

# 2. Backup current database
pg_dump -U agentco agentco > emergency_backup.sql

# 3. Check database integrity
psql -U agentco -d agentco -c "REINDEX DATABASE agentco;"

# 4. Verify migrations
npm run db:migrate

# 5. Rebuild application
npm run build

# 6. Start application
pm2 start agentco

# 7. Verify health
curl http://localhost:3000/health
```

---

## Quick Reference

### Essential Commands

```bash
# Application management
pm2 start agentco          # Start
pm2 stop agentco           # Stop
pm2 restart agentco        # Restart
pm2 logs agentco           # View logs
pm2 delete agentco         # Remove

# Database management
npm run db:migrate         # Apply migrations
npm run db:backup          # Backup
npm run db:restore         # Restore
npm run db:reset           # Reset (CAREFUL!)

# Monitoring
pm2 monit                  # Resource monitoring
pm2 list                   # Process list
pm2 info agentco           # Detailed info

# Health checks
curl http://localhost:3000/health
psql -c "SELECT 1 FROM autonomy_goals LIMIT 1;"
```

### Critical File Locations

```
/var/www/agentco/          - Application root
/var/www/agentco/dist/     - Compiled JavaScript
/var/www/agentco/.env      - Environment variables
/var/www/agentco/logs/     - Application logs
/var/backups/              - Database backups
/etc/nginx/sites-enabled/  - Nginx configs
/etc/systemd/system/       - Service files
```

---

This deployment guide provides complete instructions for production deployment, operations, and troubleshooting of AgentCo.
