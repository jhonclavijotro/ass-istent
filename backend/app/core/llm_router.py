import os
import time
import logging
import httpx
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel

from app.core.gemini_service import gemini_service

logger = logging.getLogger("llm_router")
logging.basicConfig(level=logging.INFO)

class LLMProviderInfo(BaseModel):
    tier: str  # "Tier 1: PC Local", "Tier 2: Gemini Cloud", "Tier 3: RPi Edge"
    model: str
    status: str
    latency_ms: float

class ResilientLLMRouter:
    def __init__(self):
        self.ollama_pc_url = os.getenv("OLLAMA_PC_URL", "http://192.168.1.50:11434")
        self.ollama_pc_model = os.getenv("OLLAMA_PC_MODEL", "qwen3.5:4b")
        self.ollama_rpi_url = os.getenv("OLLAMA_RPI_URL", "http://localhost:11434")
        self.ollama_rpi_model = os.getenv("OLLAMA_RPI_MODEL", "qwen2.5:1.5b")

    @property
    def gemini_api_key(self) -> str:
        return gemini_service.api_key

    @property
    def gemini_model(self) -> str:
        return gemini_service.active_model

    async def check_pc_ollama_health(self) -> Tuple[bool, float]:
        """Verifica la conectividad con el PC local Ollama con un timeout rápido de 1.5s"""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{self.ollama_pc_url}/api/version")
                if response.status_code == 200:
                    latency = round((time.time() - start) * 1000, 2)
                    return True, latency
        except Exception as e:
            logger.warning(f"Tier 1 (PC Ollama en {self.ollama_pc_url}) inalcanzable: {e}")
        return False, 0.0

    async def check_rpi_ollama_health(self) -> Tuple[bool, float]:
        """Verifica la conectividad con Ollama local en la Raspberry Pi 5"""
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{self.ollama_rpi_url}/api/version")
                if response.status_code == 200:
                    latency = round((time.time() - start) * 1000, 2)
                    return True, latency
        except Exception as e:
            logger.warning(f"Tier 3 (RPi Ollama local) inalcanzable: {e}")
        return False, 0.0

    async def get_active_provider(self) -> Tuple[str, str, str]:
        """
        Determina cuál proveedor de LLM está disponible según la cascada de resiliencia:
        1. PC Local LAN (qwen3.5:4b)
        2. Gemini Cloud API (dinámico según la cuenta del usuario)
        3. RPi Local Edge (qwen2.5:1.5b)
        Retorna: (tier_id, model_name, endpoint_url)
        """
        # Intentar Tier 1: PC Local LAN
        pc_ok, _ = await self.check_pc_ollama_health()
        if pc_ok:
            return "tier1_pc", self.ollama_pc_model, self.ollama_pc_url

        # Intentar Tier 2: Gemini Cloud API
        if self.gemini_api_key and self.gemini_api_key != "tu_api_key_aqui":
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    res = await client.get("https://generativelanguage.googleapis.com", timeout=2.0)
                    return "tier2_cloud", self.gemini_model, "https://generativelanguage.googleapis.com"
            except Exception:
                logger.warning("Tier 2 (Gemini Cloud API) inalcanzable o sin internet.")

        # Intentar Tier 3: RPi Edge Fallback
        rpi_ok, _ = await self.check_rpi_ollama_health()
        if rpi_ok:
            return "tier3_rpi", self.ollama_rpi_model, self.ollama_rpi_url

        # Si ninguno responde, usar fallback virtual informativo
        return "tier1_pc", self.ollama_pc_model, self.ollama_pc_url

    async def generate_response(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """
        Ejecuta la inferencia a través del proveedor activo del router con tolerancia a fallos.
        """
        tier_id, model_name, endpoint = await self.get_active_provider()
        start_time = time.time()

        if tier_id == "tier2_cloud":
            gemini_res = await gemini_service.generate_content(prompt, system_prompt)
            if gemini_res:
                elapsed = round((time.time() - start_time) * 1000, 2)
                return {
                    "response": gemini_res,
                    "tier": "Tier 2: Gemini Cloud",
                    "model": gemini_service.active_model,
                    "latency_ms": elapsed
                }

        if tier_id in ["tier1_pc", "tier3_rpi"]:
            url = f"{endpoint}/api/generate"
            payload = {
                "model": model_name,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False
            }
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        elapsed = round((time.time() - start_time) * 1000, 2)
                        return {
                            "response": data.get("response", ""),
                            "tier": "Tier 1: PC Local LAN" if tier_id == "tier1_pc" else "Tier 3: RPi Edge",
                            "model": model_name,
                            "latency_ms": elapsed
                        }
            except Exception as e:
                logger.error(f"Error generando inferencia en {tier_id}: {e}")

        # Fallback de simulación estructurada si la llamada directa no completa
        elapsed = round((time.time() - start_time) * 1000, 2)
        return {
            "response": f"[Simulación del Asistente Agéntico - Modelo {model_name}]: He procesado la consulta: '{prompt}'",
            "tier": "Tier 1: PC Local LAN" if tier_id == "tier1_pc" else ("Tier 2: Gemini Cloud" if tier_id == "tier2_cloud" else "Tier 3: RPi Edge"),
            "model": model_name,
            "latency_ms": elapsed
        }

# Instancia global exportada del router
llm_router = ResilientLLMRouter()
