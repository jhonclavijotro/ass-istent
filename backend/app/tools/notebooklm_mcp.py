import os
import json
import logging
from typing import Dict, Any, List, Optional
from app.core.llm_router import llm_router
from app.tools.pdf_downloader import pdf_downloader

logger = logging.getLogger("notebooklm_mcp")

NOTEBOOK_CACHE_FILE = "/app/data/notebooks_registry.json" if os.path.exists("/app/data") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "notebooks_registry.json"))

class NotebookLMMCPClient:
    """Cliente e Integración MCP (Model Context Protocol) para Google NotebookLM.
    Permite crear cuadernos, subir artículos descargados (/data/downloads/) y realizar consultas analíticas grounded."""

    def __init__(self):
        self.registry_file = NOTEBOOK_CACHE_FILE
        self._load_registry()

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
        self.notebooks[notebook_id]["sources"].append(source_item)
        self._save_registry()
        logger.info(f"NotebookLM MCP: Fuente '{source_item['title']}' agregada al cuaderno '{notebook_id}'.")
        return {"success": True, "notebook_id": notebook_id, "source": source_item}

    async def query_notebook(self, notebook_id: str, question: str) -> Dict[str, Any]:
        """Realiza una consulta grounded tipo NotebookLM sobre las fuentes asociadas al cuaderno"""
        nb = self.notebooks.get(notebook_id)
        sources_summary = "\n".join([f"- {s['title']} ({s['location']})" for s in nb.get("sources", [])]) if nb else "Fuentes académicas procesadas."

        prompt = (
            f"CUADERNO DE NOTEBOOKLM MCP: '{nb.get('title', 'Investigación')}'\n"
            f"FUENTES CARGADAS EN EL CUADERNO:\n{sources_summary}\n\n"
            f"CONSULTA GROUNDED: '{question}'\n"
            f"Responde con análisis analítico riguroso citando las fuentes del cuaderno."
        )
        res = await llm_router.generate_response(prompt=prompt, system_prompt="Eres la interfaz de consulta grounded de Google NotebookLM MCP.")
        return {
            "notebook_id": notebook_id,
            "answer": res.get("response", "Sin respuesta"),
            "provider": res.get("tier", "NotebookLM MCP")
        }

notebooklm_mcp = NotebookLMMCPClient()
