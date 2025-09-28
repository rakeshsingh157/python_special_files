# Security Configuration Guide

## Overview
All sensitive information has been moved from hardcoded values to environment variables for better security.

## Required Environment Variables

### Database Configuration
- `DB_HOST`: Database server hostname
- `DB_USER`: Database username  
- `DB_PASSWORD`: Database password
- `DB_NAME`: Database name
- `DB_DATABASE`: Database name (fallback)
- `USE_PURE`: Use pure Python MySQL connector (True/False)

### API Keys
- `GOOGLE_GEMINI_API_KEY`: Google Gemini AI API key
- `GROQ_API_KEY`: Groq AI API key  
- `COHERE_API_KEY`: Cohere AI API key

### Flask Configuration
- `FLASK_SECRET_KEY`: Flask session secret key

## Setup Instructions

1. **Copy Environment File**
   ```bash
   cp .env.example .env
   ```

2. **Update Values**
   Edit `.env` file and replace all placeholder values with your actual credentials.

3. **File Permissions** (Linux/Mac)
   ```bash
   chmod 600 .env
   ```

## Security Features Implemented

### ✅ Environment Variables
- All sensitive data moved from hardcoded values to environment variables
- Configuration centralized in `config.py`
- Validation of required environment variables on startup

### ✅ Git Security
- `.env` files added to `.gitignore`
- `.env.example` provided as template
- Backup files excluded from version control

### ✅ Code Security
- Database credentials no longer in source code
- API keys loaded from environment only
- Flask secret key now secure and configurable

## Files Updated

### Core Configuration
- `config.py` - Central configuration management
- `.env` - Environment variables (not in version control)
- `.env.example` - Template for environment variables

### Application Files
- `app.py` - Updated to use Config class
- `database.py` - Uses environment variables
- `login_register.py` - Secure database configuration
- `user_profile.py` - Environment-based configuration  
- `ai.py` - Secure API configuration
- `ai_assistant.py` - Already using environment variables
- `ai_scheduler.py` - Already using environment variables

### Security Files
- `.gitignore` - Prevents sensitive files from being committed

## Validation

The application now validates that all required environment variables are set on startup. If any are missing, it will display an error message.

## Best Practices

1. **Never commit `.env` files** to version control
2. **Use different `.env` files** for different environments (dev, staging, prod)
3. **Regularly rotate** API keys and database passwords
4. **Use strong, unique values** for Flask secret keys
5. **Limit database user permissions** to only what's needed
6. **Monitor access logs** for suspicious activity

## Production Deployment

For production deployment:

1. Set environment variables through your hosting platform's configuration
2. Use secure secret management services (AWS Secrets Manager, Azure Key Vault, etc.)
3. Enable database SSL connections
4. Use environment-specific API keys
5. Regular security audits and dependency updates