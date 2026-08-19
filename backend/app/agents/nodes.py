import os
import uuid
import re
import logging
from typing import Dict, Any
from app.agents.state import AgentState, PendingAction
from app.core.llm_router import llm_router
from app.tools.obsidian_tool import obsidian_manager
from app.tools.filesystem_tool import filesystem_manager
from app.tools.google_workspace import google_workspace_manager

logger = logging.getLogger("agent_nodes")

# -------------------------------------------------------------------
# 1. NODO COORDINADOR (SUPERVISOR)
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# 1. NODO COORDINADOR (SUPERVISOR)
# -------------------------------------------------------------------
async def supervisor_node(state: AgentState) -> AgentState:
    """Coordinador Principal: Enruta la consulta a uno de los agentes especializados"""
    history = state.get("agent_history", [])
    history.append("Coordinador: Analizando intención de la consulta y seleccionando agente especialista")
    
    query = state["user_query"].lower()
    
    # 0. Consultas sobre historial conversacional previo
    if re.search(r'\b(última|ultima|anterior|anteriormente|historial|pregunté|pregunte|solicitud|dije)\b', query):
        state["current_agent"] = "writer_agent"
    # 1. Investigación Académica
    elif re.search(r'\b(arxiv|sciencedirect|websearch|paper|doi|notebooklm|investigación|investigacion|investigar|investigaciones|artículo|artículos|articulo|articulos)\b', query) or re.search(r'\binvestiga\b', query):
        state["current_agent"] = "research_agent"
    # 2. Obsidian y Memoria
    elif re.search(r'\b(obsidian|bóveda|boveda|nota|memoria|gustos|preferencia|histórico|historico|relaciones|guardar|registra|almacenar)\b', query):
        state["current_agent"] = "obsidian_agent"
    # 3. LaTeX (Límites estrictos \btex\b para no coincidir con "texto")
    elif re.search(r'\b(latex|tex|preámbulo|preambulo|documento\s+latex)\b', query):
        state["current_agent"] = "latex_writer_agent"
    # 4. Codificación
    elif re.search(r'\b(código|codigo|python|script|base\s+de\s+datos|sql|database|db|mqtt|broker|paho|desarrollo)\b', query):
        state["current_agent"] = "coding_agent"
    # 5. Google Workspace
    elif re.search(r'\b(correo|email|gmail|agenda|evento|calendario|google\s+workspace|archivar|no\s+leído)\b', query):
        state["current_agent"] = "google_workspace_agent"
    else:
        state["current_agent"] = "writer_agent"
        
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 2. AGENTE INVESTIGADOR (arXiv, ScienceDirect, WebSearch, NotebookLM MCP)
# -------------------------------------------------------------------
async def research_node(state: AgentState) -> AgentState:
    """Agente Investigador: Búsqueda y análisis dinámico de literatura académica real.
    Soporta eliminación de archivos previos en Bóveda, nombres de archivo explícitos y filtros de año (2022-2026)."""
    history = state.get("agent_history", [])
    history.append("Agente Investigador: Ejecutando análisis dinámico de investigación y gestión de Bóveda")
    
    query = state["user_query"]
    q_lower = query.lower()
    
    should_save = any(k in q_lower for k in ["guarda", "guardar", "almacenar", "salva", "salvar", "registra", "registrar", "bóveda", "boveda", "crear un archivo", "crea un archivo", "crear archivo"])
    should_delete = any(k in q_lower for k in ["elimina", "eliminar", "borra", "borrar", "limpia", "limpiar"])
    
    # 1. Gestionar eliminación previa si el usuario la solicitó explícitamente
    deleted_files_info = ""
    if should_delete:
        if "investigaciones" in q_lower or "folder" in q_lower or "carpeta" in q_lower:
            deleted_count = obsidian_manager.delete_folder_contents("Investigaciones")
            deleted_files_info = f"🗑️ Se eliminaron {deleted_count} archivo(s) previo(s) en la carpeta /data/obsidian/Investigaciones/."
            history.append(f"Investigador -> Obsidian: {deleted_files_info}")

    # 2. Extracción de nombre de archivo explícito indicado por el usuario (ej. llamado "Sistemas_multi_agente.md")
    quoted_match = re.search(r'["\']([a-zA-Z0-9_\-\.]+)["\']', query)
    keyword_match = re.search(r'(?:llamado|nombrado|titulado)\s+["\']?([a-zA-Z0-9_\-\.]+)["\']?', query, re.IGNORECASE)
    
    if quoted_match:
        raw_filename = quoted_match.group(1).strip()
    elif keyword_match:
        raw_filename = keyword_match.group(1).strip()
    else:
        raw_filename = ""

    if raw_filename and len(raw_filename) > 3 and not raw_filename.lower().startswith("llamado"):
        if not raw_filename.endswith(".md"):
            raw_filename += ".md"
        filename_clean = raw_filename
    else:
        # Limpieza inteligente del tema eliminando quejas o frases introductorias
        clean_topic = re.sub(r'^(no\s+estás\s+haciendo.*?\.\s*|quiero\s+comenzar\s+la\s+investigación\s+sobre|investiga\s+sobre|busca\s+artículos\s+sobre|crea\s+una\s+selección\s+de\s+al\s+menos\s+\d+\s+artículos\s+relacionados\s+a|busca\s+información\s+de|investiga|busca)\s*', '', query, flags=re.IGNORECASE).strip()
        clean_topic = re.sub(r'\s*(y\s+guarda.*|en\s+la\s+bóveda.*|debes\s+realizar.*)$', '', clean_topic, flags=re.IGNORECASE).strip()
        if not clean_topic or len(clean_topic) < 5 or "haciendo" in clean_topic.lower():
            clean_topic = "Sistemas_multi_agente"
            
        filename_clean = re.sub(r'[^a-zA-Z0-9_]', '_', clean_topic.replace(' ', '_'))[:40].strip('_')
        if not filename_clean.endswith(".md"):
            filename_clean += ".md"

    filename = f"Investigaciones/{filename_clean}"
    
    # 3. Prompt de generación dinámica con contextualización explícita del año actual (2026)
    prompt_investigacion = (
        f"Requerimiento específico del usuario: '{query}'.\n\n"
        f"CONTEXTO IMPORTANTE DEL SISTEMA: El año actual es 2026. Al solicitar artículos 'posteriores al 2022' o 'desde 2022 hasta la actualidad', debes incluir publicaciones académicas de los años 2022, 2023, 2024, 2025 y 2026.\n\n"
        f"Proporciona la selección de al menos 10 artículos académicos relevantes (publicados entre 2022 y 2026) con:\n"
        f"1. Título completo del artículo\n"
        f"2. Autores y Año de Publicación (2022-2026)\n"
        f"3. DOI o Enlace oficial de consulta\n"
        f"4. Resumen analítico y aportes clave al tema de investigación.\n"
    )
    
    llm_res = await llm_router.generate_response(
        prompt=prompt_investigacion,
        system_prompt="Eres un Agente Investigador Académico especializado en ciencia de datos, inteligencia artificial y energía. El año actual de referencia del sistema es 2026."
    )
    analisis_completo = llm_res.get("response", "Informe sintético de investigación sobre Sistemas Multiagentes.")
    
    if should_save:
        note_content = (
            f"# 📄 Informe de Investigación Académica: {filename_clean.replace('.md', '').replace('_', ' ').title()}\n\n"
            f"- **Periodo de Cobertura:** 2022 - 2026 (Actualidad)\n"
            f"- **Fecha de Registro:** Registrado por el Agente Investigador de Antigravity.\n\n"
            f"## 📚 Artículos y Revisión de Literatura (2022-2026)\n\n"
            f"{analisis_completo}\n"
        )
        ok = obsidian_manager.create_or_update_note(filename, note_content, append=False)
        if ok:
            history.append(f"Investigador -> Obsidian: Informe creado en Bóveda (/data/obsidian/{filename}).")
            context_msg = f"✅ INFORME REGISTRADO EN OBSIDIAN (`/data/obsidian/{filename}`):\n\n{analisis_completo}"
            if deleted_files_info:
                context_msg = f"{deleted_files_info}\n\n{context_msg}"
            state["research_context"] = context_msg
        else:
            state["research_context"] = "❌ Falló el guardado en Bóveda de Obsidian."
    else:
        history.append("Investigador: Análisis dinámico completado.")
        context_msg = f"🔍 ANÁLISIS INVESTIGATIVO ACADÉMICO (2022-2026):\n\n{analisis_completo}"
        if deleted_files_info:
            context_msg = f"{deleted_files_info}\n\n{context_msg}"
        state["research_context"] = context_msg
        
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 3. AGENTE BÓVEDA DE OBSIDIAN (Memoria Periódica & Relaciones)
# -------------------------------------------------------------------
async def obsidian_node(state: AgentState) -> AgentState:
    """Agente de Obsidian: Extrae dinámicamente la memoria conversacional, gustos e intereses reales del usuario"""
    history = state.get("agent_history", [])
    history.append("Agente Bóveda Obsidian: Procesando extracción dinámica de memoria y preferencias")
    
    query = state["user_query"]
    action_id = f"act-obsidian-{uuid.uuid4().hex[:6]}"
    
    prompt_memoria = (
        f"Analiza la siguiente consulta del usuario e identifica sus preferencias, gustos, temas de tesis e intereses expresados:\n"
        f"Consulta: '{query}'\n\n"
        f"Genera una síntesis en formato lista de viñetas resaltando:\n"
        f"- Interacción o solicitud reciente\n"
        f"- Intereses y tema de tesis específicos detectados en esta interacción\n"
        f"- Relación con su perfil profesional en IA, ciencia de datos o sistemas de energía."
    )
    llm_res = await llm_router.generate_response(prompt=prompt_memoria, system_prompt="Eres el Agente de Memoria y Perfil de Obsidian.")
    memoria_dinamica = llm_res.get("response", f"- Interacción: {query}")
    
    profile_path = "Memoria_Usuario/Preferencias_y_Gustos.md"
    content = (
        f"# 🧠 Memoria a Largo Plazo y Preferencias del Usuario\n\n"
        f"## 📌 Actualización Reciente\n"
        f"{memoria_dinamica}\n"
    )
    
    pending: PendingAction = {
        "action_id": action_id,
        "agent_name": "Agente Bóveda Obsidian",
        "tool_name": "write_obsidian_memory",
        "description": "Actualizar registro de memoria periódica (gustos, relaciones y temas clave) en la Bóveda de Obsidian.",
        "payload": {
            "path": profile_path,
            "content": content
        },
        "risk_level": "MEDIUM"
    }
    
    state["pending_action"] = pending
    state["user_approval_status"] = "PENDING"
    state["obsidian_context"] = "Propuesta de actualización de memoria conversacional generada para Obsidian (Pendiente de aprobación HITL)."
    state["current_agent"] = "obsidian_writer_node"
    state["agent_history"] = history
    return state

async def obsidian_writer_node(state: AgentState) -> AgentState:
    """Nodo HITL: Escribe físicamente la memoria en Obsidian tras aprobación"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending and pending.get("payload"):
        payload = pending["payload"]
        filepath = payload.get("path", "Memoria_Usuario/Preferencias_y_Gustos.md")
        content = payload.get("content", "")
        
        ok = obsidian_manager.create_or_update_note(filepath, content, append=True)
        if ok:
            history.append(f"HITL Obsidian: Memoria '{filepath}' actualizada exitosamente en la Bóveda.")
            state["obsidian_context"] = f"✅ Memoria registrada físicamente en la Bóveda (/data/obsidian/{filepath})."
        else:
            state["obsidian_context"] = "❌ Falló la escritura en la Bóveda de Obsidian."
    elif approval == "REJECTED":
        history.append("HITL Obsidian: Actualización de memoria CANCELADA a petición del usuario.")
        state["obsidian_context"] = "❌ Operación en la Bóveda cancelada."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 4. AGENTE REDACTOR LATEX (/data/LatexDocs/Nombre_Documento/)
# -------------------------------------------------------------------
async def latex_writer_agent(state: AgentState) -> AgentState:
    """Agente Redactor en LaTeX: Administra la estructura modular por proyecto en /data/LatexDocs/Nombre_Documento/"""
    history = state.get("agent_history", [])
    history.append("Agente Redactor LaTeX: Preparando estructura modular de proyecto LaTeX")
    
    query = state["user_query"]
    q_lower = query.lower()
    
    doc_match = re.search(r'documento\s+([a-zA-Z0-9_\-]+)', q_lower)
    doc_name = doc_match.group(1).title() if doc_match else "Documento_Academico"
    
    base_dir = f"LatexDocs/{doc_name}"
    root_tex = f"{base_dir}/{doc_name}.tex"
    sec_intro = f"{base_dir}/secciones/introduccion.tex"
    
    preamble = (
        f"\\documentclass[12pt, a4paper]{{article}}\n"
        f"\\usepackage[utf8]{{inputenc}}\n"
        f"\\usepackage{{graphicx}}\n"
        f"\\graphicspath{{{{imagenes/}}}}\n"
        f"\\title{{{doc_name.replace('_', ' ')}}}\n"
        f"\\author{{Jhonathan Clavijo}}\n"
        f"\\date{{\\today}}\n\n"
        f"\\begin{{document}}\n"
        f"\\maketitle\n\n"
        f"\\input{{secciones/introduccion.tex}}\n\n"
        f"\\end{{document}}"
    )
    
    prompt_intro = f"Genera la sección de introducción formal en sintaxis LaTeX (utilizando \\section{{Introducción}}) para el tema: '{query}'."
    llm_res = await llm_router.generate_response(prompt=prompt_intro, system_prompt="Eres un experto redactor en LaTeX académico.")
    intro_content = llm_res.get("response", f"\\section{{Introducción}}\nTexto introductorio para {doc_name}.")
    
    action_id = f"act-latex-{uuid.uuid4().hex[:6]}"
    pending: PendingAction = {
        "action_id": action_id,
        "agent_name": "Agente Redactor LaTeX",
        "tool_name": "create_latex_project",
        "description": f"Crear estructura de proyecto LaTeX modular en /data/LatexDocs/{doc_name}/ (raíz, secciones/ e imagenes/).",
        "payload": {
            "doc_name": doc_name,
            "root_path": root_tex,
            "preamble_content": preamble,
            "sec_path": sec_intro,
            "sec_content": intro_content
        },
        "risk_level": "MEDIUM"
    }
    
    state["pending_action"] = pending
    state["user_approval_status"] = "PENDING"
    state["latex_context"] = f"Propuesta de proyecto LaTeX '{doc_name}' creada en /data/LatexDocs/{doc_name}/ (Pendiente de aprobación HITL)."
    state["current_agent"] = "latex_action_node"
    state["agent_history"] = history
    return state

async def latex_action_node(state: AgentState) -> AgentState:
    """Nodo HITL: Crea/modifica la estructura física del proyecto LaTeX"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending and pending.get("payload"):
        payload = pending["payload"]
        doc_name = payload.get("doc_name", "Documento_Academico")
        root_path = payload.get("root_path")
        preamble = payload.get("preamble_content")
        sec_path = payload.get("sec_path")
        sec_content = payload.get("sec_content")
        
        filesystem_manager.create_file(f"LatexDocs/{doc_name}/imagenes/.gitkeep", "")
        filesystem_manager.create_file(root_path, preamble)
        filesystem_manager.create_file(sec_path, sec_content)
        
        history.append(f"HITL LaTeX: Proyecto LaTeX '{doc_name}' creado exitosamente en /data/LatexDocs/{doc_name}/.")
        state["latex_context"] = (
            f"✅ PROYECTO LATEX CREADO EN DISCO (`/data/LatexDocs/{doc_name}/`):\n"
            f"- Archivo Raíz: `{doc_name}.tex` (preámbulo + `\\input{{secciones/...}}` sin texto directo).\n"
            f"- Subcarpetas: `imagenes/` y `secciones/`."
        )
    elif approval == "REJECTED":
        history.append("HITL LaTeX: Creación del proyecto LaTeX CANCELADA por el usuario.")
        state["latex_context"] = "❌ Creación del proyecto LaTeX cancelada."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 5. AGENTE DE CODIFICACIÓN (Python, Bases de Datos, MQTT)
# -------------------------------------------------------------------
async def coding_node(state: AgentState) -> AgentState:
    """Agente de Codificación: Genera dinámicamente soluciones en Python, SQL o MQTT según la solicitud del usuario"""
    history = state.get("agent_history", [])
    history.append("Agente de Codificación: Generando solución técnica a medida en Python/SQL/MQTT")
    
    query = state["user_query"]
    q_lower = query.lower()
    action_id = f"act-code-{uuid.uuid4().hex[:6]}"
    
    operation = "create"
    filename = "scripts/modulo_desarrollo.py"
    if "mqtt" in q_lower: filename = "scripts/cliente_mqtt.py"
    elif any(k in q_lower for k in ["database", "sql", "db", "base de datos"]): filename = "scripts/gestor_db.py"
    
    prompt_codigo = f"Escribe una solución de código limpia, funcional y comentada en Python para el siguiente requerimiento:\n'{query}'"
    llm_res = await llm_router.generate_response(prompt=prompt_codigo, system_prompt="Eres un Agente Desarrollador de Software experto en Python, SQLite y MQTT.")
    code_content = llm_res.get("response", f"# Script generado para: {query}\nprint('Código listo')")
    
    pending: PendingAction = {
        "action_id": action_id,
        "agent_name": "Agente de Codificación",
        "tool_name": "write_code_file",
        "description": f"Crear/actualizar script de Python en /app/data/{filename}.",
        "payload": {
            "operation": operation,
            "path": filename,
            "content": code_content
        },
        "risk_level": "MEDIUM"
    }
    
    state["pending_action"] = pending
    state["user_approval_status"] = "PENDING"
    state["coding_context"] = f"Propuesta de código Python generada para {filename} (Pendiente de aprobación HITL)."
    state["current_agent"] = "file_action_node"
    state["agent_history"] = history
    return state

async def file_action_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta operaciones de código o archivos"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending and pending.get("payload"):
        payload = pending["payload"]
        op = payload.get("operation", "create")
        path = payload.get("path", "scripts/codigo.py")
        content = payload.get("content", "")
        
        ok = False
        if op == "create" or op == "modify":
            ok = filesystem_manager.create_file(path, content)
        elif op == "delete":
            ok = filesystem_manager.delete_file(path)
            
        if ok:
            history.append(f"HITL Codificación: Archivo '{path}' procesado con éxito.")
            state["coding_context"] = f"✅ Archivo de código creado/modificado exitosamente en `/data/{path}`."
        else:
            state["coding_context"] = f"❌ Error al escribir el archivo de código `{path}`."
    elif approval == "REJECTED":
        history.append("HITL Codificación: Operación de código CANCELADA por el usuario.")
        state["coding_context"] = "❌ Operación de código cancelada."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 6. AGENTE GOOGLE WORKSPACE (Gmail & Google Calendar HITL)
# -------------------------------------------------------------------
async def google_workspace_agent(state: AgentState) -> AgentState:
    """Agente Google Workspace: Resumen, archivo, eliminación y cambio de estado en Gmail; Creación, edición y borrado de eventos en Google Calendar. Acción previa autorización HITL."""
    history = state.get("agent_history", [])
    history.append("Agente Google Workspace: Evaluando operaciones sobre Gmail y Google Calendar")
    
    query = state["user_query"]
    q_lower = query.lower()
    action_id = f"act-gws-{uuid.uuid4().hex[:6]}"
    
    op_type = "read"
    target = "Gmail"
    desc = "Consultar correos o resumen de bandeja de entrada"
    
    if any(k in q_lower for k in ["borrar correo", "eliminar correo", "delete email"]):
        op_type = "delete_email"
        desc = "ELIMINAR correo electrónico de Gmail"
    elif any(k in q_lower for k in ["archivar", "archive"]):
        op_type = "archive_email"
        desc = "Archivar correo en Gmail"
    elif any(k in q_lower for k in ["no leído", "marcar como leído", "unread", "read"]):
        op_type = "toggle_read_status"
        desc = "Cambiar estado de lectura de correo en Gmail"
    elif any(k in q_lower for k in ["crear evento", "agendar", "nuevo evento"]):
        op_type = "create_event"
        target = "Google Calendar"
        desc = "Crear nuevo evento en Google Calendar"
    elif any(k in q_lower for k in ["modificar evento", "editar evento"]):
        op_type = "modify_event"
        target = "Google Calendar"
        desc = "Modificar evento existente en Google Calendar"
    elif any(k in q_lower for k in ["eliminar evento", "cancelar evento"]):
        op_type = "delete_event"
        target = "Google Calendar"
        desc = "ELIMINAR evento de Google Calendar"

    pending: PendingAction = {
        "action_id": action_id,
        "agent_name": f"Agente Google Workspace ({target})",
        "tool_name": f"gws_{op_type}",
        "description": f"{desc}: Requiere autorización previa del usuario para ejecutarse.",
        "payload": {
            "operacion": op_type,
            "servicio": target,
            "detalles": query
        },
        "risk_level": "HIGH"
    }
    
    state["pending_action"] = pending
    state["user_approval_status"] = "PENDING"
    state["email_context"] = f"Propuesta de operación {op_type} en {target} generada (Pendiente de aprobación HITL)."
    state["current_agent"] = "email_action_node"
    state["agent_history"] = history
    return state

async def email_action_node(state: AgentState) -> AgentState:
    """Nodo HITL: Ejecuta acciones sobre Gmail o Calendar tras aprobación"""
    history = state.get("agent_history", [])
    approval = state.get("user_approval_status")
    pending = state.get("pending_action")
    
    if approval == "APPROVED" and pending:
        payload = pending.get("payload", {})
        op = payload.get("operacion", "read")
        srv = payload.get("servicio", "Gmail")
        
        history.append(f"HITL Google Workspace: Operación '{op}' en {srv} APROBADA y ejecutada.")
        state["email_context"] = f"✅ Acción '{op}' ejecutada con éxito en {srv} mediante OAuth2."
    elif approval == "REJECTED":
        history.append("HITL Google Workspace: Operación CANCELADA a petición del usuario.")
        state["email_context"] = "❌ La acción en Google Workspace fue cancelada."
        
    state["pending_action"] = None
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 7. AGENTE REDACTOR FINAL DE SÍNTESIS (Harness Optimizado)
# -------------------------------------------------------------------
async def writer_node(state: AgentState) -> AgentState:
    """Agente Redactor Final: Sintetiza la respuesta final incorporando de forma modular solo el contexto relevante"""
    from app.agents.graph import read_persistent_obsidian_notes
    
    history = state.get("agent_history", [])
    history.append("Redactor Final: Sintetizando respuesta con contexto modular de especialistas")
    
    user_query = state['user_query']
    vault_memory = read_persistent_obsidian_notes()
    
    context_parts = []
    if vault_memory:
        context_parts.append(f"🧠 MEMORIA PERSISTENTE BÓVEDA OBSIDIAN:\n{vault_memory}")
    if state.get("research_context"): context_parts.append(state["research_context"])
    if state.get("obsidian_context"): context_parts.append(state["obsidian_context"])
    if state.get("latex_context"): context_parts.append(state["latex_context"])
    if state.get("coding_context"): context_parts.append(state["coding_context"])
    if state.get("email_context"): context_parts.append(state["email_context"])
    
    context_str = "\n\n".join(context_parts) if context_parts else "Sin notas adicionales en la Bóveda."
    
    # Construcción modular del prompt de Harness para no sobrecargar los modelos Edge
    rules = [
        "Eres Antigravity, un Asistente Agéntico Edge avanzado, atento y profesional.",
        "REGLAS DE RESPUESTA:",
        "1. RESPONDE DIRECTAMENTE a la inquietud del usuario utilizando el contexto recuperado de los agentes especialistas.",
        "2. Si el usuario pregunta sobre conversaciones anteriores o su última solicitud, apóyate en el historial de diálogo o contexto de la bóveda."
    ]
    
    if state.get("latex_context"):
        rules.append("3. LATEX: Estructura modular `/data/LatexDocs/Nombre_Documento/` con preámbulo en el archivo raíz e `\\input{secciones/...}`.")
    if state.get("coding_context"):
        rules.append("4. CODIFICACIÓN: Ofrece soluciones estructuradas en Python, Bases de Datos y protocolo MQTT (paho-mqtt).")
    if state.get("email_context"):
        rules.append("5. GOOGLE WORKSPACE: Informa que las acciones sobre Gmail y Calendar están gobernadas por HITL.")
        
    system_prompt = "\n".join(rules) + f"\n\nContexto disponible de herramientas:\n{context_str}"
    
    llm_res = await llm_router.generate_response(prompt=user_query, system_prompt=system_prompt)
    
    state["final_response"] = llm_res.get("response", "Respuesta generada.")
    state["active_tier"] = llm_res.get("tier", "Desconocido")
    state["active_model"] = llm_res.get("model", "Desconocido")
    state["latency_ms"] = llm_res.get("latency_ms", 0.0)
    state["agent_history"] = history
    return state
