import os
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState
from app.agents.nodes import (
    supervisor_node,
    research_node,
    obsidian_node,
    finance_node,
    writer_node
)

logger = logging.getLogger("agent_graph")

# Instancia global del checkpointer de memoria de LangGraph
memory_checkpointer = MemorySaver()

def router_conditional(state: AgentState) -> str:
    """Función de enrutamiento condicional basada en la decisión del Supervisor"""
    return state.get("current_agent", "writer_agent")

def build_agent_graph():
    """Construye e inicializa el grafo agéntico de LangGraph con Checkpointer de Memoria persistente"""
    workflow = StateGraph(AgentState)
    
    # Agregar Nodos del Grafo
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_agent", research_node)
    workflow.add_node("obsidian_agent", obsidian_node)
    workflow.add_node("finance_agent", finance_node)
    workflow.add_node("writer_agent", writer_node)
    
    # Definir Punto de Entrada
    workflow.set_entry_point("supervisor")
    
    # Transiciones desde el Supervisor hacia agentes especializados
    workflow.add_conditional_edges(
        "supervisor",
        router_conditional,
        {
            "research_agent": "research_agent",
            "obsidian_agent": "obsidian_agent",
            "finance_agent": "finance_agent",
            "writer_agent": "writer_agent"
        }
    )
    
    # Todos los agentes especializados convergen en el Redactor para sintetizar
    workflow.add_edge("research_agent", "writer_agent")
    workflow.add_edge("obsidian_agent", "writer_agent")
    workflow.add_edge("finance_agent", "writer_agent")
    
    # El Redactor finaliza la ejecución
    workflow.add_edge("writer_agent", END)
    
    # Compilar el grafo con checkpointer para persistencia de memoria por hilo (thread_id)
    app_graph = workflow.compile(checkpointer=memory_checkpointer)
    return app_graph

# Instancia global del Grafo Agéntico
agent_graph = build_agent_graph()
