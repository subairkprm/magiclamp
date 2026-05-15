# 🪄 MagicLamp

**AI-Powered CRM Brain for UAE Banking**

MagicLamp is an enterprise-grade AI brain system designed specifically for UAE banking CRM operations. It provides autonomous memory management, intelligent reasoning, pattern analysis, and decision-making capabilities powered by local LLM infrastructure.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)](https://fastapi.tiangolo.com/)

---

## 📋 Overview

MagicLamp combines cutting-edge AI technology with robust enterprise architecture to deliver:

- **🧠 Memory Management**: Store, recall, and consolidate facts with confidence scoring
- **💡 Intelligent Reasoning**: Lead analysis, decision-making, and Q&A capabilities
- **📊 Pattern Analysis**: Autonomous detection of trends and anomalies
- **🔄 Event Bus Architecture**: Loosely coupled, scalable module system
- **🛡️ Circuit Breakers**: Resilience against service failures
- **📅 Autonomous Scheduler**: Background jobs for CRM snapshots, scoring, and briefings
- **🔐 Enterprise Security**: JWT authentication, API keys, audit logging, RBAC

### Key Features

- **Local LLM Integration**: Uses Ollama for on-premises AI processing
- **Supabase Backend**: Scalable PostgreSQL database with real-time capabilities
- **N8N Automation**: Workflow automation and integration support
- **Telegram Integration**: Daily briefings and notifications
- **Vector Memory**: ChromaDB for semantic search and retrieval
- **Training Data Export**: Automatic collection and export for model fine-tuning

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      NGINX (Reverse Proxy)                  │
│                     SSL/TLS Termination                     │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
         │  Brain  │    │  Agent  │    │   N8N   │
         │  (9000) │    │  (8000) │    │ (5678)  │
         └────┬────┘    └────┬────┘    └────┬────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Ollama (11434)    │
                    │  qwen2.5:7b        │
                    └────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Supabase          │
                    │  (PostgreSQL)      │
                    └────────────────────┘
```

---

## 🚀 Prerequisites

Before installing MagicLamp, ensure you have:

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Git** for cloning the repository
- **Python 3.11+** (for local development)
- **Supabase Account** (or self-hosted instance)
- **8GB+ RAM** (16GB recommended for Ollama)
- **20GB+ Disk Space** for models and data

### Required Accounts

1. **Supabase**: [supabase.com](https://supabase.com) (free tier available)
2. **Telegram Bot** (optional): [@BotFather](https://t.me/botfather) for notifications

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/subairkprm/magiclamp.git
cd magiclamp
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here
JWT_SECRET=$(openssl rand -hex 32)
BRAIN_SECRET=$(openssl rand -hex 32)

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_CHAT_ID=your_chat_id

# N8N
N8N_USER=admin
N8N_PASSWORD=$(openssl rand -base64 32)
N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)

# AI Model
OLLAMA_MODEL=qwen2.5:7b

# Server
SERVER_HOST=YOUR_VPS_IP_OR_DOMAIN

# CORS (Production)
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### 3. Start the Stack

```bash
# Start all services
docker-compose up -d

# Check status
make status

# View logs
make logs
```

### 3A. Local Brain-Only Deploy (No Docker)

If Docker is not available and you only need the FastAPI brain service locally:

```bash
# One command setup + run on http://localhost:9000
./scripts/deploy_local.sh
```

This script creates `.env` from `.env.example`, generates local secrets, creates a virtualenv, installs `brain/requirements.txt`, and starts Uvicorn.

### 4. Pull AI Model

```bash
# Pull the default model (7B parameters, ~4GB)
make pull-model MODEL=qwen2.5:7b

# Or use a smaller/larger model
make pull-model MODEL=qwen2.5:3b   # Lighter (2GB)
make pull-model MODEL=qwen2.5:14b  # Stronger (8GB)
```

### 5. Verify Installation

```bash
# Check brain health
curl http://localhost:9000/health

# Access API documentation
open http://localhost:9000/docs

# View Coolify panel (if installed)
make panel
```

---

## 🔧 Environment Configuration

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | ✅ | - | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | ✅ | - | Service role key (admin access) |
| `JWT_SECRET` | ✅ | - | JWT signing secret (32+ chars) |
| `BRAIN_SECRET` | ✅ | - | Brain API key (32+ chars) |

### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2.5:7b` | LLM model to use |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama service URL |
| `BRAIN_AUTO_MODE` | `true` | Enable autonomous scheduler |
| `BRAIN_DATA_DIR` | `/data/brain` | Data storage directory |
| `CORS_ALLOWED_ORIGINS` | `*` | Comma-separated allowed origins |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token for notifications |
| `TELEGRAM_ADMIN_CHAT_ID` | - | Telegram chat ID for admin alerts |
| `N8N_API_KEY` | - | N8N API key for workflow automation |

### Security Best Practices

1. **Generate Strong Secrets**: Use `openssl rand -hex 32` for all secrets
2. **Restrict CORS**: Set specific origins in production (not `*`)
3. **Use HTTPS**: Enable SSL with Let's Encrypt (see `make ssl`)
4. **Rotate Keys**: Change JWT/API keys periodically
5. **Backup Data**: Regular backups with `make backup`

---

## 💻 Development

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/subairkprm/magiclamp.git
cd magiclamp

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd brain
pip install -r requirements.txt
pip install -r ../tests/requirements-test.txt  # For testing

# Set up environment
cp ../.env.example ../.env
# Edit .env with your local configuration

# Run brain locally
uvicorn main:app --reload --host 0.0.0.0 --port 9000
```

### Running Tests

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Run all tests with coverage
pytest tests/ --cov=brain --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run with markers
pytest tests/ -m unit         # Unit tests only
pytest tests/ -m integration  # Integration tests only

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Format code with black
black brain/

# Sort imports
isort brain/

# Type checking
mypy brain/

# Linting
flake8 brain/
pylint brain/
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 🔌 API Usage

### Authentication

```bash
# Login to get access token
curl -X POST http://localhost:9000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@example.com", "password": "your_password"}'

# Use token in subsequent requests
TOKEN="your_access_token"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9000/api/v1/brain/memory/stats
```

### Memory Operations

```bash
# Remember a fact
curl -X POST http://localhost:9000/api/v1/brain/memory/remember \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "customer.preference",
    "value": "prefers digital banking",
    "confidence": 0.95
  }'

# Recall a fact
curl http://localhost:9000/api/v1/brain/memory/recall/customer.preference \
  -H "Authorization: Bearer $TOKEN"
```

### AI Reasoning

```bash
# Analyze a lead
curl -X POST http://localhost:9000/api/v1/brain/reason/lead \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "lead": {
      "name": "Ahmed Hassan",
      "company": "TechCorp UAE",
      "revenue": "5M AED",
      "employees": 50
    }
  }'

# Ask a question
curl -X POST http://localhost:9000/api/v1/brain/reason/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the eligibility criteria for SME loans?"}'
```

### Interactive API Documentation

Visit `http://localhost:9000/docs` for interactive Swagger documentation with built-in testing capabilities.

---

## 🛠️ Makefile Commands

MagicLamp includes a comprehensive Makefile for common operations:

### Stack Control

```bash
make start          # Start entire stack
make stop           # Stop entire stack
make restart        # Restart all services
make build          # Rebuild brain + agent
make update         # Pull latest code + rebuild
make deploy         # Full deploy with health checks
```

### Monitoring

```bash
make status         # Container health + API status
make logs           # All service logs (follow mode)
make brain-logs     # Brain service logs only
make agent-logs     # Agent service logs only
make n8n-logs       # N8N logs
make ollama-logs    # Ollama logs
```

### AI Models

```bash
make pull-model MODEL=qwen2.5:7b    # Pull specific model
make list-models                    # List installed models
make delete-model MODEL=mistral:7b  # Delete a model
```

### Maintenance

```bash
make backup                          # Backup all data + .env
make restore FILE=backups/xxx.tar.gz # Restore from backup
make ssl DOMAIN=yourdomain.com       # Setup Let's Encrypt SSL
```

### Database

```bash
make brain-stats           # View brain memory statistics
make trigger-briefing      # Manually trigger daily briefing
```

---

## 🔐 Security

### Password Policy

MagicLamp enforces strong password requirements:
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- Not in common password list

### Authentication Methods

1. **JWT Tokens**: Short-lived access tokens + refresh tokens
2. **API Keys**: For service-to-service communication
3. **Brain Key**: Internal service authentication

### Input Validation

All API endpoints use Pydantic validation models to prevent:
- SQL injection
- XSS attacks
- Command injection
- SSRF vulnerabilities

### Audit Logging

Every mutating operation (POST/PUT/PATCH/DELETE) is automatically logged with:
- User ID and organization
- Action performed
- Timestamp and IP address
- Request details

---

## 🚢 Deployment

For environment-specific steps:
- Local development: see `DEPLOY_LOCAL.md` (`docker compose -f docker-compose.yml -f docker-compose.local.yml up -d`)
- Production VPS: see `DEPLOY_PROD.md` (`docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`)

### Production Checklist

- [ ] Set strong, unique secrets in `.env`
- [ ] Configure specific CORS origins (not `*`)
- [ ] Enable HTTPS with SSL certificate
- [ ] Set `BRAIN_AUTO_MODE=true` for autonomous operations
- [ ] Configure backup schedule
- [ ] Set up monitoring and alerting
- [ ] Configure Telegram notifications
- [ ] Review and adjust rate limits
- [ ] Set up log aggregation
- [ ] Configure firewall rules

### Docker Deployment

```bash
# Deploy to production
make deploy

# Monitor deployment
make status
```

### Health Checks

```bash
# Brain API health
curl http://localhost:9000/health

# Admin system health (requires auth)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9000/api/v1/admin/health
```

### Scaling

MagicLamp is designed to scale horizontally:

1. **Brain Service**: Can run multiple instances behind a load balancer
2. **Ollama**: Can run on separate GPU servers
3. **Supabase**: Built-in scaling and connection pooling
4. **N8N**: Supports queue mode for distributed execution

---

## 📊 Monitoring

### Key Metrics

- **API Response Time**: Monitor via `/api/v1/admin/health`
- **Circuit Breaker States**: Check service availability
- **Event Bus Queue**: Monitor queue size and processing
- **Memory Stats**: Track facts, events, decisions count
- **Training Data**: Monitor sample collection progress

### Logs

All services use structured JSON logging:

```bash
# View brain logs
docker-compose logs -f brain

# Filter by level
docker-compose logs brain | grep '"level":"ERROR"'

# View specific module
docker-compose logs brain | grep '"module":"scheduler"'
```

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Follow** code style (black, isort, pylint)
4. **Add** tests for new features
5. **Ensure** all tests pass (`pytest tests/`)
6. **Commit** with clear messages
7. **Push** to your branch
8. **Open** a Pull Request

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and test
pytest tests/

# Format and lint
black brain/
flake8 brain/

# Commit changes
git commit -m "feat: add awesome feature"

# Push and create PR
git push origin feature/my-feature
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

### Documentation

- **API Docs**: `http://localhost:9000/docs`
- **ReDoc**: `http://localhost:9000/redoc`
- **Makefile Help**: `make help`

### Issues

Report bugs and request features at: [GitHub Issues](https://github.com/subairkprm/magiclamp/issues)

### Community

- **Discord**: [Join our community](#) (coming soon)
- **Twitter**: [@magiclamp_ai](#) (coming soon)

---

## 🙏 Acknowledgments

- **FastAPI**: Modern, fast web framework
- **Ollama**: Local LLM inference
- **Supabase**: Backend-as-a-Service
- **N8N**: Workflow automation
- **ChromaDB**: Vector database
- **APScheduler**: Background job scheduling

---

## 📈 Roadmap

- [ ] Multi-tenancy support
- [ ] Enhanced RAG capabilities
- [ ] Real-time WebSocket notifications
- [ ] Mobile app integration
- [ ] Advanced analytics dashboard
- [ ] Custom model fine-tuning UI
- [ ] Multi-language support
- [ ] Voice interface

---

**Built with ❤️ for the UAE Banking Industry**

🪄 *Make a wish, and let MagicLamp's AI brain make it happen.*
