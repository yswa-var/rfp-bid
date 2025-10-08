import os

class DefaultConfig:
    """Bot Configuration"""
    
    PORT = 3978
    APP_ID = os.environ.get("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    APP_TYPE = os.environ.get("MicrosoftAppType", "MultiTenant")
    APP_TENANTID = os.environ.get("MicrosoftAppTenantId", "")
    
    # Backend API settings
    BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
    
    # Teams specific settings
    TEAMS_ENABLED = True