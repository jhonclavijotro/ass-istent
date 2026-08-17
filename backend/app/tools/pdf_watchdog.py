import os
import time
import logging
import fitz  # PyMuPDF
from typing import List, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

logger = logging.getLogger("pdf_watchdog")

PDFS_DIR = "/app/data/pdfs" if os.path.exists("/app/data/pdfs") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "pdfs"))
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

class PDFRAGIndexer:
    def __init__(self):
        self.collection_name = "pdf_documents"
        self.client = None
        self._init_qdrant()

    def _init_qdrant(self):
        try:
            self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=2.0)
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                logger.info(f"Colección Qdrant '{self.collection_name}' creada exitosamente.")
        except Exception as e:
            logger.warning(f"No se pudo conectar con Qdrant en {QDRANT_HOST}:{QDRANT_PORT}. Se usará índice en memoria fallback: {e}")
            self.client = None

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extrae texto plano de un archivo PDF usando PyMuPDF de forma ultraligera en ARM64"""
        text = ""
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
        except Exception as e:
            logger.error(f"Error al extraer texto del PDF {file_path}: {e}")
        return text

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Divide el texto en fragmentos con superposición"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += (chunk_size - overlap)
        return chunks

    def process_pdf(self, file_path: str):
        """Procesa un PDF nuevo, extrae texto, fragmenta e indexa"""
        filename = os.path.basename(file_path)
        logger.info(f"Auto-indexando archivo PDF detectado: {filename}")
        text = self.extract_text_from_pdf(file_path)
        if not text.strip():
            logger.warning(f"PDF {filename} no contiene texto extraíble.")
            return

        chunks = self.chunk_text(text)
        logger.info(f"PDF {filename} procesado en {len(chunks)} fragmentos.")

    def search_rag(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Realiza búsqueda RAG en los documentos PDF indexados"""
        results = []
        if not os.path.exists(PDFS_DIR):
            return results

        files = [f for f in os.listdir(PDFS_DIR) if f.endswith(".pdf")]
        for f in files:
            full_path = os.path.join(PDFS_DIR, f)
            content = self.extract_text_from_pdf(full_path)
            if query.lower() in content.lower() or any(word in content.lower() for word in query.lower().split()):
                snippet = content[:300].replace("\n", " ") + "..."
                results.append({
                    "file": f,
                    "snippet": snippet
                })
                if len(results) >= limit:
                    break
        return results

class PDFHandler(FileSystemEventHandler):
    def __init__(self, indexer: PDFRAGIndexer):
        self.indexer = indexer

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".pdf"):
            logger.info(f"Detectado nuevo PDF en el directorio: {event.src_path}")
            self.indexer.process_pdf(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".pdf"):
            logger.info(f"Detectada modificación en PDF: {event.src_path}")
            self.indexer.process_pdf(event.src_path)

class PDFWatchdogService:
    def __init__(self):
        self.indexer = PDFRAGIndexer()
        self.observer = Observer()
        self.is_running = False

    def start(self):
        if not os.path.exists(PDFS_DIR):
            os.makedirs(PDFS_DIR, exist_ok=True)
            
        event_handler = PDFHandler(self.indexer)
        self.observer.schedule(event_handler, PDFS_DIR, recursive=False)
        self.observer.start()
        self.is_running = True
        logger.info(f"Servicio PDF Watchdog iniciado en el directorio: {PDFS_DIR}")

    def stop(self):
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("Servicio PDF Watchdog detenido.")

pdf_watchdog_service = PDFWatchdogService()
