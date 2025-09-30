"""
Configuration for Teams bot using existing main system
"""
import os
from pathlib import Path

class Config:
    """Bot Configuration"""
    
    # Teams Bot Configuration
    PORT = int(os.environ.get("PORT", 3978))
    APP_ID = os.environ.get("BOT_APP_ID", "")
    APP_PASSWORD = os.environ.get("BOT_APP_PASSWORD", "")
    
    # Main System Integration Paths
    TEAMS_DIR = Path(__file__).parent
    MAIN_DIR = TEAMS_DIR.parent / "main"
    MAIN_SRC_DIR = MAIN_DIR / "src"
    
    RFP_RAG_DB = os.environ.get("RFP_RAG_DB", str(MAIN_SRC_DIR / "agent" / "rfp_rag.db"))
    TEMPLATE_RAG_DB = os.environ.get("TEMPLATE_RAG_DB", str(MAIN_SRC_DIR / "agent" / "template_rag.db"))
    SESSION_DB = os.environ.get("SESSION_DB", str(MAIN_DIR / "session.db"))  # USE MAIN'S SESSION.DB
    
    # LangGraph Configuration
    RECURSION_LIMIT = int(os.environ.get("RECURSION_LIMIT", 12))
    
    @classmethod
    def setup_system_paths(cls):
        """Setup Python paths for main system access"""
        import sys
        paths_to_add = [str(cls.MAIN_DIR), str(cls.MAIN_SRC_DIR), str(cls.TEAMS_DIR)]
        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)
        print(f"✅ System paths configured: {paths_to_add}")

Config.setup_system_paths()