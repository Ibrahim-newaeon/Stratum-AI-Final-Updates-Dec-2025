# Stratum AI Beta Deployment Guide

## Quick Start

### Prerequisites
- DigitalOcean account
- Domain with DNS access
- SSH key configured

### 1. Create Infrastructure

**DigitalOcean Droplet:**
```bash
# Create via console or CLI
doctl compute droplet create stratum-beta \
  --region nyc1 \
  --size s-2vcpu-4gb \
  --image docker-20-04 \
  --ssh-keys <your-ssh-key-id>
```

**Managed PostgreSQL:**
- Go to: DigitalOcean > Databases > Create
- Engine: PostgreSQL 16
- Plan: Basic ($15/mo)
- Region: Same as Droplet (nyc1)
- Database name: `stratum_ai`

### 2. Configure DNS

Add A record pointing to your Droplet IP:
```
Type: A
Name: beta
Value: <droplet-ip>
TTL: 300
```

### 3. Server Setup

SSH into your Droplet and run:
```bash
ssh root@<droplet-ip>

# Download and run setup
curl -fsSL https://raw.githubusercontent.com/Ibrahim-newaeon/Javna-StratumAi/main/scripts/deploy-beta.sh -o /tmp/deploy.sh
chmod +x /tmp/deploy.sh
/tmp/deploy.sh setup
```

### 4. Configure Environment

Edit `/opt/stratum-ai/.env.production`:
```bash
cd /opt/stratum-ai
nano .env.production
```

**Required values to change:**
1. `SECRET_KEY` - Generate: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
2. `JWT_SECRET_KEY` - Generate another unique key
3. `PII_ENCRYPTION_KEY` - Generate another unique key
4. `DATABASE_URL` - Get from DigitalOcean Database dashboard
5. `DATABASE_URL_SYNC` - Same connection, without `+asyncpg`
6. `SMTP_PASSWORD` - SendGrid API key (if using email)

### 5. Deploy

```bash
cd /opt/stratum-ai
./scripts/deploy-beta.sh deploy
```

### 6. Verify

```bash
# Check status
./scripts/deploy-beta.sh status

# View logs
./scripts/deploy-beta.sh logs

# Test HTTPS
curl https://beta.stratum-ai.com/health
```

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `./deploy-beta.sh setup` | Initial server setup |
| `./deploy-beta.sh deploy` | Full deployment |
| `./deploy-beta.sh update` | Update to latest version |
| `./deploy-beta.sh status` | Check service health |
| `./deploy-beta.sh logs [service]` | View logs |
| `./deploy-beta.sh backup` | Create backup |
| `./deploy-beta.sh rollback` | Rollback to last backup |
| `./deploy-beta.sh stop` | Stop all services |
| `./deploy-beta.sh restart` | Restart all services |
| `./deploy-beta.sh migrate` | Run DB migrations |
| `./deploy-beta.sh shell [service]` | Shell access |

---

## Architecture

```
                    [Internet]
                        │
                   [Cloudflare DNS]
                        │
              [DigitalOcean Droplet]
                   4GB RAM / 2 vCPU
                        │
         ┌──────┬──────┬──────┬──────┐
         │      │      │      │      │
      [Nginx] [API]  [Worker] [Beat] [Frontend]
         │      │      │      │      │
         └──────┴──────┴──────┴──────┘
                        │
              ┌─────────┴─────────┐
              │                   │
      [PostgreSQL]            [Redis]
      (Managed DB)         (On Droplet)
```

---

## Estimated Costs

| Resource | Monthly Cost |
|----------|-------------|
| Droplet (4GB/2vCPU) | $24 |
| Managed PostgreSQL | $15 |
| Domain (if new) | ~$1 |
| **Total** | **~$40/month** |

---

## Security Checklist

- [ ] All secrets generated and unique
- [ ] SSL certificate installed
- [ ] Firewall configured (only 22, 80, 443)
- [ ] Database SSL enabled (sslmode=require)
- [ ] Debug mode disabled
- [ ] CORS restricted to beta domain

---

## Troubleshooting

### Services not starting
```bash
docker compose -f docker-compose.beta.yml logs
```

### Database connection issues
- Verify DATABASE_URL in .env.production
- Check DigitalOcean firewall allows Droplet IP
- Ensure `sslmode=require` is in connection string

### SSL certificate issues
```bash
# Renew manually
certbot renew --force-renewal
docker compose -f docker-compose.beta.yml exec nginx nginx -s reload
```

### Out of memory
```bash
# Check memory usage
docker stats
# Restart services
./scripts/deploy-beta.sh restart
```
