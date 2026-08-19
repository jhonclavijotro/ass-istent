import os
import re
import urllib.request
import urllib.parse
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("pdf_downloader")

# Ruta exclusiva para descargas (fuera del folder RAG /data/pdfs/)
DOWNLOADS_DIR = "/app/data/downloads" if os.path.exists("/app/data/downloads") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "downloads"))
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

class OpenAccessPDFDownloader:
    """Descargador de artículos científicos en formato PDF desde fuentes de acceso libre (arXiv, Unpaywall, DOIs OA).
    Guarda los archivos exclusivamente en /data/downloads/."""

    def __init__(self, target_dir: str = DOWNLOADS_DIR):
        self.target_dir = target_dir
        os.makedirs(self.target_dir, exist_ok=True)

    def _sanitize_filename(self, title: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', title.replace(' ', '_'))
        clean = re.sub(r'_+', '_', clean).strip('_')[:50]
        if not clean.endswith(".pdf"):
            clean += ".pdf"
        return clean

    def download_pdf_from_url(self, url: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """Descarga un PDF desde una URL directa y lo almacena en /data/downloads/"""
        import ssl
        try:
            filename = self._sanitize_filename(custom_name) if custom_name else self._sanitize_filename(os.path.basename(url))
            target_path = os.path.join(self.target_dir, filename)

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            
            ssl_context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response, open(target_path, "wb") as out_file:
                content = response.read()
                out_file.write(content)

            file_size_kb = round(os.path.getsize(target_path) / 1024, 2)
            logger.info(f"PDF descargado exitosamente: '{filename}' ({file_size_kb} KB) en '{target_path}'.")
            return {
                "success": True,
                "filename": filename,
                "filepath": target_path,
                "size_kb": file_size_kb,
                "source_url": url
            }
        except Exception as e:
            logger.error(f"Error al descargar PDF desde '{url}': {e}")
            return {"success": False, "error": str(e), "source_url": url}

    def download_arxiv_pdf(self, arxiv_input: str) -> Dict[str, Any]:
        """Descarga un PDF de arXiv dado un ID (ej. '2301.00001') o URL de abs/pdf"""
        arxiv_match = re.search(r'(\d{4}\.\d{4,5}(?:v\d+)?)', arxiv_input)
        if not arxiv_match:
            return {"success": False, "error": f"No se pudo extraer un ID válido de arXiv desde '{arxiv_input}'."}
        
        arxiv_id = arxiv_match.group(1)
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        filename = f"arXiv_{arxiv_id}.pdf"
        return self.download_pdf_from_url(pdf_url, filename)

    def list_downloaded_pdfs(self) -> List[Dict[str, Any]]:
        """Lista todos los PDFs almacenados en la carpeta /data/downloads/"""
        results = []
        if os.path.exists(self.target_dir):
            for fname in os.listdir(self.target_dir):
                if fname.endswith(".pdf"):
                    fpath = os.path.join(self.target_dir, fname)
                    results.append({
                        "filename": fname,
                        "filepath": fpath,
                        "size_kb": round(os.path.getsize(fpath) / 1024, 2)
                    })
        return results

pdf_downloader = OpenAccessPDFDownloader()
