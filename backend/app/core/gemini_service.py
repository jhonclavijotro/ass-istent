import os
import json
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger("gemini_service")

CREDENTIALS_FILE = "/app/dbs/credentials.json"

def get_credentials_path() -> str:
    dbs_dir = "/app/dbs"
    if os.path.exists(dbs_dir):
        return CREDENTIALS_FILE
    local_dbs = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dbs"))
    os.makedirs(local_dbs, exist_ok=True)
    return os.path.join(local_dbs, "credentials.json")

# Lista de modelos estándar de respaldo para Gemini
DEFAULT_GEMINI_MODELS = [
    {"id": "gemini-2.0-flash", "displayName": "Gemini 2.0 Flash (Recomendado)", "description": "Rápido y multimodal"},
    {"id": "gemini-1.5-flash", "displayName": "Gemini 1.5 Flash", "description": "Alta velocidad y contexto extenso"},
    {"id": "gemini-1.5-pro", "displayName": "Gemini 1.5 Pro", "description": "Razonamiento complejo"},
    {"id": "gemini-2.0-flash-lite", "displayName": "Gemini 2.0 Flash Lite", "description": "Ultraligero y económico"},
    {"id": "gemini-1.0-pro", "displayName": "Gemini 1.0 Pro", "description": "Modelo clásico de texto"}
]

class GeminiService:
    def __init__(self):
        self.api_key: str = ""
        self.active_model: str = "gemini-2.0-flash"
        self._load_saved_config()

    def _load_saved_config(self):
        path = get_credentials_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.api_key = data.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
                    raw_model = data.get("gemini_model", os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
                    self.active_model = raw_model.replace("models/", "")
                    logger.info(f"Credenciales de Gemini cargadas. Modelo activo: {self.active_model}")
            except Exception as e:
                logger.error(f"Error al leer credenciales: {e}")
        else:
            self.api_key = os.getenv("GEMINI_API_KEY", "")
            raw_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            self.active_model = raw_model.replace("models/", "")

    def _save_config(self):
        path = get_credentials_path()
        data = {
            "gemini_api_key": self.api_key,
            "gemini_model": self.active_model
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.chmod(path, 0o600)
            logger.info("Credenciales de Gemini guardadas con éxito.")
        except Exception as e:
            logger.error(f"Error al guardar credenciales: {e}")

    async def fetch_available_models(self, key_to_test: Optional[str] = None) -> List[Dict[str, str]]:
        api_key = key_to_test or self.api_key
        if not api_key:
            return DEFAULT_GEMINI_MODELS

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    fetched = []
                    for m in data.get("models", []):
                        name = m.get("name", "").replace("models/", "")
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            fetched.append({
                                "id": name,
                                "displayName": m.get("displayName", name),
                                "description": m.get("description", "")
                            })
                    if fetched:
                        return fetched
        except Exception as e:
            logger.warning(f"No se pudo consultar API de modelos de Gemini: {e}")
        
        return DEFAULT_GEMINI_MODELS

    async def update_key_and_get_models(self, new_key: str) -> List[Dict[str, str]]:
        models = await self.fetch_available_models(new_key)
        self.api_key = new_key
        if models and self.active_model not in [m["id"] for m in models]:
            self.active_model = models[0]["id"]
        self._save_config()
        return models

    def set_active_model(self, model_name: str) -> bool:
        clean_name = model_name.replace("models/", "").strip()
        self.active_model = clean_name
        self._save_config()
        logger.info(f"Modelo de Gemini actualizado a: {clean_name}")
        return True

    async def generate_content(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Genera respuesta usando la API REST oficial de Google Gemini v1beta"""
        if not self.api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.active_model}:generateContent?key={self.api_key}"
        
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"Instrucción del Sistema: {system_prompt}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {"contents": contents}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    logger.error(f"Gemini API retornó código HTTP {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Error al generar inferencia con Gemini API: {e}")
        return None

gemini_service = GeminiService()
