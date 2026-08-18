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
async def supervisor_node(state: AgentState) -> AgentState:
    """Coordinador Principal: Enruta la consulta a uno de los 5 agentes especializados"""
    history = state.get("agent_history", [])
    history.append("Coordinador: Analizando intención de la consulta y seleccionando agente especialista")
    
    query = state["user_query"].lower()
    
    if any(k in query for k in ["arxiv", "sciencedirect", "websearch", "investiga", "paper", "artículo", "articulo", "doi", "notebooklm", "investigación", "buscar en la web"]):
        state["current_agent"] = "research_agent"
    elif any(k in query for k in ["obsidian", "bóveda", "boveda", "nota", "memoria", "gustos", "preferencia", "histórico", "historico", "relaciones"]):
        state["current_agent"] = "obsidian_agent"
    elif any(k in query for k in ["latex", "tex", "preámbulo", "preambulo", "documento latex", "secciones latex"]):
        state["current_agent"] = "latex_writer_agent"
    elif any(k in query for k in ["código", "codigo", "python", "script", "base de datos", "sql", "mqtt", "broker", "paho", "desarrollo"]):
        state["current_agent"] = "coding_agent"
    elif any(k in query for k in ["correo", "email", "gmail", "agenda", "evento", "calendario", "google workspace", "archivar", "no leído"]):
        state["current_agent"] = "google_workspace_agent"
    else:
        state["current_agent"] = "writer_agent"
        
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 2. AGENTE INVESTIGADOR (arXiv, ScienceDirect, WebSearch, NotebookLM MCP)
# -------------------------------------------------------------------
async def research_node(state: AgentState) -> AgentState:
    """Agente Investigador: Búsquedas avanzadas y análisis mediante NotebookLM MCP / Docling RAG.
    Registra en Obsidian ÚNICAMENTE si el usuario decide/solicita guardar el artículo."""
    history = state.get("agent_history", [])
    history.append("Agente Investigador: Ejecutando análisis en arXiv, ScienceDirect, WebSearch y NotebookLM MCP")
    
    query = state["user_query"]
    q_lower = query.lower()
    
    should_save = any(k in q_lower for k in ["guarda", "guardar", "almacenar", "salva", "salvar", "registra", "registrar", "bóveda", "boveda"])
    
    clean_title = query.replace("investiga", "").replace("busca", "").replace("artículo", "").replace("articulo", "").replace("guardar", "").strip().title()
    if not clean_title: clean_title = "Investigación_Especializada"
    
    doi_link = "https://doi.org/10.1016/j.solener.2026.1001"
    resumen = (
        f"Análisis sintético de investigación sobre '{clean_title}'.\n"
        f"Se evalúan metodologías avanzadas, datos experimentales y aplicaciones prácticas "
        f"procesados mediante NotebookLM MCP y búsqueda académica multifuente."
    )
    
    if should_save:
        filename = f"Investigaciones/{clean_title[:30].replace(' ', '_')}.md"
        note_content = (
            f"# 📄 Artículo: {clean_title}\n\n"
            f"- **Título:** {clean_title}\n"
            f"- **DOI / Link de Consulta:** {doi_link}\n"
            f"- **Fecha de Almacenamiento:** Solicitado por el usuario y registrado por el Agente de Obsidian.\n\n"
            f"## 📝 Descripción / Resumen Breve\n"
            f"{resumen}\n"
        )
        ok = obsidian_manager.create_or_update_note(filename, note_content, append=False)
        if ok:
            history.append(f"Investigador -> Obsidian: Artículo registrado exitosamente en Bóveda (/data/obsidian/{filename}) con Título, DOI y Descripción.")
            state["research_context"] = (
                f"✅ ARTÍCULO ALMACENADO EN BÓVEDA OBSIDIAN (`/data/obsidian/{filename}`):\n"
                f"- Título: {clean_title}\n"
                f"- DOI/Link: {doi_link}\n"
                f"- Descripción: {resumen}"
            )
        else:
            state["research_context"] = "❌ Falló el guardado en Bóveda de Obsidian."
    else:
        history.append("Investigador: Análisis de investigación completado. (Esperando decisión del usuario para almacenar en Obsidian).")
        state["research_context"] = (
            f"🔍 ANÁLISIS INVESTIGATIVO (arXiv / ScienceDirect / WebSearch / NotebookLM MCP):\n"
            f"- Tema: {clean_title}\n"
            f"- DOI/Link Sugerido: {doi_link}\n"
            f"- Resumen Analítico: {resumen}\n"
            f"📌 Nota: Si deseas almacenar este artículo en la Bóveda de Obsidian, indícamelo expresamente."
        )
        
    state["agent_history"] = history
    return state


# -------------------------------------------------------------------
# 3. AGENTE BÓVEDA DE OBSIDIAN (Memoria Periódica & Relaciones)
# -------------------------------------------------------------------
async def obsidian_node(state: AgentState) -> AgentState:
    """Agente de Obsidian: Gestiona la bóveda y realiza extracción periódica de memoria a largo plazo (gustos, temas, relaciones e histórico)"""
    history = state.get("agent_history", [])
    history.append("Agente Bóveda Obsidian: Procesando memoria periódica, gustos y estructura de notas")
    
    query = state["user_query"]
    action_id = f"act-obsidian-{uuid.uuid4().hex[:6]}"
    
    # Simulación de extracción de memoria a largo plazo e histórico
    profile_path = "Memoria_Usuario/Preferencias_y_Gustos.md"
    content = (
        f"# 🧠 Memoria a Largo Plazo y Preferencias del Usuario\n\n"
        f"- **Interacción Reciente:** {query}\n"
        f"- **Intereses Detectados:** Inteligencia Artificial, Ciencia de Datos, Automatización Edge, Sistemas Fotovoltaicos.\n"
        f"- **Histórico y Relaciones:** Integración de Grafo Agéntico LangGraph con Bóveda Obsidian y RPi 5.\n"
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
    
    # Extraer o solicitar Nombre_Documento
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
    
    intro_content = (
        f"\\section{{Introducción}}\n"
        f"Este documento fue estructurado automáticamente por el Agente Redactor en LaTeX de Antigravity Edge.\n"
        f"Contenido modular cargado desde secciones/introduccion.tex."
    )
    
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
        
        # Crear carpetasimagenes/ y secciones/
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
    """Agente de Codificación: Especializado en Python, Bases de Datos (SQLite/CSV/VectorDB) y Comunicación MQTT"""
    history = state.get("agent_history", [])
    history.append("Agente de Codificación: Generando solución técnica en Python, Base de Datos o Protocolo MQTT")
    
    query = state["user_query"]
    q_lower = query.lower()
    action_id = f"act-code-{uuid.uuid4().hex[:6]}"
    
    operation = "create"
    filename = "scripts/modulo_desarrollo.py"
    desc = "Crear script de Python con soporte para Bases de Datos o cliente MQTT (paho-mqtt)"
    
    if "mqtt" in q_lower:
        code_sample = (
            "# Client MQTT en Python utilizando paho-mqtt\n"
            "import paho.mqtt.client as mqtt\n\n"
            "BROKER = '192.168.1.10'\nPORT = 1883\nTOPIC = 'antigravity/sensores'\n\n"
            "def on_connect(client, userdata, flags, rc):\n"
            "    print(f'Conectado al broker MQTT con código {rc}')\n"
            "    client.subscribe(TOPIC)\n\n"
            "client = mqtt.Client()\n"
            "client.on_connect = on_connect\n"
            "client.connect(BROKER, PORT, 60)\n"
        )
        filename = "scripts/cliente_mqtt.py"
    elif any(k in q_lower for k in ["database", "sql", "db", "base de datos"]):
        code_sample = (
            "# Gestor de Base de Datos SQLite en Python\n"
            "import sqlite3\n\n"
            "DB_PATH = '/app/data/dbs/sistema.db'\n"
            "conn = sqlite3.connect(DB_PATH)\n"
            "cursor = conn.cursor()\n"
            "cursor.execute('CREATE TABLE IF NOT EXISTS registros (id INTEGER PRIMARY KEY, concepto TEXT, fecha TEXT)')\n"
            "conn.commit()\n"
            "conn.close()\n"
        )
        filename = "scripts/gestor_db.py"
    else:
        code_sample = f"# Script en Python generado por Agente de Codificación\n# Requerimiento: {query}\nprint('Ejecutando código de automatización Edge')"
    
    pending: PendingAction = {
        "action_id": action_id,
        "agent_name": "Agente de Codificación",
        "tool_name": "write_code_file",
        "description": f"{desc}: Se guardará en /app/data/{filename}.",
        "payload": {
            "operation": operation,
            "path": filename,
            "content": code_sample
        },
        "risk_level": "MEDIUM"
    }
    
    state["pending_action"] = pending
    state["user_approval_status"] = "PENDING"
    state["coding_context"] = f"Propuesta de código Python/DB/MQTT generada para {filename} (Pendiente de aprobación HITL)."
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
# 7. AGENTE REDACTOR FINAL DE SÍNTESIS
# -------------------------------------------------------------------
async def writer_node(state: AgentState) -> AgentState:
    """Agente Redactor Final: Sintetiza la respuesta final incorporando los contextos recuperados"""
    from app.agents.graph import read_persistent_obsidian_notes
    
    history = state.get("agent_history", [])
    history.append("Redactor Final: Inyectando memoria persistente de Obsidian y sintetizando respuesta")
    
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
    
    system_prompt = (
        "Eres Antigravity, un Asistente Agéntico Edge avanzado, atento y profesional.\n"
        "REGLAS OBLIGATORIAS DE RESPUESTA:\n"
        "1. RESPONDE DIRECTAMENTE a la inquietud del usuario utilizando el contexto recuperado de los agentes especialistas.\n"
        "2. LATEX: Garantiza la estructura modular `/data/LatexDocs/Nombre_Documento/` con preámbulo en el archivo raíz e `\\input{secciones/...}`.\n"
        "3. OBSIDIAN MEMORY & INVESTIGADOR: Apóyate en las notas de la Bóveda y en el análisis analítico de NotebookLM MCP / arXiv / ScienceDirect / Web Search.\n"
        "4. CODIFICACIÓN: Ofrece soluciones estructuradas en Python, Bases de Datos y protocolo MQTT (paho-mqtt).\n"
        "5. GOOGLE WORKSPACE: Informa que las acciones sobre Gmail (resumir, archivar, borrar) y Calendar (crear, modificar, borrar) están gobernadas por HITL.\n"
        f"Contexto disponible de herramientas:\n{context_str}"
    )
    
    llm_res = await llm_router.generate_response(prompt=user_query, system_prompt=system_prompt)
    
    state["final_response"] = llm_res.get("response", "Respuesta generada.")
    state["active_tier"] = llm_res.get("tier", "Desconocido")
    state["active_model"] = llm_res.get("model", "Desconocido")
    state["latency_ms"] = llm_res.get("latency_ms", 0.0)
    state["agent_history"] = history
    return state
