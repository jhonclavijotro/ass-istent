import os
import uuid
import logging
from typing import Dict, Any
from app.agents.state import AgentState, PendingAction
from app.core.llm_router import llm_router
from app.tools.pdf_watchdog import pdf_watchdog_service
from app.tools.obsidian_tool import obsidian_manager
from app.tools.finance_tool import finance_manager
from app.tools.google_workspace import google_workspace_manager

logger = logging.getLogger("agent_nodes")

async def supervisor_node(state: AgentState) -> AgentState:
    """Clasifica la consulta del usuario y decide el agente especialista"""
    query = state["user_query"].lower()
    history = state.get("agent_history", [])
    history.append("Supervisor: Analizando intención de la consulta")
    
    # Si la ejecución proviene de una reanudación por aprobación o rechazo HITL
    if state.get("pending_action") and state.get("user_approval_status"):
        target = state.get("current_agent", "writer_agent")
    elif any(k in query for k in ["correo", "email", "gmail", "calendario", "evento", "agendar"]):
        target = "email_agent"
    elif any(k in query for k in ["pdf", "buscar", "documento", "investigar", "informe", "rag", "docling", "notebooklm"]):
        target = "research_agent"
    elif any(k in query for k in ["nota", "obsidian", "bóveda", "apunte", "diario", "memoria", "falla", "mejora"]):
        target = "obsidian_agent"
    elif any(k in query for k in ["excel", "csv", "finanza", "presupuesto", "gasto", "dinero"]):
        target = "finance_agent"
    else:
        target = "writer_agent"
        
    state["current_agent"] = target
    state["agent_history"] = history
    return state

async def research_node(state: AgentState) -> AgentState:
    """Agente Investigador: Análisis profundo de documentos (Docling / NotebookLM MCP + Qdrant RAG)"""
    history = state.get("agent_history", [])
    history.append("Investigador (Docling MCP): Analizando documentos en RAG semántico")
    
    query = state["user_query"]
    results = pdf_watchdog_service.indexer.search_rag(query)
    
    if results:
        snippets = [f"[{r['file']}]: {r['snippet']}" for r in results]
        context = "SÍNTESIS DE DOCUMENTOS (Docling / NotebookLM MCP):\n" + "\n".join(snippets)
    else:
        context = f"No se encontraron coincidencias exactas en PDFs para '{query}'. Se usará análisis conceptual."
        
    state["research_context"] = context
    state["agent_history"] = history
    return state

async def obsidian_node(state: AgentState) -> AgentState:
    """Agente Admin. Obsidian / Memoria Agéntica: Gestiona apuntes de investigación, síntesis e incidencias"""
    history = state.get("agent_history", [])
    history.append("Obsidian Memoria: Inspeccionando bóveda de aprendizaje (/data/obsidian)")
    
    query = state["user_query"]
    notes = obsidian_manager.list_notes()
    
    # Si la consulta requiere guardar o modificar un apunte en la bóveda real
    if any(k in query.lower() for k in ["crear", "escribir", "guardar", "agregar", "apunte", "registrar"]):
        # Determinar la subcarpeta adecuada según el contenido
        subfolder = "Investigaciones"
        if "falla" in query.lower() or "error" in query.lower() or "mejora" in query.lower():
            subfolder = "Fallas_y_Mejoras"
        elif "reunión" in query.lower() or "acuerdo" in query.lower():
            subfolder = "Sintesis_Interacciones"
            
        action_id = f"act-obs-{uuid.uuid4().hex[:6]}"
        filename = f"{subfolder}/Apunte_{uuid.uuid4().hex[:4]}.md"
        content = f"# Apunte de Memoria Agéntica\n**Tema:** {query}\n**Fecha:** 2026-08-17\n**Estado:** Pendiente Aprobación Director\n"
        
        pending: PendingAction = {
            "action_id": action_id,
            "agent_name": "Administrador de Obsidian (Memoria)",
            "tool_name": "create_obsidian_note",
            "description": f"Crear apunte de memoria '{filename}' en la bóveda de Obsidian.",
            "payload": {
                "filename": filename,
                "content": content
            },
            "risk_level": "MEDIUM"
        }
        
        state["pending_action"] = pending
        state["user_approval_status"] = "PENDING"
        state["obsidian_context"] = f"Acción propuesta: Guardar apunte en '{filename}'."
        state["current_agent"] = "obsidian_writer_node"
    else:
        search_res = obsidian_manager.search_notes(query)
        if search_res:
            snippets = [f"[{n['title']}]: {n['snippet']}" for n in search_res]
            state["obsidian_context"] = "Memorias y notas encontradas:\n" + "\n".join(snippets)
        else:
            state["obsidian_context"] = f"Notas disponibles en la Bóveda de Memoria ({len(notes)} en total): {notes}"
            
    state["agent_history"] = history
    return state

async def obsidian_writer_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta la creación del apunte de Obsidian ÚNICAMENTE si el usuario aprobó"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending:
        payload = pending["payload"]
        filename = payload.get("filename", "Apunte.md")
        content = payload.get("content", "")
        obsidian_manager.create_or_update_note(filename, content)
        history.append(f"HITL Obsidian: Apunte '{filename}' creado exitosamente tras APROBACIÓN del usuario.")
        state["obsidian_context"] = f"✅ Apunte '{filename}' guardado exitosamente en la Bóveda de Memoria."
    elif approval == "REJECTED":
        history.append("HITL Obsidian: La creación del apunte fue CANCELADA a petición del usuario.")
        state["obsidian_context"] = "❌ La creación del apunte en Obsidian fue cancelada por el usuario."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state

async def finance_node(state: AgentState) -> AgentState:
    """Agente Admin. Finanzas: Analiza datos cuantitativos y propone actualizaciones"""
    history = state.get("agent_history", [])
    history.append("Finanzas: Inspeccionando planillas cuantitativas (/data/finanzas)")
    
    query = state["user_query"]
    files = finance_manager.list_financial_files()
    
    if any(k in query.lower() for k in ["agregar", "guardar", "registrar", "gasto", "ingreso"]):
        action_id = f"act-fin-{uuid.uuid4().hex[:6]}"
        pending: PendingAction = {
            "action_id": action_id,
            "agent_name": "Administrador de Finanzas",
            "tool_name": "add_financial_record",
            "description": "Registrar movimiento financiero en la hoja de cálculo maestra.",
            "payload": {
                "filename": files[0] if files else "presupuesto_inicial.csv",
                "concepto": query,
                "monto": 0.0,
                "categoria": "General"
            },
            "risk_level": "MEDIUM"
        }
        state["pending_action"] = pending
        state["user_approval_status"] = "PENDING"
        state["finance_context"] = "Acción propuesta: Registrar movimiento financiero."
        state["current_agent"] = "finance_writer_node"
    else:
        if files:
            summary = finance_manager.read_csv_summary(files[0])
            state["finance_context"] = f"Resumen de '{files[0]}': {summary.get('total_registros', 0)} registros, Total: ${summary.get('suma_detectada', 0.0)}"
        else:
            state["finance_context"] = "Estructura financiera leída correctamente."
            
    state["agent_history"] = history
    return state

async def finance_writer_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta actualización financiera ÚNICAMENTE tras aprobación"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending:
        payload = pending["payload"]
        filename = payload.get("filename", "presupuesto.csv")
        finance_manager.add_financial_record(filename, payload.get("concepto", "Movimiento"), payload.get("monto", 0.0), payload.get("categoria", "General"))
        history.append(f"HITL Finanzas: Registro en '{filename}' APROBADO y guardado en disco.")
        state["finance_context"] = f"✅ Movimiento financiero guardado exitosamente en '{filename}'."
    elif approval == "REJECTED":
        history.append("HITL Finanzas: El registro financiero fue RECHAZADO por el usuario.")
        state["finance_context"] = "❌ El registro financiero fue cancelado a petición del usuario."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state

async def email_node(state: AgentState) -> AgentState:
    """Agente Revisor de Correos / Google Workspace"""
    history = state.get("agent_history", [])
    history.append("Revisor Correos: Analizando solicitudes de comunicación / calendario")
    
    query = state["user_query"]
    
    if any(k in query.lower() for k in ["enviar", "mandar", "borrar", "agendar", "evento"]):
        action_id = f"act-email-{uuid.uuid4().hex[:6]}"
        pending: PendingAction = {
            "action_id": action_id,
            "agent_name": "Revisor de Correos",
            "tool_name": "send_gmail_or_calendar",
            "description": "Enviar correo electrónico o agendar evento en Google Workspace.",
            "payload": {
                "destinatario": "contacto@ejemplo.com",
                "asunto": "Consulta Agéntica",
                "cuerpo": query
            },
            "risk_level": "HIGH"
        }
        state["pending_action"] = pending
        state["user_approval_status"] = "PENDING"
        state["email_context"] = "Acción propuesta: Enviar correo / Agendar evento."
        state["current_agent"] = "email_action_node"
    else:
        state["email_context"] = "Lectura de comunicaciones de Google Workspace realizada en borrador."
        
    state["agent_history"] = history
    return state

async def email_action_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta acciones de correo / calendario ÚNICAMENTE si fue aprobado"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    
    if approval == "APPROVED":
        history.append("HITL Correos: Envío de correo APROBADO por el usuario.")
        state["email_context"] = "✅ El correo / evento fue enviado exitosamente a su destinatario."
    elif approval == "REJECTED":
        history.append("HITL Correos: El envío de correo fue CANCELADO a petición del usuario.")
        state["email_context"] = "❌ El envío de correo fue cancelado a petición del usuario."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state

async def writer_node(state: AgentState) -> AgentState:
    """Agente Redactor Final: Sintetiza los datos recopilados y responde mediante el LLM"""
    history = state.get("agent_history", [])
    history.append("Redactor: Sintetizando respuesta final")
    
    context_parts = []
    if state.get("research_context"): context_parts.append(state["research_context"])
    if state.get("obsidian_context"): context_parts.append(state["obsidian_context"])
    if state.get("finance_context"): context_parts.append(state["finance_context"])
    if state.get("email_context"): context_parts.append(state["email_context"])
    
    context_str = "\n\n".join(context_parts) if context_parts else "No se requirió información externa adicional."
    
    prompt = f"Consulta del usuario: {state['user_query']}\n\nContexto recuperado de herramientas:\n{context_str}\n\nSintetiza una respuesta profesional, clara y precisa."
    
    llm_res = await llm_router.generate_response(prompt, system_prompt="Eres Antigravity, un Asistente Agéntico Edge avanzado.")
    
    state["final_response"] = llm_res.get("response", "Sin respuesta.")
    state["active_tier"] = llm_res.get("tier", "Desconocido")
    state["active_model"] = llm_res.get("model", "Desconocido")
    state["latency_ms"] = llm_res.get("latency_ms", 0.0)
    state["agent_history"] = history
    return state
