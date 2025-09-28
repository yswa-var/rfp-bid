"""
Bridge module to connect Teams bot with main RFP system
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

main_path = Path(__file__).parent.parent / "main"
sys.path.insert(0, str(main_path))
sys.path.insert(0, str(main_path / "src"))

class RFPSystemBridge:
    """Bridge to connect Teams integration with main RFP system"""
    
    def __init__(self):
        self.main_path = main_path
        self._validate_paths()
    
    def _validate_paths(self):
        """Validate that main system paths exist"""
        required_paths = [
            self.main_path / "src" / "agent",
            self.main_path / "src" / "agent" / "proposal_supervisor.py",
            self.main_path / "src" / "agent" / "team_agents.py"
        ]
        
        for path in required_paths:
            if not path.exists():
                raise FileNotFoundError(f"Required path not found: {path}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the main RFP system"""
        try:
            from main.src.agent.proposal_rag_coordinator import ProposalRAGCoordinator
            
            coordinator = ProposalRAGCoordinator()
            db_status = coordinator.check_databases_status()
            
            return {
                "main_path": str(self.main_path),
                "databases": db_status,
                "teams_available": [
                    "technical_team",
                    "finance_team", 
                    "legal_team",
                    "qa_team"
                ]
            }
        except Exception as e:
            return {
                "error": str(e),
                "main_path": str(self.main_path)
            }
    
    def test_integration(self) -> bool:
        """Test if RFP system integration works"""
        try:
            # Add paths first
            import sys
            from pathlib import Path
            
            current_dir = Path(__file__).parent
            main_path = current_dir.parent / "main"
            src_path = main_path / "src"
            
            paths_to_add = [str(main_path), str(src_path)]
            for path in paths_to_add:
                if path not in sys.path:
                    sys.path.insert(0, path)
            
            # Change to main directory
            import os
            original_cwd = os.getcwd()
            os.chdir(str(main_path))
            
            try:
                # Test imports - Import graph directly
                from agent.graph import graph
                from agent.state import MessagesState
                
                print("✅ Successfully imported main system components")
                print(f"✅ Graph type: {type(graph)}")
                return True
                
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            print(f"Integration test failed: {e}")
            return False