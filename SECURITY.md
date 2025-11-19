# Security Guidelines

## Protecting Sensitive Data

This project handles sensitive information including API keys, Google Sheets IDs, and service account credentials. Follow these guidelines to keep your data secure:

### Files That Should NEVER Be Committed

The following files contain secrets and are excluded via `.gitignore`:

- `.env` - Contains all API keys and configuration
- `credentials.json` - Google service account JSON key file
- `*-key.json` - Any service account key files
- `service-account*.json` - Service account credentials

### Before Pushing to GitHub

1. **Verify .gitignore is working:**
   ```bash
   git status
   ```
   Make sure `.env` and `credentials.json` are NOT listed

2. **Check for leaked secrets:**
   ```bash
   git diff --cached
   ```
   Review all changes to ensure no API keys or credentials are included

3. **Use .env.example as template:**
   - `.env.example` contains placeholder values
   - Never put real credentials in `.env.example`
   - Share `.env.example` with your team as a template

### Environment Variables in Production

For Cloud Run deployment:

- **DO NOT** hardcode secrets in code
- **DO NOT** commit `.env` file
- **USE** Google Secret Manager for all sensitive values
- **USE** Application Default Credentials (ADC) for authentication

### Google Sheets Sharing

When sharing Google Sheets with service accounts:

1. Share with the service account email (e.g., `your-sa@project.iam.gserviceaccount.com`)
2. Grant only necessary permissions (Viewer for master sheet, Editor for output sheet)
3. Never share sheets publicly if they contain sensitive business data

### Rotating Credentials

If credentials are accidentally exposed:

1. **Immediately revoke** the exposed credentials
2. **Generate new** API keys/service accounts
3. **Update** Secret Manager with new values:
   ```bash
   ./update_secrets.sh
   ```
4. **Redeploy** the service to use new secrets

### Audit Trail

- Review Cloud Run logs for unauthorized access
- Monitor API usage in GCP Console
- Set up billing alerts to detect unusual activity

### Development Best Practices

- Never print or log API keys
- Use environment variables, not hardcoded values
- Keep local `.env` file outside version control
- Use separate development and production credentials when possible
