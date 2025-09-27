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
- Orchestrates daily workflow execution at configurable time (default 03:50 AM)
- Triggers collector → waits for analyzer idle → triggers composer → waits for notion worker idle
- Uses tenacity retry patterns for service communication
- Configurable timing and retry behavior via environment variables
- Entry point: `services/scheduler/src/main.py`

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

## Recent Critical Fixes & Known Issues ✅

### Fixed Issues (Priority Fixes)

1. **NoneType Redis Serialization Error** ✅ FIXED
   - **Location**: `shared/utils/redis_client.py:_serialize_value()`
   - **Issue**: UUID objects not properly serialized for Redis streams
   - **Fix**: Added UUID handling with `hasattr(value, "hex")` check
   - **Impact**: Prevents collector service crashes during article publishing

2. **Notion API Text Length Validation Error** ✅ FIXED
   - **Location**: `services/notion_worker/app/markdown_parser.py`
   - **Issue**: Text blocks exceeding 2000 character limit causing API rejection
   - **Fix**: Added `truncate_text()` function with smart word-boundary breaking
   - **Impact**: Ensures successful digest publishing to Notion

3. **Docker Health Check Failures** ✅ FIXED
   - **Location**: All service Dockerfiles (analyzer, composer, notion_worker)
   - **Issue**: Health checks using `curl` but `curl` not installed in slim images
   - **Fix**: Added `RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*`
   - **Impact**: Proper container health monitoring in production

4. **Dependency Naming Inconsistency** ✅ FIXED
   - **Location**: `services/scheduler/requirements.txt`
   - **Issue**: Used `pydantic_settings` while others use `pydantic-settings`
   - **Fix**: Standardized to `pydantic-settings` across all services
   - **Impact**: Prevents CI/CD installation conflicts

5. **Database Initialization Errors** ✅ FIXED
   - **Location**: `shared/database/session.py:init_db()`
   - **Issue**: `create_all()` failing when tables already exist
   - **Fix**: Added `checkfirst=True` parameter to `create_all()`
   - **Impact**: Prevents service startup failures on restart

### Development Best Practices

**Error Handling Patterns**
- Always use `@retry` decorators for external service calls
- Implement proper exception handling with specific error types
- Log errors with sufficient context for debugging
- Use circuit breaker patterns for cascading failure prevention

**Redis Stream Patterns**
- Ensure all message fields are serializable (strings, numbers, booleans)
- Use `exclude_none=True` in Pydantic model dumps
- Handle UUID and datetime objects explicitly in serialization
- Implement proper consumer group management and acknowledgment

**Notion API Integration**
- Validate all text content length (2000 char max per text block)
- Implement smart truncation with word boundaries
- Use retry patterns for API rate limiting
- Handle API validation errors gracefully

**Docker Best Practices**
- Install required tools (curl, etc.) for health checks
- Use multi-stage builds for production images
- Implement proper health check commands
- Handle container startup dependencies correctly

**Testing Patterns**
- Use service-specific PYTHONPATH configurations
- Test with proper dependency isolation
- Mock external service dependencies
- Validate error handling scenarios

### Debugging Common Issues

**NoneType Errors in Redis**
```python
# Check for None values before Redis operations
if value is None:
    return ""  # or appropriate default
```

**Text Length Issues with Notion**
```python
# Truncate text content before API calls
content = truncate_text(original_text, max_length=2000)
```

**Container Health Check Failures**
```bash
# Verify curl is available in container
docker exec -it service_name curl --version
```

**Service Communication Failures**
```bash
# Check service discovery
docker-compose exec service1 nslookup service2
# Test internal connectivity
docker-compose exec service1 curl http://service2:port/health
```