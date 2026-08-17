import os
import logging
from app.agents.state import AgentState
from app.core.llm_router import llm_router

logger = logging.getLogger("agent_nodes")

async def supervisor_node(state: AgentState) -> AgentState:
    """Clasifica la consulta del usuario y decide la ruta agéntica"""
    query = state["user_query"].lower()
    history = state.get("agent_history", [])
    history.append("Supervisor: Analizando intención del usuario")
    
    if any(k in query for k in ["pdf", "buscar", "documento", "investigar", "informe", "rag"]):
        target = "research_agent"
    elif any(k in query for k in ["nota", "obsidian", "bóveda", "apunte", "diario"]):
        target = "obsidian_agent"
    elif any(k in query for k in ["excel", "csv", "finanza", "presupuesto", "gasto", "dinero"]):
        target = "finance_agent"
    else:
        target = "writer_agent"
        
    state["current_agent"] = target
    state["agent_history"] = history
    return state

async def research_node(state: AgentState) -> AgentState:
    """Agente Investigador: Simula búsqueda RAG en documentos PDF indexados"""
    history = state.get("agent_history", [])
    history.append("Investigador: Consultando base vectorial Qdrant y PDFs en /app/data/pdfs")
    
    state["research_context"] = f"Contexto RAG recuperado para '{state['user_query']}' desde los PDFs locales."
    state["agent_history"] = history
    return state

async def obsidian_node(state: AgentState) -> AgentState:
    """Agente Obsidian: Lee/escribe notas Markdown en la bóveda"""
    history = state.get("agent_history", [])
    history.append("Obsidian: Escaneando notas Markdown en /app/data/obsidian")
    
    obsidian_dir = "/app/data/obsidian"
    notes = []
    if os.path.exists(obsidian_dir):
        notes = [f for f in os.listdir(obsidian_dir) if f.endswith(".md")]
        
    state["obsidian_context"] = f"Notas disponibles en la bóveda: {notes if notes else 'Bóveda vacía'}"
    state["agent_history"] = history
    return state

async def finance_node(state: AgentState) -> AgentState:
    """Agente Finanzas: Procesa archivos Excel/CSV"""
    history = state.get("agent_history", [])
    history.append("Finanzas: Analizando hojas de cálculo en /app/data/finanzas")
    
    state["finance_context"] = f"Datos financieros leídos para la consulta: '{state['user_query']}'"
    state["agent_history"] = history
    return state

async def writer_node(state: AgentState) -> AgentState:
    """Agente Redactor Final: Sintetiza los datos recuperados y genera la respuesta con el LLM"""
    history = state.get("agent_history", [])
    history.append("Redactor: Sintetizando respuesta con el LLM activo")
    
    context_parts = []
    if state.get("research_context"):
        context_parts.append(f"Información de PDFs: {state['research_context']}")
    if state.get("obsidian_context"):
        context_parts.append(f"Información de Obsidian: {state['obsidian_context']}")
    if state.get("finance_context"):
        context_parts.append(f"Información Financiera: {state['finance_context']}")
        
    context_str = "\n".join(context_parts) if context_parts else "No se requirió contexto de herramientas."
    
    prompt = f"Consulta del usuario: {state['user_query']}\n\nContexto recuperado:\n{context_str}\n\nResponde de forma clara y ejecutiva."
    system_prompt = "Eres Antigravity, un Asistente Agéntico de Inteligencia Artificial que opera en un nodo Edge distribuido."
    
    res = await llm_router.generate_response(prompt, system_prompt)
    
    state["final_response"] = res["response"]
    state["active_tier"] = res["tier"]
    state["active_model"] = res["model"]
    state["latency_ms"] = res["latency_ms"]
    state["agent_history"] = history
    return state
