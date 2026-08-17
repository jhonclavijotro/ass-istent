# CONSTITUCIÓN DEL PROYECTO: ASISTENTE AGÉNTICO EDGE DISTRIBUIDO

**Versión:** 1.0.0  
**Estado:** Propuesto para Revisión del Director del Proyecto  
**Fecha:** 2026-08-17  

---

## ARTÍCULO I: GOVERNANZA Y ROLES

1. **Director del Proyecto (Usuario):** Posee la autoridad suprema sobre el diseño, arquitectura, validación y aprobación de cada fase. Ninguna funcionalidad, cambio de stack o despliegue de código se ejecutará sin su aprobación explícita (*Phase-Gate Review*).
2. **Arquitecto y Ejecutor (Antigravity):** Encargado de proponer soluciones técnicas, redactar especificaciones, construir la infraestructura y desarrollar el código siguiendo rigurosamente las reglas de esta Constitución.

---

## ARTÍCULO II: REGLAS INQUEBRANTABLES DE DESARROLLO (Spec-Driven Development)

1. **Especificación Previa Obligatoria:** No se escribirá una sola línea de código fuente (`.py`, `.js`, `.dockerfile`, etc.) sin que antes exista un documento de especificación técnica (`.md`) aprobado por el Director del Proyecto.
2. **Ciclo de Desarrollo Estricto:**
   $$\text{Master Prompt / Requisito} \longrightarrow \text{Especificación (.md)} \longrightarrow \text{Aprobación Director} \longrightarrow \text{Implementación} \longrightarrow \text{Verificación Empírica}$$
3. **Registro de Errores e Incidentes:** Todo fallo runtime, incompatibilidad de dependencia o error de despliegue debe ser registrado en `BUG_TRACKER.md` con su correspondiente análisis de causa raíz y solución aplicada.

---

## ARTÍCULO III: ARQUITECTURA Y TOPOLOGÍA EDGE

1. **Distribución Física:**
   - **Nodo Principal (Raspberry Pi 5 - ARM64):** Servidor de orquestación (FastAPI), motor multiagente (LangGraph), VectorDB (Qdrant), servicios OCR/extracción, Web UI y almacenamiento de datos montado.
   - **Nodo de Cómputo (PC Local):** Servidor de inferencia local de alta velocidad ejecutando Ollama sobre red Ethernet local (LAN).
2. **Aislamiento por Contenedores Docker:**
   - Cada servicio pesado o con dependencias nativas debe aislarse en su propio contenedor dentro del archivo `docker-compose.yml` en la RPi 5.
   - Está prohibido consolidar la VectorDB y el motor agéntico en el mismo entorno de ejecución.
3. **Compatibilidad Estricta ARM64:**
   - Toda imagen base seleccionada en `Dockerfile` o `docker-compose.yml` debe ser nativamente compatible con la arquitectura ARM64 de la RPi 5 (`linux/arm64`).

---

## ARTÍCULO IV: ALTA DISPONIBILIDAD Y CASCADA DE FAILOVER (LLM Strategy)

El sistema de orquestación de LLMs debe implementar un patrón **Circuit Breaker / Resilient Router** con tolerancia a fallos en 3 niveles de prioridad:

$$\text{Petición} \longrightarrow \underbrace{\text{Prioridad 1: PC Local Ollama (LAN)}}_{\text{Timeout < 2s}} \xrightarrow{\text{Fail}} \underbrace{\text{Prioridad 2: Gemini API (Cloud)}}_{\text{Fallback Automático}} \xrightarrow{\text{Fail / Sin Internet}} \underbrace{\text{Prioridad 3: RPi Ollama (Edge Fallback)}}_{\text{Modelo Ligero Local}}$$

1. **Prioridad 1 (PC Local LAN):** Inferencia principal en PC local vía HTTP (`http://<PC_IP>:11434`) ejecutando el modelo `qwen3.5:4b`.
2. **Prioridad 2 (Cloud Fallback):** Transición automática e ininterrumpida a Gemini API (`gemini-2.0-flash`) si el PC no responde en un timeout estipulado (ej. 2.0s) o está apagado.
3. **Prioridad 3 (Edge Fallback Offline):** Transición a instancia local de Ollama en la RPi 5 ejecutando el modelo ligero `qwen2.5:1.5b` cuando no haya conexión a internet y el PC esté inalcanzable.

---

## ARTÍCULO V: GESTIÓN DE RECURSOS Y EFICIENCIA EN EDGE

1. **Límites de Memoria y CPU:** Dado el entorno restrictivo de la Raspberry Pi 5 (4GB/8GB RAM), cada servicio en `docker-compose.yml` declarará límites de recursos (`deploy.resources.limits`).
2. **Elección de Componentes Ligeros:**
   - VectorDB preferida: **Qdrant** (Rust binario nativo, bajo consumo de memoria y CPU frente a alternativas).
   - Extracción de PDFs/Documentos: Priorizar librerías nativas ligeras (`PyMuPDF` / `pdfplumber`) dentro de la app, delegando contenedores pesados (Tika / Unstructured) a ejecución bajo demanda si se requieren OCRs complejos.

---

## ARTÍCULO VI: PERSISTENCIA Y PRIVACIDAD DE DATOS

1. **Almacenamiento Local Físico:** Las carpetas del sistema (PDFs, Finanzas, Bóveda Obsidian) residen en el disco de la RPi 5 y se exponen a los contenedores mediante *Bind Mounts* explícitos.
2. **Memoria y Estado de Agentes:** El estado del grafo LangGraph se persistirá en SQLite/Postgres local (`AsyncSqliteSaver`), garantizando la continuidad de conversaciones y sesiones entre reinicios.
3. **Seguridad y OAuth:** Las credenciales de APIs (Gemini, Google Workspace OAuth) se gestionarán strictly mediante variables de entorno en un archivo `.env` excluido del control de versiones.

---

## ARTÍCULO VII: FLUJO DE DESARROLLO, VERSIONADO Y DESPLIEGUE (Git & SSH)

1. **Fuente Única de Verdad (Single Source of Truth):** Todo el código, especificaciones técnicas (`.md`), archivos de configuración Docker y manifiestos del proyecto serán versionados en un repositorio de **GitHub**.
2. **Generación de Código en PC Local:** Todo el desarrollo, refactorización y creación de código se ejecutará localmente en el PC del Director del Proyecto / Entorno Antigravity.
3. **Despliegue Remoto en Raspberry Pi 5:** La actualización del sistema en el Nodo Principal (RPi 5 en `192.168.1.10`, usuario `jhonclavijotro`) se realizará mediante comandos remotos SSH vía terminal (`git pull` y `docker compose up -d --build`).
4. **Protección de Datos Sensibles:** Ninguna contraseña, token OAuth o clave SSH será subida al repositorio GitHub (`.gitignore` estricto para `.env`, llaves pem/rsa y datos personales).
