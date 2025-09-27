"""
Configuration for RFP Teams Bot
"""
import os
from dotenv import load_dotenv

# Load Teams-specific environment
load_dotenv("src/teams/.env.teams")

class RFPTeamsConfig:
    """Configuration for RFP Teams integration"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-small")
    
    # Teams Bot Configuration
    BOT_APP_ID = os.getenv("BOT_APP_ID", "")
    BOT_APP_PASSWORD = os.getenv("BOT_APP_PASSWORD", "")
    
    # Memory Configuration
    MEMORY_DB_PATH = "src/teams/data/rfp_memory.db"
    
    # RFP-specific memory topics
    RFP_MEMORY_TOPICS = [
        {
            "name": "client_company",
            "description": "Client company name and details"
        },
        {
            "name": "project_type",
            "description": "Type of project (web development, cloud migration, etc.)"
        },
        {
            "name": "budget_range",
            "description": "Project budget or budget constraints"
        },
        {
            "name": "timeline",
            "description": "Project timeline and key deadlines"
        },
        {
            "name": "technical_requirements",
            "description": "Specific technical requirements and constraints"
        },
        {
            "name": "compliance_needs",
            "description": "Regulatory and compliance requirements"
        }
    ]