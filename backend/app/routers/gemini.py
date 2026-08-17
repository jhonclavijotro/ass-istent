from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.gemini_service import gemini_service

router = APIRouter(prefix="/api/gemini", tags=["Gemini Configuration"])

class GeminiKeyRequest(BaseModel):
    api_key: str

class GeminiModelSelectRequest(BaseModel):
    model: str

class GeminiConfigResponse(BaseModel):
    has_key: bool
    active_model: str
    available_models: List[dict]

@router.get("/config", response_model=GeminiConfigResponse)
async def get_gemini_config():
    """Obtiene la configuración actual de Gemini y la lista de modelos disponibles para la clave registrada"""
    has_key = bool(gemini_service.api_key)
    models = []
    if has_key:
        models = await gemini_service.fetch_available_models()
        
    return GeminiConfigResponse(
        has_key=has_key,
        active_model=gemini_service.active_model,
        available_models=models
    )

@router.post("/key")
async def update_gemini_key(request: GeminiKeyRequest):
    """
    Recibe la clave de API de Gemini, la valida contra los servidores de Google,
    la almacena de forma segura y devuelve la lista de modelos disponibles para la cuenta.
    """
    if not request.api_key.strip():
        raise HTTPException(status_code=400, detail="La API Key no puede estar vacía.")
        
    models = await gemini_service.update_key_and_get_models(request.api_key.strip())
    if not models:
        raise HTTPException(status_code=400, detail="La API Key provista es inválida o la cuenta no tiene modelos de generación disponibles.")
        
    return {
        "status": "success",
        "message": "API Key de Gemini almacenada de forma segura.",
        "active_model": gemini_service.active_model,
        "available_models": models
    }

@router.post("/select-model")
def select_gemini_model(request: GeminiModelSelectRequest):
    """Permite al usuario seleccionar el modelo activo de Gemini desde el desplegable"""
    if not request.model.strip():
        raise HTTPException(status_code=400, detail="Debe especificar un nombre de modelo válido.")
        
    gemini_service.set_active_model(request.model.strip())
    return {
        "status": "success",
        "message": f"Modelo activo de Gemini actualizado a '{gemini_service.active_model}'.",
        "active_model": gemini_service.active_model
    }
