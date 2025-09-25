# Security Guidelines for RaveDigest

## 🔒 Repository Security

### Before Making Repository Public

1. **Environment Variables**
   - ✅ Never commit `.env` files
   - ✅ Use `.env.example` as template
   - ✅ Store secrets in GitHub Secrets
   - ✅ Use test values in CI/CD

2. **API Keys & Secrets**
   - ✅ OpenAI API Key → GitHub Secret
   - ✅ Notion API Key → GitHub Secret
   - ✅ Database passwords → GitHub Secret or environment-specific

## 🛠️ Setting Up GitHub Secrets

### Required Secrets for CI/CD

Go to your repository → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for content analysis | `sk-proj-...` |
| `NOTION_API_KEY` | Notion integration API key | `ntn_...` |
| `NOTION_DB_ID` | Target Notion database ID | `2420816f...` |

### Optional Secrets

| Secret Name | Description |
|-------------|-------------|
| `POSTGRES_PASSWORD` | Production database password |
| `REDIS_PASSWORD` | Redis password (if using auth) |
| `SENTRY_DSN` | Error tracking (production) |

## 🔐 Environment Configuration

### Local Development (.env)
```bash
# Copy template and fill real values
cp .env.example .env
# Edit .env with your actual keys
```

### Production Deployment
```bash
# Use environment-specific files
.env.production  # Real production values
.env.staging     # Staging environment values
```

### Docker Compose
```yaml
# Use secrets or environment files
env_file:
  - .env.production
environment:
  OPENAI_API_KEY: ${OPENAI_API_KEY}
```

## 🚨 Security Best Practices

### ✅ Do This
- Use GitHub Secrets for sensitive data
- Rotate API keys regularly
- Use different keys for different environments
- Monitor API key usage
- Use least-privilege access
- Enable 2FA on all accounts

### ❌ Never Do This
- Commit API keys to version control
- Share API keys in chat/email
- Use production keys in development
- Store passwords in plain text
- Push `.env` files to GitHub

## 🔍 Security Scanning

The CI workflow includes:
- **Bandit**: Python security linting
- **Safety**: Dependency vulnerability scanning
- **GitHub Dependabot**: Automated dependency updates

## 📊 Monitoring & Alerts

### API Key Usage
- Monitor OpenAI API usage: https://platform.openai.com/usage
- Monitor Notion API limits: Notion workspace settings
- Set up billing alerts

### Security Alerts
- Enable GitHub security alerts
- Configure Dependabot security updates
- Monitor application logs for suspicious activity

## 🆘 Security Incident Response

### If API Key is Compromised:
1. **Immediately revoke** the compromised key
2. **Generate new key** from provider
3. **Update GitHub Secrets** with new key
4. **Monitor usage** for unauthorized activity
5. **Review logs** for potential data access

### If Repository is Accidentally Public:
1. **Make repository private** immediately
2. **Rotate all API keys** mentioned in code/commits
3. **Review commit history** for sensitive data
4. **Clean up git history** if needed (consider new repo)

## 📞 Security Contacts

- **GitHub Security**: https://github.com/security
- **OpenAI Security**: security@openai.com
- **Notion Security**: security@makenotion.com

---

**Remember**: Security is an ongoing process, not a one-time setup. Regularly review and update your security practices.