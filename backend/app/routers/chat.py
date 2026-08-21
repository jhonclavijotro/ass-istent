import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.graph import agent_graph
from app.core.llm_router import llm_router
from app.core.gemini_service import gemini_service

router = APIRouter(prefix="/api", tags=["Chat & Multi-Agent"])

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ActionApprovalRequest(BaseModel):
    thread_id: str
    action_id: Optional[str] = None
    approved: Optional[bool] = True
    feedback: Optional[str] = None

class ChatResponse(BaseModel):
    status: str  # "COMPLETED" | "AWAITING_USER_APPROVAL"
    response: Optional[str] = "Respuesta generada correctamente."
    thread_id: str
    active_tier: str
    active_model: str
    agent_path: List[str]
    latency_ms: float
    pending_action: Optional[Dict[str, Any]] = None

class SelectProviderRequest(BaseModel):
    provider: str  # "auto", "tier1_pc", "tier2_cloud", "tier3_rpi"

class SelectPcModelRequest(BaseModel):
    model: str

class UpdatePcUrlRequest(BaseModel):
    pc_url: Optional[str] = None
    url: Optional[str] = None

class SetGeminiKeyRequest(BaseModel):
    api_key: str

class SelectGeminiModelRequest(BaseModel):
    model_id: Optional[str] = None
    model: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
@router.post("/chat/query", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Endpoint principal de interacción agéntica"""
    thread_id = request.thread_id or "thread_main_user"
    config = {"configurable": {"thread_id": thread_id}}
    
    initial_state = {
        "user_query": request.message,
        "thread_id": thread_id,
        "agent_history": [],
        "current_agent": "supervisor",
        "active_tier": "",
        "active_model": "",
        "research_context": None,
        "obsidian_context": None,
        "latex_context": None,
        "coding_context": None,
        "email_context": None,
        "finance_context": None,
        "pending_action": None,
        "user_approval_status": None,
        "user_approval_feedback": None,
        "final_response": None,
        "latency_ms": 0.0
    }
    
    try:
        final_state = await agent_graph.ainvoke(initial_state, config=config)
        
        pending = final_state.get("pending_action")
        if pending and final_state.get("user_approval_status") == "PENDING":
            return ChatResponse(
                status="AWAITING_USER_APPROVAL",
                response=f"⚠️ El agente **{pending.get('agent_name')}** requiere tu aprobación para ejecutar: *{pending.get('description')}*",
                thread_id=thread_id,
                active_tier="Harness Safety Control",
                active_model="Human-In-The-Loop",
                agent_path=final_state.get("agent_history", []),
                latency_ms=0.0,
                pending_action=pending
            )
            
        raw_response = final_state.get("final_response")
        safe_response = raw_response if (raw_response and isinstance(raw_response, str) and raw_response.strip()) else "Respuesta sintetizada correctamente."

        return ChatResponse(
            status="COMPLETED",
            response=safe_response,
            thread_id=thread_id,
            active_tier=final_state.get("active_tier") or "Tier 2: Gemini Cloud",
            active_model=final_state.get("active_model") or gemini_service.get_active_model_id(),
            agent_path=final_state.get("agent_history", []),
            latency_ms=final_state.get("latency_ms", 0.0),
            pending_action=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la ejecución agéntica: {str(e)}")

@router.post("/chat/approve-action", response_model=ChatResponse)
async def approve_action(request: ActionApprovalRequest):
    """Aprueba la ejecución de una acción crítica pausada por HITL y reanuda el grafo"""
    config = {"configurable": {"thread_id": request.thread_id}}
    try:
        await agent_graph.aupdate_state(config, {"user_approval_status": "APPROVED", "user_approval_feedback": request.feedback})
        final_state = await agent_graph.ainvoke(None, config=config)
        
        raw_response = final_state.get("final_response")
        safe_response = raw_response if (raw_response and isinstance(raw_response, str) and raw_response.strip()) else "Acción aprobada y ejecutada exitosamente."

        return ChatResponse(
            status="COMPLETED",
            response=safe_response,
            thread_id=request.thread_id,
            active_tier=final_state.get("active_tier") or "Harness Executed",
            active_model=final_state.get("active_model") or "HITL Handler",
            agent_path=final_state.get("agent_history", []),
            latency_ms=final_state.get("latency_ms", 0.0),
            pending_action=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reanudar acción aprobada: {str(e)}")

@router.post("/chat/reject-action", response_model=ChatResponse)
async def reject_action(request: ActionApprovalRequest):
    """Rechaza la ejecución de una acción crítica pausada por HITL y reanuda el grafo"""
    config = {"configurable": {"thread_id": request.thread_id}}
    try:
        await agent_graph.aupdate_state(config, {"user_approval_status": "REJECTED", "user_approval_feedback": request.feedback})
        final_state = await agent_graph.ainvoke(None, config=config)
        
        raw_response = final_state.get("final_response")
        safe_response = raw_response if (raw_response and isinstance(raw_response, str) and raw_response.strip()) else "La acción fue cancelada a petición del usuario."

        return ChatResponse(
            status="COMPLETED",
            response=safe_response,
            thread_id=request.thread_id,
            active_tier=final_state.get("active_tier") or "Harness Cancelled",
            active_model=final_state.get("active_model") or "HITL Handler",
            agent_path=final_state.get("agent_history", []),
            latency_ms=final_state.get("latency_ms", 0.0),
            pending_action=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cancelar acción: {str(e)}")

@router.post("/chat/reset-thread")
async def reset_thread_memory(thread_id: Optional[str] = "thread_main_user"):
    """Reinicia la memoria conversacional del hilo especificado"""
    new_thread_id = str(uuid.uuid4())
    return {
        "status": "success",
        "message": f"Memoria de hilo '{thread_id}' reiniciada.",
        "new_thread_id": new_thread_id
    }

@router.post("/system/select-provider")
def select_provider(request: SelectProviderRequest):
    """Permite seleccionar el proveedor de LLM manualmente o activar Auto Failover"""
    llm_router.set_selected_provider(request.provider)
    return {
        "status": "success",
        "selected_provider": llm_router.selected_provider
    }

@router.post("/system/select-pc-model")
def select_pc_model(request: SelectPcModelRequest):
    """Permite seleccionar el modelo específico de Ollama a utilizar en el PC local"""
    llm_router.set_pc_model(request.model)
    return {
        "status": "success",
        "active_pc_model": llm_router.ollama_pc_model
    }

@router.post("/system/update-pc-url")
def update_pc_url(request: UpdatePcUrlRequest):
    """Permite al usuario actualizar la dirección IP/URL de Ollama en su PC Local"""
    target_url = request.pc_url or request.url or "http://192.168.1.9:11434"
    llm_router.update_pc_url(target_url)
    return {
        "status": "success",
        "ollama_pc_url": llm_router.ollama_pc_url
    }

@router.post("/system/set-gemini-key")
async def set_gemini_key_sys(request: SetGeminiKeyRequest):
    """Guarda la API Key de Gemini y recupera modelos disponibles"""
    models = await gemini_service.update_key_and_get_models(request.api_key.strip())
    return {
        "status": "success",
        "message": "API Key de Gemini almacenada.",
        "active_model": gemini_service.get_active_model_id(),
        "available_models": models
    }

@router.post("/system/select-gemini-model")
def select_gemini_model_sys(request: SelectGeminiModelRequest):
    """Selecciona el modelo activo de Gemini"""
    m = request.model_id or request.model
    if m:
        gemini_service.set_active_model(m.strip())
    return {
        "status": "success",
        "message": f"Modelo activo actualizado a {gemini_service.get_active_model_id()}.",
        "active_model": gemini_service.get_active_model_id()
    }

@router.get("/system/status")
async def system_status():
    """Retorna el estado de salud en tiempo real de los 3 niveles y modelos disponibles en el PC"""
    pc_ok, pc_lat, pc_msg = await llm_router.check_pc_ollama_health()
    rpi_ok, rpi_lat, rpi_msg = await llm_router.check_rpi_ollama_health()
    gemini_ok, gemini_msg = await llm_router.check_gemini_health()
    active_tier, active_model, _ = await llm_router.get_active_provider()
    pc_models = await llm_router.fetch_pc_ollama_models()
    
    return {
        "selected_provider": llm_router.selected_provider,
        "selected_provider_mode": llm_router.selected_provider,
        "ollama_pc_model": llm_router.ollama_pc_model,
        "ollama_pc_url": llm_router.ollama_pc_url,
        "gemini_model": gemini_service.get_active_model_id(),
        "active_provider": active_tier,
        "providers": {
            "tier1_pc": {
                "name": "PC Local LAN",
                "model": llm_router.ollama_pc_model,
                "url": llm_router.ollama_pc_url,
                "available": pc_ok,
                "latency_ms": pc_lat,
                "message": pc_msg,
                "available_models": pc_models
            },
            "tier2_cloud": {
                "name": "Gemini Cloud API",
                "model": gemini_service.get_active_model_id(),
                "available": gemini_ok,
                "latency_ms": 0.0,
                "message": gemini_msg
            },
            "tier3_rpi": {
                "name": "RPi Local Edge",
                "model": llm_router.ollama_rpi_model,
                "url": llm_router.ollama_rpi_url,
                "available": rpi_ok,
                "latency_ms": rpi_lat,
                "message": rpi_msg
            }
        }
    }
