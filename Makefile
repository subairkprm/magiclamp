# =============================================================
#  MAGICLAMP — Admin Commands
#  Usage: make <command>
# =============================================================

.PHONY: help start stop restart logs status build update \
        pull-model list-models shell-brain shell-agent \
        backup restore ssl coolify-logs coolify-restart \
        brain-logs agent-logs n8n-logs ollama-logs

# Default target
help:
	@echo ""
	@echo "  🪄  MagicLamp — Admin Commands"
	@echo ""
	@echo "  Stack Control:"
	@echo "    make start          Start entire stack"
	@echo "    make stop           Stop entire stack"
	@echo "    make restart        Restart all services"
	@echo "    make build          Rebuild brain + agent"
	@echo "    make update         Pull latest git + rebuild"
	@echo ""
	@echo "  Monitoring:"
	@echo "    make logs           All service logs"
	@echo "    make status         Container health + brain API health"
	@echo "    make brain-logs     Brain service logs only"
	@echo "    make agent-logs     Agent service logs only"
	@echo "    make n8n-logs       N8N logs"
	@echo "    make ollama-logs    Ollama logs"
	@echo ""
	@echo "  AI Models:"
	@echo "    make pull-model MODEL=qwen2.5:7b"
	@echo "    make list-models"
	@echo ""
	@echo "  Maintenance:"
	@echo "    make backup         Backup all data + .env"
	@echo "    make restore FILE=backups/xxx.tar.gz"
	@echo "    make ssl DOMAIN=yourdomain.com"
	@echo ""
	@echo "  Coolify (Web Panel):"
	@echo "    make coolify-logs   Coolify service logs"
	@echo "    make coolify-restart Restart Coolify"
	@echo "    make panel          Open Coolify URL"
	@echo ""

# ── Stack Control ─────────────────────────────────────────────
start:
	@echo "Starting MagicLamp..."
	docker-compose up -d
	@echo "Done. Run 'make status' to check health."

stop:
	@echo "Stopping MagicLamp..."
	docker-compose down

restart:
	docker-compose restart

build:
	docker-compose build --parallel brain agent

update:
	@echo "Updating MagicLamp..."
	git pull
	docker-compose build --parallel brain agent
	docker-compose up -d brain agent
	@echo "Brain and Agent updated."

# ── Monitoring ────────────────────────────────────────────────
logs:
	docker-compose logs -f --tail=100

status:
	@echo ""
	@echo "=== Container Status ==="
	@docker-compose ps
	@echo ""
	@echo "=== Brain API Health ==="
	@curl -s http://localhost:9000/health 2>/dev/null | python3 -m json.tool || echo "Brain unreachable"
	@echo ""
	@echo "=== Ollama Models ==="
	@docker exec ml_ollama ollama list 2>/dev/null || echo "Ollama unreachable"
	@echo ""
	@echo "=== Resource Usage ==="
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
	  ml_ollama ml_brain ml_agent ml_n8n ml_nginx 2>/dev/null || true

brain-logs:
	docker-compose logs -f brain

agent-logs:
	docker-compose logs -f agent

n8n-logs:
	docker-compose logs -f n8n

ollama-logs:
	docker-compose logs -f ollama

# ── AI Models ─────────────────────────────────────────────────
pull-model:
	@[ "$(MODEL)" ] || (echo "Usage: make pull-model MODEL=qwen2.5:7b" && exit 1)
	docker exec ml_ollama ollama pull $(MODEL)

list-models:
	@docker exec ml_ollama ollama list

delete-model:
	@[ "$(MODEL)" ] || (echo "Usage: make delete-model MODEL=mistral:7b" && exit 1)
	docker exec ml_ollama ollama rm $(MODEL)

# ── Shell Access ──────────────────────────────────────────────
shell-brain:
	docker exec -it ml_brain bash

shell-agent:
	docker exec -it ml_agent bash

shell-ollama:
	docker exec -it ml_ollama bash

# ── Maintenance ───────────────────────────────────────────────
backup:
	@mkdir -p backups
	@FILENAME=backups/magiclamp-$(shell date +%Y%m%d-%H%M).tar.gz; \
	tar -czf $$FILENAME data/ .env 2>/dev/null; \
	echo "Backup saved: $$FILENAME ($(shell du -sh $$FILENAME 2>/dev/null | cut -f1))"

restore:
	@[ "$(FILE)" ] || (echo "Usage: make restore FILE=backups/xxx.tar.gz" && exit 1)
	@echo "Restoring from $(FILE)..."
	tar -xzf $(FILE)
	@echo "Restore complete. Run 'make start'."

# ── SSL Setup ─────────────────────────────────────────────────
ssl:
	@[ "$(DOMAIN)" ] || (echo "Usage: make ssl DOMAIN=yourdomain.com EMAIL=your@email.com" && exit 1)
	@EMAIL=$(or $(EMAIL),admin@$(DOMAIN))
	@echo "Getting SSL certificate for $(DOMAIN)..."
	docker run --rm \
	  -v $(PWD)/data/certbot/conf:/etc/letsencrypt \
	  -v $(PWD)/data/certbot/www:/var/www/certbot \
	  certbot/certbot certonly \
	  --webroot -w /var/www/certbot \
	  -d $(DOMAIN) --email $(EMAIL) \
	  --agree-tos --no-eff-email --non-interactive
	@echo "SSL certificate obtained. Update nginx config to enable HTTPS."

# ── Coolify ───────────────────────────────────────────────────
coolify-logs:
	docker logs coolify -f --tail=100 2>/dev/null || \
	  journalctl -u coolify -f 2>/dev/null || \
	  echo "Coolify logs not found — check: docker ps | grep coolify"

coolify-restart:
	docker restart coolify 2>/dev/null || \
	  systemctl restart coolify 2>/dev/null || \
	  echo "Restart Coolify at: http://$(shell curl -s ifconfig.me 2>/dev/null):8000"

panel:
	@VPS_IP=$$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $$1}'); \
	echo "Coolify Panel: http://$$VPS_IP:8000"

# ── Database ──────────────────────────────────────────────────
brain-stats:
	@curl -s -H "X-Brain-Key: $$(grep BRAIN_SECRET .env | cut -d= -f2)" \
	  http://localhost:9000/api/v1/brain/memory/stats | python3 -m json.tool

trigger-briefing:
	@curl -s -X POST -H "X-Brain-Key: $$(grep BRAIN_SECRET .env | cut -d= -f2)" \
	  http://localhost:9000/api/v1/brain/scheduler/run/daily_briefing | python3 -m json.tool
