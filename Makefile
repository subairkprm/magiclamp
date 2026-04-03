# MagicLamp — Admin Commands
# Usage: make <command>

.PHONY: start stop restart logs status build pull-model backup shell-brain shell-agent

start:
	docker-compose up -d
	@echo "MagicLamp started. Run 'make status' to check health."

stop:
	docker-compose down

restart:
	docker-compose restart

build:
	docker-compose build brain agent

logs:
	docker-compose logs -f --tail=100

logs-brain:
	docker-compose logs -f brain

logs-agent:
	docker-compose logs -f agent

status:
	@echo "=== Container Status ==="
	@docker-compose ps
	@echo ""
	@echo "=== Health ==="
	@curl -s http://localhost:9000/health | python3 -m json.tool 2>/dev/null || echo "Brain unreachable"

pull-model:
	@echo "Pulling $(MODEL)..."
	docker exec ml_ollama ollama pull $(MODEL)

list-models:
	docker exec ml_ollama ollama list

shell-brain:
	docker exec -it ml_brain bash

shell-agent:
	docker exec -it ml_agent bash

backup:
	@echo "Backing up data..."
	@mkdir -p backups
	@tar -czf backups/magiclamp-$(shell date +%Y%m%d-%H%M).tar.gz data/ .env
	@echo "Backup saved to backups/"

restore:
	@echo "Restoring from $(FILE)..."
	tar -xzf $(FILE)

update:
	git pull
	docker-compose build brain agent
	docker-compose up -d brain agent
	@echo "Brain and Agent updated."

db-tunnel:
	@echo "Connect to DB at localhost:54322"
	docker run --rm -it --network magiclamp_magiclamp alpine/socat TCP-LISTEN:54322,fork TCP:db.qdjzzvlhawzttgharjfw.supabase.co:5432
