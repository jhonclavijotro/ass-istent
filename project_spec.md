# ESPECIFICACIÓN TÉCNICA DEL PROYECTO (`project_spec.md`)

**Proyecto:** Asistente Agéntico Edge Distribuido  
**Fase:** Fase 1 - Especificación y Arquitectura Edge  
**Estado:** Propuesto para Revisión del Director del Proyecto  
**Fecha:** 2026-08-17  

---

## 1. RESUMEN EJECUTIVO Y OBJETIVOS

El sistema es una solución agéntica inteligente de alta disponibilidad construida sobre una **Arquitectura Edge Distribuida**. El sistema combina la potencia del hardware local en red (PC con GPU) con la flexibilidad y resiliencia de un nodo de control independiente en hardware ARM64 (Raspberry Pi 5).

---

## 2. ARQUITECTURA DE RED Y TOPOLOGÍA EDGE

### 2.1 Diagrama de Conectividad de Nodos

```
  +-------------------------------------------------------------------------+
  |                             NODO PRINCIPAL                              |
  |                    Raspberry Pi 5 (ARM64 - Linux)                       |
  |                        IP: 192.168.1.10                                 |
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
  |  - /data/pdfs (Entrada RAG)                                             |
  |  - /data/obsidian (Bóveda Notas)                                        |
  |  - /data/finanzas (Hojas Excel/CSV)                                    |
  +-------------------------------------------------------------------------+
                         |                              ^
                         | (LAN Ethernet 1Gbps)          | (Failover Tier 2)
                         v                              v
  +-----------------------------------+     +-------------------------------+
  |          NODO DE CÓMPUTO          |     |           CLOUD API           |
  |         PC Local (Inferencia)     |     |       Google Gemini API       |
  |         Ollama (qwen3.5:4b)       |     |      (gemini-2.0-flash)       |
  |       http://<PC_IP>:11434        |     +-------------------------------+
  +-----------------------------------+
```

---

## 3. ESTRATEGIA DE MODELOS Y CASCADA DE FAILOVER (3 NIVELES)

El motor agéntico enviará peticiones a través de un **LLM Resilient Router** personalizado que evalúa la disponibilidad en tiempo real antes de enviar la solicitud completa:

$$\text{Petición Agéntica} \longrightarrow \text{Evaluador de Salud (Circuit Breaker)}$$

1. **Nivel 1 (PC Local LAN - Prioridad Alta):**
   - **Endpoint:** `http://<PC_IP>:11434`
   - **Modelo:** `qwen3.5:4b`
   - **Mecanismo:** Verificación de puerto con `HTTP HEAD` y timeout de **1.5 segundos**. Si el PC está encendido y responde, la petición se procesa en el PC a máxima velocidad de VRAM.
2. **Nivel 2 (Cloud Fallback - Prioridad Media):**
   - **Endpoint:** Google Gemini API
   - **Modelo:** `gemini-2.0-flash`
   - **Mecanismo:** Si el PC no responde (offline / timeout), la solicitud se conmuta automáticamente a la API de Gemini mediante conexión a internet.
3. **Nivel 3 (Edge Fallback Offline - Prioridad de Emergencia):**
   - **Endpoint:** Ollama local en RPi 5 (`http://localhost:11434`)
   - **Modelo:** `qwen2.5:1.5b`
   - **Mecanismo:** Si el PC está apagado y no hay conexión a internet, el sistema conmuta a un modelo ultra-ligero alojado dentro de la Raspberry Pi 5.

---

## 4. FLUJO DE TRABAJO, VERSIONADO Y DESPLIEGUE (Git & SSH)

1. **Entorno de Desarrollo (PC Local):**
   - Todo el código fuente (FastAPI, LangGraph, Frontend, Dockerfile, `docker-compose.yml`) se escribe y prueba localmente en el PC en `d:\Antigravity\Projects\ASISTENTE`.
2. **Repositorio Central (GitHub):**
   - El código se sube al repositorio remoto de **GitHub**, el cual actúa como la única fuente de verdad (*Single Source of Truth*).
3. **Despliegue en Raspberry Pi 5 (Terminal SSH):**
   - Desde la terminal, se establece conexión SSH con la RPi 5:
     ```bash
     ssh jhonclavijotro@192.168.1.10
     ```
   - Se ejecutan los comandos de actualización y despliegue:
     ```bash
     git pull origin main
     docker compose up -d --build
     ```

---

## 5. STACK TECNOLÓGICO Y CONTENEDORES DOCKER (RPi 5 ARM64)

| Servicio | Tecnología | Imagen Base Docker ARM64 | Función en el Sistema |
|---|---|---|---|
| **Backend API** | Python 3.11 / FastAPI | `python:3.11-slim` | Orquestación REST/WebSocket, motor LangGraph y herramientas de agentes. |
| **Vector DB** | Qdrant | `qdrant/qdrant:v1.9-arm64` | Almacenamiento vectorial y búsqueda semántica de alta velocidad para RAG. |
| **Web UI** | HTML5 / JS / Vanilla CSS | `nginx:alpine` | Interfaz gráfica servida estáticamente en la red local. |
| **Persistencia** | SQLite | Archivo local montado | Persistencia de estado de conversaciones LangGraph (`AsyncSqliteSaver`). |

---

## 6. ESTRUCTURA DE VOLÚMENES Y MONTAJE DE ARCHIVOS LOCALES

La Raspberry Pi 5 mantendrá volúmenes montados directamente desde el sistema de archivos del host hacia el contenedor del Backend:

- **PDFs Ingesta RAG:** `/home/jhonclavijotro/asistente/data/pdfs` $\rightarrow$ `/app/data/pdfs`
- **Bóveda Obsidian:** `/home/jhonclavijotro/asistente/data/obsidian` $\rightarrow$ `/app/data/obsidian`
- **Finanzas:** `/home/jhonclavijotro/asistente/data/finanzas` $\rightarrow$ `/app/data/finanzas`

Un servicio de monitoreo en tiempo real (`watchdog`) dentro del backend detectará la adición de nuevos PDFs en la carpeta montada e iniciará automáticamente el pipeline de fragmentación e indexación en Qdrant.

---

## 7. CRITERIOS DE ACEPTACIÓN Y VERIFICACIÓN (FASE 1)

1. [x] Definición completa del flujo de desarrollo PC Local -> GitHub -> SSH RPi 5 (`jhonclavijotro@192.168.1.10`).
2. [x] Especificación de modelos aprobados (`qwen3.5:4b` en PC Local, `gemini-2.0-flash` en Cloud y `qwen2.5:1.5b` en RPi).
3. [x] Diseño de arquitectura aislada en contenedores ARM64.
4. [ ] Aprobación explícita del **Director del Proyecto**.
