# graph/state.py

from langgraph.graph.message import MessagesState

class SweBenchState(MessagesState):
    """
    Estado global del ciclo evolutivo para agentes codificadores con SWE-bench.
    """
    # Problema actual (por ejemplo: id, descripción, código relevante)
    problem = None

    # Salidas de los 3 codificadores: dict con claves coderA, coderB, coderC
    coder_outputs = {}

    # Resultados de evaluación de SWE-bench: dict con claves coderA, coderB, coderC
    eval_results = {}

    # Feedback del agente de evaluación meta (LLM grande)
    meta_feedback = None

    # Prompts optimizados para los codificadores para la siguiente iteración
    optimized_prompts = None

    # Contador de iteración actual
    iteration = 0

    # Límite máximo de iteraciones
    max_iterations = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inicializar campos mutables si es necesario
        self.problem = None
        self.coder_outputs = {}
        self.eval_results = {}
        self.meta_feedback = None
        self.optimized_prompts = None
        self.iteration = 0
        self.prompts = {}
        self.models = {}
        # Podrías cargar max_iterations desde configuración externa
