from typing import TypedDict, List, Dict, Any, Optional

class PendingAction(TypedDict):
    action_id: str             # Identificador único de la acción propuesta
    agent_name: str            # Nombre del agente solicitante
    tool_name: str             # Nombre de la herramienta a ejecutar
    description: str           # Resumen descriptivo para el usuario
    payload: Dict[str, Any]    # Parámetros de la acción (destinatario, cuerpo, diff o contenido)
    risk_level: str            # "MEDIUM" (modificación local) | "HIGH" (envío externo / borrado)

class AgentState(TypedDict):
    """Estado compartido en el Grafo de LangGraph con soporte para Harness Engineering & HITL"""
    user_query: str
    thread_id: str
    agent_history: List[str]
    current_agent: str
    active_tier: str
    active_model: str
    
    # Contextos de herramientas acumulados
    research_context: Optional[str]
    obsidian_context: Optional[str]
    finance_context: Optional[str]
    email_context: Optional[str]
    
    # Campos de Harness Engineering & Human-In-The-Loop (HITL)
    pending_action: Optional[PendingAction]  # Acción propuesta que requiere validación
    user_approval_status: Optional[str]      # "PENDING" | "APPROVED" | "REJECTED"
    user_approval_feedback: Optional[str]    # Retroalimentación o instrucciones del usuario
    
    final_response: Optional[str]
    latency_ms: float
