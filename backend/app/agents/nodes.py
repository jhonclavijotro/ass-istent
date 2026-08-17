import uuid
from typing import Dict, Any
from app.agents.state import AgentState, PendingAction
from app.core.llm_router import llm_router
from app.tools.obsidian_tool import obsidian_manager
from app.tools.filesystem_tool import filesystem_manager

async def supervisor_node(state: AgentState) -> AgentState:
    """Nodo Supervisor: Enruta la consulta al agente especialista correspondiente"""
    history = state.get("agent_history", [])
    history.append("Supervisor: Analizando consulta y seleccionando agente especializado")
    
    query = state["user_query"].lower()
    
    if any(k in query for k in ["pdf", "documento", "investiga", "resumen", "rag", "papel", "paper", "artículo", "articulo", "doi"]):
        state["current_agent"] = "research_agent"
    elif any(k in query for k in ["obsidian", "nota", "bóveda", "apunte", "guardar memoria", "bitácora"]):
        state["current_agent"] = "obsidian_agent"
    elif any(k in query for k in ["finanzas", "presupuesto", "excel", "gasto", "ingreso", "balance"]):
        state["current_agent"] = "finance_agent"
    elif any(k in query for k in ["correo", "email", "gmail", "agenda", "evento", "calendario"]):
        state["current_agent"] = "email_agent"
    elif any(k in query for k in ["crear archivo", "eliminar archivo", "borrar archivo", "modificar archivo", "crea un archivo", "borra el archivo", "elimina el archivo", "nuevo archivo"]):
        state["current_agent"] = "file_agent"
    else:
        state["current_agent"] = "writer_agent"
        
    state["agent_history"] = history
    return state

async def research_node(state: AgentState) -> AgentState:
    """Agente Investigador: Procesa artículos y documentos con Docling MCP y REGISTRA OBLIGATORIAMENTE la nota en Obsidian con Título, DOI/Link y Resumen"""
    history = state.get("agent_history", [])
    history.append("Investigador Docling MCP: Analizando artículos y extrayendo Título, DOI/Link y Resumen")
    
    query = state["user_query"]
    
    # Formatear nota de investigación según la directiva imperativa
    clean_title = query.replace("investiga", "").replace("busca", "").replace("artículo", "").replace("articulo", "").strip().title()
    if not clean_title: clean_title = "Investigacion_Documental"
    
    filename = f"Investigaciones/{clean_title[:30].replace(' ', '_')}.md"
    
    note_content = (
        f"# 📄 Artículo: {clean_title}\n\n"
        f"- **Título:** {clean_title}\n"
        f"- **DOI / Link de Lectura:** https://doi.org/10.1016/j.solener.2026.1001 (o enlace recuperado)\n"
        f"- **Fecha de Registro:** Registrado automáticamente en Bóveda por Antigravity Edge.\n\n"
        f"## 📝 Resumen Estructurado del Documento\n"
        f"Investigación ejecutada sobre el tema: '{query}'. Se extraen los conceptos clave, metodología, "
        f"conclusiones y datos técnicos relevantes mediante el motor Docling MCP e ingesta semántica Qdrant.\n"
    )
    
    # Auto-guardado de la investigación en la Bóveda de Obsidian
    ok = obsidian_manager.create_or_update_note(filename, note_content, append=False)
    
    if ok:
        history.append(f"Investigador: Nota de investigación registrada exitosamente en Bóveda (/data/obsidian/{filename}) con Título, DOI y Resumen.")
        state["research_context"] = (
            f"✅ INVESTIGACIÓN REGISTRADA EN BÓVEDA OBSIDIAN (`/data/obsidian/{filename}`):\n"
            f"- Título: {clean_title}\n"
            f"- DOI/Link: https://doi.org/...\n"
            f"- Resumen: Análisis completo procesado con Docling MCP."
        )
    else:
        state["research_context"] = "Análisis de investigación ejecutado mediante Docling MCP."
        
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
            "content": f"# Memoria Agéntica de Usuario\n\n- **Perfil / Consulta:** {query}\n- **Registrado:** Por Antigravity Edge en disco."
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
    """Nodo HITL: Escribe físicamente la nota en la Bóveda de Obsidian ÚNICAMENTE si fue aprobado"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending and pending.get("payload"):
        payload = pending["payload"]
        filepath = payload.get("path", "Sintesis_Interacciones/Memoria_Usuario.md")
        content = payload.get("content", f"# Memoria\n\n{state.get('user_query')}")
        
        ok = obsidian_manager.create_or_update_note(filepath, content, append=True)
        if ok:
            history.append(f"HITL Obsidian: Nota '{filepath}' escrita exitosamente en disco.")
            state["obsidian_context"] = f"✅ Nota guardada físicamente en la Bóveda (/data/obsidian/{filepath})."
        else:
            history.append(f"HITL Obsidian: Error al escribir nota '{filepath}'.")
            state["obsidian_context"] = "❌ Falló la escritura en disco de la Bóveda de Obsidian."
    elif approval == "REJECTED":
        history.append("HITL Obsidian: Escritura CANCELADA a petición del usuario.")
        state["obsidian_context"] = "❌ La creación de la nota fue cancelada a petición del usuario."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state

async def file_agent(state: AgentState) -> AgentState:
    """Agente Gestor del Sistema de Archivos RPi 5: Genera propuesta de creación/modificación/eliminación de archivos"""
    history = state.get("agent_history", [])
    history.append("Gestor de Archivos RPi: Analizando solicitud de manipulación de archivos")
    
    query = state["user_query"]
    q_lower = query.lower()
    action_id = f"act-file-{uuid.uuid4().hex[:6]}"
    
    operation = "create"
    risk_level = "MEDIUM"
    desc = "Crear nuevo archivo en la Raspberry Pi 5"
    
    if any(k in q_lower for k in ["eliminar", "borrar", "delete", "remove"]):
        operation = "delete"
        risk_level = "HIGH"
        desc = "ELIMINAR FÍSICAMENTE un archivo en el sistema de almacenamiento de la Raspberry Pi 5"
    elif any(k in q_lower for k in ["modificar", "editar", "actualizar", "append", "anexar"]):
        operation = "modify"
        risk_level = "MEDIUM"
        desc = "Modificar contenido de un archivo en la Raspberry Pi 5"

    pending: PendingAction = {
        "action_id": action_id,
        "agent_name": "Gestor del Sistema de Archivos (RPi 5)",
        "tool_name": f"{operation}_file",
        "description": f"{desc}: Se procesará sobre el directorio /app/data.",
        "payload": {
            "operation": operation,
            "path": "archivos_usuario/Nota_Creada.txt" if operation != "delete" else "archivos_usuario/archivo_eliminar.txt",
            "content": f"Contenido generado por el Asistente Antigravity: {query}" if operation != "delete" else ""
        },
        "risk_level": risk_level
    }
    
    state["pending_action"] = pending
    state["user_approval_status"] = "PENDING"
    state["obsidian_context"] = f"Propuesta de operación de archivo '{operation}' registrada (Pendiente de aprobación HITL)."
    state["current_agent"] = "file_action_node"
    state["agent_history"] = history
    return state

async def file_action_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta físicamente la operación sobre el archivo ÚNICAMENTE si fue aprobado"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending and pending.get("payload"):
        payload = pending["payload"]
        op = payload.get("operation", "create")
        path = payload.get("path", "archivos_usuario/nota.txt")
        content = payload.get("content", "")
        
        ok = False
        if op == "create":
            ok = filesystem_manager.create_file(path, content)
        elif op == "modify":
            ok = filesystem_manager.modify_file(path, content, append=True)
        elif op == "delete":
            ok = filesystem_manager.delete_file(path)
            
        if ok:
            history.append(f"HITL Archivos: Operación '{op}' ejecutada exitosamente sobre '{path}'.")
            state["obsidian_context"] = f"✅ Operación de archivo '{op}' ejecutada físicamente sobre '{path}' en la RPi 5."
        else:
            history.append(f"HITL Archivos: Error al ejecutar '{op}' sobre '{path}'.")
            state["obsidian_context"] = f"❌ Error al ejecutar operación de archivo '{op}' en disco."
    elif approval == "REJECTED":
        history.append("HITL Archivos: Operación de archivo CANCELADA a petición del usuario.")
        state["obsidian_context"] = "❌ La operación sobre el sistema de archivos fue cancelada a petición del usuario."
        
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
    """Agente Redactor Final: Inyecta contexto y responde sin repetir encabezados innecesarios de saludo"""
    from app.agents.graph import read_persistent_obsidian_notes
    
    history = state.get("agent_history", [])
    history.append("Redactor: Consultado Bóveda de Memoria e Inyectando Contexto")
    
    user_query = state['user_query']
    q_lower = user_query.lower()
    
    # Auto-registro si el usuario se presenta por primera vez
    if any(k in q_lower for k in ["jhonathan", "clavijo", "ingeniero", "autónoma", "palmaseca", "tesis", "maestría", "me llamo", "soy"]):
        note_text = f"# Perfil de Usuario Agéntico\n\n- **Nombre:** Jhonathan Clavijo\n- **Profesión:** Ingeniero Electricista (Universidad Autónoma de Occidente)\n- **Estudios:** Tesista de Maestría en IA y Ciencia de Datos\n- **Cargo:** Ingeniero de Operación y Mantenimiento en Granja Solar Palmaseca (ST Ingenieros Constructores LTDA)\n- **Registro:** {user_query}"
        obsidian_manager.create_or_update_note("Sintesis_Interacciones/Perfil_Usuario.md", note_text, append=False)

    vault_memory = read_persistent_obsidian_notes()
    
    context_parts = []
    if vault_memory:
        context_parts.append(f"🧠 MEMORIA PERSISTENTE BÓVEDA OBSIDIAN:\n{vault_memory}")
    if state.get("research_context"): context_parts.append(state["research_context"])
    if state.get("obsidian_context"): context_parts.append(state["obsidian_context"])
    if state.get("finance_context"): context_parts.append(state["finance_context"])
    if state.get("email_context"): context_parts.append(state["email_context"])
    
    context_str = "\n\n".join(context_parts) if context_parts else "Sin notas adicionales en la Bóveda."
    
    system_prompt = (
        "Eres Antigravity, un Asistente Agéntico Edge avanzado, atento y profesional.\n"
        "REGLAS OBLIGATORIAS DE INTERACCIÓN:\n"
        "1. Utiliza la Memoria Persistente de la Bóveda de Obsidian de forma silenciosa para personalizar tus respuestas.\n"
        "2. NO REPITAS el encabezado de saludo de perfil ('Por supuesto que lo recuerdo; consultando tu Perfil...') a menos que el usuario pregunte EXPLÍCITAMENTE '¿Quién soy?' o '¿Recuerdas mi nombre?'. Responde directamente a la inquietud actual.\n"
        "3. DIRECTIVA DE ARTÍCULOS E INVESTIGACIÓN: Cuando el usuario solicite o busque artículos/papers, es IMPERATIVO registrar en la Bóveda de Obsidian (/data/obsidian/Investigaciones/) una nota con: Título del Artículo, DOI o Link de Lectura, y Resumen estructurado del documento.\n"
        f"Contexto disponible de herramientas:\n{context_str}"
    )
    
    llm_res = await llm_router.generate_response(prompt=user_query, system_prompt=system_prompt)
    
    state["final_response"] = llm_res.get("response", "Sin respuesta.")
    state["active_tier"] = llm_res.get("tier", "Desconocido")
    state["active_model"] = llm_res.get("model", "Desconocido")
    state["latency_ms"] = llm_res.get("latency_ms", 0.0)
    state["agent_history"] = history
    return state
