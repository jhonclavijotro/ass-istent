# Especificación Técnica: Diagnóstico de Proveedores LLM y Validación Agéntica

**Fecha de la Sesión:** Mañana (19 de Agosto de 2026)  
**Proyecto:** Asistente Agéntico Distribuido (Raspberry Pi 5 + PC Local Ollama + Gemini Cloud + Obsidian Vault)  
**Estado:** PLANIFICADO / PENDIENTE DE EJECUCIÓN

---

## 🎯 Objetivo General

Realizar una revisión exhaustiva del sistema agéntico para diagnosticar, corregir y validar la comunicación con los dos proveedores de LLM (**PC Local Ollama** y **Gemini Cloud**). Se investigará por qué las solicitudes enviadas no retornan respuesta o se estancan, prestando especial atención a la falta de actividad en el modelo local de Ollama a pesar de estar reportado como disponible.

---

## 🔍 Problemas Detectados a Investigar

### 1. Ausencia de Procesamiento en PC Local Ollama (`tier1_pc`)
- **Síntoma**: Aun cuando Ollama se encuentra ejecutándose en el PC local y pasa las comprobaciones de salud (`check_pc_ollama_health`), las consultas agénticas no muestran actividad de procesamiento en Ollama ni devuelven respuestas.
- **Puntos a Investigar**:
  1. **Endpoint y Payload API de Ollama**: Verificar si `llm_router.py` envía la estructura correcta a `/api/generate` o `/api/chat` (campos `model`, `prompt`, `system`, `stream: false`, `options`).
  2. **Timeout e Interbloqueos (Hangs)**: Inspeccionar si las peticiones `httpx` se bloquean indefinidamente por falta de timeout estricto o por interbloqueos de socket en la red local LAN entre la Raspberry Pi 5 y el PC (`192.168.1.X`).
  3. **Configuración de CORS y Host en Ollama**: Confirmar que `OLLAMA_HOST=0.0.0.0` y `OLLAMA_ORIGINS=*` estén activos en la PC local para permitir conexiones entrantes desde la RPi 5.

### 2. Fallos o Estancamiento en Gemini Cloud (`tier2_cloud`)
- **Síntoma**: Las peticiones a Gemini Cloud sufren timeouts o retornan errores de comunicación en escenarios de alta carga.
- **Puntos a Investigar**:
  1. Validación de claves de API y cuotas (`check_gemini_health`).
  2. Manejo de excepciones y conmutación (*failover*) limpia hacia el siguiente nivel sin congelar la interfaz de usuario.

---

## 🛠️ Plan de Trabajo para la Sesión

### Fase 1: Diagnóstico de Comunicaciones y Telemetría de Red
- [ ] Implementar **logs detallados de diagnóstico** en `backend/app/core/llm_router.py` para cada llamada saliente:
  - Timestamp exacto.
  - Proveedor y modelo objetivo (ej. `http://192.168.1.X:11434/api/generate` / `qwen3.5:4b`).
  - Tamaño de prompt y payload enviado.
  - Código de respuesta HTTP y latencia en milisegundos.
  - Detalle completo del error en caso de fallo.
- [ ] Probar la conectividad directa desde la Raspberry Pi 5 hacia Ollama en el PC Local mediante `curl` HTTP directo:
  ```bash
  curl http://<IP_PC_LOCAL>:11434/api/generate -d '{"model": "qwen3.5:4b", "prompt": "hola", "stream": false}'
  ```

### Fase 2: Corrección y Ajuste en `llm_router.py` y `gemini_service.py`
- [ ] Garantizar que las solicitudes a Ollama envíen el parámetro `"stream": False` y utilicen el endpoint adecuado.
- [ ] Configurar un timeout estricto no bloqueante (ej. 15 segundos para salud, 45 segundos para inferencia completa).
- [ ] Refactorizar el mecanismo de *failover* automático: si el PC Local Ollama no responde en X segundos, conmutar inmediatamente a Gemini Cloud o al fallback del sistema sin colgar la UI.

### Fase 3: Pruebas de Validación End-to-End por Agente
- [ ] **Coordinador Supervisor**: Validar enrutamiento rápido sin latencia innecesaria.
- [ ] **Agente Investigador con NotebookLM MCP**: Confirmar que las búsquedas y síntesis de 10 artículos se procesen de forma fluida.
- [ ] **Agente Bóveda Obsidian**: Confirmar que las acciones de creación y purga en disco se ejecuten y reporten al usuario sin alucinaciones.
- [ ] **Agentes de Codificación y LaTeX**: Probar generación de scripts Python y plantillas `.tex`.

---

## 📋 Criterios de Aceptación

1. **Visibilidad de Ollama**: Se observa actividad de inferencia activa en la consola del PC Local Ollama cuando la Raspberry Pi le envía consultas.
2. **Respuesta Fluida**: Ninguna solicitud a la API `/api/chat` se queda congelada indefinidamente en la interfaz web.
3. **Failover Robusto**: Si un proveedor falla o se desconecta, el sistema pasa al siguiente nivel en menos de 5 segundos y reporta el proveedor activo real en la respuesta.
4. **Validación Agéntica 100%**: Todos los agentes responden correctamente y ejecutan sus funciones asignadas de forma verificable.
