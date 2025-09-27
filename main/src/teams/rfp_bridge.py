"""
Bridge module to safely connect Teams bot with existing RFP system
"""
from typing import Dict, Any, Optional
from rfp_system_loader import RFPSystemLoader

class RFPSystemBridge:
    """Bridge to connect Teams bot with your existing RFP system"""
    
    def __init__(self):
        print("🔄 Initializing RFP System Bridge...")
        self.rfp_loader = RFPSystemLoader()
        self.agents_available = self.rfp_loader.agents_available
        
        if self.agents_available:
            print("✅ RFP System Bridge: Connected to LangGraph workflow")
        else:
            print("⚠️ RFP System Bridge: Using fallback mode")
    
    async def generate_proposal(self, user_request: str, memories: Dict[str, Any]) -> str:
        """Generate proposal using your existing RFP system"""
        return await self.rfp_loader.generate_proposal_with_langgraph(user_request, memories)
    
    async def query_technical_team(self, query: str, memories: Dict[str, Any]) -> str:
        """Query technical team using RFP system"""
        if self.agents_available:
            # For technical queries, we can use the same LangGraph workflow
            # but with a technical focus
            technical_query = f"Technical analysis request: {query}"
            response = await self.rfp_loader.generate_proposal_with_langgraph(technical_query, memories)
            return f"🔧 **Technical Team Analysis**\n\n{response}"
        else:
            return """
🔧 **Technical Analysis** *(Fallback Mode)*

**Architecture Recommendations:**
- Scalable microservices architecture
- Cloud-native deployment strategy
- Modern technology stack selection
- Security-first design principles

**Implementation Approach:**
- Containerized application deployment
- CI/CD pipeline setup
- Monitoring and logging integration
- Performance optimization strategies

*Full technical team integration coming soon...*
            """
    
    async def query_finance_team(self, query: str, memories: Dict[str, Any]) -> str:
        """Query finance team using RFP system"""
        if self.agents_available:
            finance_query = f"Financial analysis request: {query}"
            response = await self.rfp_loader.generate_proposal_with_langgraph(finance_query, memories)
            return f"💰 **Finance Team Analysis**\n\n{response}"
        else:
            budget = memories.get('budget_range', 'To be determined') if memories else 'To be determined'
            return f"""
💰 **Financial Analysis** *(Fallback Mode)*

**Budget Overview:** {budget}

**Cost Breakdown:**
- Development: 60-70% of total budget
- Project Management: 10-15%
- Infrastructure & Tools: 10-15%
- Testing & QA: 10-15%

**Payment Structure:**
- Initial deposit: 25%
- Development milestones: 50%
- Final delivery: 25%

*Full finance team integration coming soon...*
            """