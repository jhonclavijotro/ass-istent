import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.routers import chat, gemini, tools

logger = logging.getLogger("main_app")

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

# Incluir rutas de chat, gemini y herramientas agénticas
app.include_router(chat.router)
app.include_router(gemini.router)
app.include_router(tools.router)

@app.on_event("startup")
def startup_event():
    """Garantiza la creación física de carpetas y archivos iniciales al arrancar la app"""
    data_dirs = [
        "/app/data/pdfs",
        "/app/data/obsidian",
        "/app/data/finanzas",
        "/app/dbs"
    ]
    
    # También verificar rutas locales si no está dentro de Docker
    for d in data_dirs:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            logger.warning(f"No se pudo crear carpeta '{d}': {e}")
            
    # Crear nota de bienvenida inicial en Obsidian si está vacía
    obs_dir = "/app/data/obsidian" if os.path.exists("/app/data/obsidian") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "obsidian"))
    os.makedirs(obs_dir, exist_ok=True)
    welcome_file = os.path.join(obs_dir, "Bienvenida_Obsidian.md")
    if not os.path.exists(welcome_file):
        try:
            with open(welcome_file, "w", encoding="utf-8") as f:
                f.write("# 📝 Bóveda de Obsidian Conectada\n\n¡Bienvenido a tu bóveda personal de notas Markdown!\nCualquier nota que agregues o edites aquí estará sincronizada con el Asistente Antigravity en la Raspberry Pi 5.\n")
        except Exception as e:
            logger.error(f"Error creando nota de bienvenida: {e}")

    # Crear archivo financiero por defecto si está vacío
    fin_dir = "/app/data/finanzas" if os.path.exists("/app/data/finanzas") else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "finanzas"))
    os.makedirs(fin_dir, exist_ok=True)
    fin_file = os.path.join(fin_dir, "presupuesto_inicial.csv")
    if not os.path.exists(fin_file):
        try:
            with open(fin_file, "w", encoding="utf-8") as f:
                f.write("fecha,concepto,monto,categoria\n2026-08-17,Inicialización Sistema Edge,0.00,General\n")
        except Exception as e:
            logger.error(f"Error creando archivo financiero inicial: {e}")

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
