from langgraph.graph import StateGraph, END
from state import SweBenchState

# Importamos los agentes (ya hechos con LangChain)
from tool import run_agent
from tool import run_swebench_eval
from tool import run_meta_evaluator
from tool import run_prompt_optimizer
from tool import select_problem
import json
# ---------------------------------------------------------------------
# NODOS DEL
# ---------------------------------------------------------------------

def get_prompts(state: SweBenchState):
    with open("agents.json","r") as f:
        prompts = json.load(f)
    
    state["prompts"] = prompts
    state["models"] = ["A","B","C"]
    return state


def node_select_problem(state: SweBenchState):
    """Selecciona un problema de SWE-bench."""
    problem = select_problem()
    state["problem"] = problem
    return state


def node_run_coders(state: SweBenchState):
    """Ejecuta los 3 codificadores con el mismo problema."""
    print("Ejecutando agentes codificadores...")
    
    problem = state["problem"]
    prompts = state["prompts"]

    state["coder_outputs"] = {
        "A": run_agent(problem, prompts["A"],"A"),
        "B": run_agent(problem, prompts["B"],"B"),
        "C": run_agent(problem, prompts["C"],"C")
    }
    return state


def node_swebench_eval(state: SweBenchState):
    """Evalúa los resultados de los coders con SWE-bench."""
    print("🧪 Evaluando parches en SWE-bench...")
    outputs = state["coder_outputs"]

    models = ["A","B","C"]

    logs_output = {}
    for model, result_path in outputs.items():
        run_swebench_eval(result_path)
        #logs/run_evaluation/'run_id'/'model_id'/
        logs_output[model] = "logs/run_evaluation/improve_process/"+model+"/"
    state["logs_output"] = logs_output
    return state


def node_meta_evaluator(state: SweBenchState):
    """El agente grande evalúa los resultados de SWE-bench."""
    print("🧠 MetaEvaluador analizando resultados...")

    feedback = {}
    for model in state["models"]:
        model_feedback = run_meta_evaluator(
            problem=state["problem"],
            coder_outputs=state["coder_outputs"][model],
            logs = state["logs_output"][model]
        )
        feedback[model] = model_feedback
    state["meta_feedback"] = feedback
    return state


def node_prompt_optimizer(state: SweBenchState):
    """Genera nuevos prompts basados en el feedback del evaluador."""
    print("🔧 Optimizando prompts...")
    optimized = run_prompt_optimizer(state["meta_feedback"], state["prompts"])
    state["optimized_prompts"] = optimized
    return state


def node_update_coders(state: SweBenchState):
    """Actualiza los coders con los nuevos prompts."""
    print("🔄 Actualizando coders...")
    state["prompts"] = state["optimized_prompts"]
    with open("agents.json","w") as f:
       json.dump(state["prompts"],f)
    state["iteration"] = state.get("iteration", 0) + 1
    return state


# ---------------------------------------------------------------------
# 2️⃣ CONDICIÓN DEL LOOP
# ---------------------------------------------------------------------
def should_continue(state: SweBenchState):
    """Decide si continuar el ciclo o finalizar."""
    max_score = max(v["score"] for v in state["eval_results"].values())
    if max_score >= 0.9 or state.get("iteration", 0) >= state.get("max_iterations", 5):
        print(f"✅ Fin del ciclo: iteraciones={state.get('iteration', 0)}, mejor score={max_score}")
        return END
    else:
        print(f"🔁 Continuando ciclo, iteración {state.get('iteration', 0) + 1}...")
        return "select_problem"


# ---------------------------------------------------------------------
# 3️⃣ CONSTRUCCIÓN DEL GRAFO
# ---------------------------------------------------------------------
def build_cycle_graph():
    workflow = StateGraph(SweBenchState)
    
    # Agregar nodos
    workflow.add_node("get_prompts",get_prompts)
    workflow.add_node("select_problem", node_select_problem)
    workflow.add_node("run_coders", node_run_coders)
    workflow.add_node("swebench_eval", node_swebench_eval)
    workflow.add_node("meta_evaluator", node_meta_evaluator)
    workflow.add_node("prompt_optimizer", node_prompt_optimizer)
    workflow.add_node("update_coders", node_update_coders)

    # Definir conexiones
    workflow.set_entry_point("get_prompts")
    workflow.add_edge("get_prompts","select_problem")
    workflow.add_edge("select_problem", "run_coders")
    workflow.add_edge("run_coders", "swebench_eval")
    workflow.add_edge("swebench_eval", "meta_evaluator")
    workflow.add_edge("meta_evaluator", "prompt_optimizer")
    workflow.add_edge("prompt_optimizer", "update_coders")

    # Bucle condicional
    workflow.add_conditional_edges("update_coders", should_continue)

    return workflow.compile()

if __name__ == "__main__":
    graph = build_cycle_graph()
    initial_state = {}
    graph.invoke(initial_state)