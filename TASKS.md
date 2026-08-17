# PLAN DE TAREAS Y HOJA DE RUTA (TASKS.md)

**Proyecto:** Asistente Agéntico Edge Distribuido  
**Enfoque:** Spec-Driven Development (Fase por Fase con aprobación del Director)  
**Última Actualización:** 2026-08-17  

---

## ESTRUCTURA DE CONTROL (PHASE-GATE REVIEWS)

- [x] **FASE 1: ESPECIFICACIÓN Y ARQUITECTURA EDGE (Spec)**
- [x] **FASE 2: INFRAESTRUCTURA DOCKER EN RASPBERRY PI 5**
- [x] **FASE 3: MOTOR MULTIAGENTE Y SISTEMA DE FAILOVER (LangGraph)**
- [x] **FASE 4: HERRAMIENTAS, INTEGRACIÓN Y SINCRONIZACIÓN DE RECURSOS**
- [ ] **FASE 5: INTERFAZ WEB (UI) Y PANEL DE CONTROL EDGE**

---

## DETALLE DE TAREAS POR FASE

### FASE 1: ESPECIFICACIÓN Y ARQUITECTURA EDGE (Spec)
> **Objetivo:** Definir completamente la arquitectura, esquemas de datos, diagramas de red y estrategias de failover antes de escribir código.

- [x] **1.1 Establecimiento de Gobernanza y Constitución**
  - [x] Crear `CONSTITUTION.md` con principios de desarrollo y reglas edge.
  - [x] Crear `TASKS.md` para seguimiento detallado de trabajo.
  - [x] Crear `BUG_TRACKER.md` para registro de incidencias y correcciones.
- [x] **1.2 Redacción del Documento de Especificación del Proyecto (`project_spec.md`)**
  - [x] Diseñar el Diagrama de Red Edge (Topología Ethernet RPi 5 <-> PC Local <-> Cloud Gemini).
  - [x] Especificar la estrategia de prueba de conectividad y latencia (Circuit Breaker LLM Router).
  - [x] Definir el Stack de Software (FastAPI, LangGraph, Qdrant, React/Vue/Vanilla UI).
  - [x] Mapear los esquemas de directorios locales (PDFs, Obsidian Vault, Excel Finanzas).
  - [x] Definir el flujo de versionado en GitHub y despliegue SSH a la RPi 5 (`jhonclavijotro@192.168.1.10`).
- [x] **1.3 Inicialización del Repositorio GitHub y Conectividad SSH**
  - [x] Configurar el control de versiones local Git (`git init`, `.gitignore`).
  - [x] Vincular el repositorio remoto en GitHub para versionado de configuraciones.
- [x] **1.4 Phase-Gate Review 1**
  - [x] Presentar `project_spec.md` al Director del Proyecto y obtener aprobación explícita.

---

### FASE 2: INFRAESTRUCTURA DOCKER EN RASPBERRY PI 5
> **Objetivo:** Configurar el entorno de contenedores optimizado para ARM64 en la Raspberry Pi 5.

- [x] **2.1 Definición de la Configuración Docker**
  - [x] Diseñar `docker-compose.yml` especificando contenedores independientes: Backend FastAPI, VectorDB (Qdrant ARM64), Frontend (Nginx).
  - [x] Definir volúmenes (`bind mounts`) para persistencia local de carpetas físicas y base de datos vectoriales en `/AssAntigravity`.
  - [x] Configurar restricciones de memoria (cgroups RAM limits) para prevenir thrashing en RPi 5.
- [x] **2.2 Pruebas de Despliegue de Infraestructura**
  - [x] Validar compatibilidad de imágenes Docker en entorno ARM64 (`python:3.11-slim`, `qdrant/qdrant`, `nginx:alpine`).
  - [x] Verificar estructura de volúmenes locales y plantilla de configuración `.env.example`.
- [x] **2.3 Phase-Gate Review 2**
  - [x] Presentar infraestructura Docker desplegada al Director del Proyecto para aprobación.

---

### FASE 3: MOTOR MULTIAGENTE Y FAILOVER (LangGraph)
> **Objetivo:** Construir el servidor Backend en FastAPI con LangGraph y el enrutador de modelos tolerante a fallos.

- [x] **3.1 Desarrollo del Enrutador de LLM con Failover Resiliente (3 Capas)**
  - [x] Implementar cliente de inferencia Prioridad 1: PC Ollama LAN (`http://<PC_IP>:11434`) ejecutando `qwen3.5:4b` con timeout rápido (< 2.0s).
  - [x] Implementar cliente de inferencia Prioridad 2: Fallback a Gemini API (`gemini-2.0-flash`).
  - [x] Implementar cliente de inferencia Prioridad 3: Fallback a Ollama local RPi (`qwen2.5:1.5b`).
  - [x] Pruebas unitarias e integración del Circuit Breaker de Failover.
- [x] **3.2 Orquestación Multiagente con LangGraph**
  - [x] Definir arquitectura de agentes (Agente Investigador RAG, Agente Finanzas, Agente Obsidian, Agente Redactor).
  - [x] Configurar persisterna de estado de sesión con `AsyncSqliteSaver`.
  - [x] Exponer endpoints REST / WebSockets en FastAPI para interacción en tiempo real (`/api/chat` y `/api/system/status`).
- [x] **3.3 Phase-Gate Review 3**
  - [x] Demostrar el funcionamiento del enrutador de failover y la ejecución de agentes al Director para aprobación.

---

### FASE 4: HERRAMIENTAS, INTEGRACIÓN Y SINCRONIZACIÓN DE RECURSOS
> **Objetivo:** Conectar el backend agéntico con los datos locales (Obsidian, PDFs RAG, Excel) y servicios externos (Google Workspace).

- [x] **4.1 Sistema RAG y Ingesta de Documentos (PDF Watchdog)**
  - [x] Desarrollar servicio de monitoreo de archivos (`watchdog`) para auto-indexar PDFs colocados en `/AssAntigravity/data/pdfs` hacia Qdrant.
  - [x] Implementar pipeline de fragmentación (*chunking*) y extracción PyMuPDF ultraligera para ARM64.
- [x] **4.2 Integración con Bóveda de Obsidian y Archivos Financieros**
  - [x] Crear herramientas de agente para lectura, edición y búsqueda de notas Markdown en `/AssAntigravity/data/obsidian`.
  - [x] Crear herramientas de lectura/procesamiento de hojas de cálculo de finanzas en `/AssAntigravity/data/finanzas` (CSV/Excel).
- [x] **4.3 Autenticación Google OAuth2 (Workspace)**
  - [x] Adaptar flujo de autenticación OAuth2 para integración segura de correo (Gmail) y calendario en `/AssAntigravity/dbs/google_tokens.json`.
- [x] **4.4 Phase-Gate Review 4**
  - [x] Presentar flujo completo RAG y manipulación de archivos locales al Director para aprobación.

---

### FASE 5: INTERFAZ WEB (UI) Y PANEL DE CONTROL EDGE
> **Objetivo:** Construir la interfaz de usuario moderna, fluida y con telemetría visual de los nodos del sistema.

- [ ] **5.1 Diseño y Desarrollo de la Web UI**
  - [ ] Interfaz de Chat con soporte para streaming de respuestas, Markdown y bloques de código.
  - [ ] Panel de Estado del Sistema en tiempo real: Indicador visual del LLM activo (PC Local LAN / Cloud Gemini / RPi Edge).
  - [ ] Vista de gestión de documentos indexados en el RAG y estado de agentes.
- [ ] **5.2 Pruebas End-to-End (E2E) y Validación Final**
  - [ ] Realizar pruebas de desconexión de red (simular caída de PC local y caída de internet) y verificar respuesta del sistema.
  - [ ] Documentación final y manual de operaciones.
- [ ] **5.3 Phase-Gate Review 5 (Entrega Final)**
  - [ ] Presentar proyecto completo funcionando en la Raspberry Pi 5 al Director del Proyecto.
