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
# Collector service tests
cd services/collector
pip install -r requirements.txt pytest
PYTHONPATH=. pytest tests

# Other services follow similar patterns with pytest.ini configurations
# Each service has its own requirements.txt and test configuration
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
- Python path adjustments needed for imports: `PYTHONPATH=. pytest`
- Service-specific test directories under each service folder

**Environment Setup**
- Services expect `.env` file in project root
- Database runs on port 8586 (mapped from container port 5432)
- Redis runs on standard port 6379
- Each service runs on ports 8001-8005