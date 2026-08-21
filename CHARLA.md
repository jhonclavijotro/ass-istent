## CONECTOR NOTEBOOKLM
Conectar un MCP (Model Context Protocol) a una arquitectura LangGraph dockerizada requiere resolver un problema fundamental: **el aislamiento del contexto**. El motor de NotebookLM (o un servidor MCP impulsado por Gemini 1.5 Pro) que corre en la nube no tiene forma de acceder directamente a la carpeta `/pdfs/` que está físicamente en tu Raspberry Pi.

Para que el Agente Investigador pueda usar este MCP sin romper la arquitectura, debemos diseñar un puente de datos. Aquí te explico cómo se estructura esta conexión a nivel técnico, paso a paso:

### 1. La Topología del Servidor MCP (Docker + SSE)

El protocolo MCP permite dos tipos de conexión: `stdio` (entrada/salida estándar para procesos en la misma máquina) y **SSE (Server-Sent Events sobre HTTP)**.

Dado que tu sistema está 100% dockerizado en la Raspberry Pi, la mejor opción es levantar el servidor MCP como un contenedor independiente y comunicarlo vía SSE.

* **Contenedor Backend (LangGraph):** Actúa como el **MCP Client**.
* **Contenedor MCP (NotebookLM/Gemini):** Actúa como el **MCP Server**. Expone un endpoint HTTP (ej. `http://mcp-server:8080/sse`).

### 2. El Oleoducto de Datos (Pipeline)

Cuando el Investigador decide que necesita un análisis profundo de 3 papers, no le envía los PDFs en crudo al MCP. El flujo técnico es el siguiente:

1. **Lectura Local:** El agente invoca la herramienta local de lectura.
2. **Extracción (Tika OCR):** El archivo físico (ej. `/data/RAG_Papers/paper_1.pdf`) se envía al contenedor de Apache Tika en la red local de Docker. Tika devuelve el texto estructurado en memoria (Strings/JSON).
3. **Inyección al MCP:** Ahora que tenemos el texto limpio, el Cliente MCP de tu backend de LangGraph empaqueta este texto masivo junto con tu prompt (ej. *"Compara las métricas de estos estudios"*) y lo envía vía API al Servidor MCP de NotebookLM/Gemini 1.5 Pro. Aprovechamos aquí la ventana de 2 millones de tokens de Gemini, que puede ingerir el texto de docenas de papers de un solo golpe.

### 3. El Wrapper en LangGraph (El Código Conceptual)

Para que el modelo local (Qwen 3.5) entienda cómo usar esta maravilla de la nube, debemos envolver el cliente MCP en una herramienta estándar de Python (`@tool`). Así es como Antigravity debería diseñarlo:

```python
from langchain_core.tools import tool
import mcp_client # Librería teórica del cliente MCP

@tool
def notebooklm_mcp_analyze(document_ids: list[str], instruction: str) -> str:
    """
    Usa esta herramienta EXCLUSIVAMENTE para sintetizar, comparar o extraer el estado 
    del arte de múltiples documentos. 
    Requiere una lista de IDs de documentos y una instrucción de análisis detallada.
    """
    # 1. Recuperar el texto limpio de los PDFs desde la VectorDB o File System (pre-procesados por Tika)
    documents_text = retrieve_text_from_local_storage(document_ids)
    
    # 2. Conectar al contenedor del Servidor MCP vía Server-Sent Events (SSE)
    async with mcp_client.SSEClient("http://mcp-notebooklm-server:8080") as client:
        
        # 3. Llamar a la herramienta remota expuesta por el MCP
        resultado = client.call_tool(
            name="deep_synthesis",
            arguments={
                "documents": documents_text, 
                "prompt": instruction
            }
        )
        
    # 4. Devolver la síntesis pura al Agente Investigador
    return resultado.text

```

### 4. ¿Por qué esto es brillante a nivel arquitectónico?

* **Agnóstico al Proveedor:** El Agente Investigador (impulsado por Qwen local en tu PC) no sabe qué es Gemini ni qué es NotebookLM. Él solo sabe que tiene una función de Python llamada `notebooklm_mcp_analyze` que mágicamente le devuelve resúmenes perfectos. Si mañana quieres cambiar NotebookLM por otro MCP, cambias el servidor de Docker, no el código del Agente.
* **Cero Alucinaciones de Ruta:** Al extraer el texto con Tika primero, evitas que el modelo en la nube alucine rutas de archivos o intente acceder a directorios de la Raspberry Pi a los que no tiene permisos de red.
* **Eficiencia de Ancho de Banda:** Enviar texto plano extraído (JSON) a través de la API es muchísimo más rápido y económico que subir archivos PDF pesados con imágenes a la nube para cada consulta.
