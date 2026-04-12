#!/bin/bash
# =============================================================
#  MAGICLAMP — Complete VPS Setup + Coolify Integration
#  One command deploys the entire platform including web panel
#  Usage: bash start.sh
#  Run as root on Ubuntu 22.04
# =============================================================

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info()  { echo -e "${CYAN}[→]${NC} $1"; }
title() { echo -e "\n${BOLD}${CYAN}$1${NC}\n"; }

clear
echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║         🪄  MagicLamp Enterprise             ║"
echo "  ║      Full VPS Setup — One Command            ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: System Check ─────────────────────────────────────
title "Step 1/9 — System Check"
[[ $EUID -ne 0 ]] && err "Must run as root: sudo bash start.sh"
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
DISK_GB=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
CPU_COUNT=$(nproc)
VPS_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

echo "  RAM:  ${RAM_GB}GB $([ $RAM_GB -ge 12 ] && echo '✅' || echo '⚠️  (12GB recommended)')"
echo "  Disk: ${DISK_GB}GB $([ $DISK_GB -ge 30 ] && echo '✅' || echo '⚠️  (30GB+ recommended)')"
echo "  CPUs: ${CPU_COUNT}"
echo "  IP:   ${VPS_IP}"
log "System check complete"

# ── Step 2: Install Dependencies ─────────────────────────────
title "Step 2/9 — Installing Dependencies"
apt-get update -qq
apt-get install -y -qq curl git ufw openssl nano htop

if ! command -v docker &>/dev/null; then
  info "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
  log "Docker installed"
else
  log "Docker $(docker --version | cut -d' ' -f3 | tr -d ',') already installed"
fi

if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
  info "Installing Docker Compose..."
  COMPOSE_VER=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d'"' -f4)
  curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VER}/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  log "Docker Compose installed"
else
  log "Docker Compose already installed"
fi

if docker compose version &>/dev/null; then
  DC="docker compose"
elif command -v docker-compose &>/dev/null; then
  DC="docker-compose"
else
  err "Docker Compose not available"
fi

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

# ── Step 3: Firewall ─────────────────────────────────────────
title "Step 3/9 — Firewall Configuration"
ufw allow 22/tcp    comment "SSH"
ufw allow 80/tcp    comment "HTTP"
ufw allow 443/tcp   comment "HTTPS"
ufw allow 8000/tcp  comment "Coolify Panel"
ufw deny  11434/tcp comment "Ollama — internal only"
ufw deny  9000/tcp  comment "Brain — via Nginx only"
ufw deny  5678/tcp  comment "N8N — via Nginx only"
ufw --force enable
log "Firewall: 22, 80, 443, 8000 open | 11434, 9000, 5678 blocked"

# ── Step 4: Environment Setup ────────────────────────────────
title "Step 4/9 — Environment Configuration"
if [ ! -f ".env" ]; then
  cp .env.example .env
  warn "──────────────────────────────────────────"
  warn "  .env created — you MUST fill these in:"
  warn "  SUPABASE_URL"
  warn "  SUPABASE_SERVICE_KEY"
  warn "  TELEGRAM_BOT_TOKEN (optional)"
  warn "  N8N_PASSWORD"
  warn "──────────────────────────────────────────"
  echo ""
  read -p "  Press ENTER after editing .env..." _
fi

# Auto-generate missing secrets
auto_secret() {
  KEY=$1; VAL=$(grep "^${KEY}=" .env | cut -d= -f2-)
  if [ -z "$VAL" ] || echo "$VAL" | grep -q "generate_with\|your_"; then
    NEW=$(openssl rand -hex 32)
    if grep -q "^${KEY}=" .env; then
      sed -i "s|^${KEY}=.*|${KEY}=${NEW}|" .env
    else
      echo "${KEY}=${NEW}" >> .env
    fi
    log "Auto-generated: ${KEY}"
  fi
}
auto_secret "JWT_SECRET"
auto_secret "BRAIN_SECRET"
auto_secret "N8N_ENCRYPTION_KEY"

# Write VPS IP to .env
sed -i "s|^SERVER_HOST=.*|SERVER_HOST=${VPS_IP}|" .env 2>/dev/null || echo "SERVER_HOST=${VPS_IP}" >> .env
log "Environment configured"

# ── Step 5: Install Coolify ──────────────────────────────────
title "Step 5/9 — Installing Coolify (Web Panel)"
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "coolify"; then
  info "Installing Coolify — this takes 2-3 minutes..."
  curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
  sleep 5
  log "Coolify installed → http://${VPS_IP}:8000"
else
  log "Coolify already running"
fi

# ── Step 6: Create Data Directories ──────────────────────────
title "Step 6/9 — Data Directories"
mkdir -p data/{brain/chroma,brain/exports,ollama,n8n,ssl,certbot/www,certbot/conf}
chmod -R 755 data/
log "Data directories created at ./data/"

# ── Step 7: Build and Start MagicLamp ────────────────────────
title "Step 7/9 — Building MagicLamp"
info "Pulling base images..."
$DC $COMPOSE_FILES pull ollama n8n 2>&1 | grep -E "Pulling|pulled|up to date" || true

info "Building Brain and Agent (first time: ~5 min)..."
$DC $COMPOSE_FILES build --parallel brain agent

info "Starting all services..."
$DC $COMPOSE_FILES up -d

# ── Step 8: Wait for Health ───────────────────────────────────
title "Step 8/9 — Waiting for Services"
info "Waiting for services to pass health checks..."
TRIES=0; MAX=40
while [ $TRIES -lt $MAX ]; do
  HEALTHY=$($DC $COMPOSE_FILES ps 2>/dev/null | grep -c "healthy" || echo 0)
  TOTAL=$($DC $COMPOSE_FILES ps 2>/dev/null | grep -c "Up" || echo 0)
  echo -ne "\r  Containers healthy: ${HEALTHY}/${TOTAL} (${TRIES}/${MAX} checks)"
  [ $HEALTHY -ge 2 ] && break
  sleep 5; TRIES=$((TRIES+1))
done
echo ""

# ── Step 9: Final Setup ───────────────────────────────────────
title "Step 9/9 — Final Configuration"

# Pull AI model in background
OLLAMA_MODEL=$(grep "^OLLAMA_MODEL=" .env | cut -d= -f2-)
OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:7b}
info "Pulling AI model: ${OLLAMA_MODEL} (background, ~5-15 min)..."
docker exec ml_ollama ollama pull ${OLLAMA_MODEL} &
log "Model pull started in background (check: docker exec ml_ollama ollama list)"

# Set Telegram webhook
TG_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" .env | cut -d= -f2-)
if [ ! -z "$TG_TOKEN" ] && ! echo "$TG_TOKEN" | grep -q "your_"; then
  curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/setWebhook" \
    -d "url=http://${VPS_IP}/telegram/webhook" | grep -q "true" && \
    log "Telegram webhook registered" || warn "Telegram webhook failed"
fi

# Register Coolify SSH key
if command -v coolify &>/dev/null 2>&1; then
  info "Coolify SSH key info:"
  cat ~/.ssh/coolify.pub 2>/dev/null || true
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     🪄  MagicLamp is LIVE!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Platform URLs:${NC}"
echo -e "  ${CYAN}MagicLamp UI:${NC}       http://${VPS_IP}/"
echo -e "  ${CYAN}Coolify Panel:${NC}      http://${VPS_IP}:8000"
echo -e "  ${CYAN}Brain API Docs:${NC}     http://${VPS_IP}/docs"
echo -e "  ${CYAN}N8N Workflows:${NC}      http://${VPS_IP}/n8n/"
echo -e "  ${CYAN}Agent Health:${NC}       http://${VPS_IP}/agent/health"
echo ""
echo -e "  ${BOLD}Default Credentials:${NC}"
echo -e "  ${YELLOW}MagicLamp login:${NC}    admin / admin123  ← change immediately"
echo -e "  ${YELLOW}N8N login:${NC}          admin / (your N8N_PASSWORD from .env)"
echo -e "  ${YELLOW}Coolify:${NC}            Create account at http://${VPS_IP}:8000"
echo ""
echo -e "  ${BOLD}Next Steps:${NC}"
echo -e "  1. Open Coolify: http://${VPS_IP}:8000"
echo -e "  2. Connect GitHub repo: github.com/$(git remote get-url origin 2>/dev/null | cut -d/ -f4-5 | sed 's/.git//' || echo 'your/repo')"
echo -e "  3. Add your .env variables in Coolify"
echo -e "  4. Enable auto-deploy on git push"
echo ""
echo -e "  ${BOLD}Useful Commands:${NC}"
echo -e "  make logs         → view all logs"
echo -e "  make status       → container health"
echo -e "  make pull-model MODEL=mistral:7b"
echo -e "  make backup       → backup all data"
echo ""
