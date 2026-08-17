import os
import glob
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("obsidian_tool")

OBSIDIAN_DIR = "/app/data/obsidian" if os.path.exists("/app/data/obsidian") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "obsidian"))

class ObsidianVaultManager:
    def __init__(self, vault_dir: str = OBSIDIAN_DIR):
        self.vault_dir = vault_dir
        os.makedirs(self.vault_dir, exist_ok=True)

    def list_notes(self) -> List[str]:
        """Lista todas las notas Markdown disponibles en la bóveda de Obsidian"""
        pattern = os.path.join(self.vault_dir, "**", "*.md")
        files = glob.glob(pattern, recursive=True)
        rel_files = [os.path.relpath(f, self.vault_dir) for f in files]
        return rel_files

    def get_note_content(self, filename: str) -> Optional[str]:
        """Lee y devuelve el texto plano de la nota"""
        if not filename.endswith(".md"):
            filename += ".md"
        full_path = os.path.join(self.vault_dir, filename)
        if not os.path.exists(full_path):
            return None
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error al leer nota Obsidian '{filename}': {e}")
            return None

    def create_or_update_note(self, filename: str, content: str, append: bool = False) -> bool:
        """Crea una nueva nota Markdown o la actualiza en la bóveda, creando subcarpetas automáticamente"""
        if not filename.endswith(".md"):
            filename += ".md"
        full_path = os.path.join(self.vault_dir, filename)
        
        # Garantizar que subcarpetas como Sintesis_Interacciones/, Investigaciones/, etc. existan
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        mode = "a" if append else "w"
        try:
            with open(full_path, mode, encoding="utf-8") as f:
                if append and os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                    f.write("\n\n")
                f.write(content)
            logger.info(f"Nota Obsidian '{filename}' {'actualizada' if append else 'creada'} en '{full_path}'.")
            return True
        except Exception as e:
            logger.error(f"Error al escribir nota Obsidian '{filename}': {e}")
            return False

    def search_notes(self, keyword: str) -> List[Dict[str, str]]:
        """Busca notas Markdown por palabra clave en título o contenido"""
        results = []
        notes = self.list_notes()
        keyword_lower = keyword.lower()
        for note in notes:
            content = self.get_note_content(note) or ""
            if keyword_lower in note.lower() or keyword_lower in content.lower():
                snippet = content[:200].replace("\n", " ") + "..." if content else "Sin contenido"
                results.append({
                    "title": note,
                    "snippet": snippet
                })
        return results

obsidian_manager = ObsidianVaultManager()
