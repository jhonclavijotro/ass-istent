import os
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState
from app.agents.nodes import (
    supervisor_node,
    research_node,
    obsidian_node,
    obsidian_writer_node,
    finance_node,
    finance_writer_node,
    email_node,
    email_action_node,
    writer_node
)

logger = logging.getLogger("agent_graph")

# Instancia global del checkpointer de memoria de LangGraph
memory_checkpointer = MemorySaver()

def router_conditional(state: AgentState) -> str:
    """Función de enrutamiento condicional basada en la decisión del Supervisor"""
    return state.get("current_agent", "writer_agent")

def build_agent_graph():
    """Construye e inicializa el grafo agéntico de LangGraph con Checkpointer e Interrupciones HITL"""
    workflow = StateGraph(AgentState)
    
    # Agregar Nodos del Grafo
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research_agent", research_node)
    workflow.add_node("obsidian_agent", obsidian_node)
    workflow.add_node("obsidian_writer_node", obsidian_writer_node)
    workflow.add_node("finance_agent", finance_node)
    workflow.add_node("finance_writer_node", finance_writer_node)
    workflow.add_node("email_agent", email_node)
    workflow.add_node("email_action_node", email_action_node)
    workflow.add_node("writer_agent", writer_node)
    
    # Punto de entrada principal
    workflow.set_entry_point("supervisor")
    
    # Transiciones desde el Supervisor
    workflow.add_conditional_edges(
        "supervisor",
        router_conditional,
        {
            "research_agent": "research_agent",
            "obsidian_agent": "obsidian_agent",
            "obsidian_writer_node": "obsidian_writer_node",
            "finance_agent": "finance_agent",
            "finance_writer_node": "finance_writer_node",
            "email_agent": "email_agent",
            "email_action_node": "email_action_node",
            "writer_agent": "writer_agent"
        }
    )
    
    # Conexiones hacia los nodos de escritura o directamente al redactor
    workflow.add_edge("research_agent", "writer_agent")
    
    workflow.add_edge("obsidian_agent", "obsidian_writer_node")
    workflow.add_edge("obsidian_writer_node", "writer_agent")
    
    workflow.add_edge("finance_agent", "finance_writer_node")
    workflow.add_edge("finance_writer_node", "writer_agent")
    
    workflow.add_edge("email_agent", "email_action_node")
    workflow.add_edge("email_action_node", "writer_agent")
    
    # El Redactor finaliza el grafo
    workflow.add_edge("writer_agent", END)
    
    # Compilar el grafo con Checkpointer e Interrupciones HITL antes de ejecutar nodos destructivos
    app_graph = workflow.compile(
        checkpointer=memory_checkpointer,
        interrupt_before=[
            "obsidian_writer_node",
            "finance_writer_node",
            "email_action_node"
        ]
    )
    return app_graph

# Instancia global del Grafo Agéntico
agent_graph = build_agent_graph()
