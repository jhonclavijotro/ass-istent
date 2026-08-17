import os
import json
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger("gemini_service")

# Ruta segura de credenciales dentro del directorio montado dbs
CREDENTIALS_FILE = "/app/dbs/credentials.json"
# Ruta local alternativa si no existe /app/dbs
LOCAL_CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "dbs", "credentials.json")

def get_credentials_path() -> str:
    """Retorna la ruta válida para guardar credenciales de forma segura"""
    dbs_dir = "/app/dbs"
    if os.path.exists(dbs_dir):
        return CREDENTIALS_FILE
    
    local_dbs = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dbs"))
    os.makedirs(local_dbs, exist_ok=True)
    return os.path.join(local_dbs, "credentials.json")

class GeminiService:
    def __init__(self):
        self.api_key: str = ""
        self.active_model: str = "gemini-2.0-flash"
        self._load_saved_config()

    def _load_saved_config(self):
        """Carga la API key y el modelo seleccionado desde el archivo seguro de credenciales"""
        path = get_credentials_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.api_key = data.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
                    self.active_model = data.get("gemini_model", os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
                    logger.info(f"Credenciales de Gemini cargadas. Modelo activo: {self.active_model}")
            except Exception as e:
                logger.error(f"Error al leer archivo de credenciales: {e}")
        else:
            self.api_key = os.getenv("GEMINI_API_KEY", "")
            self.active_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def _save_config(self):
        """Guarda la API key y modelo activo en el archivo protegido de credenciales"""
        path = get_credentials_path()
        data = {
            "gemini_api_key": self.api_key,
            "gemini_model": self.active_model
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.chmod(path, 0o600)  # Permisos estrictos de lectura/escritura solo para el dueño
            logger.info("Credenciales de Gemini guardadas de forma segura.")
        except Exception as e:
            logger.error(f"Error al guardar credenciales de Gemini: {e}")

    async def fetch_available_models(self, key_to_test: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Consulta la API de Google Gemini para obtener los modelos disponibles asociados a la clave.
        """
        api_key = key_to_test or self.api_key
        if not api_key:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models_list = []
                    for model in data.get("models", []):
                        name = model.get("name", "").replace("models/", "")
                        methods = model.get("supportedGenerationMethods", [])
                        # Filtrar solo modelos que soporten generación de texto/contenido
                        if "generateContent" in methods:
                            models_list.append({
                                "id": name,
                                "displayName": model.get("displayName", name),
                                "description": model.get("description", "")
                            })
                    return models_list
                else:
                    logger.warning(f"Error al consultar modelos de Gemini: HTTP {res.status_code}")
        except Exception as e:
            logger.error(f"Excepción al conectar con la API de Gemini: {e}")
        return []

    async def update_key_and_get_models(self, new_key: str) -> List[Dict[str, str]]:
        """Prueba la nueva clave API, la almacena si es válida y retorna la lista de modelos disponibles"""
        models = await self.fetch_available_models(new_key)
        if models:
            self.api_key = new_key
            # Si el modelo activo actual no está entre los devueltos, seleccionar el primero
            model_ids = [m["id"] for m in models]
            if self.active_model not in model_ids:
                self.active_model = model_ids[0]
            self._save_config()
        return models

    def set_active_model(self, model_name: str) -> bool:
        """Actualiza el modelo de Gemini seleccionado para la cuenta"""
        self.active_model = model_name
        self._save_config()
        return True

# Instancia singleton del servicio Gemini
gemini_service = GeminiService()
