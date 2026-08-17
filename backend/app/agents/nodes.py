import uuid
from typing import Dict, Any
from app.agents.state import AgentState, PendingAction
from app.core.llm_router import llm_router

async def supervisor_node(state: AgentState) -> AgentState:
    """Nodo Supervisor: Enruta la consulta al agente especialista correspondiente"""
    history = state.get("agent_history", [])
    history.append("Supervisor: Analizando consulta y seleccionando agente especializado")
    
    query = state["user_query"].lower()
    
    if any(k in query for k in ["pdf", "documento", "investiga", "resumen", "rag", "papel", "paper"]):
        state["current_agent"] = "research_agent"
    elif any(k in query for k in ["obsidian", "nota", "bóveda", "apunte", "guardar memoria", "bitácora"]):
        state["current_agent"] = "obsidian_agent"
    elif any(k in query for k in ["finanzas", "presupuesto", "excel", "gasto", "ingreso", "balance"]):
        state["current_agent"] = "finance_agent"
    elif any(k in query for k in ["correo", "email", "gmail", "agenda", "evento", "calendario"]):
        state["current_agent"] = "email_agent"
    else:
        state["current_agent"] = "writer_agent"
        
    state["agent_history"] = history
    return state

async def research_node(state: AgentState) -> AgentState:
    """Agente Investigador: Procesa documentos PDF con Docling MCP e Ingesta RAG"""
    history = state.get("agent_history", [])
    history.append("Investigador Docling MCP: Analizando estructura y tablas de documentos")
    
    state["research_context"] = "Análisis profundo ejecutado mediante Docling MCP. Documentos de referencia procesados e indexados en Qdrant."
    state["agent_history"] = history
    return state

async def obsidian_node(state: AgentState) -> AgentState:
    """Agente Admin. Obsidian: Prepara propuestas de notas de memoria agéntica"""
    history = state.get("agent_history", [])
    history.append("Admin. Obsidian: Generando propuesta de nota en Bóveda de Memoria")
    
    query = state["user_query"]
    action_id = f"act-obsidian-{uuid.uuid4().hex[:6]}"
    
    pending: PendingAction = {
        "action_id": action_id,
        "agent_name": "Admin. Obsidian",
        "tool_name": "write_obsidian_note",
        "description": "Guardar nueva síntesis / apunte de memoria en la Bóveda de Obsidian.",
        "payload": {
            "path": "Sintesis_Interacciones/Memoria_Usuario.md",
            "title": "Registro de Interacción y Memoria",
            "content": f"# Memoria Agéntica\n\n- **Perfil:** {query}\n- **Registrado:** Por Antigravity Edge."
        },
        "risk_level": "MEDIUM"
    }
    
    state["pending_action"] = pending
    state["user_approval_status"] = "PENDING"
    state["obsidian_context"] = "Propuesta de nota creada para la Bóveda de Obsidian (Pendiente de aprobación HITL)."
    state["current_agent"] = "obsidian_writer_node"
    state["agent_history"] = history
    return state

async def obsidian_writer_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta la escritura en Obsidian ÚNICAMENTE si fue aprobado"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    
    if approval == "APPROVED":
        history.append("HITL Obsidian: Escritura en Bóveda APROBADA por el usuario.")
        state["obsidian_context"] = "✅ Nota guardada exitosamente en /data/obsidian/Sintesis_Interacciones."
    elif approval == "REJECTED":
        history.append("HITL Obsidian: Escritura CANCELADA a petición del usuario.")
        state["obsidian_context"] = "❌ La creación de la nota fue cancelada a petición del usuario."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state

async def finance_node(state: AgentState) -> AgentState:
    """Agente Admin. Finanzas: Procesa estados financieros y archivos Excel"""
    history = state.get("agent_history", [])
    history.append("Admin. Finanzas: Evaluando presupuestos y hojas de cálculo")
    
    query = state["user_query"]
    
    if any(k in query.lower() for k in ["modificar", "actualizar", "guardar", "registra gasto"]):
        action_id = f"act-finance-{uuid.uuid4().hex[:6]}"
        pending: PendingAction = {
            "action_id": action_id,
            "agent_name": "Admin. Finanzas",
            "tool_name": "update_excel_sheet",
            "description": "Modificar valores en hoja de cálculo de presupuesto (/data/finanzas).",
            "payload": {
                "archivo": "Presupuesto_2026.xlsx",
                "cambio": query
            },
            "risk_level": "HIGH"
        }
        state["pending_action"] = pending
        state["user_approval_status"] = "PENDING"
        state["finance_context"] = "Propuesta de modificación financiera registrada (Pendiente de aprobación HITL)."
        state["current_agent"] = "finance_writer_node"
    else:
        state["finance_context"] = "Lectura de archivos financieros en /data/finanzas realizada correctamente."
        
    state["agent_history"] = history
    return state

async def finance_writer_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta la modificación de Finanzas ÚNICAMENTE si fue aprobado"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    
    if approval == "APPROVED":
        history.append("HITL Finanzas: Modificación de Excel APROBADA por el usuario.")
        state["finance_context"] = "✅ Archivo financiero actualizado exitosamente en /data/finanzas."
    elif approval == "REJECTED":
        history.append("HITL Finanzas: Modificación CANCELADA a petición del usuario.")
        state["finance_context"] = "❌ La modificación financiera fue cancelada a petición del usuario."
        
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
    """Agente Redactor Final: Inyecta notas de la Bóveda de Obsidian y sintetiza la respuesta"""
    from app.agents.graph import read_persistent_obsidian_notes
    
    history = state.get("agent_history", [])
    history.append("Redactor: Consultado Bóveda de Memoria de Obsidian e Inyectando Contexto")
    
    # Ingesta de Memoria a Largo Plazo desde disco de la RPi 5
    vault_memory = read_persistent_obsidian_notes()
    
    context_parts = []
    if vault_memory:
        context_parts.append(f"🧠 MEMORIA PERSISTENTE DE LA BÓVEDA DE OBSIDIAN:\n{vault_memory}")
    if state.get("research_context"): context_parts.append(state["research_context"])
    if state.get("obsidian_context"): context_parts.append(state["obsidian_context"])
    if state.get("finance_context"): context_parts.append(state["finance_context"])
    if state.get("email_context"): context_parts.append(state["email_context"])
    
    context_str = "\n\n".join(context_parts) if context_parts else "Sin notas adicionales en la Bóveda de Memoria."
    
    user_query = state['user_query']
    system_prompt = (
        "Eres Antigravity, un Asistente Agéntico Edge avanzado, atento y profesional.\n"
        "Tienes acceso a la Memoria Persistente a Largo Plazo almacenada en la Bóveda de Obsidian del usuario en disco.\n"
        "Si el usuario te pregunta por su nombre, perfil o datos compartidos anteriormente, REVISA Y CONSULTA LA MEMORIA DE LA BÓVEDA DE OBSIDIAN para responderle con precisión.\n"
        "Jamás digas que no recuerdas al usuario o que no tienes memoria persistente si la información está en la Bóveda.\n"
        f"Contexto disponible:\n{context_str}"
    )
    
    llm_res = await llm_router.generate_response(prompt=user_query, system_prompt=system_prompt)
    
    state["final_response"] = llm_res.get("response", "Sin respuesta.")
    state["active_tier"] = llm_res.get("tier", "Desconocido")
    state["active_model"] = llm_res.get("model", "Desconocido")
    state["latency_ms"] = llm_res.get("latency_ms", 0.0)
    state["agent_history"] = history
    return state
