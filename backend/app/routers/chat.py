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
    action_id: str
    feedback: Optional[str] = None

class ChatResponse(BaseModel):
    status: str  # "COMPLETED" | "AWAITING_USER_APPROVAL"
    response: str
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
    pc_url: str

@router.post("/chat", response_model=ChatResponse)
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
        "finance_context": None,
        "email_context": None,
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
            
        return ChatResponse(
            status="COMPLETED",
            response=final_state.get("final_response", "No se pudo generar respuesta."),
            thread_id=thread_id,
            active_tier=final_state.get("active_tier", "Desconocido"),
            active_model=final_state.get("active_model", "Desconocido"),
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
        
        return ChatResponse(
            status="COMPLETED",
            response=final_state.get("final_response", "Acción aprobada y ejecutada exitosamente."),
            thread_id=request.thread_id,
            active_tier=final_state.get("active_tier", "Desconocido"),
            active_model=final_state.get("active_model", "Desconocido"),
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
        
        return ChatResponse(
            status="COMPLETED",
            response=final_state.get("final_response", "La acción fue cancelada a petición del usuario."),
            thread_id=request.thread_id,
            active_tier=final_state.get("active_tier", "Desconocido"),
            active_model=final_state.get("active_model", "Desconocido"),
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
    llm_router.update_pc_url(request.pc_url)
    return {
        "status": "success",
        "ollama_pc_url": llm_router.ollama_pc_url
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
        "selected_provider_mode": llm_router.selected_provider,
        "tier1_pc": {
            "name": "PC Local LAN",
            "model": llm_router.ollama_pc_model,
            "url": llm_router.ollama_pc_url,
            "available": pc_ok,
            "latency_ms": pc_lat,
            "detail": pc_msg,
            "available_models": pc_models
        },
        "tier2_cloud": {
            "name": "Gemini Cloud API",
            "model": gemini_service.get_active_model_id(),
            "available": gemini_ok,
            "latency_ms": 0.0,
            "detail": gemini_msg
        },
        "tier3_rpi": {
            "name": "RPi Local Edge",
            "model": llm_router.ollama_rpi_model,
            "url": llm_router.ollama_rpi_url,
            "available": rpi_ok,
            "latency_ms": rpi_lat,
            "detail": rpi_msg
        },
        "active_provider": {
            "tier": active_tier,
            "model": active_model
        }
    }
