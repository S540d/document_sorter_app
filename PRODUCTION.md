# Production Deployment Guide

## Overview

This Document Sorter application is production-ready with comprehensive features including:

- 🐳 **Docker containerization** with multi-stage builds
- 🔒 **Security middleware** with rate limiting and request validation
- 📊 **Performance monitoring** with middleware and health checks
- 🚨 **Error handling** with global handlers and recovery mechanisms
- ⚙️ **Configuration management** with environment variable support
- 🏥 **Health checks** for service monitoring
- 🔄 **Workflow automation** with template recognition
- 📦 **Batch processing** with persistent state

## Quick Start

### Development Mode

```bash
# Start development server
docker-compose --profile dev up

# Or run locally
python app.py
```

### Production Mode

```bash
# Build and start production container
docker-compose up -d

# Check health
curl http://localhost:5000/api/monitoring/health

# View logs
docker-compose logs -f document-sorter
```

## Configuration

### Environment Variables

Production configuration is managed via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Environment mode |
| `FLASK_DEBUG` | `false` | Debug mode |
| `FLASK_HOST` | `0.0.0.0` | Server host |
| `FLASK_PORT` | `5000` | Server port |
| `WORKERS` | `4` | Gunicorn workers |
| `SCAN_DIR` | `/app/data/scan` | Input directory |
| `SORTED_DIR` | `/app/data/sorted` | Output directory |
| `LM_STUDIO_URL` | `http://localhost:1234` | AI service URL |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size |
| `RATE_LIMIT_PER_MINUTE` | `60` | Rate limit per IP |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PERFORMANCE_TRACKING` | `true` | Enable monitoring |

### Example Production Environment

```bash
# .env file for production
FLASK_ENV=production
FLASK_DEBUG=false
WORKERS=8
SCAN_DIR=/data/documents/scan
SORTED_DIR=/data/documents/sorted
LM_STUDIO_URL=http://ai-service:1234
MAX_FILE_SIZE_MB=100
RATE_LIMIT_PER_MINUTE=120
LOG_LEVEL=WARNING
```

## Monitoring & Health

### Health Check

```bash
# Basic health check
curl http://localhost:5000/api/monitoring/health

# Response format:
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "uptime": 3600,
  "version": "1.0.0",
  "checks": {
    "logging": "ok",
    "error_reporting": "ok",
    "performance_tracking": "ok"
  }
}
```

### Performance Metrics

```bash
# Current performance
curl http://localhost:5000/api/performance/current

# Historical metrics
curl http://localhost:5000/api/performance/historical?hours=24

# Middleware performance
curl http://localhost:5000/api/performance/middleware

# Rate limit status
curl http://localhost:5000/api/security/rate-limits
```

### Dashboard

Access the monitoring dashboard at:
- **Main Dashboard**: http://localhost:5000/api/dashboard/overview
- **Workflow Management**: http://localhost:5000/workflows
- **Batch Processing**: http://localhost:5000/batch
- **Templates**: http://localhost:5000/templates

## Security Features

### Rate Limiting

- **Per-IP rate limiting**: Default 60 requests/minute with burst of 10
- **Automatic cleanup**: Old entries cleaned up periodically
- **Headers**: Rate limit info included in response headers

### Request Validation

- **File size limits**: Configurable max upload size
- **Path traversal protection**: Validates file paths
- **Security headers**: CSRF, XSS, and other security headers

### Error Handling

- **Global error handlers**: Consistent error responses
- **Error tracking**: Automatic error reporting and IDs
- **Recovery mechanisms**: Retry logic with exponential backoff

## Deployment Options

### Docker (Recommended)

```bash
# Production build
docker build --target production -t document-sorter:latest .

# Run with volumes
docker run -d \
  --name document-sorter \
  -p 5000:5000 \
  -v /host/data/scan:/app/data/scan \
  -v /host/data/sorted:/app/data/sorted \
  -v /host/logs:/app/logs \
  -e FLASK_ENV=production \
  document-sorter:latest
```

### Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  document-sorter:
    build:
      context: .
      target: production
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - WORKERS=8
    volumes:
      - ./data/scan:/app/data/scan
      - ./data/sorted:/app/data/sorted
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/monitoring/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/document-sorter
server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:5000/api/monitoring/health;
        access_log off;
    }
}
```

## Performance Optimization

### Resource Allocation

```bash
# Recommended production settings
WORKERS=4-8  # Based on CPU cores
TIMEOUT=120  # Request timeout
MAX_FILE_SIZE_MB=50-100  # Based on storage
RATE_LIMIT_PER_MINUTE=60-120  # Based on load
```

### Scaling

1. **Horizontal scaling**: Run multiple container instances behind a load balancer
2. **Vertical scaling**: Increase worker count and resource limits
3. **Database scaling**: Use Redis for shared state (rate limiting, sessions)

### Monitoring

```bash
# Performance monitoring
docker stats document-sorter

# Application logs
docker logs -f document-sorter

# Health monitoring with external tools
curl -f http://localhost:5000/api/monitoring/health || alert
```

## Troubleshooting

### Common Issues

1. **High memory usage**
   - Reduce worker count
   - Check for memory leaks in processing
   - Monitor batch processing queue

2. **Rate limiting issues**
   - Adjust rate limits
   - Check for bot traffic
   - Implement IP whitelisting

3. **Performance degradation**
   - Check middleware metrics
   - Monitor slow requests
   - Review error rates

### Debugging

```bash
# Enable debug logging
docker-compose exec document-sorter \
  env LOG_LEVEL=DEBUG python app.py

# Check performance metrics
curl http://localhost:5000/api/performance/middleware

# Export error reports
curl -X POST http://localhost:5000/api/monitoring/logs/export

# View workflow statistics
curl http://localhost:5000/api/workflows/stats
```

## Backup & Recovery

### Data Backup

```bash
# Backup sorted documents
tar -czf backup-$(date +%Y%m%d).tar.gz data/sorted/

# Backup configuration and state
cp batch_operations.json backups/
cp docker-compose.yml backups/
```

### Recovery

```bash
# Restore from backup
tar -xzf backup-20240101.tar.gz -C data/

# Restart services
docker-compose restart
```

## Testing

### Production Tests

```bash
# Run production feature tests
pytest tests/test_production_features.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Load testing
ab -n 1000 -c 10 http://localhost:5000/api/monitoring/health
```

### Integration Tests

```bash
# Test Docker build
docker build --target production -t test-image .

# Test health check
docker run --rm test-image curl -f http://localhost:5000/api/monitoring/health

# Test workflow processing
curl -X POST http://localhost:5000/api/workflows/test \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/test/document.pdf"}'
```

## Maintenance

### Regular Tasks

1. **Log cleanup**: Configure log rotation
2. **Performance review**: Monitor metrics weekly
3. **Security updates**: Update dependencies monthly
4. **Health checks**: Monitor endpoint availability

### Updates

```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Rebuild production image
docker build --no-cache --target production -t document-sorter:latest .

# Rolling update
docker-compose up -d --no-deps document-sorter
```

## Support

For production issues:

1. Check health endpoint: `/api/monitoring/health`
2. Review performance metrics: `/api/performance/current`
3. Export error reports: `/api/monitoring/logs/export`
4. Monitor workflow statistics: `/api/workflows/stats`

The application includes comprehensive monitoring and error reporting to help diagnose and resolve production issues quickly.