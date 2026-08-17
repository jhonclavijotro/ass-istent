import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.graph import agent_graph
from app.core.llm_router import llm_router

router = APIRouter(prefix="/api", tags=["Chat & Multi-Agent"])

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    active_tier: str
    active_model: str
    agent_path: List[str]
    latency_ms: float

class StatusResponse(BaseModel):
    tier1_pc: dict
    tier2_cloud: dict
    tier3_rpi: dict
    active_provider: str

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Endpoint principal de interacción agéntica con persistencia de memoria por hilo"""
    # Usar un hilo constante por defecto si el cliente no envía uno
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
        "final_response": None,
        "latency_ms": 0.0
    }
    
    try:
        final_state = await agent_graph.ainvoke(initial_state, config=config)
        return ChatResponse(
            response=final_state.get("final_response", "No se pudo generar respuesta."),
            thread_id=thread_id,
            active_tier=final_state.get("active_tier", "Desconocido"),
            active_model=final_state.get("active_model", "Desconocido"),
            agent_path=final_state.get("agent_history", []),
            latency_ms=final_state.get("latency_ms", 0.0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la ejecución agéntica: {str(e)}")

@router.post("/chat/reset-thread")
async def reset_thread_memory(thread_id: Optional[str] = "thread_main_user"):
    """Reinicia la memoria conversacional del hilo especificado"""
    new_thread_id = str(uuid.uuid4())
    return {
        "status": "success",
        "message": f"Memoria de hilo '{thread_id}' reiniciada.",
        "new_thread_id": new_thread_id
    }

@router.get("/system/status")
async def system_status():
    """Retorna el estado de salud de los 3 niveles de la cascada de failover"""
    pc_ok, pc_lat = await llm_router.check_pc_ollama_health()
    rpi_ok, rpi_lat = await llm_router.check_rpi_ollama_health()
    active_tier, active_model, _ = await llm_router.get_active_provider()
    
    return {
        "tier1_pc": {
            "name": "PC Local LAN",
            "model": llm_router.ollama_pc_model,
            "url": llm_router.ollama_pc_url,
            "available": pc_ok,
            "latency_ms": pc_lat
        },
        "tier2_cloud": {
            "name": "Gemini Cloud API",
            "model": llm_router.gemini_model,
            "available": bool(llm_router.gemini_api_key and llm_router.gemini_api_key != "tu_api_key_aqui"),
            "latency_ms": 0.0
        },
        "tier3_rpi": {
            "name": "RPi Local Edge",
            "model": llm_router.ollama_rpi_model,
            "url": llm_router.ollama_rpi_url,
            "available": rpi_ok,
            "latency_ms": rpi_lat
        },
        "active_provider": {
            "tier": active_tier,
            "model": active_model
        }
    }
