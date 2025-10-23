# graph/cycle_graph.py
from langgraph.graph import StateGraph, END
from graph.state import SweBenchState

# Importamos los agentes (ya hechos con LangChain)
from agents.coder_a import run_coder_a
from agents.coder_b import run_coder_b
from agents.coder_c import run_coder_c
from agents.meta_evaluator import run_meta_evaluator
from agents.prompt_optimizer import run_prompt_optimizer

# Importamos las herramientas utilitarias
from tools.swebench_eval import run_swebench_eval
from tools.problem_selector import select_problem
from tools.update_coders import update_coders_prompts


# ---------------------------------------------------------------------
# NODOS DEL
# ---------------------------------------------------------------------

def node_select_problem(state: SweBenchState):
    """Selecciona un problema de SWE-bench."""
    problem = select_problem()
    state.problem = problem
    print(f"🧩 Problema seleccionado: {problem['id']}")
    return state


def node_run_coders(state: SweBenchState):
    """Ejecuta los 3 codificadores con el mismo problema."""
    print("Ejecutando agentes codificadores...")
    problem = state.problem

    state.coder_outputs = {
        "coderA": run_coder_a(problem, prompt),
        "coderB": run_coder_b(problem),
        "coderC": run_coder_c(problem)
    }
    return state


def node_swebench_eval(state: SweBenchState):
    """Evalúa los resultados de los coders con SWE-bench."""
    print("🧪 Evaluando parches en SWE-bench...")
    results = run_swebench_eval(state.coder_outputs)
    state.eval_results = results
    return state


def node_meta_evaluator(state: SweBenchState):
    """El agente grande evalúa los resultados de SWE-bench."""
    print("🧠 MetaEvaluador analizando resultados...")
    feedback = run_meta_evaluator(
        problem=state.problem,
        coder_outputs=state.coder_outputs,
        eval_results=state.eval_results
    )
    state.meta_feedback = feedback
    return state


def node_prompt_optimizer(state: SweBenchState):
    """Genera nuevos prompts basados en el feedback del evaluador."""
    print("🔧 Optimizando prompts...")
    optimized = run_prompt_optimizer(state.meta_feedback)
    state.optimized_prompts = optimized
    return state


def node_update_coders(state: SweBenchState):
    """Actualiza los coders con los nuevos prompts."""
    print("🔄 Actualizando coders...")
    update_coders_prompts(state.optimized_prompts)
    state.iteration += 1
    return state


# ---------------------------------------------------------------------
# 2️⃣ CONDICIÓN DEL LOOP
# ---------------------------------------------------------------------
def should_continue(state: SweBenchState):
    """Decide si continuar el ciclo o finalizar."""
    max_score = max(v["score"] for v in state.eval_results.values())
    if max_score >= 0.9 or state.iteration >= state.max_iterations:
        print(f"✅ Fin del ciclo: iteraciones={state.iteration}, mejor score={max_score}")
        return END
    else:
        print(f"🔁 Continuando ciclo, iteración {state.iteration + 1}...")
        return "select_problem"


# ---------------------------------------------------------------------
# 3️⃣ CONSTRUCCIÓN DEL GRAFO
# ---------------------------------------------------------------------
def build_cycle_graph():
    workflow = StateGraph(SweBenchState)

    # Agregar nodos
    workflow.add_node("select_problem", node_select_problem)
    workflow.add_node("run_coders", node_run_coders)
    workflow.add_node("swebench_eval", node_swebench_eval)
    workflow.add_node("meta_evaluator", node_meta_evaluator)
    workflow.add_node("prompt_optimizer", node_prompt_optimizer)
    workflow.add_node("update_coders", node_update_coders)

    # Definir conexiones
    workflow.set_entry_point("select_problem")
    workflow.add_edge("select_problem", "run_coders")
    workflow.add_edge("run_coders", "swebench_eval")
    workflow.add_edge("swebench_eval", "meta_evaluator")
    workflow.add_edge("meta_evaluator", "prompt_optimizer")
    workflow.add_edge("prompt_optimizer", "update_coders")

    # Bucle condicional
    workflow.add_conditional_edges("update_coders", should_continue)

    return workflow.compile()
