# Deployment Guide — Dental DICOM Portal

This guide covers production deployment on a Linux application server with an
optional Docker Compose path as an alternative to systemd.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Server Setup](#server-setup)
4. [SSL Certificates](#ssl-certificates)
5. [Database Setup](#database-setup)
6. [Keycloak Setup](#keycloak-setup)
7. [Guacamole Setup](#guacamole-setup)
8. [Backend Deployment](#backend-deployment)
9. [Frontend Build & Deployment](#frontend-build--deployment)
10. [Nginx Configuration](#nginx-configuration)
11. [systemd Services](#systemd-services)
12. [DICOM Watcher Configuration](#dicom-watcher-configuration)
13. [Health Checks](#health-checks)
14. [Docker Compose (Alternative)](#docker-compose-alternative)
15. [Maintenance](#maintenance)
16. [Deployment Checklist](#deployment-checklist)

---

## Architecture Overview

```
Internet
  │
  ▼
Nginx (443/80)  ←  SSL termination, static SPA serving
  ├─ /api/*       → FastAPI / uvicorn   (127.0.0.1:8000)
  ├─ /guacamole/* → Guacamole / Tomcat  (127.0.0.1:8080)
  └─ /*           → React SPA           (/var/www/dental-dicom-portal)

FastAPI ─────────────────────────────────────────────────────────────
  ├─ async PostgreSQL (asyncpg)
  ├─ Keycloak OIDC JWT validation
  └─ WinRM → Windows RDS server (DTX Studio sessions)

DICOM Watcher (background process)
  └─ Watches /mnt/dicom/incoming, ingests files via FastAPI DB

Keycloak (OIDC/OAuth2 IdP)
PostgreSQL 15
Guacamole + guacd (RDP proxy)
```

---

## Prerequisites

### Windows Server (RDS host — separate machine)
- Windows Server 2019 or later
- Remote Desktop Services role installed and configured
- DTX Studio installed at the configured path
- Dedicated non-admin RDS user accounts provisioned
- WinRM enabled: `Enable-PSRemoting -Force` (run as Administrator)

### Linux Application Server
- Ubuntu 22.04 LTS (or equivalent RHEL 9 / Debian 12)
- 4 vCPU, 8 GB RAM minimum
- Python 3.11+
- Node.js 20+ (build only — not needed on the server at runtime)
- PostgreSQL 15
- Nginx 1.24+
- Java 17+ (for Keycloak and Guacamole/Tomcat)
- Sufficient disk for DICOM files (SAN/NFS mount recommended)

---

## Server Setup

```bash
# Create the application user
sudo useradd -r -m -s /bin/false dental-app

# Create application directories
sudo mkdir -p /opt/dental-dicom-portal
sudo chown dental-app:dental-app /opt/dental-dicom-portal

# Create DICOM directories
sudo mkdir -p /mnt/dicom/{incoming,processed,error}
sudo chown dental-app:dental-app /mnt/dicom/{incoming,processed,error}

# Install system packages
sudo apt update && sudo apt install -y \
    nginx python3.11 python3.11-venv \
    postgresql postgresql-contrib \
    openjdk-17-jre-headless \
    tomcat10 \
    certbot python3-certbot-nginx
```

---

## SSL Certificates

### Let's Encrypt (recommended for internet-facing deployments)
```bash
sudo certbot --nginx -d dental-portal.example.com
# Certbot writes cert paths to nginx config automatically.
# Auto-renewal: certbot installs a systemd timer or cron job.
```

### Self-signed / Enterprise CA (internal deployments)
```bash
# Generate a self-signed cert (replace with real CA-signed cert for production)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/dental-portal.key \
    -out    /etc/ssl/certs/dental-portal.crt \
    -subj "/CN=dental-portal.example.com"
```

---

## Database Setup

```bash
# Connect as postgres superuser
sudo -u postgres psql <<'SQL'
CREATE USER dental_user WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE dental_portal OWNER dental_user;
CREATE DATABASE guacamole_db  OWNER dental_user;
CREATE DATABASE keycloak       OWNER dental_user;
SQL

# Run Alembic migrations
cd /opt/dental-dicom-portal/backend
source venv/bin/activate
alembic upgrade head
```

---

## Keycloak Setup

### Installation
```bash
# Download Keycloak 23.0
wget https://github.com/keycloak/keycloak/releases/download/23.0.0/keycloak-23.0.0.tar.gz
sudo tar -xzf keycloak-23.0.0.tar.gz -C /opt/
sudo ln -s /opt/keycloak-23.0.0 /opt/keycloak
sudo chown -R keycloak:keycloak /opt/keycloak
```

### Realm Import
1. Log in to the Keycloak Admin Console: `https://auth.example.com/admin`
2. Create a new realm named `dental-portal`
3. Import `scripts/keycloak-realm-export.json` (if provided) via
   **Realm Settings → Action → Partial Import**
4. Alternatively, configure manually:
   - Create client `dental-backend` (confidential, Service Accounts enabled)
   - Create client `dental-frontend` (public, Standard Flow enabled)
   - Create roles: `admin`, `doctor`
   - Add realm-level role mapper to include `roles` in the access token

### Initial Admin User
```
Keycloak Admin Console → dental-portal realm → Users → Add user
Username: admin@example.com
Assign role: admin
Set temporary password → user changes on first login
```

---

## Guacamole Setup

### Install guacd
```bash
sudo apt install -y libcairo2-dev libjpeg-turbo8-dev libpng-dev libavcodec-dev \
    libavformat-dev libavutil-dev libswscale-dev freerdp2-dev libpango1.0-dev \
    libssh2-1-dev libtelnet-dev libvncserver-dev libwebsockets-dev libpulse-dev \
    libssl-dev libvorbis-dev libwebp-dev

# Build guacd from source or use Docker image (see Docker Compose section)
```

### Guacamole Web App (Tomcat)
1. Download `guacamole-1.5.4.war` from the Apache Guacamole releases page
2. Deploy to Tomcat: `sudo cp guacamole-1.5.4.war /var/lib/tomcat10/webapps/guacamole.war`
3. Configure `/etc/guacamole/guacamole.properties`:
   ```properties
   guacd-hostname: localhost
   guacd-port:     4822
   postgresql-hostname: localhost
   postgresql-port:     5432
   postgresql-database: guacamole_db
   postgresql-username: dental_user
   postgresql-password: CHANGE_ME
   ```
4. Initialize the Guacamole DB schema using the SQL scripts bundled with the extension

---

## Backend Deployment

```bash
# Clone or copy code
cd /opt/dental-dicom-portal
git clone https://github.com/Temirlaaan/dental-dicom-portal.git .

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Copy and configure the environment file
cp .env.production /opt/dental-dicom-portal/.env.production
# Edit .env.production with real values (see .env.production template)

# Run migrations
cd backend
alembic upgrade head
```

---

## Frontend Build & Deployment

```bash
# Build on a machine with Node.js (can be CI/CD or a dev workstation)
cd frontend
npm ci
VITE_GUACAMOLE_URL=/guacamole npm run build

# Copy dist to the server
rsync -av dist/ user@server:/var/www/dental-dicom-portal/

# Or on the server directly if Node is installed:
sudo mkdir -p /var/www/dental-dicom-portal
sudo cp -r frontend/dist/* /var/www/dental-dicom-portal/
sudo chown -R www-data:www-data /var/www/dental-dicom-portal
```

---

## Nginx Configuration

```bash
# Install the production config
sudo cp nginx/nginx.prod.conf /etc/nginx/sites-available/dental-dicom-portal

# Edit server_name and ssl_certificate paths
sudo nano /etc/nginx/sites-available/dental-dicom-portal

# Enable the site
sudo ln -s /etc/nginx/sites-available/dental-dicom-portal \
           /etc/nginx/sites-enabled/dental-dicom-portal

# Remove the default site (if present)
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

---

## systemd Services

Install all service units and enable them:

```bash
# Copy unit files
sudo cp backend/systemd/dental-api.service              /etc/systemd/system/
sudo cp backend/systemd/dental-dicom-watcher.service    /etc/systemd/system/
sudo cp backend/systemd/dental-session-cleanup.service  /etc/systemd/system/
sudo cp backend/systemd/dental-session-cleanup.timer    /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable --now dental-api.service
sudo systemctl enable --now dental-dicom-watcher.service
sudo systemctl enable --now dental-session-cleanup.timer

# Check status
sudo systemctl status dental-api
sudo systemctl status dental-dicom-watcher
sudo systemctl list-timers dental-session-cleanup

# View logs
sudo journalctl -u dental-api -f
sudo journalctl -u dental-dicom-watcher -f
```

---

## DICOM Watcher Configuration

1. Set `DICOM_WATCH_DIR` in `.env.production` to the incoming DICOM folder
   (typically an NFS or CIFS mount from the dental imaging workstation)
2. Ensure the `dental-app` user has read access to the watch directory and
   write access to `DICOM_PROCESSED_DIR` and `DICOM_ERROR_DIR`
3. Configure the imaging workstation to export DICOM files to the watch directory

```bash
# Example NFS mount in /etc/fstab:
# imaging-server:/exports/dicom  /mnt/dicom/incoming  nfs  defaults,_netdev  0 0

# Verify permissions
sudo -u dental-app ls /mnt/dicom/incoming
```

---

## Health Checks

```bash
# API health through Nginx
curl -k https://dental-portal.example.com/api/health

# Direct API health
curl http://127.0.0.1:8000/api/health

# Guacamole reachable
curl -I http://127.0.0.1:8080/guacamole/

# WebSocket check (requires wscat: npm i -g wscat)
wscat -c wss://dental-portal.example.com/guacamole/websocket-tunnel
```

Expected response from `/api/health`:
```json
{"status": "ok", "database": "ok", "version": "0.1.0"}
```

---

## Docker Compose (Alternative)

Use this instead of the systemd approach if you prefer container-based deployment.

```bash
# Copy and edit the environment file
cp .env.production .env.production.local
# Set POSTGRES_PASSWORD and KEYCLOAK_ADMIN_PASSWORD in the file

# Build frontend first
cd frontend && npm ci && npm run build && cd ..

# Start all services
docker compose -f docker-compose.prod.yml --env-file .env.production.local up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx

# Run migrations inside the backend container
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### SSL with Docker Compose
Mount real certificate files into the nginx service:
```yaml
volumes:
  - /etc/letsencrypt/live/dental-portal.example.com/fullchain.pem:/etc/ssl/certs/dental-portal.crt:ro
  - /etc/letsencrypt/live/dental-portal.example.com/privkey.pem:/etc/ssl/private/dental-portal.key:ro
```

---

## Maintenance

### Log Rotation
Nginx and journald handle rotation automatically.
To adjust journald retention: `/etc/systemd/journald.conf` → `MaxRetentionSec=90day`

### Database Backups
```bash
# Daily backup via cron
pg_dump -U dental_user dental_portal | gzip > /backups/dental_portal_$(date +%F).sql.gz
```

### SSL Certificate Renewal
Let's Encrypt certificates renew automatically via `certbot.timer`.
To test renewal: `sudo certbot renew --dry-run`

### Audit Log Retention
The audit log table grows over time. Archive or purge old rows periodically:
```sql
DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '1 year';
```

### Applying Updates
```bash
cd /opt/dental-dicom-portal
git pull
source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && alembic upgrade head
sudo systemctl restart dental-api dental-dicom-watcher

# Rebuild and redeploy frontend if changed
cd ../frontend && npm ci && npm run build
sudo rsync -av dist/ /var/www/dental-dicom-portal/
```

---

## Deployment Checklist

### Pre-deployment
- [ ] Windows Server RDS role configured and DTX Studio installed
- [ ] Non-admin RDS user accounts created
- [ ] WinRM enabled on Windows Server
- [ ] Linux server provisioned and hardened
- [ ] SSL certificate obtained and installed
- [ ] DNS record pointing to the server

### Database
- [ ] PostgreSQL installed and running
- [ ] `dental_user`, `dental_portal`, `guacamole_db`, and `keycloak` databases created
- [ ] Alembic migrations applied (`alembic upgrade head`)

### Keycloak
- [ ] Keycloak installed and reachable
- [ ] `dental-portal` realm created
- [ ] `dental-backend` (confidential) and `dental-frontend` (public) clients configured
- [ ] `admin` and `doctor` roles created
- [ ] Token claim mapper for `roles` in place
- [ ] Initial admin user created and tested

### Guacamole
- [ ] guacd running
- [ ] Guacamole web app deployed and reachable at `http://127.0.0.1:8080/guacamole/`
- [ ] Guacamole database schema initialised
- [ ] Test RDP connection to the Windows RDS server works

### Backend
- [ ] Python venv created and dependencies installed
- [ ] `.env.production` populated with real values
- [ ] `dental-api.service` enabled and running
- [ ] `/api/health` returns `{"status": "ok"}`

### DICOM Watcher
- [ ] DICOM watch directory mounted and accessible
- [ ] `dental-dicom-watcher.service` enabled and running
- [ ] `dental-session-cleanup.timer` enabled and listed in `systemctl list-timers`

### Frontend & Nginx
- [ ] React build deployed to `/var/www/dental-dicom-portal`
- [ ] `nginx.prod.conf` installed and symlinked to `sites-enabled`
- [ ] `nginx -t` passes without errors
- [ ] `https://dental-portal.example.com` loads the login page
- [ ] HTTP → HTTPS redirect works
- [ ] Security headers present (`curl -I https://...` shows `Strict-Transport-Security`)

### End-to-end
- [ ] Admin user can log in and access the admin dashboard
- [ ] Doctor user can log in and see the patient list
- [ ] Patient assignment works (admin assigns a patient to a doctor)
- [ ] "Open in DTX Studio" button launches a Guacamole RDP session
- [ ] Session timer, idle warning, and hard timeout warnings work
- [ ] DICOM file dropped into watch directory appears in a patient's studies
- [ ] Audit log records admin and doctor actions
- [ ] All systemd services restart automatically after `sudo kill -9 <pid>`
