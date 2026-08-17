# ⚡ Asistente Agéntico Edge - Sistema Distribuido (/AssAntigravity)

Bienvenido al repositorio oficial del **Asistente Agéntico Edge Distribuido**, un sistema agéntico inteligente de arquitectura distribuida ejecutado sobre **Raspberry Pi 5 (ARM64)**, integrado con un **PC Local (Ollama LAN)** y la **Cloud (Google Gemini API)** bajo principios de **Harness Engineering** y control **Human-In-The-Loop (HITL)**.

---

## 🏛️ Arquitectura del Sistema Multiagente

```
+-----------------------------------------------------------------------------------+
|                                 INTERFAZ WEB UI                                   |
|       (Chat Agéntico + Dashboard Financiero + Bóveda Obsidian + RAG PDFs)         |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            GRAFO AGÉNTICO LANGGRAPH                               |
|                                                                                   |
|  +----------------+      +-------------------+      +--------------------------+  |
|  |  Supervisor    | ---> | Research Agent    | ---> |  Redactor (Writer Agent) |  |
|  |  (Router LLM)  |      | (Docling MCP RAG) |      +--------------------------+  |
|  +----------------+      +-------------------+                    ^               |
|          |                         |                              |               |
|          v                         v                              |               |
|  +----------------+      +-------------------+                    |               |
|  | Finance Agent  | ---> | File System Agent | -------------------+               |
|  | (BDV/BLB CSV)  |      | (RPi 5 Storage)   |                                    |
|  +----------------+      +-------------------+                                    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        MOTOR DE INFERENCIA RESILIENTE (LLM)                        |
|                                                                                   |
|  [Capal 1: PC Local LAN]  --->  [Capa 2: Cloud Gemini]  --->  [Capa 3: RPi Edge]  |
|  (Ollama 192.168.1.9)           (Gemini 2.0 Flash)             (qwen2.5:1.5b)      |
+-----------------------------------------------------------------------------------+
```

---

## 📊 Módulo y Dashboard Financiero (BDV & BLB)

El asistente cuenta con una **base de datos financiera estructurada** en `/app/data/finanzas/finanzas_db.csv` con los siguientes parámetros obligatorios:

- **Cuenta:** `BDV` (*Banco Davivienda*) o `BLB` (*Bancolombia*)
- **Monto:** Valor numérico en Pesos Colombianos ($ COP)
- **Fecha:** Formato de fecha (`DD/MM/YYYY`)
- **Tipo:** `ingreso` o `egreso`
- **Categoría:** `comida`, `ocio`, `casa`, `trabajo`, `transporte`, `otros`
- **Concepto:** Descripción detallada de la transacción

### 📈 Características del Dashboard Financiero en Web UI:
1. **Estado de Fondos por Cuenta:** Monitoreo en tiempo real del saldo disponible en `BDV`, `BLB` y el **Saldo Consolidado Total**.
2. **Top 3 Movimientos Más Comunes:** Frecuencia y acumulación por concepto/categoría.
3. **Historial de Últimos Movimientos:** Tabla con insignias visuales de tipo (`🟢 Ingreso` / `🔴 Egreso`) y banco.
4. **Formulario de Registro Interactivo:** Permite añadir nuevas transacciones directamente a la base de datos física en disco.

---

## 🧰 Herramientas Agénticas Incluidas

- 📄 **RAG Watchdog de PDFs:** Servicio `watchdog` que auto-indexa PDFs colocados en `/AssAntigravity/data/pdfs` usando extracción PyMuPDF (ARM64) e indexación en Qdrant.
- 📝 **Integración Obsidian:** Lectura, creación, actualización y búsqueda de notas Markdown en `/AssAntigravity/data/obsidian`.
- 📊 **Módulo de Finanzas & Dashboard:** Base de datos estructurada y visualización interactiva de saldo de cuentas BDV/BLB.
- 📁 **Gestor del Sistema de Archivos RPi 5:** Creación, modificación y eliminación física de archivos bajo gobernanza HITL.
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
