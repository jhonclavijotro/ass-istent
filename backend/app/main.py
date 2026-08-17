import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Asistente Agéntico Edge API",
    version="1.0.0",
    description="Backend de orquestación agéntica con LangGraph y Failover Resiliente"
)

# Configuración de CORS para acceso en red local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthStatus(BaseModel):
    status: str
    node: str
    version: str

class SystemConfig(BaseModel):
    ollama_pc_url: str
    ollama_pc_model: str
    gemini_model: str
    ollama_rpi_model: str
    qdrant_host: str

@app.get("/health", response_model=HealthStatus)
def get_health():
    return HealthStatus(
        status="online",
        node="Raspberry Pi 5 (ARM64)",
        version="1.0.0"
    )

@app.get("/api/config", response_model=SystemConfig)
def get_config():
    return SystemConfig(
        ollama_pc_url=os.getenv("OLLAMA_PC_URL", "http://192.168.1.50:11434"),
        ollama_pc_model=os.getenv("OLLAMA_PC_MODEL", "qwen3.5:4b"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        ollama_rpi_model=os.getenv("OLLAMA_RPI_MODEL", "qwen2.5:1.5b"),
        qdrant_host=os.getenv("QDRANT_HOST", "qdrant")
    )
