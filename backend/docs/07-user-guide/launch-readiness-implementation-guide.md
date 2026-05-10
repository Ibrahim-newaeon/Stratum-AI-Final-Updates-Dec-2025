# Launch Readiness — Step-by-Step Implementation Guide

This guide turns every Launch Readiness checklist item into actionable commands, clicks, and configurations. Follow phases in order — each phase unlocks the next.

> **Prerequisites:** GCP billing account, domain name, GitHub repo access, `gcloud` CLI installed and authenticated.

---

## Phase 1: Foundation

> **Goal:** GCP organization, projects, DNS, IAM, VPC, and infrastructure-as-code baseline.

### 1.1 Dedicated GCP Organization Created

```bash
# If you don't have a GCP org, create one via Google Workspace or Cloud Identity
# Free Cloud Identity: https://admin.google.com/signup/createnewaccount

# Verify org exists
gcloud organizations list
# Note the ORGANIZATION_ID

# Set default org for subsequent commands
gcloud config set organization YOUR_ORG_ID
```

### 1.2 Prod / Staging / Shared Projects Provisioned

```bash
# Create folder structure
ORG_ID="YOUR_ORG_ID"

# Create folders
gcloud resource-manager folders create --display-name="Stratum AI" --organization=$ORG_ID
# Note FOLDER_ID from output

FOLDER_ID="YOUR_FOLDER_ID"

# Create projects
gcloud projects create stratum-ai-prod --folder=$FOLDER_ID --name="Stratum AI Production"
gcloud projects create stratum-ai-staging --folder=$FOLDER_ID --name="Stratum AI Staging"
gcloud projects create stratum-ai-shared --folder=$FOLDER_ID --name="Stratum AI Shared"

# Link billing account to each project
BILLING_ID="YOUR_BILLING_ACCOUNT_ID"
for proj in stratum-ai-prod stratum-ai-staging stratum-ai-shared; do
  gcloud billing projects link $proj --billing-account=$BILLING_ID
done

# Enable essential APIs in shared project
gcloud config set project stratum-ai-shared

gcloud services enable cloudresourcemanager.googleapis.com \
  cloudbilling.googleapis.com \
  iam.googleapis.com \
  compute.googleapis.com \
  container.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

### 1.3 Production Domain Registered

```bash
# Register domain (example via Cloud DNS / Google Domains / Namecheap)
# If using Google Domains / Cloud DNS:

gcloud dns managed-zones create stratum-ai-zone \
  --dns-name="stratumai.app." \
  --description="Stratum AI production domain" \
  --visibility=public

# Get NS records to set at your registrar
gcloud dns record-sets list --zone=stratum-ai-zone --type=NS
# Copy these 4 NS records to your domain registrar
```

### 1.4 Cloud DNS Managed Zone Configured

```bash
# Add A record for root domain (point to load balancer IP later)
gcloud dns record-sets create stratumai.app. \
  --zone=stratum-ai-zone \
  --type=A \
  --ttl=300 \
  --rrdatas="0.0.0.0"  # placeholder, update after LB creation

# Add CNAME for www
gcloud dns record-sets create www.stratumai.app. \
  --zone=stratum-ai-zone \
  --type=CNAME \
  --ttl=300 \
  --rrdatas="stratumai.app."
```

### 1.5 Org Policies Enabled

```bash
# Set organization policies
gcloud resource-manager org-policies describe iam.disableServiceAccountKeyCreation --organization=$ORG_ID

# Disable service account key creation (use Workload Identity instead)
gcloud resource-manager org-policies set-policy --organization=$ORG_ID \
  --file=- <<EOF
constraint: constraints/iam.disableServiceAccountKeyCreation
booleanPolicy:
  enforced: true
EOF

# Enforce uniform bucket-level access
gcloud resource-manager org-policies set-policy --organization=$ORG_ID \
  --file=- <<EOF
constraint: constraints/storage.uniformBucketLevelAccess
booleanPolicy:
  enforced: true
EOF

# Restrict VM external IPs
gcloud resource-manager org-policies set-policy --organization=$ORG_ID \
  --file=- <<EOF
constraint: constraints/compute.vmExternalIpAccess
listPolicy:
  allValues: DENY
EOF
```

### 1.6 Security Command Center Enabled

```bash
# Enable Security Command Center Standard (free tier)
gcloud services enable securitycenter.googleapis.com --project=stratum-ai-shared

# SCC is automatically enabled for the org; verify:
gcloud scc assets list --organization=$ORG_ID --limit=5
```

### 1.7 Cloud Audit Logs + VPC Flow Logs Enabled

```bash
# Enable audit logging for all services
gcloud logging sinks create audit-log-sink \
  bigquery.googleapis.com/projects/stratum-ai-shared/datasets/audit_logs \
  --log-filter='protoPayload.serviceName!=""' \
  --project=stratum-ai-shared

# Enable VPC Flow Logs (will be configured when VPC is created)
```

### 1.8 IAM Groups Configured via Cloud Identity

```bash
# Create groups via Google Admin Console or gcloud identity
# Admin Console: https://admin.google.com → Directory → Groups

# Groups to create:
# - stratum-ai-admins@yourdomain.com (Superadmin access)
# - stratum-ai-developers@yourdomain.com (Developer access)
# - stratum-ai-viewers@yourdomain.com (Read-only)
```

### 1.9 Workload Identity Federation Set Up for GitHub Actions

```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create github-actions-pool \
  --project=stratum-ai-shared \
  --location=global \
  --display-name="GitHub Actions"

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc github-actions-provider \
  --project=stratum-ai-shared \
  --location=global \
  --workload-identity-pool=github-actions-pool \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Grant IAM roles to the pool
PROJECT_NUMBER=$(gcloud projects describe stratum-ai-shared --format='value(projectNumber)')

gcloud projects add-iam-policy-binding stratum-ai-shared \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025" \
  --role="roles/artifactregistry.writer"
```

### 1.10 Per-Workload Service Accounts Created

```bash
# Create service accounts
gcloud iam service-accounts create stratum-api \
  --display-name="Stratum API Service" \
  --project=stratum-ai-prod

gcloud iam service-accounts create stratum-worker \
  --display-name="Stratum Worker Service" \
  --project=stratum-ai-prod

gcloud iam service-accounts create stratum-scheduler \
  --display-name="Stratum Scheduler Service" \
  --project=stratum-ai-prod

gcloud iam service-accounts create stratum-migrate \
  --display-name="Stratum Migration Service" \
  --project=stratum-ai-prod

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding stratum-ai-prod \
  --member="serviceAccount:stratum-api@stratum-ai-prod.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

### 1.11 VPC with Private Subnets + Private Google Access

```bash
gcloud compute networks create stratum-vpc \
  --project=stratum-ai-prod \
  --subnet-mode=custom \
  --mtu=1460

# Create subnet in us-central1
gcloud compute networks subnets create stratum-subnet-us \
  --project=stratum-ai-prod \
  --network=stratum-vpc \
  --region=us-central1 \
  --range=10.0.0.0/20 \
  --enable-private-ip-google-access

# Create secondary ranges for pods and services
gcloud compute networks subnets update stratum-subnet-us \
  --project=stratum-ai-prod \
  --region=us-central1 \
  --add-secondary-ranges=pods=10.4.0.0/14,services=10.8.0.0/20
```

### 1.12 Cloud NAT Configured for Egress

```bash
# Allocate static IP for NAT
gcloud compute addresses create stratum-nat-ip \
  --region=us-central1 \
  --project=stratum-ai-prod

# Create router
gcloud compute routers create stratum-router \
  --network=stratum-vpc \
  --region=us-central1 \
  --project=stratum-ai-prod

# Create NAT
gcloud compute routers nats create stratum-nat \
  --router=stratum-router \
  --region=us-central1 \
  --nat-external-ip-pool=stratum-nat-ip \
  --nat-all-subnet-ip-ranges \
  --project=stratum-ai-prod
```

### 1.13 Static External IP Reserved for HTTPS Load Balancer

```bash
gcloud compute addresses create stratum-lb-ip \
  --global \
  --project=stratum-ai-prod

# Note the IP address
gcloud compute addresses describe stratum-lb-ip --global --project=stratum-ai-prod --format='value(address)'
```

### 1.14 Terraform Repository Initialized

```bash
# Create terraform repo
mkdir -p ~/stratum-ai-terraform && cd ~/stratum-ai-terraform
git init

# Create basic structure
mkdir -p environments/{prod,staging,shared} modules/{vpc,gke,dns,sql}

# Create backend.tf
cat > backend.tf <<'EOF'
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "stratum-ai-terraform-state"
    prefix = "terraform/state"
  }
}
EOF

# Create state bucket
gsutil mb -p stratum-ai-shared gs://stratum-ai-terraform-state
gsutil versioning set on gs://stratum-ai-terraform-state
```

---

## Phase 2: Data Layer

> **Goal:** Cloud SQL PostgreSQL, Redis, backups, migrations.

### 2.1 Cloud SQL PostgreSQL 16 Regional (HA) Provisioned

```bash
gcloud sql instances create stratum-postgres \
  --database-version=POSTGRES_16 \
  --tier=db-g1-small \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --storage-size=100GB \
  --storage-auto-increase \
  --storage-auto-increase-limit=500 \
  --backup-start-time=03:00 \
  --project=stratum-ai-prod

# Set password
gcloud sql users set-password postgres \
  --instance=stratum-postgres \
  --password=$(openssl rand -base64 32)
```

### 2.2 Cloud SQL Configured with Private IP Only

```bash
# Allocate IP range for private services
gcloud compute addresses create stratum-sql-range \
  --global \
  --purpose=VPC_PEERING \
  --addresses=10.10.0.0 \
  --prefix-length=16 \
  --network=stratum-vpc \
  --project=stratum-ai-prod

# Create private connection
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=stratum-sql-range \
  --network=stratum-vpc \
  --project=stratum-ai-prod

# Configure Cloud SQL to use private IP
gcloud sql instances patch stratum-postgres \
  --network=stratum-vpc \
  --no-assign-ip \
  --project=stratum-ai-prod
```

### 2.3 Cloud SQL Auth Proxy Configured

```bash
# Download Cloud SQL Auth Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.9.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Run locally (for development)
# ./cloud-sql-proxy --private-ip stratum-ai-prod:us-central1:stratum-postgres

# For GKE: add as sidecar in deployment manifests
```

### 2.4 Automated Daily Backups, 30-Day Retention

```bash
# Already enabled at creation with --backup-start-time=03:00
# Verify backup configuration
gcloud sql backups list --instance=stratum-postgres --project=stratum-ai-prod
```

### 2.5 Point-in-Time Recovery Enabled

```bash
gcloud sql instances patch stratum-postgres \
  --enable-point-in-time-recovery \
  --retained-transaction-log-days=7 \
  --project=stratum-ai-prod
```

### 2.6 Cross-Region Backup Copy to DR Region

```bash
# Create cross-region backup schedule
gcloud sql backups create --instance=stratum-postgres --project=stratum-ai-prod

# For automated cross-region: use Cloud Scheduler + Cloud Functions
# Or configure using Terraform with google_sql_database_instance settings
```

### 2.7 DB Flags Tuned

```bash
gcloud sql instances patch stratum-postgres \
  --database-flags="shared_buffers=256MB,effective_cache_size=768MB,work_mem=16MB" \
  --project=stratum-ai-prod
```

### 2.8 PgBouncer Connection Pool Deployed

```bash
# Deploy PgBouncer as a GKE Deployment (see Phase 3 for GKE setup)
# Or use Cloud SQL Proxy which handles pooling
```

### 2.9 Memorystore Redis 7 Standard Tier (HA) Provisioned

```bash
gcloud redis instances create stratum-redis \
  --tier=standard \
  --size=5 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --network=stratum-vpc \
  --connect-mode=PRIVATE_SERVICE_CONNECT \
  --project=stratum-ai-prod

# Get connection details
gcloud redis instances describe stratum-redis --region=us-central1 --project=stratum-ai-prod
```

### 2.10 Redis AUTH + In-Transit TLS Enabled

```bash
# Generate AUTH token
REDIS_AUTH=$(openssl rand -base64 32)

gcloud redis instances update stratum-redis \
  --region=us-central1 \
  --redis-config=auth-enabled=yes \
  --project=stratum-ai-prod

# Store auth token in Secret Manager (see Phase 4)
```

### 2.11 Redis 3-Database Topology Verified

```bash
# Connect and verify databases
redis-cli -h <REDIS_HOST> -p 6379 -a <AUTH_TOKEN> INFO keyspace

# Expected: 3 logical databases
# DB 0: cache
# DB 1: broker (Celery)
# DB 2: results (Celery results)
```

### 2.12 Alembic Rehearsed Against Cloud SQL Clone

```bash
# Create clone for testing
gcloud sql instances clone stratum-postgres stratum-postgres-clone \
  --project=stratum-ai-prod

# Run migrations against clone
# DATABASE_URL="postgresql+psycopg2://postgres:PASSWORD@localhost:5432/postgres" alembic upgrade head

# Delete clone when done
gcloud sql instances delete stratum-postgres-clone --project=stratum-ai-prod
```

### 2.13 Migration Rollbacks Documented

```bash
# Test rollback for latest migration
# alembic downgrade -1

# Document in runbook: docs/runbooks/database-migrations.md
```

### 2.14 Scheduled pg_dump to GCS

```bash
# Create Cloud Scheduler job for daily pg_dump
gcloud scheduler jobs create pg-dump \
  --schedule="0 4 * * *" \
  --timezone="America/New_York" \
  --uri="https://sqladmin.googleapis.com/v1/projects/stratum-ai-prod/instances/stratum-postgres/export" \
  --message-body="{\"exportContext\":{\"fileType\":\"SQL\",\"uri\":\"gs://stratum-ai-backups/daily/stratum-postgres-$(date +%Y%m%d).sql.gz\"}}"

# Create lifecycle rule for archive
gsutil lifecycle set - <<EOF gs://stratum-ai-backups
{
  "rule": [
    {
      "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
      "condition": {"age": 30}
    },
    {
      "action": {"type": "Delete"},
      "condition": {"age": 365}
    }
  ]
}
EOF
```

---

## Phase 3: Container Platform

> **Goal:** Artifact Registry, GKE Autopilot, Load Balancer, CDN, Cloud Armor.

### 3.1 Artifact Registry Repository Created (Multi-Region)

```bash
gcloud artifacts repositories create stratum-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="Stratum AI container images" \
  --project=stratum-ai-prod

# Configure Docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 3.2 Image Build Pipeline Pushes to Artifact Registry

```bash
# Build and push manually (CI will automate this)
docker build -t us-central1-docker.pkg.dev/stratum-ai-prod/stratum-images/api:latest .
docker push us-central1-docker.pkg.dev/stratum-ai-prod/stratum-images/api:latest
```

### 3.3 GKE Autopilot Cluster Provisioned

```bash
gcloud container clusters create-auto stratum-cluster \
  --region=us-central1 \
  --network=stratum-vpc \
  --subnetwork=stratum-subnet-us \
  --release-channel=regular \
  --project=stratum-ai-prod

# Get credentials
gcloud container clusters get-credentials stratum-cluster --region=us-central1 --project=stratum-ai-prod
```

### 3.4 Private Control Plane + Authorized Networks

```bash
# GKE Autopilot has private control plane by default
# Add authorized networks (your office / VPN IPs)
gcloud container clusters update stratum-cluster \
  --enable-master-authorized-networks \
  --master-authorized-networks="YOUR_OFFICE_IP/32" \
  --region=us-central1 \
  --project=stratum-ai-prod
```

### 3.5 Workload Identity Enabled

```bash
# GKE Autopilot enables Workload Identity by default
# Verify:
kubectl get serviceaccount default -n default -o yaml
# Should see: metadata.annotations.iam.gke.io/gcp-service-account
```

### 3.6 Binary Authorization Requires Signed Images

```bash
# Enable Binary Authorization
gcloud container binauthz policy create-standard-policy \
  --platform=gke \
  --project=stratum-ai-prod

# Require attestations
gcloud container binauthz policy update \
  --project=stratum-ai-prod \
  --file=- <<EOF
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  requireAttestationsBy:
    - projects/stratum-ai-prod/attestors/build-attestor
EOF
```

### 3.7 Deployment Manifests Applied

```bash
# Create namespace
kubectl create namespace stratum

# Apply deployment manifests (see k8s/ directory in repo)
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/scheduler-deployment.yaml
```

### 3.8 HorizontalPodAutoscaler Configured

```bash
# Apply HPA
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stratum-api-hpa
  namespace: stratum
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stratum-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
```

### 3.9 Default-Deny NetworkPolicies Applied

```bash
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: stratum
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-ingress
  namespace: stratum
spec:
  podSelector:
    matchLabels:
      app: stratum-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
EOF
```

### 3.10 Alembic Migrations Run as Kubernetes Job

```bash
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: alembic-migrate
  namespace: stratum
spec:
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: migrate
        image: us-central1-docker.pkg.dev/stratum-ai-prod/stratum-images/api:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
EOF
```

### 3.11 Liveness + Readiness Probes on `/health`

```yaml
# In deployment manifest:
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 3.12 Cloud SQL Auth Proxy Sidecar

```yaml
# In deployment manifest:
spec:
  containers:
  - name: cloud-sql-proxy
    image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.9.0
    args:
      - "--structured-logs"
      - "--private-ip"
      - "stratum-ai-prod:us-central1:stratum-postgres"
    securityContext:
      runAsNonRoot: true
```

### 3.13 Frontend Built + Deployed to GCS Bucket

```bash
# Build frontend
npm run build

# Create GCS bucket for frontend
gsutil mb -p stratum-ai-prod -l us-central1 gs://stratum-ai-frontend

# Upload build files
gsutil -m cp -r frontend/dist/* gs://stratum-ai-frontend/

# Make public (or use signed URLs)
gsutil iam ch allUsers:objectViewer gs://stratum-ai-frontend
```

### 3.14 HTTPS Load Balancer with URL Map

```bash
# Create backend services
gcloud compute backend-services create stratum-api-backend \
  --protocol=HTTP \
  --health-checks=stratum-api-health \
  --global \
  --project=stratum-ai-prod

# Create URL map
gcloud compute url-maps create stratum-url-map \
  --default-service=stratum-api-backend \
  --project=stratum-ai-prod

# Create SSL certificate
gcloud compute ssl-certificates create stratum-ssl-cert \
  --domains=stratumai.app \
  --global \
  --project=stratum-ai-prod

# Create target HTTPS proxy
gcloud compute target-https-proxies create stratum-https-proxy \
  --ssl-certificates=stratum-ssl-cert \
  --url-map=stratum-url-map \
  --project=stratum-ai-prod

# Create forwarding rule
gcloud compute forwarding-rules create stratum-https-forwarding \
  --load-balancing-scheme=EXTERNAL_MANAGED \
  --network-tier=PREMIUM \
  --address=stratum-lb-ip \
  --global \
  --ports=443 \
  --target-https-proxy=stratum-https-proxy \
  --project=stratum-ai-prod
```

### 3.15 Google-Managed SSL Certificate Attached

```bash
# Already created in 3.14
# Wait for certificate to provision (may take 15-60 min)
gcloud compute ssl-certificates describe stratum-ssl-cert --global --project=stratum-ai-prod
```

### 3.16 Cloud Armor Policy Applied

```bash
gcloud compute security-policies create stratum-security-policy \
  --project=stratum-ai-prod

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy=stratum-security-policy \
  --expression="true" \
  --action="rate-based-ban(100,600,ban_duration_sec=3600,conform_action=allow,exceed_action=deny(403),enforce_on_key=IP)" \
  --project=stratum-ai-prod

# Add OWASP rule
gcloud compute security-policies rules create 2000 \
  --security-policy=stratum-security-policy \
  --expression="evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 2})" \
  --action="deny(403)" \
  --project=stratum-ai-prod

# Attach to backend
gcloud compute backend-services update stratum-api-backend \
  --security-policy=stratum-security-policy \
  --global \
  --project=stratum-ai-prod
```

### 3.17 HTTP to HTTPS Redirect + HSTS

```bash
# Create HTTP forwarding rule that redirects to HTTPS
gcloud compute url-maps create stratum-http-redirect \
  --default-service=stratum-api-backend \
  --project=stratum-ai-prod

# Add redirect rule
gcloud compute url-maps add-path-matcher stratum-http-redirect \
  --path-matcher-name=redirect \
  --default-url-redirect=https://stratumai.app/
```

---

## Phase 4: Secrets & Config

> **Goal:** Production secrets generated, stored in Secret Manager, wired into workloads.

### 4.1 SECRET_KEY Generated

```bash
SECRET_KEY=$(openssl rand -base64 32)
gcloud secrets create secret-key --data-file=<(echo -n "$SECRET_KEY") --project=stratum-ai-prod
```

### 4.2 JWT_SECRET_KEY Generated

```bash
JWT_SECRET=$(openssl rand -base64 32)
gcloud secrets create jwt-secret-key --data-file=<(echo -n "$JWT_SECRET") --project=stratum-ai-prod
```

### 4.3 PII_ENCRYPTION_KEY Generated (Fernet)

```bash
# Generate Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > fernet.key
gcloud secrets create pii-encryption-key --data-file=fernet.key --project=stratum-ai-prod
rm fernet.key
```

### 4.4 Cloud SQL Password in Secret Manager

```bash
# Already created in Phase 2; store in Secret Manager
gcloud secrets create db-password --data-file=<(echo -n "YOUR_DB_PASSWORD") --project=stratum-ai-prod
```

### 4.5 Redis AUTH Token in Secret Manager

```bash
gcloud secrets create redis-auth --data-file=<(echo -n "$REDIS_AUTH") --project=stratum-ai-prod
```

### 4.6-4.12 Platform Credentials in Secret Manager

```bash
# Meta
gcloud secrets create meta-app-id --data-file=<(echo -n "YOUR_META_APP_ID") --project=stratum-ai-prod
gcloud secrets create meta-app-secret --data-file=<(echo -n "YOUR_META_APP_SECRET") --project=stratum-ai-prod
gcloud secrets create meta-access-token --data-file=<(echo -n "YOUR_META_ACCESS_TOKEN") --project=stratum-ai-prod

# Google
gcloud secrets create google-ads-developer-token --data-file=<(echo -n "YOUR_DEV_TOKEN") --project=stratum-ai-prod
gcloud secrets create google-ads-client-id --data-file=<(echo -n "YOUR_CLIENT_ID") --project=stratum-ai-prod
gcloud secrets create google-ads-client-secret --data-file=<(echo -n "YOUR_CLIENT_SECRET") --project=stratum-ai-prod

# TikTok
gcloud secrets create tiktok-app-id --data-file=<(echo -n "YOUR_TIKTOK_APP_ID") --project=stratum-ai-prod
gcloud secrets create tiktok-secret --data-file=<(echo -n "YOUR_TIKTOK_SECRET") --project=stratum-ai-prod

# Snapchat
gcloud secrets create snapchat-client-id --data-file=<(echo -n "YOUR_SNAPCHAT_CLIENT_ID") --project=stratum-ai-prod
gcloud secrets create snapchat-client-secret --data-file=<(echo -n "YOUR_SNAPCHAT_SECRET") --project=stratum-ai-prod

# WhatsApp
gcloud secrets create whatsapp-access-token --data-file=<(echo -n "YOUR_WHATSAPP_TOKEN") --project=stratum-ai-prod
gcloud secrets create whatsapp-verify-token --data-file=<(echo -n "YOUR_VERIFY_TOKEN") --project=stratum-ai-prod

# Stripe
gcloud secrets create stripe-secret-key --data-file=<(echo -n "sk_live_...") --project=stratum-ai-prod
gcloud secrets create stripe-publishable-key --data-file=<(echo -n "pk_live_...") --project=stratum-ai-prod
gcloud secrets create stripe-webhook-secret --data-file=<(echo -n "whsec_...") --project=stratum-ai-prod
```

### 4.13 SMTP / SendGrid Credentials

```bash
gcloud secrets create smtp-password --data-file=<(echo -n "YOUR_SMTP_PASSWORD") --project=stratum-ai-prod
```

### 4.14 Sentry DSN

```bash
gcloud secrets create sentry-dsn --data-file=<(echo -n "YOUR_SENTRY_DSN") --project=stratum-ai-prod
```

### 4.15 Secret Manager CSI Driver Mounts Secrets into Pods

```yaml
# In deployment manifest:
volumes:
- name: secrets-volume
  csi:
    driver: secrets-store.csi.k8s.io
    readOnly: true
    volumeAttributes:
      secretProviderClass: stratum-secrets

volumeMounts:
- name: secrets-volume
  mountPath: "/mnt/secrets"
  readOnly: true
```

### 4.16 CORS_ORIGINS Set to Exact Production Frontend URL

```bash
# In your .env or ConfigMap:
CORS_ORIGINS=https://stratumai.app,https://www.stratumai.app
```

### 4.17 USE_MOCK_AD_DATA Set to False

```bash
# In production ConfigMap:
USE_MOCK_AD_DATA=false
```

### 4.18 Git History Scanned for Leaked Secrets

```bash
# Install gitleaks
brew install gitleaks  # macOS
# or download from https://github.com/gitleaks/gitleaks

# Scan repo
gitleaks detect --source . --verbose

# Add to CI pipeline (see .github/workflows/ci.yml)
```

---

## Phase 5: Multi-Tenancy Hardening

> **Goal:** Tenant isolation verified across every query, task, endpoint.

### 5.1 Every Query Audited for tenant_id Filter

```bash
# Run audit script
python scripts/audit_tenant_isolation.py

# Or manually search for queries without tenant filter:
grep -r "select\|query\|filter" backend/app/api --include="*.py" | grep -v "tenant_id"
```

### 5.2 PostgreSQL Row-Level Security Enabled

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY tenant_isolation ON users
  USING (tenant_id = current_setting('app.current_tenant')::int);
```

### 5.3 Integration Tests Assert 403/404 on Cross-Tenant Access

```python
# In tests:
async def test_cannot_access_other_tenant_data(client, auth_headers_tenant_a):
    response = await client.get(
        "/api/v1/campaigns",
        headers={**auth_headers_tenant_a, "X-Tenant-ID": "2"}
    )
    assert response.status_code == 403
```

### 5.4 JWT tenant_id Validated on Every Request

```python
# In auth middleware:
from fastapi import Request, HTTPException

async def validate_tenant(request: Request):
    token_tenant = request.state.jwt_payload.get("tenant_id")
    header_tenant = request.headers.get("X-Tenant-ID")
    if token_tenant != int(header_tenant):
        raise HTTPException(status_code=403, detail="Tenant mismatch")
```

### 5.5 Rate Limits Scoped Per-Tenant

```python
# In rate limiter:
key = f"rate_limit:{tenant_id}:{endpoint}:{client_ip}"
```

### 5.6 Celery Tasks Carry + Re-Validate Tenant Context

```python
# In task decorator:
@app.task(bind=True)
def process_campaign(self, tenant_id, campaign_id):
    # Re-validate tenant context
    set_tenant_context(tenant_id)
    # ... process
```

### 5.7 Audit Log Scoped Per-Tenant

```sql
-- Ensure audit_log table has tenant_id column
ALTER TABLE audit_log ADD COLUMN tenant_id int;
CREATE INDEX idx_audit_log_tenant ON audit_log(tenant_id);
```

### 5.8 GDPR Erasure Cascade Documented + Tested

```python
# GDPR erasure endpoint:
@router.post("/gdpr/erasure")
async def gdpr_erasure(request: Request, user_id: int):
    """
    1. Anonymize PII in users table
    2. Delete or anonymize related records (cascade)
    3. Log erasure event
    4. Return confirmation ID
    """
```

---

## Phase 6: Trust Engine / Autopilot Safety

> **Goal:** Guardrails for automation that moves ad spend.

### 6.1 Trust Gate Thresholds Configurable Per Tenant

```python
# In tenant settings:
class TenantSettings(BaseModel):
    trust_gate_threshold: float = 0.7  # 0-1 scale
    autopilot_max_budget_shift_pct: float = 20.0
    autopilot_enforcement_mode: str = "advisory"  # advisory | auto
```

### 6.2 New Tenants Default to Advisory Mode

```python
# In tenant creation:
default_settings = {
    "autopilot_enforcement_mode": "advisory",
    "trust_gate_threshold": 0.7,
}
```

### 6.3 Global Autopilot Kill Switch

```python
# Feature flag in database:
class FeatureFlag(Base):
    name = "autopilot_kill_switch"
    value = False  # True = disable all autopilot
```

### 6.4 Circuit Breakers on Outbound API Calls

```python
# Using pybreaker or tenacity:
from pybreaker import CircuitBreaker

breaker = CircuitBreaker(fail_max=5, reset_timeout=60)

@breaker
def call_meta_api(...):
    ...
```

### 6.5 Dry-Run Mode Verified

```python
# In autopilot action:
if settings.autopilot_dry_run:
    logger.info(f"[DRY RUN] Would adjust budget for campaign {id} by {delta}")
    return DryRunResult(...)
```

### 6.6 Audit Retention 1 Year

```bash
# Set BigQuery table partition expiration
bq update --time_partitioning_expiration 31536000 stratum-ai-prod:audit.trust_gate_events
```

### 6.7 Spend Anomaly Alerts

```python
# Alert rule:
if spend_delta_pct > 30 and time_window < timedelta(minutes=15):
    send_alert(
        severity="critical",
        message=f"Spend anomaly detected: {spend_delta_pct}% change in 15 min"
    )
```

---

## Phase 7: Observability

> **Goal:** Logs, metrics, traces, alerts, error tracking.

### 7.1 Cloud Logging Ingesting Structured JSON

```python
# In Python logging config:
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        })
```

### 7.2 Log Sinks Export to GCS

```bash
gcloud logging sinks create gcs-sink \
  bigquery.googleapis.com/projects/stratum-ai-prod/datasets/logs \
  --log-filter='resource.type="k8s_container"' \
  --project=stratum-ai-prod
```

### 7.3 Cloud Monitoring Dashboards

```bash
# Create dashboard via gcloud or Cloud Console
# Key metrics to monitor:
# - Request latency (p50, p95, p99)
# - Error rate
# - Queue depth (Celery)
# - DB connection count
# - Trust gate decisions per minute
```

### 7.4 Managed Service for Prometheus

```bash
# Enable managed collection
gcloud container clusters update stratum-cluster \
  --region=us-central1 \
  --enable-managed-prometheus \
  --project=stratum-ai-prod
```

### 7.5 Managed Grafana

```bash
# Enable Grafana
gcloud monitoring dashboards create --config-from-file=dashboard.json
```

### 7.6 Alert Routing

```bash
# Create notification channel for Slack
gcloud alpha monitoring channels create \
  --display-name="Stratum Alerts" \
  --type=slack \
  --channel-labels=auth_token=YOUR_SLACK_TOKEN,channel_name="#alerts"

# Create alert policy
gcloud alpha monitoring policies create --policy-from-file=alert-policy.json
```

### 7.7 Sentry Configured

```bash
# Add to requirements: sentry-sdk[fastapi]
# In main.py:
import sentry_sdk
sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
)
```

### 7.8 External Synthetic Uptime Check

```bash
# Use UptimeRobot, Pingdom, or GCP uptime checks
gcloud monitoring uptime create stratum-uptime \
  --display-name="Stratum AI Homepage" \
  --protocol=https \
  --resource-type=url \
  --resource-labels=host=stratumai.app,path=/health \
  --period=60 \
  --project=stratum-ai-prod
```

### 7.9 Cloud Trace + Cloud Profiler

```bash
# Enable in deployment:
env:
- name: GOOGLE_CLOUD_PROJECT
  value: stratum-ai-prod
- name: ENABLE_PROFILER
  value: "true"
```

---

## Phase 8: Security & Compliance

> **Goal:** Dependency scanning, pen testing, headers, encryption, legal.

### 8.1 CI Dependency Scanning

```yaml
# .github/workflows/ci.yml:
- name: Dependency audit
  run: |
    pip install pip-audit
    pip-audit --requirement=backend/requirements.txt
    npm audit --audit-level=high
```

### 8.2 Binary Authorization Attestations

```bash
# Sign image after CI passes
gcloud beta container binauthz attestations sign-and-create \
  --artifact-url=us-central1-docker.pkg.dev/stratum-ai-prod/stratum-images/api:latest \
  --attestor=build-attestor \
  --keyversion-project=stratum-ai-prod \
  --keyversion-location=us-central1 \
  --keyversion-keyring=binauthz-keyring \
  --keyversion-key=build-key \
  --keyversion=1
```

### 8.3-8.12 Security Reviews, Pentest, MFA, CSP, PII, GDPR, Legal, VPC-SC, Runbook

These are process/documentation items:

| Item | Action |
|------|--------|
| Security review | Schedule internal security review meeting |
| Pentest | Hire third-party (e.g., Bishop Fox, NCC Group) |
| MFA | Enforce in Auth settings + Google Workspace |
| CSP headers | Configure in nginx/Cloud Armor |
| PII encryption | Verify Fernet encryption on all PII fields |
| GDPR endpoints | Test `/gdpr/export` and `/gdpr/erasure` |
| Legal docs | Draft ToS, Privacy Policy, DPA |
| VPC-SC | Configure perimeter in GCP Console |
| Incident runbook | Create `docs/runbooks/incident-response.md` |

---

## Phase 9: OAuth & Platform Compliance

> **Goal:** External approvals from ad platforms and payment processors.

### 9.1 Meta App Review

1. Go to https://developers.facebook.com/apps/YOUR_APP_ID/app-review/permissions
2. Request `ads_management`, `ads_read`, `business_management`
3. Submit app for review with screencast
4. Wait 3-5 business days

### 9.2 Google Ads API Production Token

1. Apply at https://ads.google.com/aw/apicenter
2. Complete Basic Access → Standard Access application
3. Wait 2-3 business days

### 9.3 TikTok App Approval

1. Go to https://business-api.tiktok.com/portal/
2. Submit app for review
3. Wait 5-7 business days

### 9.4 Snapchat App Approval

1. Go to https://developers.snap.com/
2. Submit app for review
3. Wait 3-5 business days

### 9.5 Stripe Live Mode

1. Switch to Live mode in Stripe Dashboard
2. Update webhook endpoint to production URL
3. Verify webhook signatures work

### 9.6 WhatsApp Business Number Verified

1. In Meta Business Suite → WhatsApp Manager
2. Add phone number
3. Verify via SMS or voice call
4. Display name approval (24-48 hours)

---

## Phase 10: Deploy Pipeline & Rollback

> **Goal:** CI/CD, staging parity, rollback procedures.

### 10.1 GitHub Actions Authenticates via WIF

```yaml
# .github/workflows/deploy.yml:
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
    - uses: actions/checkout@v4
    - uses: google-github-actions/auth@v2
      with:
        workload_identity_provider: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-actions-provider
        service_account: github-actions@stratum-ai-shared.iam.gserviceaccount.com
```

### 10.2 Pipeline Runs Tests, Builds, Pushes

```yaml
# Full pipeline:
1. Run unit tests
2. Run integration tests
3. Build Docker image
4. Push to Artifact Registry
5. Sign image (Binary Authorization)
6. Deploy to staging
7. Run smoke tests
8. Deploy to production (manual approval)
```

### 10.3 Staging Mirrors Prod

```bash
# Staging uses same architecture, smaller sizes:
# - Cloud SQL: db-f1-micro instead of db-g1-small
# - GKE: smaller node pools
# - Redis: 1 GB instead of 5 GB
```

### 10.4 Rolling Deploy Configured

```yaml
# In deployment spec:
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

### 10.5 Migration Job Runs Before API Rollout

```yaml
# In deployment pipeline:
steps:
- name: Run migrations
  run: kubectl apply -f k8s/migration-job.yaml && kubectl wait --for=condition=complete job/alembic-migrate

- name: Deploy API
  run: kubectl apply -f k8s/api-deployment.yaml
```

### 10.6 Staging-First Policy

```bash
# Require staging deployment before prod
# Enforced via GitHub Actions branch protection
```

### 10.7 Release Notes Automation

```bash
# Use GitHub releases or conventional commits:
npx semantic-release
# Generates changelog from conventional commit messages
```

---

## Phase 11: Pre-Launch Dress Rehearsal

> **Goal:** Load test, failover, restore, secret rotation, DR drills.

### 11.1 Load Test Against Staging (30+ Minutes)

```bash
# Install k6
brew install k6

# Run load test
k6 run --duration 30m --vus 100 load-test.js

# Check: response time p95 < 500ms, error rate < 0.1%
```

### 11.2 Cloud SQL Failover Drill

```bash
# Trigger failover
gcloud sql instances failover stratum-postgres --project=stratum-ai-prod

# Measure RTO (should be < 60 seconds for HA)
```

### 11.3 PITR Restore Drill

```bash
# Restore to a specific point in time
gcloud sql instances clone stratum-postgres stratum-restore-test \
  --point-in-time="2024-01-15T10:00:00Z" \
  --project=stratum-ai-prod

# Verify data integrity, then delete
gcloud sql instances delete stratum-restore-test --project=stratum-ai-prod
```

### 11.4 Secret Rotation Drill

```bash
# Rotate JWT secret
NEW_JWT=$(openssl rand -base64 32)
gcloud secrets versions add jwt-secret-key --data-file=<(echo -n "$NEW_JWT") --project=stratum-ai-prod

# Restart pods to pick up new secret
kubectl rollout restart deployment/stratum-api -n stratum
```

### 11.5 Full DR Drill in Alternate Region

```bash
# Simulate region failure
# 1. Failover Cloud SQL to us-east1
# 2. Update DNS to point to DR load balancer
# 3. Verify application works from DR region
```

### 11.6 Security Headers Review

```bash
# Verify headers:
curl -I https://stratumai.app | grep -E "strict-transport-security|content-security-policy|x-frame-options"

# Expected:
# strict-transport-security: max-age=31536000; includeSubDomains; preload
# x-frame-options: DENY
# content-security-policy: default-src 'self'; ...
```

---

## Phase 12: Launch

> **Goal:** Soft launch, monitoring, progressive enforcement rollout.

### 12.1 1-3 Pilot Tenants Onboarded

```bash
# Create pilot tenants with close monitoring
# - Daily standup with pilot users
# - Real-time Slack alerts for errors
# - Weekly performance review
```

### 12.2 All Tenants Start in Advisory Mode

```sql
UPDATE tenant_settings SET enforcement_mode = 'advisory' WHERE id IN (...);
```

### 12.3 Two-Week Monitoring Window

```bash
# Monitor daily:
# - Error rate < 0.1%
# - P95 latency < 500ms
# - Zero P0/P1 incidents
# - Trust gate accuracy > 95%
```

### 12.4 Weekly Review Cadence

```bash
# Schedule recurring meetings:
# - Monday: Error review + trust gate accuracy
# - Wednesday: Autopilot decision review
# - Friday: Performance + capacity review
```

### 12.5 Per-Tenant Enforcement Upgrade Plan

```markdown
# docs/launch/enforcement-rollout.md
## Rollout Schedule
- Week 3-4: Pilot tenants → Auto mode (if comfortable)
- Week 5-6: Early adopters → Auto mode
- Week 7-8: All tenants → Auto mode (with kill switch ready)
```

### 12.6 Post-Mortem Process

```markdown
# docs/runbooks/post-mortem.md
## Process
1. Page the on-call engineer within 5 minutes of P0
2. Create incident channel within 10 minutes
3. Mitigation within 30 minutes
4. Post-mortem document within 48 hours
5. Action items assigned within 72 hours
```

---

## Appendix: Complete Command Checklist

Copy this into a spreadsheet and tick off as you complete each item:

```
Phase | # | Item | Status | Date | Notes
1.1 | GCP Organization | ⬜ | | |
1.2 | Projects | ⬜ | | |
1.3 | Domain | ⬜ | | |
1.4 | DNS Zone | ⬜ | | |
... (all 80+ items)
```

---

*Last updated: 2026-04-26*
