# Stratum AI - Complete Setup Guide

This guide walks you through deploying Stratum AI on DigitalOcean from start to finish.

---

## Table of Contents

1. [Create DigitalOcean Account](#1-create-digitalocean-account)
2. [Create SSH Key](#2-create-ssh-key)
3. [Create Droplet](#3-create-droplet)
4. [Configure Domain](#4-configure-domain)
5. [Deploy Application](#5-deploy-application)
6. [Create Admin User](#6-create-admin-user)
7. [Configure Email](#7-configure-email)
8. [Verify Deployment](#8-verify-deployment)

---

## 1. Create DigitalOcean Account

### Step 1.1: Sign Up
1. Go to **https://www.digitalocean.com**
2. Click **"Sign Up"**
3. Enter email and password (or use Google/GitHub)
4. Verify your email

### Step 1.2: Add Payment Method
1. Go to **Billing** → **Payment Methods**
2. Add credit card or PayPal
3. New accounts get **$200 free credit** for 60 days

### Step 1.3: Create Project
1. Click **"New Project"** in left sidebar
2. Name: `Stratum AI`
3. Description: `Ad Performance Platform`
4. Environment: `Production`
5. Click **"Create Project"**

---

## 2. Create SSH Key

SSH keys let you securely connect to your server without passwords.

### On Windows (PowerShell):

```powershell
# Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# Press Enter for default location (C:\Users\YourName\.ssh\id_ed25519)
# Enter a passphrase (optional but recommended)

# View your public key
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

### On Mac/Linux:

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"

# Press Enter for default location (~/.ssh/id_ed25519)
# Enter a passphrase (optional but recommended)

# View your public key
cat ~/.ssh/id_ed25519.pub
```

### Add SSH Key to DigitalOcean:

1. Go to **Settings** → **Security** → **SSH Keys**
2. Click **"Add SSH Key"**
3. Paste your public key (starts with `ssh-ed25519`)
4. Name: `My Laptop` (or any name)
5. Click **"Add SSH Key"**

---

## 3. Create Droplet

### Step 3.1: Start Creation
1. Click **"Create"** → **"Droplets"**

### Step 3.2: Choose Region
Select the region closest to your users:
- **New York** (NYC1/NYC3) - US East
- **San Francisco** (SFO3) - US West
- **London** (LON1) - Europe
- **Singapore** (SGP1) - Asia
- **Bangalore** (BLR1) - India

### Step 3.3: Choose Image
1. Click **"Marketplace"** tab
2. Search for **"Docker"**
3. Select **"Docker on Ubuntu 22.04"**

### Step 3.4: Choose Size

**Recommended (Production):**
| Plan | CPU | RAM | Storage | Price |
|------|-----|-----|---------|-------|
| **Basic** | 4 vCPU | 8 GB | 160 GB | $48/mo |

**Minimum (Testing/Development):**
| Plan | CPU | RAM | Storage | Price |
|------|-----|-----|---------|-------|
| **Basic** | 2 vCPU | 4 GB | 80 GB | $24/mo |

### Step 3.5: Choose Authentication
1. Select **"SSH Key"**
2. Check the SSH key you added earlier

### Step 3.6: Additional Options (Optional)
- ✅ **Enable Monitoring** (free)
- ✅ **Enable Backups** (+$9.60/mo, recommended)

### Step 3.7: Finalize
1. **Hostname:** `stratum-ai`
2. **Project:** Select "Stratum AI"
3. Click **"Create Droplet"**

### Step 3.8: Wait for Creation
- Takes 30-60 seconds
- Copy the **IP address** when ready (e.g., `164.92.123.45`)

---

## 4. Configure Domain

### Step 4.1: Add Domain to DigitalOcean

1. Go to **Networking** → **Domains**
2. Enter your domain: `yourdomain.com`
3. Click **"Add Domain"**

### Step 4.2: Create DNS Records

Add these A records pointing to your Droplet IP:

| Type | Hostname | Value | TTL |
|------|----------|-------|-----|
| A | @ | YOUR_DROPLET_IP | 300 |
| A | api | YOUR_DROPLET_IP | 300 |
| A | app | YOUR_DROPLET_IP | 300 |

### Step 4.3: Update Domain Nameservers

At your domain registrar (GoDaddy, Namecheap, etc.), set nameservers to:
```
ns1.digitalocean.com
ns2.digitalocean.com
ns3.digitalocean.com
```

### Step 4.4: Wait for DNS Propagation
- Usually 5-30 minutes
- Can take up to 48 hours in rare cases
- Check status: https://dnschecker.org

---

## 5. Deploy Application

### Step 5.1: Connect to Server

```bash
# Replace with your Droplet IP
ssh root@YOUR_DROPLET_IP

# Example:
ssh root@164.92.123.45
```

First connection will ask to verify fingerprint - type `yes`.

### Step 5.2: Clone Repository

```bash
# Clone the repository
git clone https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025.git /opt/stratum

# Navigate to project
cd /opt/stratum

# Make deploy script executable
chmod +x scripts/deploy.sh
```

### Step 5.3: Run Full Deployment

```bash
./scripts/deploy.sh full
```

This will prompt you for:
1. **API Domain:** `api.yourdomain.com`
2. **App Domain:** `app.yourdomain.com`
3. **Admin Email:** `admin@yourdomain.com`
4. **Database Password:** Press Enter to auto-generate

**The script will:**
- ✅ Update system packages
- ✅ Install Docker (already installed on Docker image)
- ✅ Install Nginx and Certbot
- ✅ Configure firewall
- ✅ Generate secure credentials
- ✅ Obtain SSL certificates
- ✅ Configure Nginx reverse proxy
- ✅ Start all Docker containers
- ✅ Run database migrations

**This takes about 5-10 minutes.**

### Step 5.4: Verify Services

```bash
# Check status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs api
```

---

## 6. Create Admin User

### Step 6.1: Connect to API Container

```bash
cd /opt/stratum
docker compose exec api python
```

### Step 6.2: Run Setup Script

```python
from app.db.session import SessionLocal
from app.models import Tenant, User, UserRole
from app.core.security import get_password_hash, encrypt_pii, hash_pii_for_lookup

db = SessionLocal()

# Create tenant
tenant = Tenant(
    name='Your Company Name',
    slug='your-company',
    plan='professional',
    max_users=10,
    max_campaigns=100,
)
db.add(tenant)
db.commit()
db.refresh(tenant)

# Create admin user
email = 'admin@yourdomain.com'  # Change this!
password = 'YourSecurePassword123!'  # Change this!

user = User(
    tenant_id=tenant.id,
    email=encrypt_pii(email),
    email_hash=hash_pii_for_lookup(email),
    password_hash=get_password_hash(password),
    full_name=encrypt_pii('Admin User'),
    role=UserRole.ADMIN,
    is_active=True,
    is_verified=True,
)
db.add(user)
db.commit()

print(f'Tenant ID: {tenant.id}')
print(f'User Email: {email}')
print('Admin user created successfully!')

# Exit Python
exit()
```

### Step 6.3: Test Login

1. Open **https://app.yourdomain.com**
2. Login with the email and password you created

---

## 7. Configure Email (Optional)

To enable password reset and email notifications:

### Step 7.1: Get SendGrid API Key

1. Sign up at **https://sendgrid.com** (free tier: 100 emails/day)
2. Go to **Settings** → **API Keys**
3. Click **"Create API Key"**
4. Name: `Stratum AI`
5. Permissions: **Full Access** or **Restricted** (Mail Send only)
6. Copy the API key (starts with `SG.`)

### Step 7.2: Update Environment

```bash
cd /opt/stratum
nano .env
```

Update these values:
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your_api_key_here
FROM_EMAIL=noreply@yourdomain.com
FROM_NAME=Stratum AI
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`

### Step 7.3: Restart API

```bash
docker compose restart api
```

### Step 7.4: Verify Email (SendGrid)

1. Go to SendGrid → **Settings** → **Sender Authentication**
2. **Verify Single Sender** with your FROM_EMAIL
3. Or set up **Domain Authentication** for better deliverability

---

## 8. Verify Deployment

### Check All Services

```bash
# Service status
./scripts/deploy.sh status

# Expected output: all containers "Up" and "healthy"
```

### Test Endpoints

```bash
# Health check
curl https://api.yourdomain.com/health

# Expected: {"status": "healthy", ...}
```

### Test Application

1. **Landing Page:** https://yourdomain.com
2. **App Login:** https://app.yourdomain.com
3. **API Docs:** https://api.yourdomain.com/docs (dev only)

---

## Quick Reference Commands

### Service Management

```bash
cd /opt/stratum

# View status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs api
./scripts/deploy.sh logs worker
./scripts/deploy.sh logs db

# Restart services
docker compose restart api
docker compose restart worker

# Stop all services
docker compose down

# Start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Database

```bash
# Create backup
./scripts/deploy.sh backup

# Restore backup
./scripts/deploy.sh restore

# Connect to database
docker compose exec db psql -U stratum stratum_ai
```

### Updates

```bash
# Pull latest code and redeploy
cd /opt/stratum
git pull
./scripts/deploy.sh update
```

### SSL Certificates

```bash
# Check certificate status
certbot certificates

# Renew certificates (auto via cron)
certbot renew
```

---

## Troubleshooting

### Cannot Connect via SSH

```bash
# Check if droplet is running in DigitalOcean dashboard
# Verify your IP address is correct
# Try with verbose output:
ssh -v root@YOUR_DROPLET_IP
```

### SSL Certificate Failed

```bash
# Make sure DNS is propagated
dig api.yourdomain.com

# Retry SSL setup
./scripts/deploy.sh ssl
```

### API Not Responding

```bash
# Check API logs
docker compose logs api --tail=50

# Restart API
docker compose restart api

# Check if port 8000 is listening
netstat -tlnp | grep 8000
```

### Database Connection Error

```bash
# Check database status
docker compose ps db

# View database logs
docker compose logs db

# Restart database
docker compose restart db
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Scale down workers
docker compose up -d --scale worker=1
```

---

## Security Checklist

After deployment, verify:

- [ ] SSH key authentication working
- [ ] Password login disabled (optional)
- [ ] Firewall active (ports 22, 80, 443 only)
- [ ] SSL certificates valid
- [ ] Strong database password set
- [ ] Admin password is secure
- [ ] Backups enabled in DigitalOcean
- [ ] Monitoring enabled

---

## Cost Summary

| Service | Monthly Cost |
|---------|-------------|
| Droplet (4 vCPU, 8GB) | $48 |
| Backups | $9.60 |
| Domain (optional) | ~$12/year |
| **Total** | **~$58/month** |

Or start with smaller droplet at **$24/month** and upgrade as needed.

---

## Support

- **DigitalOcean Docs:** https://docs.digitalocean.com
- **Project Docs:** `/opt/stratum/docs/`
- **GitHub Issues:** https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025/issues

---

## Next Steps

After successful deployment:

1. **Configure Ad Platforms** - Add Meta, Google, TikTok API keys in Settings
2. **Set Up CAPI** - Configure Conversions API for each platform
3. **Create Campaigns** - Import or create campaigns to track
4. **Enable Automation** - Set up rules for automatic optimization
5. **Train ML Models** - Run ML training with your campaign data
