import asyncio
import sys
import os

# Agregar la raíz del backend al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.llm_router import llm_router
from app.agents.graph import agent_graph

async def test_llm_router():
    print("=== PRUEBA 1: VERIFICACIÓN DEL ROUTER LLM ===")
    provider_tier, model_name, endpoint = await llm_router.get_active_provider()
    print(f"[+] Proveedor Activo: {provider_tier}")
    print(f"[+] Modelo Seleccionado: {model_name}")
    print(f"[+] Endpoint: {endpoint}")
    
    response = await llm_router.generate_response("Hola, responde de forma breve.")
    print(f"[+] Respuesta Generada ({response['tier']}): {response['response']}")
    print(f"[+] Latencia: {response['latency_ms']} ms")
    assert response["response"] is not None

async def test_agent_graph():
    print("\n=== PRUEBA 2: EJECUCIÓN DEL GRAFO LANGGRAPH ===")
    test_queries = [
        "¿Puedes analizar el archivo PDF de informes?",
        "Escribe una nota en Obsidian sobre la reunión de hoy.",
        "¿Cuál es el saldo del presupuesto en Excel?",
        "Explícame cómo funciona la energía solar."
    ]
    
    for q in test_queries:
        print(f"\n--- Probando consulta: '{q}' ---")
        state = {
            "user_query": q,
            "thread_id": "test_thread",
            "agent_history": [],
            "current_agent": "supervisor",
            "active_tier": "",
            "active_model": "",
            "research_context": None,
            "obsidian_context": None,
            "finance_context": None,
            "final_response": None,
            "latency_ms": 0.0
        }
        res = await agent_graph.ainvoke(state)
        print(f"[+] Agente seleccionado: {res['current_agent']}")
        print(f"[+] Historial del grafo: {res['agent_history']}")
        print(f"[+] Nivel LLM utilizado: {res['active_tier']}")
        print(f"[+] Respuesta sintética: {res['final_response']}")

if __name__ == "__main__":
    asyncio.run(test_llm_router())
    asyncio.run(test_agent_graph())
