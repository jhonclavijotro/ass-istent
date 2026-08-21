import os
import json
import logging
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
from app.core.llm_router import llm_router

logger = logging.getLogger("notebooklm_mcp")

NOTEBOOK_CACHE_FILE = "/app/data/notebooks_registry.json" if os.path.exists("/app/data") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "notebooks_registry.json"))
EXTRACTED_TEXT_DIR = "/app/data/extracted_text" if os.path.exists("/app/data") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "extracted_text"))

# Asegurar que el directorio de caché de texto extraído exista
os.makedirs(EXTRACTED_TEXT_DIR, exist_ok=True)

class NotebookLMMCPClient:
    """Cliente e Integración MCP (Model Context Protocol) para Google NotebookLM.
    Permite crear cuadernos, subir artículos descargados (/data/downloads/) y realizar consultas analíticas grounded."""

    def __init__(self):
        self.registry_file = NOTEBOOK_CACHE_FILE
        self._load_registry()
        self.mcp_url = os.getenv("MCP_SERVER_URL", "http://mcp-server:8080/sse")

    def _load_registry(self):
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    self.notebooks = json.load(f)
            except Exception:
                self.notebooks = {}
        else:
            self.notebooks = {}

    def _save_registry(self):
        try:
            os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(self.notebooks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error al guardar registro de cuadernos NotebookLM: {e}")

    def create_notebook(self, title: str) -> Dict[str, Any]:
        """Crea un nuevo cuaderno de investigación en NotebookLM MCP"""
        nb_id = f"nb-{len(self.notebooks) + 1:03d}"
        notebook_data = {
            "notebook_id": nb_id,
            "title": title,
            "sources": [],
            "status": "ACTIVE"
        }
        self.notebooks[nb_id] = notebook_data
        self._save_registry()
        logger.info(f"NotebookLM MCP: Cuaderno '{title}' creado con ID '{nb_id}'.")
        return notebook_data

    def list_notebooks(self) -> List[Dict[str, Any]]:
        """Lista todos los cuadernos de investigación registrados en NotebookLM MCP"""
        return list(self.notebooks.values())

    def add_source_to_notebook(self, notebook_id: str, source_path_or_url: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Asocia una fuente (PDF de /data/downloads/ o enlace) a un cuaderno de NotebookLM"""
        if notebook_id not in self.notebooks:
            nb = self.create_notebook("Investigaciones Académicas")
            notebook_id = nb["notebook_id"]

        source_item = {
            "title": title or os.path.basename(source_path_or_url),
            "location": source_path_or_url,
            "added_at": "2026-08-18"
        }
        
        # Evitar duplicados
        existing_sources = [s["location"] for s in self.notebooks[notebook_id]["sources"]]
        if source_path_or_url not in existing_sources:
            self.notebooks[notebook_id]["sources"].append(source_item)
            self._save_registry()
            logger.info(f"NotebookLM MCP: Fuente '{source_item['title']}' agregada al cuaderno '{notebook_id}'.")
            
            # Extraer y cachear texto en segundo plano/proactivamente
            self.extract_and_cache_text(source_path_or_url)
            
        return {"success": True, "notebook_id": notebook_id, "source": source_item}

    def extract_and_cache_text(self, file_path: str) -> str:
        """Extrae texto de un archivo PDF y lo guarda en cache de texto para evitar reprocesamiento"""
        if not file_path or not os.path.exists(file_path) or not file_path.endswith(".pdf"):
            return ""

        filename = os.path.basename(file_path)
        cache_file = os.path.join(EXTRACTED_TEXT_DIR, f"{filename}.txt")

        # Si ya está en caché, leer y retornar
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error al leer caché de texto {cache_file}: {e}")

        # Si no, extraer usando PyMuPDF
        logger.info(f"Extraer texto de {file_path} usando PyMuPDF...")
        text = ""
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()

            # Guardar en caché
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Caché de texto guardado para {filename} ({len(text)} caracteres).")
        except Exception as e:
            logger.error(f"Error al extraer texto del PDF {file_path}: {e}")
        
        return text

    async def query_notebook(self, notebook_id: str, question: str) -> Dict[str, Any]:
        """Realiza una consulta grounded tipo NotebookLM sobre las fuentes asociadas al cuaderno vía MCP SSE"""
        nb = self.notebooks.get(notebook_id)
        if not nb:
            return {"error": "Cuaderno no encontrado", "notebook_id": notebook_id}

        # 1. Recuperar el texto de todas las fuentes asociadas al cuaderno
        documents_text = []
        for source in nb.get("sources", []):
            loc = source["location"]
            # Intentar resolver ruta absoluta si es relativa
            if not os.path.isabs(loc):
                # Probar descargas
                downloads_path = os.path.join(os.path.dirname(self.registry_file), "downloads", loc)
                if os.path.exists(downloads_path):
                    loc = downloads_path
                else:
                    # Probar pdfs
                    pdfs_path = os.path.join(os.path.dirname(self.registry_file), "pdfs", loc)
                    if os.path.exists(pdfs_path):
                        loc = pdfs_path

            text = self.extract_and_cache_text(loc)
            if text.strip():
                documents_text.append(text)

        if not documents_text:
            return {
                "notebook_id": notebook_id,
                "answer": "No hay texto extraído disponible en las fuentes para realizar el análisis.",
                "provider": "NotebookLM MCP"
            }

        # 2. Conectar al contenedor del Servidor MCP vía SSE
        try:
            from mcp.client.sse import sse_client
            from mcp import ClientSession

            logger.info(f"Conectando al servidor MCP en {self.mcp_url}...")
            async with sse_client(self.mcp_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    logger.info("Llamando a la herramienta deep_synthesis en el servidor MCP...")
                    result = await session.call_tool(
                        "deep_synthesis",
                        arguments={
                            "documents": documents_text,
                            "prompt": question
                        }
                    )
                    
                    ans = "Sin respuesta del servidor MCP."
                    if result and hasattr(result, 'content') and result.content:
                        ans = "".join([c.text for c in result.content if hasattr(c, 'text')])
                    elif result and isinstance(result, str):
                        ans = result
                    
                    return {
                        "notebook_id": notebook_id,
                        "answer": ans,
                        "provider": "NotebookLM MCP (SSE Real)"
                    }
        except Exception as e:
            logger.error(f"Error al conectar con el Servidor MCP: {e}. Activando fallback local...")
            # Fallback local usando el llm_router directamente
            sources_summary = "\n".join([f"- {s['title']} ({s['location']})" for s in nb.get("sources", [])])
            prompt = (
                f"CUADERNO DE NOTEBOOKLM MCP (Fallback Local): '{nb.get('title', 'Investigación')}'\n"
                f"FUENTES CARGADAS EN EL CUADERNO:\n{sources_summary}\n\n"
                f"CONSULTA GROUNDED: '{question}'\n"
                f"Responde con análisis analítico riguroso citando las fuentes del cuaderno."
            )
            res = await llm_router.generate_response(prompt=prompt, system_prompt="Eres la interfaz de consulta grounded de Google NotebookLM MCP.")
            return {
                "notebook_id": notebook_id,
                "answer": res.get("response", "Sin respuesta"),
                "provider": f"NotebookLM Fallback Local ({res.get('tier', 'Unknown')})"
            }

notebooklm_mcp = NotebookLMMCPClient()
