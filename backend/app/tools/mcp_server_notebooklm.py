import os
import sys
import logging
from fastapi import FastAPI, Request
from starlette.responses import Response

# Agregar el directorio raíz del backend al path para que encuentre el módulo `app`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.core.gemini_service import gemini_service

logger = logging.getLogger("mcp_server_notebooklm")
logging.basicConfig(level=logging.INFO)

# Intentar importar FastMCP y SseServerTransport desde mcp
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.sse import SseServerTransport
except ImportError:
    # Fallback ficticio por si no están instalados localmente al validar sintaxis
    class FastMCP:
        def __init__(self, name): pass
        def tool(self): return lambda f: f
        def create_initialization_options(self): return None
        async def run(self, r, w, opts): pass
    class SseServerTransport:
        def __init__(self, path): pass
        async def connect_sse(self, s, r, send): pass
        async def handle_post_message(self, s, r, send): pass

# Inicializar FastMCP
mcp = FastMCP("NotebookLM MCP Server")

@mcp.tool()
async def deep_synthesis(documents: list[str], prompt: str) -> str:
    """
    Sintetiza, compara y analiza profundamente una lista de documentos de texto plano
    utilizando Gemini con contexto extendido de forma 'grounded'.
    """
    logger.info(f"mcp-server: Iniciando síntesis de {len(documents)} documentos...")
    
    # Combinar documentos
    combined_docs = ""
    for idx, doc_text in enumerate(documents):
        combined_docs += f"--- INICIO DOCUMENTO {idx+1} ---\n{doc_text}\n--- FIN DOCUMENTO {idx+1} ---\n\n"
        
    synthesis_prompt = (
        f"Analiza la siguiente selección de documentos académicos/científicos:\n\n"
        f"{combined_docs}"
        f"Instrucción de análisis:\n{prompt}\n\n"
        f"Proporciona un reporte estructurado y fundamentado (grounded) citando las partes relevantes "
        f"de los documentos."
    )
    
    system_instruction = (
        "Eres el motor analítico de Google NotebookLM MCP. Tu tarea es analizar de forma rigurosa "
        "y basada estrictamente en los documentos proporcionados. No alucines información que no "
        "se encuentre en las fuentes."
    )
    
    # Usar el modelo gemini-1.5-pro de forma predeterminada para síntesis profunda
    original_model = gemini_service.get_active_model_id()
    # Si tenemos una clave de API configurada, podemos usar gemini-1.5-pro
    gemini_service.set_active_model("gemini-1.5-pro")
    
    try:
        response = await gemini_service.generate_content(prompt=synthesis_prompt, system_prompt=system_instruction)
        if not response:
            logger.info("Falló gemini-1.5-pro, intentando con el modelo activo actual...")
            gemini_service.set_active_model(original_model)
            response = await gemini_service.generate_content(prompt=synthesis_prompt, system_prompt=system_instruction)
            
        if response:
            return response
        else:
            return "Error: No se pudo generar respuesta de Gemini API. Verifica la API key."
    finally:
        gemini_service.set_active_model(original_model)

# Inicializar FastAPI
app = FastAPI(title="NotebookLM MCP Server SSE")
sse = SseServerTransport("/messages/")

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())
    return Response()

@app.post("/messages/")
async def handle_messages(request: Request):
    return await sse.handle_post_message(request.scope, request.receive, request._send)
