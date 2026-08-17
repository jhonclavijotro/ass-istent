import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from app.tools.obsidian_tool import obsidian_manager
from app.tools.finance_tool import finance_manager
from app.tools.pdf_watchdog import PDFS_DIR, pdf_watchdog_service
from app.tools.google_workspace import google_workspace_manager
from app.tools.filesystem_tool import filesystem_manager

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

class CreateFileRequest(BaseModel):
    path: str
    content: str

class ModifyFileRequest(BaseModel):
    path: str
    content: str
    append: Optional[bool] = True

class DeleteFileRequest(BaseModel):
    path: str

@router.get("/obsidian/notes")
def list_obsidian_notes():
    """Lista las notas Markdown disponibles en la bóveda de Obsidian"""
    notes = obsidian_manager.list_notes()
    return {"vault_path": obsidian_manager.vault_dir, "count": len(notes), "notes": notes}

@router.get("/obsidian/read")
def read_obsidian_note(filename: str):
    """Lee el contenido de una nota de Obsidian para visualizarla en el navegador"""
    content = obsidian_manager.get_note_content(filename)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Nota '{filename}' no encontrada.")
    return {"filename": filename, "content": content}

@router.get("/obsidian/download")
def download_obsidian_note(filename: str):
    """Descarga la nota de Obsidian al PC del usuario como archivo .md"""
    if not filename.endswith(".md"):
        filename += ".md"
    full_path = os.path.join(obsidian_manager.vault_dir, filename)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"Nota '{filename}' no encontrada.")
    return FileResponse(
        path=full_path,
        filename=os.path.basename(filename),
        media_type="text/markdown"
    )

@router.post("/obsidian/note")
def create_obsidian_note(request: CreateNoteRequest):
    """Crea o actualiza una nota en la bóveda de Obsidian"""
    ok = obsidian_manager.create_or_update_note(request.filename, request.content, request.append)
    if not ok:
        raise HTTPException(status_code=500, detail="Error al escribir nota en Obsidian.")
    return {"status": "success", "filename": request.filename}

@router.post("/rag/upload-pdf")
async def upload_pdf_to_rag(file: UploadFile = File(...)):
    """Recibe un archivo PDF subido desde el navegador y lo auto-indexa en el RAG (Qdrant)"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos en formato PDF.")

    os.makedirs(PDFS_DIR, exist_ok=True)
    target_path = os.path.join(PDFS_DIR, file.filename)

    try:
        contents = await file.read()
        with open(target_path, "wb") as f:
            f.write(contents)
            
        pdf_watchdog_service.indexer.process_pdf(target_path)
        
        return {
            "status": "success",
            "message": f"Archivo '{file.filename}' cargado e indexado exitosamente en el RAG.",
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el archivo PDF: {str(e)}")

@router.get("/file/list")
def list_rpi_files(subfolder: Optional[str] = ""):
    """Lista archivos en el sistema de almacenamiento de la RPi 5 (/app/data)"""
    files = filesystem_manager.list_files(subfolder)
    return {"base_dir": filesystem_manager.base_dir, "count": len(files), "files": files}

@router.post("/file/create")
def create_rpi_file(request: CreateFileRequest):
    """Crea un nuevo archivo en el sistema de la RPi 5"""
    ok = filesystem_manager.create_file(request.path, request.content)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Error al crear archivo '{request.path}'.")
    return {"status": "success", "path": request.path}

@router.post("/file/modify")
def modify_rpi_file(request: ModifyFileRequest):
    """Modifica o anexa contenido a un archivo en la RPi 5"""
    ok = filesystem_manager.modify_file(request.path, request.content, request.append)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Error al modificar archivo '{request.path}'.")
    return {"status": "success", "path": request.path}

@router.post("/file/delete")
def delete_rpi_file(request: DeleteFileRequest):
    """Elimina físicamente un archivo o carpeta en la RPi 5"""
    ok = filesystem_manager.delete_file(request.path)
    if not ok:
        raise HTTPException(status_code=500, detail=f"Error al eliminar archivo '{request.path}'.")
    return {"status": "success", "path": request.path}

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

@router.get("/google/status")
def google_status():
    """Estado de la integración de Google Workspace"""
    return google_workspace_manager.get_integration_status()
