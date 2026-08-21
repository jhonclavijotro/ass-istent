# Especificación de Harness Engineering, Memoria Cognitiva y Taxonomía

**Documento de Arquitectura y Gobernanza IA**  
**Proyecto:** Asistente Agéntico Edge Distribuido (/AssAntigravity)  
**Autor:** Antigravity (Arquitecto de Software Senior)  
**Revisor:** Director del Proyecto  

---

## 1. Declaración de Principios de Harness Engineering

El **Harness Engineering** (Ingeniería de Contención y Seguridad IA) en la arquitectura de Antigravity establece los límites de autonomía del sistema multiagente que opera sobre la Raspberry Pi 5.

### Reglas Inviolables de Contención:
1. **Lectura y Análisis Autónomo (Principio de Menor Riesgo):** Los agentes tienen permiso total de ejecución autónoma para tareas de solo lectura, búsqueda, consulta semántica en RAG, extracción de información y cómputo aislado.
2. **Interrupción de Estado Mandatoria (Human-In-The-Loop / HITL):** Ningún agente tiene permiso para modificar el estado persistente del usuario (Bóveda de Obsidian, archivos Excel maestros) o comunicarse con el exterior (enviar correos en Google Workspace, agendar eventos en Google Calendar) sin pausar el grafo y obtener aprobación explícita e inequívoca del Director del Proyecto.
3. **Falla Segura Abortiva (Fail-Safe Abort):** Si una herramienta de escritura o modificación recibe parámetros corruptos, alucinaciones o errores de formato, la acción debe abortarse inmediatamente y retornar el control al usuario. **Jamás se debe reintentar automáticamente una acción destructiva.**

---

## 2. Taxonomía del Ecosistema (MCPs y Skills)

Se define un inventario estricto de componentes para evitar mezcla de responsabilidades.

### A. MCPs (Model Context Protocols)
Son servidores independientes que exponen un contexto o capacidad completa:
- **NotebookLM MCP:** Para análisis profundo e ingesta de documentos complejos.
- **arXiv MCP:** Para búsqueda nativa de papers académicos.
- **LaTeX MCP (Contenedor):** Para compilación aislada de documentos `.tex`.
- **Obsidian MCP:** Para gestión de bóveda local, hipervínculos y estructura `.md`.

### B. Skills (`@tool`)
Herramientas en Python que extienden a los agentes:
- **Workspace Tools:** Gmail y Calendar API.
- **Data Tools:** Pandas y Jupyter sandbox.
- **RAG Tools:** Interacción con Qdrant/ChromaDB y Tika OCR.

---

## 3. Arquitectura de Memoria Cognitiva (State vs VectorDB)

Los agentes son **Stateless** por diseño. La memoria del sistema se gestiona en dos capas:

### 3.1 Memoria de Corto Plazo (AgentState)
Todo el contexto para actuar se inyecta dinámicamente en el estado de LangGraph. Los agentes leen este estado, ejecutan su función y añaden el resultado al historial.

### 3.2 Memoria de Largo Plazo (VectorDB Particionada)
La VectorDB (ChromaDB/Qdrant) se divide estrictamente en Colecciones lógicas (Namespaces) para evitar contaminación:
- `RAG_Papers`: Exclusiva para el **Agente Investigador**.
- `Obsidian_Vault`: Exclusiva para el **Admin. de Obsidian**.
- `Core_Memory` (Memoria Episódica): Contiene preferencias, contactos e historial clave. **Solo el Supervisor** accede a esta colección al inicio de un ciclo para inyectar preferencias relevantes en el `AgentState` antes de delegar tareas.

---

## 4. Matriz de Autonomía y Permisos (Harness Engineering)

| Agente | Acciones Autónomas (Sin Interrupción) | Acciones Interrumpidas (HITL - Requieren Aprobación) | Puntos de Pausa (LangGraph Node) |
| :--- | :--- | :--- | :--- |
| **Investigador** | Buscar en web/arXiv, leer PDFs, usar Jupyter. | *Ninguna.* (Acciones de lectura/cálculo). | N/A |
| **Redactor** | Redactar borradores, compilar `.tex`. | *Ninguna.* (Genera archivos temporales). | N/A |
| **Admin. Obsidian** | Leer bóveda local, mapear enlaces. | **Crear, modificar o eliminar archivos `.md` existentes en la bóveda real.** | `interrupt_before=["obsidian_writer_node"]` |
| **Admin. Finanzas** | Leer `.xlsx`, crear gráficos en memoria. | **Sobrescribir archivos Excel maestros o enviar reportes financieros al exterior.** | `interrupt_before=["finance_writer_node"]` |
| **Revisor Correos** | Leer bandeja de entrada, crear borradores. | **Enviar correos, eliminar correos o agendar eventos en Google Calendar.** | `interrupt_before=["email_action_node"]` |

---

## 5. Estructura del Estado Global (`AgentState`) para Human-In-The-Loop

```python
class PendingAction(TypedDict):
    action_id: str
    agent_name: str
    tool_name: str
    description: str
    payload: Dict[str, Any]
    risk_level: str

class AgentState(TypedDict):
    # Campos base conversacionales
    user_query: str
    thread_id: str
    agent_history: List[str]
    current_agent: str
    active_tier: str
    active_model: str
    
    # Contextos acumulados
    research_context: Optional[str]
    obsidian_context: Optional[str]
    latex_context: Optional[str]
    coding_context: Optional[str]
    email_context: Optional[str]
    finance_context: Optional[str]
    core_memory_context: Optional[str]  # Inyectado exclusivamente por el Supervisor
    
    # CAMPOS DE HARNESS ENGINEERING & HITL
    pending_action: Optional[PendingAction]
    user_approval_status: Optional[str]
    user_approval_feedback: Optional[str]
    
    final_response: Optional[str]
    latency_ms: float
```
