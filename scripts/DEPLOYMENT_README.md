# Stratum AI - Deployment Guide

## Quick Start

### 1. Get a Server

Recommended specifications:
- **VPS Provider**: DigitalOcean, AWS EC2, Google Cloud, Linode, Vultr
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 4 vCPUs minimum
- **RAM**: 8GB minimum
- **Storage**: 50GB SSD minimum
- **Network**: 1 Gbps

### 2. Point Domain to Server

Add DNS A records pointing to your server IP:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | api | YOUR_SERVER_IP | 300 |
| A | app | YOUR_SERVER_IP | 300 |
| A | @ | YOUR_SERVER_IP | 300 |

Wait for DNS propagation (5-30 minutes).

### 3. Upload Code to Server

```bash
# SSH into your server
ssh root@YOUR_SERVER_IP

# Clone repository
git clone https://github.com/YOUR_REPO/stratum-ai.git /opt/stratum
cd /opt/stratum

# Make deploy script executable
chmod +x scripts/deploy.sh
```

### 4. Run Full Deployment

```bash
# Run complete deployment
./scripts/deploy.sh full
```

This will:
1. Install Docker, Nginx, and Certbot
2. Configure the firewall
3. Generate secure credentials
4. Obtain SSL certificates
5. Configure Nginx reverse proxy
6. Start all services
7. Run database migrations

### 5. Verify Deployment

```bash
# Check service status
./scripts/deploy.sh status

# Check logs
./scripts/deploy.sh logs api

# Test endpoints
curl https://api.yourdomain.com/health
```

---

## Individual Commands

### Server Setup Only
```bash
./scripts/deploy.sh setup
```
Installs Docker, Nginx, Certbot, and configures firewall.

### Configure Environment
```bash
./scripts/deploy.sh configure
```
Generates `.env` file with secure credentials.

### SSL Certificates
```bash
./scripts/deploy.sh ssl
```
Obtains Let's Encrypt SSL certificates.

### Configure Nginx
```bash
./scripts/deploy.sh nginx
```
Sets up Nginx as reverse proxy.

### Deploy Application
```bash
./scripts/deploy.sh deploy
```
Builds and starts Docker containers.

### Update Application
```bash
./scripts/deploy.sh update
```
Pulls latest code, rebuilds, and restarts.

### Create Backup
```bash
./scripts/deploy.sh backup
```
Creates timestamped database backup.

### Restore Backup
```bash
./scripts/deploy.sh restore
```
Restores database from backup file.

### View Logs
```bash
./scripts/deploy.sh logs        # API logs
./scripts/deploy.sh logs worker # Worker logs
./scripts/deploy.sh logs db     # Database logs
```

### Check Status
```bash
./scripts/deploy.sh status
```
Shows service status, health checks, and resource usage.

---

## File Structure

```
/opt/stratum/
├── .env                    # Production configuration (generated)
├── docker-compose.yml      # Base Docker configuration
├── docker-compose.prod.yml # Production overrides
├── scripts/
│   ├── deploy.sh          # Main deployment script
│   └── DEPLOYMENT_README.md
├── backups/               # Database backups
├── backend/               # FastAPI application
├── frontend/              # React application
└── ml_service/            # ML models
```

---

## Post-Deployment

### Create Admin User

```bash
docker compose exec api python -c "
from app.db.session import SessionLocal
from app.models import Tenant, User, UserRole
from app.core.security import get_password_hash, encrypt_pii, hash_pii_for_lookup

db = SessionLocal()

# Create tenant
tenant = Tenant(name='My Company', slug='my-company', plan='professional')
db.add(tenant)
db.commit()

# Create admin user
email = 'admin@example.com'
user = User(
    tenant_id=tenant.id,
    email=encrypt_pii(email),
    email_hash=hash_pii_for_lookup(email),
    password_hash=get_password_hash('YourSecurePassword123'),
    full_name=encrypt_pii('Admin User'),
    role=UserRole.ADMIN,
    is_active=True,
    is_verified=True,
)
db.add(user)
db.commit()

print(f'Created tenant: {tenant.id}')
print(f'Created user: {email}')
"
```

### Configure Email (SendGrid)

1. Create SendGrid account at https://sendgrid.com
2. Create API key with "Mail Send" permissions
3. Update `.env`:
   ```
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=SG.your_api_key_here
   FROM_EMAIL=noreply@yourdomain.com
   ```
4. Restart API: `docker compose restart api`

### Configure Ad Platform APIs

Update `.env` with real API credentials:
```
USE_MOCK_AD_DATA=false
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_access_token
```

### Enable Error Tracking (Sentry)

1. Create Sentry project at https://sentry.io
2. Update `.env`:
   ```
   SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   ```
3. Restart services

---

## Maintenance

### Daily Tasks
- Monitor `/health` endpoint
- Check disk space: `df -h`
- Review error logs

### Weekly Tasks
- Run database backup: `./scripts/deploy.sh backup`
- Check for updates: `git fetch`
- Review performance metrics

### Monthly Tasks
- Rotate credentials if needed
- Update dependencies
- Review and clean old backups

---

## Troubleshooting

### Services not starting
```bash
docker compose logs api
docker compose logs db
docker compose logs redis
```

### Database connection failed
```bash
docker compose exec db psql -U stratum -c "SELECT 1"
```

### SSL certificate issues
```bash
certbot certificates
certbot renew --dry-run
```

### High memory usage
```bash
docker stats
# Scale down workers if needed
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale worker=2
```

### API returning 502
```bash
# Check if API container is running
docker compose ps api

# Check API health
curl http://localhost:8000/health

# Restart API
docker compose restart api
```

---

## Security Checklist

- [ ] Changed all default passwords
- [ ] Generated new SECRET_KEY and JWT_SECRET_KEY
- [ ] SSL certificates installed and auto-renewing
- [ ] Firewall configured (only ports 22, 80, 443)
- [ ] Database not exposed externally
- [ ] Redis not exposed externally
- [ ] CORS configured for production domains only
- [ ] Rate limiting enabled
- [ ] Sentry configured for error tracking
- [ ] Regular backups scheduled

---

## Support

For issues:
1. Check logs: `./scripts/deploy.sh logs`
2. Check status: `./scripts/deploy.sh status`
3. Review documentation in `/docs`
4. Open GitHub issue
