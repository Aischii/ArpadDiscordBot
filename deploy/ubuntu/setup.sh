#!/usr/bin/env bash
set -euo pipefail

# Ubuntu server setup for ArpadDiscordBot
# This script installs dependencies, configures systemd and nginx,
# and starts the bot as a managed service.
# Usage:
#   sudo bash deploy/ubuntu/setup.sh \
#     --repo "https://github.com/Aischii/ArpadDiscordBot.git" \
#     --branch "main" \
#     --domain "arpadbot.example.com" \
#     --bot-token "YOUR_DISCORD_BOT_TOKEN" \
#     [--email "you@example.com"]  # for Let's Encrypt (optional)

REPO_URL=""
BRANCH="main"
DOMAIN=""
BOT_TOKEN=""
EMAIL=""
PORT="8000"
APP_DIR="/opt/arpadbot"
ENV_FILE="/etc/arpadbot.env"
SERVICE_FILE="/etc/systemd/system/arpadbot.service"
NGINX_SITE="/etc/nginx/sites-available/arpadbot"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_URL="$2"; shift 2;;
    --branch) BRANCH="$2"; shift 2;;
    --domain) DOMAIN="$2"; shift 2;;
    --bot-token) BOT_TOKEN="$2"; shift 2;;
    --email) EMAIL="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

if [[ -z "$REPO_URL" || -z "$BOT_TOKEN" ]]; then
  echo "REPO_URL and BOT_TOKEN are required"; exit 1
fi

# Install deps
apt-get update
apt-get install -y git python3-venv python3-pip nginx

# Optional: certbot if email/domain provided
if [[ -n "$EMAIL" && -n "$DOMAIN" ]]; then
  apt-get install -y certbot python3-certbot-nginx
fi

# Create app user
if ! id -u arpadbot >/dev/null 2>&1; then
  adduser --system --group --home "$APP_DIR" arpadbot
fi

# Clone or update repo
if [[ ! -d "$APP_DIR" ]]; then
  mkdir -p "$APP_DIR"
  chown -R arpadbot:arpadbot "$APP_DIR"
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  sudo -u arpadbot git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR"
  sudo -u arpadbot git fetch origin "$BRANCH"
  sudo -u arpadbot git reset --hard "origin/$BRANCH"
fi

# Python venv and deps
cd "$APP_DIR"
sudo -u arpadbot python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Environment file
cat > "$ENV_FILE" <<EOF
BOT_TOKEN=$BOT_TOKEN
PORT=$PORT
EOF
chmod 640 "$ENV_FILE"
chown root:arpadbot "$ENV_FILE"

# Systemd service
cat > "$SERVICE_FILE" <<'EOF'
[Unit]
Description=Arpad Discord Bot
After=network.target

[Service]
Type=simple
User=arpadbot
Group=arpadbot
WorkingDirectory=/opt/arpadbot
EnvironmentFile=/etc/arpadbot.env
ExecStart=/opt/arpadbot/.venv/bin/python /opt/arpadbot/main.py
Restart=always
RestartSec=5
# Hardening
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Nginx site
cat > "$NGINX_SITE" <<EOF
server {
  listen 80;
  server_name ${DOMAIN:-_};

  location / {
    proxy_pass http://127.0.0.1:${PORT};
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_read_timeout 300;
    proxy_connect_timeout 300;
  }
}
EOF
ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/arpadbot
nginx -t && systemctl reload nginx

# Enable SSL if requested
if [[ -n "$EMAIL" && -n "$DOMAIN" ]]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" || true
fi

# Start service
systemctl daemon-reload
systemctl enable arpadbot
systemctl restart arpadbot

echo "Deployment complete. Check service: systemctl status arpadbot"
echo "HTTP proxy on port 80 to local :$PORT (domain: ${DOMAIN:-none})."