from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    """Estado compartido en el Grafo de LangGraph"""
    user_query: str
    thread_id: str
    agent_history: List[str]
    current_agent: str
    active_tier: str
    active_model: str
    research_context: Optional[str]
    obsidian_context: Optional[str]
    finance_context: Optional[str]
    final_response: Optional[str]
    latency_ms: float
