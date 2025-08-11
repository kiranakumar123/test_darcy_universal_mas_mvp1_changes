# Render Deployment Guide

## Environment Variables Setup

When deploying to Render, you need to set these environment variables in the Render dashboard:

### Required OpenAI Configuration

Go to your Render service → **Environment** tab and add:

```
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_ORGANIZATION=org-your-actual-organization-id-here
OPENAI_PROJECT=proj-your-actual-project-id-here
```

### Required Application Configuration

```
ENVIRONMENT=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
```

### Optional Configuration

```
# Redis (if using external Redis)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password

# Authentication
JWT_SECRET_KEY=your-secure-random-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# LangSmith (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key

# Database
DATABASE_URL=your-database-url

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

## Getting OpenAI Credentials

1. **API Key**: Go to https://platform.openai.com/api-keys
2. **Organization ID**: Go to https://platform.openai.com/settings/organization
3. **Project ID**: Go to https://platform.openai.com/settings/proj

## Deployment Notes

- ✅ **No .env file needed** - Render injects environment variables directly
- ✅ **Automatic SSL** - Render provides HTTPS automatically
- ✅ **Zero-downtime deployments** - Render does rolling deployments
- ✅ **Auto-scaling** - Configure based on your needs

## Troubleshooting

If you get authentication errors:

1. Verify all OpenAI environment variables are set in Render
2. Check that your OpenAI API key has project-scoped permissions
3. Ensure organization and project IDs are correct (start with `org-` and `proj-`)
4. Restart your Render service after updating environment variables

## Security Best Practices

- Use strong, unique values for `JWT_SECRET_KEY`
- Keep your OpenAI API key secure and rotate regularly
- Set `DEBUG=false` in production
- Enable monitoring and logging for production deployments
