# ⚡ Asistente Agéntico Edge Distribuido

[![Architecture](https://img.shields.io/badge/Architecture-Distributed%20Edge%20(ARM64)-blue.svg)](#-arquitectura-y-topología-edge)
[![Framework](https://img.shields.io/badge/Orchestration-LangGraph-purple.svg)](#-stack-tecnológico)
[![Docker](https://img.shields.io/badge/Containers-Docker%20Compose-2496ED.svg)](#-despliegue-con-docker-compose)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](#)

Sistema de asistencia agéntica inteligente distribuido en arquitectura **Edge**, diseñado para ejecutarse en una **Raspberry Pi 5 (ARM64)** como nodo de control y orquestación principal (`/AssAntigravity`), aprovechando un **PC de Cómputo Local** sobre red Ethernet LAN para inferencia GPU acelerada, con cascada de tolerancia a fallos (*Failover Resiliente*) de 3 niveles.

---

## 📸 Vista General y Arquitectura

```
  +-------------------------------------------------------------------------+
  |                             NODO PRINCIPAL                              |
  |                    Raspberry Pi 5 (ARM64 - Linux)                       |
  |                       Directorio: /AssAntigravity                       |
  |                        IP Host: 192.168.1.10                            |
  |                     Usuario SSH: jhonclavijotro                         |
  |                                                                         |
  |  +-------------------------------------------------------------------+  |
  |  |                         DOCKER COMPOSE                            |  |
  |  |                                                                   |  |
  |  |  +-----------------------+     +-------------------------------+  |  |
  |  |  |   Frontend Web UI     |     |   Backend FastAPI + LangGraph |  |  |
  |  |  |  (Nginx / Static Web) | <-> |     (Agentes + Failover)      |  |  |
  |  |  +-----------------------+     +---------------+---------------+  |  |
  |  |                                                |                  |  |
  |  |  +-----------------------+                     |                  |  |
  |  |  |   Qdrant VectorDB     | <-------------------+                  |  |
  |  |  |  (ARM64 Rust Native)  |                                        |  |
  |  |  +-----------------------+                                        |  |
  |  |                                                                   |  |
  |  +-------------------------------------------------------------------+  |
  |                                                                         |
  |  Volúmenes Montados (Bind Mounts):                                       |
  |  - /AssAntigravity/data/pdfs (Entrada RAG)                            |
  |  - /AssAntigravity/data/obsidian (Bóveda Notas Markdown)               |
  |  - /AssAntigravity/data/finanzas (Archivos CSV/Excel)                  |
  |  - /AssAntigravity/dbs (Credenciales y Checkpoint SQLite)             |
  +-------------------------------------------------------------------------+
                         |                              ^
                         | (LAN Ethernet 1Gbps)          | (Failover Tier 2)
                         v                              v
  +-----------------------------------+     +-------------------------------+
  |          NODO DE CÓMPUTO          |     |           CLOUD API           |
  |         PC Local (Inferencia)     |     |       Google Gemini API       |
  |         Ollama (qwen3.5:4b)       |     |   (Selección Dinámica en UI)  |
  |       http://<PC_IP>:11434        |     +-------------------------------+
  +-----------------------------------+
```

---

## 🛡️ Estrategia de Failover Resiliente (3 Capas)

El motor agéntico incorpora un **Circuit Breaker** de baja latencia (timeout síncrono de 1.5s):

1. **Prioridad 1 (PC Local LAN - `qwen3.5:4b`):** Inferencia principal de máxima velocidad en la GPU del PC local (`http://<PC_IP>:11434`).
2. **Prioridad 2 (Cloud Fallback - Google Gemini API):** Si el PC está apagado o no responde en 1.5s, conmuta automáticamente a Gemini API. Las credenciales y la selección de modelo (`gemini-2.0-flash`, `gemini-1.5-pro`, etc.) se gestionan desde la Web UI y se guardan de forma segura en `/AssAntigravity/dbs/credentials.json` (`chmod 600`).
3. **Prioridad 3 (Edge Fallback - `qwen2.5:1.5b`):** Si no hay conexión a internet y el PC local está offline, conmuta a una instancia local de Ollama dentro de la Raspberry Pi 5.

---

## 🧰 Herramientas Agénticas Incluidas

- 📄 **RAG Watchdog de PDFs:** Servicio `watchdog` que auto-indexa PDFs colocados en `/AssAntigravity/data/pdfs` usando extracción PyMuPDF (ARM64) e indexación en Qdrant.
- 📝 **Integración Obsidian:** Lectura, creación, actualización y búsqueda de notas Markdown en `/AssAntigravity/data/obsidian`.
- 📊 **Módulo de Finanzas:** Análisis cuantitativo y adición de registros presupuestarios en archivos CSV/Excel en `/AssAntigravity/data/finanzas`.
- 🔐 **Autenticación Google OAuth2:** Gestión de credenciales seguras para integración con Gmail y Google Calendar.

---

## 🚀 Despliegue en la Raspberry Pi 5

### 1. Conexión SSH a la RPi 5

```bash
ssh jhonclavijotro@192.168.1.10
# Clave de acceso: Jhonathan/7319
```

### 2. Clonar o Actualizar el Repositorio

```bash
# Acceder a la carpeta raíz del asistente
cd /AssAntigravity

# Actualizar cambios desde GitHub
git pull origin main
```

### 3. Iniciar la Infraestructura Docker

```bash
# Copiar plantilla de variables de entorno (si es la primera vez)
cp .env.example .env

# Levantar los contenedores aislados ARM64
docker compose up -d --build
```

---

## 🛠️ Stack Tecnológico

* **Backend:** Python 3.11, FastAPI, LangGraph, Pydantic, PyMuPDF, Watchdog.
* **Vector DB:** Qdrant Engine (Rust nativo ARM64).
* **Frontend:** Nginx Alpine, HTML5, Vanilla CSS, JS (Dashboard interactivo en tiempo real con modo oscuro).
* **Inferencia Local:** Ollama (`qwen3.5:4b` en PC Local / `qwen2.5:1.5b` en RPi 5).
* **Inferencia Cloud:** Google Gemini API (con selector dinámico de modelos de la cuenta).

---

## 📄 Licencia y Gobernanza

Este proyecto fue desarrollado bajo la metodología **Spec-Driven Development** con reglas inquebrantables estipuladas en [`CONSTITUTION.md`](file:///d:/Antigravity/Projects/ASISTENTE/CONSTITUTION.md) y especificadas en [`project_spec.md`](file:///d:/Antigravity/Projects/ASISTENTE/project_spec.md).
