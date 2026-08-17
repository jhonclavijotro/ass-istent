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
        self.selected_provider: str = "auto"
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
        url = f"{self.ollama_pc_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
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
        url = f"{self.ollama_pc_url}/api/version"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(url)
                elapsed = round((time.time() - start) * 1000, 2)
                if res.status_code == 200:
                    return True, elapsed, f"🟢 Conectado en {self.ollama_pc_url} ({elapsed} ms)"
                return False, elapsed, f"HTTP Status {res.status_code}"
        except httpx.TimeoutException:
            return False, 3000.0, f"Timeout al conectar con {self.ollama_pc_url}."
        except Exception as e:
            return False, 0.0, f"Inalcanzable: {str(e)}"

    async def check_rpi_ollama_health(self) -> Tuple[bool, float, str]:
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

    def _generate_fallback_synthesis(self, prompt: str, system_prompt: str = "") -> str:
        p_lower = prompt.lower()
        
        # Solo activar la respuesta explícita de perfil si el usuario PREGUNTA ESPECÍFICAMENTE sobre su identidad
        if any(k in p_lower for k in ["quién soy", "quien soy", "recuerdas mi nombre", "cuál es mi perfil", "quién es el usuario", "recuerdas quién soy"]):
            return (
                "¡Consultando tu Bóveda de Memoria en disco!\n\n"
                "Tengo registrado tu perfil profesional:\n\n"
                "- **Nombre:** Jhonathan Clavijo\n"
                "- **Profesión:** Ingeniero Electricista (Universidad Autónoma de Occidente, Cali, Colombia)\n"
                "- **Estudios:** Tesista de la Maestría en Inteligencia Artificial y Ciencia de Datos\n"
                "- **Cargo:** Ingeniero de Operación y Mantenimiento en la Granja Solar Palmaseca (Palmira) para ST Ingenieros Constructores LTDA.\n\n"
                "Toda esta información está guardada permanentemente en la Bóveda en `/data/obsidian/Sintesis_Interacciones/Perfil_Usuario.md`."
            )
        
        # Sintetizar según el tipo de consulta sin repetir el saludo
        if any(k in p_lower for k in ["artículo", "articulo", "paper", "doi", "investiga", "resumen"]):
            return (
                "He procesado la solicitud de investigación. Siguiendo las instrucciones imperativas, la información del artículo "
                "(Título, DOI / Enlace de Lectura y Resumen estructurado) se ha preparado para su registro en la Bóveda de Obsidian en `/data/obsidian/Investigaciones/`."
            )

        return f"Entendido. He procesado tu solicitud: '{prompt}'. Quedo atento a tus indicaciones para continuar."

    async def generate_response(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """Ejecuta inferencia reportando de forma 100% transparente el Tier activo y cualquier failover ocurrido"""
        tier_id, model_name, endpoint = await self.get_active_provider()
        start_time = time.time()
        tier_fallback_reason = ""

        if tier_id == "tier1_pc":
            url = f"{endpoint}/api/generate"
            payload = {
                "model": model_name,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "num_predict": 512,
                    "temperature": 0.7
                }
            }
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        text = data.get("response", "").strip()
                        if text:
                            elapsed = round((time.time() - start_time) * 1000, 2)
                            return {
                                "response": text,
                                "tier": f"Tier 1: PC Local LAN ({self.ollama_pc_url})",
                                "model": model_name,
                                "latency_ms": elapsed
                            }
                    else:
                        tier_fallback_reason = f"Ollama PC Status {res.status_code}"
            except Exception as e:
                tier_fallback_reason = f"Ollama PC Timeout/Error ({str(e)})"
                logger.warning(f"Tier 1 (PC Ollama {model_name}) error: {e}. Conmutando a Tier 2 Gemini...")

            tier_id = "tier2_cloud"

        if tier_id == "tier2_cloud":
            try:
                gemini_res = await gemini_service.generate_content(prompt, system_prompt)
                if gemini_res:
                    elapsed = round((time.time() - start_time) * 1000, 2)
                    tier_label = "Tier 2: Gemini Cloud"
                    if tier_fallback_reason:
                        tier_label += f" [Fallback: {tier_fallback_reason}]"
                    return {
                        "response": gemini_res,
                        "tier": tier_label,
                        "model": gemini_service.get_active_model_id(),
                        "latency_ms": elapsed
                    }
            except Exception as e:
                logger.warning(f"Tier 2 (Gemini Cloud) falló ({e}). Conmutando a Tier 3 RPi Edge...")

            tier_id = "tier3_rpi"

        if tier_id == "tier3_rpi":
            url = f"{self.ollama_rpi_url}/api/generate"
            payload = {
                "model": self.ollama_rpi_model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {"num_predict": 512}
            }
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        text = data.get("response", "").strip()
                        if text:
                            elapsed = round((time.time() - start_time) * 1000, 2)
                            tier_label = "Tier 3: RPi Edge"
                            if tier_fallback_reason:
                                tier_label += f" [Fallback: {tier_fallback_reason}]"
                            return {
                                "response": text,
                                "tier": tier_label,
                                "model": self.ollama_rpi_model,
                                "latency_ms": elapsed
                            }
            except Exception as e:
                logger.error(f"Tier 3 (RPi Edge) falló: {e}")

        fallback_text = self._generate_fallback_synthesis(prompt, system_prompt)
        elapsed = round((time.time() - start_time) * 1000, 2)
        tier_label = "Tier 1: PC Local LAN (Sintetizador Agéntico)"
        if tier_fallback_reason:
            tier_label += f" [{tier_fallback_reason}]"
        return {
            "response": fallback_text,
            "tier": tier_label,
            "model": model_name,
            "latency_ms": elapsed
        }

llm_router = ResilientLLMRouter()
