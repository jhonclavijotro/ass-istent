import os
import time
import json
import logging
import httpx
from typing import Dict, Any, Tuple, List
from app.core.gemini_service import gemini_service

logger = logging.getLogger("llm_router")

SYSTEM_CONFIG_FILE = "/app/dbs/system_config.json"

def get_system_config_path() -> str:
    dbs_dir = "/app/dbs"
    if os.path.exists(dbs_dir):
        os.makedirs(dbs_dir, exist_ok=True)
        return SYSTEM_CONFIG_FILE
    local_dbs = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dbs"))
    os.makedirs(local_dbs, exist_ok=True)
    return os.path.join(local_dbs, "system_config.json")

class ResilientLLMRouter:
    def __init__(self):
        self.ollama_pc_url: str = os.getenv("OLLAMA_PC_URL", "http://192.168.1.9:11434")
        self.ollama_pc_model: str = os.getenv("OLLAMA_PC_MODEL", "qwen3.5:4b")
        self.ollama_rpi_url: str = os.getenv("OLLAMA_RPI_URL", "http://localhost:11434")
        self.ollama_rpi_model: str = os.getenv("OLLAMA_RPI_MODEL", "qwen2.5:1.5b")
        self.selected_provider: str = "auto"  # "auto", "tier1_pc", "tier2_cloud", "tier3_rpi"
        self._load_system_config()

    def _load_system_config(self):
        path = get_system_config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ollama_pc_url = data.get("ollama_pc_url", self.ollama_pc_url)
                    self.ollama_pc_model = data.get("ollama_pc_model", self.ollama_pc_model)
                    self.selected_provider = data.get("selected_provider", "auto")
            except Exception as e:
                logger.error(f"Error al leer system_config.json: {e}")

    def save_system_config(self):
        path = get_system_config_path()
        data = {
            "ollama_pc_url": self.ollama_pc_url,
            "ollama_pc_model": self.ollama_pc_model,
            "selected_provider": self.selected_provider
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error al guardar system_config.json: {e}")

    def update_pc_url(self, new_url: str):
        cleaned = new_url.strip().rstrip("/")
        if not cleaned.startswith("http"):
            cleaned = f"http://{cleaned}"
        self.ollama_pc_url = cleaned
        self.save_system_config()

    def set_pc_model(self, model_name: str):
        self.ollama_pc_model = model_name.strip()
        self.save_system_config()

    def set_selected_provider(self, mode: str):
        valid = ["auto", "tier1_pc", "tier2_cloud", "tier3_rpi"]
        if mode in valid:
            self.selected_provider = mode
            self.save_system_config()

    async def fetch_pc_ollama_models(self) -> List[str]:
        """Obtiene la lista de modelos instalados en la instancia local de Ollama"""
        url = f"{self.ollama_pc_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    if models:
                        return models
        except Exception as e:
            logger.warning(f"No se pudieron consultar modelos de Ollama PC en {url}: {e}")
        return [self.ollama_pc_model]

    async def check_pc_ollama_health(self) -> Tuple[bool, float, str]:
        """Prueba de conectividad con el PC de Cómputo Local (Ollama)"""
        url = f"{self.ollama_pc_url}/api/version"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url)
                elapsed = round((time.time() - start) * 1000, 2)
                if res.status_code == 200:
                    return True, elapsed, f"🟢 Conectado en {self.ollama_pc_url} ({elapsed} ms)"
                return False, elapsed, f"HTTP Status {res.status_code}"
        except httpx.TimeoutException:
            return False, 4000.0, f"Timeout al conectar con {self.ollama_pc_url}. Revisa IP/Firewall."
        except Exception as e:
            return False, 0.0, f"Inalcanzable en {self.ollama_pc_url}: {str(e)}"

    async def check_rpi_ollama_health(self) -> Tuple[bool, float, str]:
        """Prueba de conectividad con Ollama en la Raspberry Pi 5"""
        url = f"{self.ollama_rpi_url}/api/version"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(url)
                elapsed = round((time.time() - start) * 1000, 2)
                if res.status_code == 200:
                    return True, elapsed, f"OK ({elapsed} ms)"
                return False, elapsed, f"HTTP Status {res.status_code}"
        except Exception as e:
            return False, 0.0, f"Offline: {str(e)}"

    async def check_gemini_health(self) -> Tuple[bool, str]:
        api_key = gemini_service.get_active_api_key()
        model_name = gemini_service.get_active_model_id()
        if not api_key or api_key == "tu_api_key_aqui":
            return False, "Sin API Key de Gemini"
        return True, f"Key Configurada ({model_name})"

    async def get_active_provider(self) -> Tuple[str, str, str]:
        self._load_system_config()
        mode = self.selected_provider

        active_gemini_model = gemini_service.get_active_model_id()

        if mode == "tier1_pc":
            return "tier1_pc", self.ollama_pc_model, self.ollama_pc_url
        elif mode == "tier2_cloud":
            return "tier2_cloud", active_gemini_model, "https://generativelanguage.googleapis.com"
        elif mode == "tier3_rpi":
            return "tier3_rpi", self.ollama_rpi_model, self.ollama_rpi_url

        # MODO AUTOMÁTICO (FAILOVER RESILIENTE DE 3 NIVELES)
        pc_ok, _, _ = await self.check_pc_ollama_health()
        if pc_ok:
            return "tier1_pc", self.ollama_pc_model, self.ollama_pc_url

        gemini_ok, _ = await self.check_gemini_health()
        if gemini_ok:
            return "tier2_cloud", active_gemini_model, "https://generativelanguage.googleapis.com"

        rpi_ok, _, _ = await self.check_rpi_ollama_health()
        if rpi_ok:
            return "tier3_rpi", self.ollama_rpi_model, self.ollama_rpi_url

        return "tier1_pc", self.ollama_pc_model, self.ollama_pc_url

    async def generate_response(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """Ejecuta inferencia con timeout de 120s para tolerar carga de modelo en VRAM"""
        tier_id, model_name, endpoint = await self.get_active_provider()
        start_time = time.time()

        if tier_id == "tier2_cloud":
            gemini_res = await gemini_service.generate_content(prompt, system_prompt)
            if gemini_res:
                elapsed = round((time.time() - start_time) * 1000, 2)
                return {
                    "response": gemini_res,
                    "tier": "Tier 2: Gemini Cloud",
                    "model": gemini_service.get_active_model_id(),
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
                # Timeout extenso (120s) para soportar la carga inicial del modelo en memoria GPU/RAM
                async with httpx.AsyncClient(timeout=120.0) as client:
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
                logger.error(f"Error generando inferencia en {tier_id} ({url}): {e}")

        elapsed = round((time.time() - start_time) * 1000, 2)
        return {
            "response": f"[Simulación del Asistente Agéntico - Modelo {model_name}]: He procesado la consulta: '{prompt}'",
            "tier": "Tier 1: PC Local LAN" if tier_id == "tier1_pc" else ("Tier 2: Gemini Cloud" if tier_id == "tier2_cloud" else "Tier 3: RPi Edge"),
            "model": model_name,
            "latency_ms": elapsed
        }

llm_router = ResilientLLMRouter()
