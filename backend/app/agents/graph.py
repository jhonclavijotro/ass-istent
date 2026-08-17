import os
import glob
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
    file_agent,
    file_action_node,
    writer_node
)

logger = logging.getLogger("agent_graph")

memory_checkpointer = MemorySaver()

def read_persistent_obsidian_notes() -> str:
    """Lee todas las notas de la Bóveda de Obsidian para inyectarlas como Memoria a Largo Plazo"""
    obs_dirs = [
        "/app/data/obsidian",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "obsidian"))
    ]
    
    target_dir = None
    for d in obs_dirs:
        if os.path.exists(d):
            target_dir = d
            break
            
    if not target_dir:
        return ""

    md_files = glob.glob(os.path.join(target_dir, "**", "*.md"), recursive=True)
    if not md_files:
        return ""

    notes_content = []
    for filepath in md_files:
        filename = os.path.basename(filepath)
        if filename.startswith("."): continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    notes_content.append(f"--- NOTA BÓVEDA ({filename}) ---\n{c}")
        except Exception as e:
            logger.warning(f"Error al leer nota {filepath}: {e}")

    return "\n\n".join(notes_content)

def router_conditional(state: AgentState) -> str:
    """Función de enrutamiento condicional basada en la decisión del Supervisor"""
    agent = state.get("current_agent", "writer_agent")
    if agent in ["writer_node", "writer_agent"]:
        return "writer_agent"
    if agent in ["research_node", "research_agent"]:
        return "research_agent"
    if agent in ["obsidian_node", "obsidian_agent"]:
        return "obsidian_agent"
    if agent in ["finance_node", "finance_agent"]:
        return "finance_agent"
    if agent in ["email_node", "email_agent"]:
        return "email_agent"
    if agent in ["file_agent", "file_node"]:
        return "file_agent"
    return agent

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
    workflow.add_node("file_agent", file_agent)
    workflow.add_node("file_action_node", file_action_node)
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
            "file_agent": "file_agent",
            "file_action_node": "file_action_node",
            "writer_agent": "writer_agent"
        }
    )
    
    # Conexiones hacia los nodos de escritura/acción o directamente al redactor
    workflow.add_edge("research_agent", "writer_agent")
    
    workflow.add_edge("obsidian_agent", "obsidian_writer_node")
    workflow.add_edge("obsidian_writer_node", "writer_agent")
    
    # El agente de finanzas se conecta directamente al redactor (a menos que requiera HITL explícito)
    workflow.add_edge("finance_agent", "writer_agent")
    workflow.add_edge("finance_writer_node", "writer_agent")
    
    workflow.add_edge("email_agent", "email_action_node")
    workflow.add_edge("email_action_node", "writer_agent")

    workflow.add_edge("file_agent", "file_action_node")
    workflow.add_edge("file_action_node", "writer_agent")
    
    # El Redactor finaliza el grafo
    workflow.add_edge("writer_agent", END)
    
    # Compilar el grafo con Checkpointer e Interrupciones HITL antes de ejecutar nodos destructivos
    app_graph = workflow.compile(
        checkpointer=memory_checkpointer,
        interrupt_before=[
            "obsidian_writer_node",
            "finance_writer_node",
            "email_action_node",
            "file_action_node"
        ]
    )
    return app_graph

agent_graph = build_agent_graph()
