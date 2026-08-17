import os
import shutil
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("filesystem_tool")

# Directorio base permitido para operaciones de archivo en la RPi 5
BASE_DATA_DIR = "/app/data" if os.path.exists("/app/data") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

class FileSystemManager:
    def __init__(self, base_dir: str = BASE_DATA_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, relative_or_abs_path: str) -> str:
        """Resuelve y valida la ruta dentro de las carpetas permitidas de /app/data"""
        clean = relative_or_abs_path.strip().lstrip("/")
        if clean.startswith("app/data/"):
            clean = clean[9:]
        elif clean.startswith("data/"):
            clean = clean[5:]
            
        full_path = os.path.abspath(os.path.join(self.base_dir, clean))
        # Garantizar que la ruta no escape fuera de base_dir (Protección Path Traversal)
        if not full_path.startswith(os.path.abspath(self.base_dir)):
            raise ValueError(f"Acceso denegado: La ruta '{relative_or_abs_path}' está fuera del directorio del sistema.")
        return full_path

    def list_files(self, subfolder: str = "") -> List[Dict[str, Any]]:
        """Lista archivos y carpetas dentro de la ruta especificada"""
        try:
            target = self._resolve_path(subfolder)
            if not os.path.exists(target):
                return []
            
            results = []
            for entry in os.listdir(target):
                full_item = os.path.join(target, entry)
                is_dir = os.path.isdir(full_item)
                size = os.path.getsize(full_item) if not is_dir else 0
                rel_path = os.path.relpath(full_item, self.base_dir)
                results.append({
                    "name": entry,
                    "path": rel_path.replace("\\", "/"),
                    "is_directory": is_dir,
                    "size_bytes": size
                })
            return results
        except Exception as e:
            logger.error(f"Error al listar archivos en '{subfolder}': {e}")
            return []

    def create_file(self, path: str, content: str) -> bool:
        """Crea un nuevo archivo en el sistema de la RPi 5"""
        try:
            full_path = self._resolve_path(path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Archivo '{full_path}' creado exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al crear archivo '{path}': {e}")
            return False

    def modify_file(self, path: str, content: str, append: bool = True) -> bool:
        """Modifica o anexa contenido a un archivo existente"""
        try:
            full_path = self._resolve_path(path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            mode = "a" if append else "w"
            with open(full_path, mode, encoding="utf-8") as f:
                if append and os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                    f.write("\n\n")
                f.write(content)
            logger.info(f"Archivo '{full_path}' modificado exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al modificar archivo '{path}': {e}")
            return False

    def delete_file(self, path: str) -> bool:
        """Elimina físicamente un archivo o carpeta en la RPi 5"""
        try:
            full_path = self._resolve_path(path)
            if not os.path.exists(full_path):
                logger.warning(f"Intento de eliminar archivo no existente '{full_path}'.")
                return False
            
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            logger.info(f"Archivo/Carpeta '{full_path}' eliminado físicamente.")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar archivo '{path}': {e}")
            return False

filesystem_manager = FileSystemManager()
