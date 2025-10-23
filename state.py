# graph/state.py

from typing import TypedDict, Any

class SweBenchState(TypedDict, total=False):
    """
    Estado global del ciclo evolutivo para agentes codificadores con SWE-bench.
    """
    # Problema actual (por ejemplo: id, descripción, código relevante)
    problem: Any

    # Salidas de los 3 codificadores: dict con claves coderA, coderB, coderC
    coder_outputs: dict

    # Resultados de evaluación de SWE-bench: dict con claves coderA, coderB, coderC
    eval_results: dict

    # Feedback del agente de evaluación meta (LLM grande)
    meta_feedback: Any

    # Prompts optimizados para los codificadores para la siguiente iteración
    optimized_prompts: Any

    # Contador de iteración actual
    iteration: int

    # Límite máximo de iteraciones
    max_iterations: int
    
    # Prompts actuales
    prompts: dict
    
    # Modelos activos
    models: list
    
    # Logs de salida
    logs_output: dict
