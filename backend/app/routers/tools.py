import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.tools.obsidian_tool import obsidian_manager
from app.tools.finance_tool import finance_manager
from app.tools.pdf_watchdog import PDFS_DIR
from app.tools.google_workspace import google_workspace_manager

router = APIRouter(prefix="/api/tools", tags=["Tools & Integrations"])

class CreateNoteRequest(BaseModel):
    filename: str
    content: str
    append: Optional[bool] = False

class AddFinanceRecordRequest(BaseModel):
    filename: str
    concepto: str
    monto: float
    categoria: Optional[str] = "General"

@router.get("/obsidian/notes")
def list_obsidian_notes():
    """Lista las notas Markdown disponibles en la bóveda de Obsidian"""
    notes = obsidian_manager.list_notes()
    return {"vault_path": obsidian_manager.vault_dir, "count": len(notes), "notes": notes}

@router.post("/obsidian/note")
def create_obsidian_note(request: CreateNoteRequest):
    """Crea o actualiza una nota en la bóveda de Obsidian"""
    ok = obsidian_manager.create_or_update_note(request.filename, request.content, request.append)
    if not ok:
        raise HTTPException(status_code=500, detail="Error al escribir nota en Obsidian.")
    return {"status": "success", "filename": request.filename}

@router.get("/finance/files")
def list_finance_files():
    """Lista los archivos financieros en /app/data/finanzas"""
    files = finance_manager.list_financial_files()
    return {"dir_path": finance_manager.dir_path, "count": len(files), "files": files}

@router.post("/finance/record")
def add_finance_record(request: AddFinanceRecordRequest):
    """Agrega un registro de gasto o ingreso en archivo CSV"""
    ok = finance_manager.add_financial_record(request.filename, request.concepto, request.monto, request.categoria)
    if not ok:
        raise HTTPException(status_code=500, detail="Error al agregar registro financiero.")
    return {"status": "success", "record": request.dict()}

@router.get("/pdfs")
def list_pdfs():
    """Lista los documentos PDF en la carpeta de ingesta RAG"""
    pdfs = []
    if os.path.exists(PDFS_DIR):
        pdfs = [f for f in os.listdir(PDFS_DIR) if f.endswith(".pdf")]
    return {"pdf_dir": PDFS_DIR, "count": len(pdfs), "files": pdfs}

@router.get("/google/status")
def google_status():
    """Estado de autenticación OAuth2 de Google Workspace"""
    return {
        "authenticated": google_workspace_manager.is_authenticated,
        "tokens_file": google_workspace_manager.tokens_file
    }
