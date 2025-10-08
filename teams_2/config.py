"""
Configuration for Teams Bot with LangGraph Server Integration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot and LangGraph Server configuration"""
    
    # Bot Framework Configuration
    APP_ID = os.getenv("MicrosoftAppId", "")
    APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")
    APP_TYPE = os.getenv("MicrosoftAppType", "MultiTenant")
    APP_TENANTID = os.getenv("MicrosoftAppTenantId", "")
    
    # LangGraph Server Configuration
    LANGGRAPH_SERVER_URL = os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:2024")
    ASSISTANT_ID = os.getenv("ASSISTANT_ID", "agent")
    
    # Server Configuration
    PORT = int(os.getenv("PORT", 3978))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # Thread Management
    THREAD_MAPPINGS_FILE = os.getenv("THREAD_MAPPINGS_FILE", "thread_mappings.json")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "teams_bot.log")
    
    # Timeout Configuration
    RUN_TIMEOUT = int(os.getenv("RUN_TIMEOUT", 120))  # seconds
    
    # Approval Keywords
    APPROVE_KEYWORDS = {"yes", "y", "approve", "approved", "/approve"}
    REJECT_KEYWORDS = {"no", "n", "reject", "rejected", "/reject"}
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.LANGGRAPH_SERVER_URL:
            raise ValueError("LANGGRAPH_SERVER_URL is required")
        
        if not cls.ASSISTANT_ID:
            raise ValueError("ASSISTANT_ID is required")
        
        return True

