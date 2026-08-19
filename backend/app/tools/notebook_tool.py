import logging
from typing import Dict, Any, List, Optional
from app.core.llm_router import llm_router

logger = logging.getLogger("notebook_tool")

class NotebookLMAnalyzer:
    """Herramienta de análisis profundo basada en la arquitectura de NotebookLM de Google.
    Utiliza modelos de contexto amplio para analizar fuentes académicas, extraer aportes clave, metodologías y citas."""
    
    def __init__(self):
        self.system_instruction = (
            "Eres el Motor Analítico de NotebookLM integrado en Antigravity. "
            "Tu tarea es analizar literatura académica de forma rigurosa y 'grounded' (basada estrictamente en las fuentes). "
            "El año actual de referencia es 2026. Al solicitar literatura reciente (2022-2026), selecciona y analiza únicamente trabajos dentro de ese rango."
        )

    async def analyze_research_topic(self, topic: str, user_query: str, num_articles: int = 10) -> Dict[str, Any]:
        """Realiza un análisis analítico tipo NotebookLM sobre un tema de investigación."""
        logger.info(f"NotebookLM: Analizando tema '{topic}' con consulta '{user_query}'...")
        
        prompt = (
            f"REQUERIMIENTO DE INVESTIGACIÓN (NotebookLM Analysis):\n"
            f"Tema: '{topic}'\n"
            f"Consulta original: '{user_query}'\n\n"
            f"Instrucciones:\n"
            f"1. Genera una selección rigurosa de al menos {num_articles} artículos académicos clave "
            f"publicados entre 2022 y 2026 (hasta la actualidad).\n"
            f"2. Para cada artículo, proporciona la siguiente estructura analítica:\n"
            f"   - **Título Oficial**\n"
            f"   - **Autores y Año** (2022-2026)\n"
            f"   - **DOI / Enlace Directo**\n"
            f"   - **Resumen Analítico (Grounding)**: Descripción técnica de la metodología y problemas resueltos.\n"
            f"   - **Aporte Clave / Innovación**: Principal contribución al campo de la ingeniería/IA/energía.\n"
            f"3. Finaliza con una **Síntesis Ejecutiva General (Takeaways)** resaltando las tendencias dominantes encontradas.\n"
        )
        
        res = await llm_router.generate_response(prompt=prompt, system_prompt=self.system_instruction)
        response_text = res.get("response", "No se pudo completar el análisis de NotebookLM.")
        
        return {
            "topic": topic,
            "analysis_markdown": response_text,
            "provider": res.get("tier", "Gemini NotebookLM"),
            "model": res.get("model", "NotebookLM Engine")
        }

notebook_analyzer = NotebookLMAnalyzer()
