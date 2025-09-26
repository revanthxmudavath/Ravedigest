# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Docker Development
```bash
make up           # Start all services with docker-compose
make down         # Stop all services
make logs         # View logs from all services
```

### Code Formatting
```bash
make format       # Format Python code with black (services/ and shared/)
```

### Testing
```bash
# Service-specific testing with correct PYTHONPATH for each service structure

# Collector service (src/collector structure)
cd services/collector
pip install -r requirements.txt pytest
PYTHONPATH=src:../.. pytest tests -v

# Analyzer service (root level structure)
cd services/analyzer
pip install -r requirements.txt pytest
PYTHONPATH=.:../.. pytest tests -v

# Composer service (app/ structure)
cd services/composer
pip install -r requirements.txt pytest
PYTHONPATH=.:../.. pytest tests -v

# Notion Worker service (app/ structure)
cd services/notion_worker
pip install -r requirements.txt pytest
PYTHONPATH=.:../.. pytest tests -v

# Scheduler service (src/ structure)
cd services/scheduler
pip install -r requirements.txt pytest
PYTHONPATH=.:../.. pytest tests -v

# Run all tests via CI workflow
# The GitHub Actions CI automatically handles all dependencies and paths
```

## Architecture Overview

RaveDigest is a microservices architecture that collects trending content, analyzes it with LLMs, and publishes digests to Notion. The system uses Redis Streams for event-driven communication between services.

### Core Services

**Collector Service** (Port 8001)
- Collects articles from RSS feeds configured in `shared/config/settings.py`
- Stores raw articles in PostgreSQL and publishes to `raw_articles` Redis stream
- Implements deduplication using Redis for URL tracking
- Entry point: `services/collector/src/collector/main.py`

**Analyzer Service** (Port 8002)
- Consumes from `raw_articles` stream
- Extracts full article content using readability and BeautifulSoup
- Performs LLM-based summarization and relevance scoring via OpenAI
- Determines developer focus using keyword matching
- Publishes enriched articles to `enriched_articles` stream
- Implements retry patterns with `@async_retry` decorator

**Composer Service** (Port 8003)
- Consumes from `enriched_articles` stream
- Generates daily digests using Jinja2 templates (`services/composer/app/templates/`)
- Filters articles based on relevance scores and developer focus
- Publishes completed digests to `digests` stream

**Notion Worker** (Port 8004)
- Consumes from `digests` stream
- Publishes formatted digests to Notion databases
- Handles markdown parsing and Notion block creation

**Scheduler Service** (Port 8005)
- Orchestrates daily workflow execution
- Triggers collector → waits for analyzer idle → triggers composer → waits for notion worker idle
- Uses tenacity retry patterns for service communication
- Configurable timing and retry behavior via environment variables

### Key Architecture Patterns

**Event-Driven Communication**
- All inter-service communication uses Redis Streams
- Consumer groups ensure message delivery and processing guarantees
- Services implement status endpoints to report processing state

**Configuration Management**
- Centralized configuration in `shared/config/settings.py` using Pydantic Settings
- Environment-based configuration with validation
- Settings organized by service area (database, redis, openai, notion, service-specific)

**Database Layer**
- SQLAlchemy models in `shared/database/models/`
- Article model supports both raw and enriched states
- Digest model for composed content
- Alembic migrations in `shared/alembic/`

**Health Checks & Monitoring**
- Each service implements `/health`, `/health/live`, and `/health/ready` endpoints
- Health checkers validate dependencies (database, redis, external APIs)
- Prometheus metrics integration in analyzer service

**Retry & Resilience Patterns**
- `shared/utils/retry.py` provides `@async_retry` decorator
- Services implement graceful degradation and error handling
- Configurable timeout and retry behavior

### Development Notes

**Shared Modules**
- `shared/` directory contains common utilities, database models, and configuration
- All services depend on shared modules for consistency
- Logging configuration centralized in `shared/app_logging/`

**Service Structure**
- Each service has its own Dockerfile and requirements.txt
- FastAPI applications with standardized health check patterns
- Service-specific business logic separated from shared infrastructure

**Testing Configuration**
- Each service uses pytest with custom pytest.ini configuration
- Service-specific PYTHONPATH requirements due to different directory structures:
  - Collector: `PYTHONPATH=src:../..` (src/collector structure)
  - Others: `PYTHONPATH=.:../..` (root or app structures)
- All tests run in CI/CD with automatic dependency management
- Service-specific test directories under each service folder

**Environment Setup**
- Services expect `.env` file in project root (use `.env.example` as template)
- Database runs on port 8586 (mapped from container port 5432)
- Redis runs on standard port 6379
- Each service runs on ports 8001-8005

### CI/CD & Security

**GitHub Actions Workflow**
- Automated testing for all services with proper dependency management
- Code formatting checks with black, isort, and flake8
- Security scanning with bandit and safety
- Environment variables managed via GitHub Secrets for security

**Security Features**
- `.env.example` template for safe environment variable setup
- GitHub Secrets integration for sensitive API keys
- Comprehensive `.gitignore` to prevent accidental secret commits
- Security documentation in `SECURITY.md`

**Branch Protection**
- CI must pass before merging to main
- Automated testing on push and pull requests
- Docker build validation