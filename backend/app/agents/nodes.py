import os
import logging
from app.agents.state import AgentState
from app.core.llm_router import llm_router
from app.tools.pdf_watchdog import pdf_watchdog_service
from app.tools.obsidian_tool import obsidian_manager
from app.tools.finance_tool import finance_manager
from app.tools.google_workspace import google_workspace_manager

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
    """Agente Investigador: Realiza búsqueda RAG en documentos PDF indexados mediante PyMuPDF / Qdrant"""
    history = state.get("agent_history", [])
    history.append("Investigador: Consultando base RAG y PDFs en /app/data/pdfs")
    
    query = state["user_query"]
    results = pdf_watchdog_service.indexer.search_rag(query)
    
    if results:
        snippets = [f"[{r['file']}]: {r['snippet']}" for r in results]
        context = "Fragmentos RAG encontrados:\n" + "\n".join(snippets)
    else:
        context = f"No se encontraron coincidencias exactas en PDFs para '{query}'."
        
    state["research_context"] = context
    state["agent_history"] = history
    return state

async def obsidian_node(state: AgentState) -> AgentState:
    """Agente Obsidian: Lee/escribe notas Markdown en la bóveda (/app/data/obsidian)"""
    history = state.get("agent_history", [])
    history.append("Obsidian: Inspeccionando bóveda en /app/data/obsidian")
    
    query = state["user_query"]
    notes = obsidian_manager.list_notes()
    
    # Si la consulta pide crear/escribir una nota
    if any(k in query.lower() for k in ["crear", "escribir", "guardar", "agregar"]):
        title = "Nota_Agéntica.md"
        content = f"# Nota Creada por Antigravity\n**Consulta:** {query}\n**Fecha:** 2026-08-17\n"
        obsidian_manager.create_or_update_note(title, content)
        state["obsidian_context"] = f"Nota '{title}' creada exitosamente en la bóveda de Obsidian."
    else:
        search_res = obsidian_manager.search_notes(query)
        if search_res:
            snippets = [f"[{n['title']}]: {n['snippet']}" for n in search_res]
            state["obsidian_context"] = "Notas relevantes encontradas:\n" + "\n".join(snippets)
        else:
            state["obsidian_context"] = f"Notas disponibles en la bóveda ({len(notes)} en total): {notes if notes else 'Bóveda vacía'}"
            
    state["agent_history"] = history
    return state

async def finance_node(state: AgentState) -> AgentState:
    """Agente Finanzas: Procesa archivos Excel/CSV en /app/data/finanzas"""
    history = state.get("agent_history", [])
    history.append("Finanzas: Analizando hojas de cálculo en /app/data/finanzas")
    
    files = finance_manager.list_financial_files()
    if files:
        summary = finance_manager.read_csv_summary(files[0])
        state["finance_context"] = f"Resumen de '{files[0]}': {summary.get('total_registros', 0)} registros, Total sumado: ${summary.get('suma_detectada', 0.0)}"
    else:
        state["finance_context"] = "No se encontraron archivos financieros (.csv) en /app/data/finanzas. Se ha inicializado la estructura de presupuesto."
        
    state["agent_history"] = history
    return state

async def writer_node(state: AgentState) -> AgentState:
    """Agente Redactor Final: Sintetiza los datos recuperados y genera la respuesta con el LLM"""
    history = state.get("agent_history", [])
    history.append("Redactor: Sintetizando respuesta final con el LLM activo")
    
    context_parts = []
    if state.get("research_context"):
        context_parts.append(f"Información de PDFs (RAG):\n{state['research_context']}")
    if state.get("obsidian_context"):
        context_parts.append(f"Información de Obsidian:\n{state['obsidian_context']}")
    if state.get("finance_context"):
        context_parts.append(f"Información Financiera:\n{state['finance_context']}")
        
    context_str = "\n\n".join(context_parts) if context_parts else "No se requirió contexto de herramientas externas."
    
    prompt = f"Consulta del usuario: {state['user_query']}\n\nContexto recuperado:\n{context_str}\n\nResponde de forma clara y ejecutiva."
    system_prompt = "Eres Antigravity, un Asistente Agéntico de Inteligencia Artificial que opera en un nodo Edge distribuido."
    
    res = await llm_router.generate_response(prompt, system_prompt)
    
    state["final_response"] = res["response"]
    state["active_tier"] = res["tier"]
    state["active_model"] = res["model"]
    state["latency_ms"] = res["latency_ms"]
    state["agent_history"] = history
    return state
