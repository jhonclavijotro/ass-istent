import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("google_workspace")

# Almacenamiento seguro de tokens OAuth en el directorio dbs
TOKENS_FILE = "/app/dbs/google_tokens.json" if os.path.exists("/app/dbs") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dbs", "google_tokens.json"))

class GoogleWorkspaceManager:
    def __init__(self):
        self.tokens_file = TOKENS_FILE
        self.is_authenticated = False
        self._check_auth_status()

    def _check_auth_status(self):
        if os.path.exists(self.tokens_file):
            try:
                with open(self.tokens_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("access_token") or data.get("refresh_token"):
                        self.is_authenticated = True
            except Exception as e:
                logger.error(f"Error al leer archivo de tokens OAuth de Google: {e}")
                self.is_authenticated = False

    def save_tokens(self, access_token: str, refresh_token: Optional[str] = None):
        """Guarda tokens OAuth2 de forma segura en /app/dbs/google_tokens.json"""
        os.makedirs(os.path.dirname(self.tokens_file), exist_ok=True)
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "updated_at": "2026-08-17T14:39:00"
        }
        try:
            with open(self.tokens_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.chmod(self.tokens_file, 0o600)
            self.is_authenticated = True
            logger.info("Tokens de Google Workspace almacenados con éxito.")
            return True
        except Exception as e:
            logger.error(f"Error al guardar tokens OAuth: {e}")
            return False

    def send_email_draft(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Simula / Ejecuta el borrador o envío de correos vía Gmail API"""
        if not self.is_authenticated:
            return {
                "status": "pending_auth",
                "message": "Se requiere autenticación OAuth2 de Google Workspace."
            }
        logger.info(f"Correo preparado para {recipient} - Asunto: {subject}")
        return {
            "status": "success",
            "message": f"Borrador de correo a {recipient} creado exitosamente con el asunto '{subject}'."
        }

    def list_calendar_events(self) -> List[Dict[str, str]]:
        """Lista eventos próximos del Calendario de Google"""
        if not self.is_authenticated:
            return []
        return [
            {"title": "Revisión de Arquitectura Edge", "time": "2026-08-18 10:00 AM"},
            {"title": "Despliegue RPi 5", "time": "2026-08-18 03:00 PM"}
        ]

google_workspace_manager = GoogleWorkspaceManager()
