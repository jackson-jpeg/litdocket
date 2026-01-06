"""
Configuration validator - ensures all required environment variables are set
"""
import sys
from app.config import settings


def validate_config():
    """
    Validate that all required configuration is set.
    
    Raises:
        RuntimeError: If any required config is missing or invalid
    """
    errors = []
    
    # Required environment variables
    required_vars = {
        'SECRET_KEY': settings.SECRET_KEY,
        'JWT_SECRET_KEY': settings.JWT_SECRET_KEY,
        'ANTHROPIC_API_KEY': settings.ANTHROPIC_API_KEY,
    }
    
    # Check for missing variables
    for var_name, var_value in required_vars.items():
        if not var_value or var_value in [
            'your-secret-key-change-in-production',
            'your-super-secret-jwt-key-change-in-production',
            'your-secret-key-change-this-to-random-64-char-string',
            'your-jwt-secret-key-change-this-to-random-64-char-string',
            'sk-ant-api03-xxx-your-api-key-here'
        ]:
            errors.append(f"❌ {var_name} is not set or using placeholder value")
    
    # Validate SECRET_KEY strength
    if settings.SECRET_KEY and len(settings.SECRET_KEY) < 32:
        errors.append(f"❌ SECRET_KEY is too short (min 32 characters, got {len(settings.SECRET_KEY)})")
    
    # Validate JWT_SECRET_KEY strength
    if settings.JWT_SECRET_KEY and len(settings.JWT_SECRET_KEY) < 32:
        errors.append(f"❌ JWT_SECRET_KEY is too short (min 32 characters, got {len(settings.JWT_SECRET_KEY)})")
    
    # Validate ANTHROPIC_API_KEY format
    if settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith('sk-ant-'):
        errors.append(f"❌ ANTHROPIC_API_KEY has invalid format (should start with 'sk-ant-')")
    
    # Warn if DEBUG is enabled
    if settings.DEBUG:
        print("⚠️  WARNING: DEBUG mode is enabled. Disable in production!")
    
    # If there are errors, print them and exit
    if errors:
        print("\n" + "="*80)
        print("CONFIGURATION VALIDATION FAILED")
        print("="*80)
        for error in errors:
            print(error)
        print("\nPlease set the required environment variables:")
        print("1. Copy .env.example to .env")
        print("2. Generate secure keys with:")
        print("   python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
        print("3. Add your Anthropic API key")
        print("4. Restart the application")
        print("="*80 + "\n")
        sys.exit(1)
    
    # All checks passed
    print("✅ Configuration validation passed")
    print(f"   - SECRET_KEY: {len(settings.SECRET_KEY)} characters")
    print(f"   - JWT_SECRET_KEY: {len(settings.JWT_SECRET_KEY)} characters")
    print(f"   - ANTHROPIC_API_KEY: Set ({settings.ANTHROPIC_API_KEY[:15]}...)")
    print(f"   - DEBUG: {settings.DEBUG}")
    print(f"   - DATABASE_URL: {settings.DATABASE_URL.split('@')[0]}...")  # Hide password


if __name__ == "__main__":
    validate_config()
