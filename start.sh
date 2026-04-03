#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  MAGICLAMP — One-Command Production Deploy
#  Run on a fresh Ubuntu 22.04 VPS as root
#  Usage: bash start.sh
# ═══════════════════════════════════════════════════════════

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${CYAN}[→]${NC} $1"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         MagicLamp Enterprise             ║${NC}"
echo -e "${CYAN}║      One-Command VPS Deployment          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 1. System check ─────────────────────────
info "Checking system..."
[[ $EUID -ne 0 ]] && err "Run as root: sudo bash start.sh"
OS=$(cat /etc/os-release | grep "^ID=" | cut -d= -f2 | tr -d '"')
[[ "$OS" != "ubuntu" ]] && warn "Tested on Ubuntu. Proceeding on $OS..."
RAM=$(free -g | awk '/^Mem:/{print $2}')
[[ $RAM -lt 8 ]] && warn "RAM: ${RAM}GB — recommended 12GB+"
log "System OK — ${RAM}GB RAM, Ubuntu $OS"

# ── 2. Install Docker ────────────────────────
if ! command -v docker &>/dev/null; then
  info "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker && systemctl start docker
  log "Docker installed"
else
  log "Docker already installed"
fi

if ! command -v docker-compose &>/dev/null; then
  info "Installing Docker Compose..."
  curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  log "Docker Compose installed"
fi

# ── 3. Firewall ──────────────────────────────
info "Configuring firewall..."
apt-get install -y ufw -qq
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw --force enable
log "Firewall configured"

# ── 4. Setup .env ────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  warn "═══════════════════════════════════════════"
  warn "  .env file created — FILL IT IN NOW"
  warn "  Required: SUPABASE_URL, SUPABASE_SERVICE_KEY"
  warn "            JWT_SECRET, BRAIN_SECRET"
  warn "  Run: nano .env"
  warn "═══════════════════════════════════════════"
  echo ""
  read -p "Press ENTER after filling .env to continue..."
fi

# Auto-generate secrets if empty
JWT_VAL=$(grep "^JWT_SECRET=" .env | cut -d= -f2)
if [ -z "$JWT_VAL" ] || [ "$JWT_VAL" = "generate_with_openssl_rand_hex_32_here" ]; then
  JWT=$(openssl rand -hex 32)
  sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$JWT/" .env
  log "JWT_SECRET auto-generated"
fi

BRAIN_VAL=$(grep "^BRAIN_SECRET=" .env | cut -d= -f2)
if [ -z "$BRAIN_VAL" ] || [ "$BRAIN_VAL" = "generate_with_openssl_rand_hex_32_here" ]; then
  BRAIN=$(openssl rand -hex 32)
  sed -i "s/^BRAIN_SECRET=.*/BRAIN_SECRET=$BRAIN/" .env
  log "BRAIN_SECRET auto-generated"
fi

N8N_VAL=$(grep "^N8N_ENCRYPTION_KEY=" .env | cut -d= -f2)
if [ -z "$N8N_VAL" ] || [ "$N8N_VAL" = "generate_with_openssl_rand_hex_32_here" ]; then
  N8N_ENC=$(openssl rand -hex 32)
  sed -i "s/^N8N_ENCRYPTION_KEY=.*/N8N_ENCRYPTION_KEY=$N8N_ENC/" .env
  log "N8N_ENCRYPTION_KEY auto-generated"
fi

# ── 5. Create directories ────────────────────
info "Creating data directories..."
mkdir -p data/{brain/chroma,brain/exports,ollama,n8n,ssl}
chmod 755 data
log "Directories created"

# ── 6. Build and start ───────────────────────
info "Building MagicLamp (first build takes 5-10 min)..."
docker-compose pull ollama n8n
docker-compose build brain agent

info "Starting all services..."
docker-compose up -d

# ── 7. Wait for health ───────────────────────
info "Waiting for services to be healthy..."
sleep 15

TRIES=0
until docker-compose ps | grep "ml_brain" | grep -q "healthy" || [ $TRIES -gt 30 ]; do
  echo -n "."
  sleep 5
  TRIES=$((TRIES+1))
done
echo ""

# ── 8. Pull AI model ─────────────────────────
OLLAMA_MODEL=$(grep "^OLLAMA_MODEL=" .env | cut -d= -f2)
OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:7b}
info "Pulling AI model: $OLLAMA_MODEL (may take 5-15 min)..."
docker exec ml_ollama ollama pull $OLLAMA_MODEL &
log "Model pull started in background"

# ── 9. Set Telegram webhook ──────────────────
TG_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" .env | cut -d= -f2)
VPS_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
if [ ! -z "$TG_TOKEN" ] && [ "$TG_TOKEN" != "your_telegram_bot_token" ]; then
  curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/setWebhook" \
    -d "url=http://${VPS_IP}/telegram/webhook" > /dev/null
  log "Telegram webhook set → http://${VPS_IP}/telegram/webhook"
fi

# ── 10. Final output ─────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     MagicLamp is LIVE! 🪄               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Platform UI:${NC}    http://${VPS_IP}/"
echo -e "  ${CYAN}Brain API:${NC}      http://${VPS_IP}/api/v1/"
echo -e "  ${CYAN}API Docs:${NC}       http://${VPS_IP}/docs"
echo -e "  ${CYAN}N8N Workflows:${NC} http://${VPS_IP}/n8n/"
echo ""
echo -e "  ${YELLOW}Default login:${NC} admin / admin123"
echo -e "  ${YELLOW}Change password immediately in Settings${NC}"
echo ""
echo -e "  ${CYAN}View logs:${NC}      docker-compose logs -f"
echo -e "  ${CYAN}Stop:${NC}           docker-compose down"
echo -e "  ${CYAN}Update:${NC}         git pull && docker-compose build && docker-compose up -d"
echo ""
