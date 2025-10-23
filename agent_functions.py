"""
Funciones encapsuladas para usar en LangGraph
Este módulo expone funciones listas para usar que NO requieren implementación adicional.
"""

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from typing import Dict, List, Any
import json

from .src import CodeAgent
from .db import DataBase
from .promts import BASE_AGENT, TASK_IMPROVEMENT_REASONER, META_IMPROMENT_GENERATOR


class AgentFunctions:
    """
    Clase que encapsula todas las funciones del sistema de agentes.
    Para usar en LangGraph: instanciar esta clase y usar sus métodos como nodos del grafo.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0):
        """
        Inicializa las funciones del agente.
        
        Args:
            model: Modelo de OpenAI a usar
            temperature: Temperatura del modelo (0.0 = determinístico)
        """
        # Configurar LangChain
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.chain = self.llm | StrOutputParser()
        
        # Base de datos de agentes
        self.database = DataBase()
        
        # Agente actual
        self.current_agent: CodeAgent = None
    
    # =========================================================================
    # FUNCIÓN 1: Inicializar Agente Base
    # =========================================================================
    
    def initialize_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea el agente inicial con el prompt BASE_AGENT.
        
        Input state:
            - Cualquier estado inicial (se ignora)
        
        Output state:
            - agent_id: int (ID del agente creado)
            - agent_prompt: str (Prompt del agente)
            - message: str (Mensaje de confirmación)
        
        Uso en LangGraph:
            graph.add_node("initialize", agent_functions.initialize_agent)
        """
        agent = CodeAgent(prompt=BASE_AGENT)
        self.database.add(agent)
        self.current_agent = agent
        
        return {
            **state,
            "agent_id": agent.id,
            "agent_prompt": agent.prompt if isinstance(agent.prompt, str) else agent.prompt.template,
            "message": f"✓ Agente inicial creado (ID: {agent.id})"
        }
    
    # =========================================================================
    # FUNCIÓN 2: Generar Código (async)
    # =========================================================================
    
    async def generate_code(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un parche de código para resolver un problema.
        
        Input state (requerido):
            - instance_id: str
            - repo: str
            - problem_statement: str
            - test_patch: str
        
        Output state:
            - instance_id: str
            - model_patch: str (código generado)
            - model_name: str
            - message: str
        
        Uso en LangGraph:
            graph.add_node("generate_code", agent_functions.generate_code)
        """
        try:
            # Obtener datos del state
            instance_id = state["instance_id"]
            repo = state["repo"]
            problem_statement = state["problem_statement"]
            test_patch = state["test_patch"]
            
            # Generar código usando el agente actual
            prompt_template = (
                self.current_agent.prompt_template 
                if self.current_agent.prompt_template 
                else PromptTemplate.from_template(self.current_agent.prompt)
            )
            
            code = await (prompt_template | self.chain).ainvoke({
                "repo": repo,
                "problem_statement": problem_statement,
                "test_patch": test_patch
            })
            
            return {
                **state,
                "instance_id": instance_id,
                "model_patch": code,
                "model_name": f"model-{self.current_agent.id}",
                "message": f"✓ Código generado para {instance_id}"
            }
            
        except Exception as e:
            return {
                **state,
                "error": str(e),
                "message": f"✗ Error generando código: {e}"
            }
    
    # =========================================================================
    # FUNCIÓN 3: Analizar Errores
    # =========================================================================
    
    def analyze_errors(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza por qué falló el agente y sugiere mejoras.
        
        Input state (requerido):
            - problem_statement: str
            - test_patch: str
            - predicted_patch: str
            - agent_patch_log: str
            - correct_patch: str
        
        Output state:
            - analysis: dict (JSON parseado con potential_improvements, etc.)
            - message: str
        
        Uso en LangGraph:
            graph.add_node("analyze_errors", agent_functions.analyze_errors)
        """
        try:
            result = (TASK_IMPROVEMENT_REASONER | self.chain).invoke({
                "problem_statement": state["problem_statement"],
                "test_patch": state["test_patch"],
                "predicted_patch": state["predicted_patch"],
                "agent_patch_log": state["agent_patch_log"],
                "patch": state["correct_patch"]
            })
            
            # Parsear JSON
            analysis = json.loads(result.strip())
            
            return {
                **state,
                "analysis": analysis,
                "potential_improvements": analysis.get("potential_improvements", []),
                "message": "✓ Análisis de errores completado"
            }
            
        except Exception as e:
            return {
                **state,
                "error": str(e),
                "message": f"✗ Error analizando: {e}"
            }
    
    # =========================================================================
    # FUNCIÓN 4: Consolidar Análisis
    # =========================================================================
    
    def consolidate_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consolida múltiples análisis de errores en un solo texto.
        
        Input state (requerido):
            - analyses: List[dict] (lista de análisis)
        
        Output state:
            - consolidated_analysis: str (texto consolidado)
            - message: str
        
        Uso en LangGraph:
            graph.add_node("consolidate", agent_functions.consolidate_analysis)
        """
        analyses = state.get("analyses", [])
        
        all_improvements = []
        for analysis in analyses:
            improvements = analysis.get("potential_improvements", [])
            all_improvements.extend(improvements)
        
        consolidated = "\n".join(f"- {imp}" for imp in all_improvements)
        
        return {
            **state,
            "consolidated_analysis": consolidated,
            "num_improvements": len(all_improvements),
            "message": f"✓ Consolidados {len(all_improvements)} mejoras"
        }
    
    # =========================================================================
    # FUNCIÓN 5: Evolucionar Agente
    # =========================================================================
    
    def evolve_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un nuevo agente mejorado basado en análisis de errores.
        
        Input state (requerido):
            - consolidated_analysis: str (análisis consolidado)
        
        Output state:
            - new_agent_id: int
            - new_agent_prompt: str
            - learning_summary: str
            - message: str
        
        Uso en LangGraph:
            graph.add_node("evolve", agent_functions.evolve_agent)
        """
        try:
            # Obtener prompts de agentes pasados
            past_prompts = [
                a.prompt if isinstance(a.prompt, str) else a.prompt.template 
                for a in self.database.get_agents()
            ]
            
            current_prompt = (
                self.current_agent.prompt 
                if isinstance(self.current_agent.prompt, str) 
                else self.current_agent.prompt.template
            )
            
            # Generar nuevo agente
            result = (META_IMPROMENT_GENERATOR | self.chain).invoke({
                "code": current_prompt,
                "error_analyzer_analysis": state["consolidated_analysis"],
                "subsequent_agent_codes": "----------Past Agent----------\n".join(past_prompts)
            })
            
            # Parsear resultado
            new_agent_data = json.loads(result.strip())
            new_prompt = new_agent_data["new_agent"]
            learning = new_agent_data.get("learning_from_previous_agents", "N/A")
            
            # Validar que el prompt sea válido
            PromptTemplate.from_template(new_prompt).format(
                repo="", 
                problem_statement="", 
                test_patch=""
            )
            
            # Crear nuevo agente
            new_agent = CodeAgent(prompt=new_prompt)
            self.database.add(new_agent)
            self.current_agent = new_agent
            
            return {
                **state,
                "new_agent_id": new_agent.id,
                "new_agent_prompt": new_prompt,
                "learning_summary": learning,
                "message": f"✓ Nuevo agente creado (ID: {new_agent.id})"
            }
            
        except Exception as e:
            return {
                **state,
                "error": str(e),
                "message": f"✗ Error evolucionando agente: {e}"
            }
    
    # =========================================================================
    # FUNCIÓN 6: Obtener Información del Agente Actual
    # =========================================================================
    
    def get_current_agent_info(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retorna información del agente actual.
        
        Output state:
            - current_agent_id: int
            - current_agent_prompt: str
            - total_agents: int
            - message: str
        
        Uso en LangGraph:
            graph.add_node("get_info", agent_functions.get_current_agent_info)
        """
        if self.current_agent is None:
            return {
                **state,
                "current_agent_id": None,
                "message": "✗ No hay agente actual"
            }
        
        return {
            **state,
            "current_agent_id": self.current_agent.id,
            "current_agent_prompt": (
                self.current_agent.prompt 
                if isinstance(self.current_agent.prompt, str) 
                else self.current_agent.prompt.template
            ),
            "total_agents": len(self.database.get_agents()),
            "message": f"✓ Agente actual: ID {self.current_agent.id}"
        }
    
    # =========================================================================
    # FUNCIÓN 7: Obtener Historial de Agentes
    # =========================================================================
    
    def get_agent_history(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retorna el historial completo de agentes.
        
        Output state:
            - agent_history: List[dict] (lista con info de cada agente)
            - total_agents: int
            - message: str
        
        Uso en LangGraph:
            graph.add_node("get_history", agent_functions.get_agent_history)
        """
        history = []
        for agent in self.database.get_agents():
            history.append({
                "id": agent.id,
                "prompt": agent.prompt if isinstance(agent.prompt, str) else agent.prompt.template
            })
        
        return {
            **state,
            "agent_history": history,
            "total_agents": len(history),
            "message": f"✓ Historial de {len(history)} agentes"
        }


# ============================================================================
# FUNCIONES AUXILIARES (sin estado, puras)
# ============================================================================

def format_predictions_for_evaluation(predictions: List[Dict]) -> str:
    """
    Formatea predicciones para guardar en JSON.
    
    Args:
        predictions: Lista de dicts con instance_id, model_patch, model_name
    
    Returns:
        JSON string formateado
    """
    return json.dumps(predictions, indent=2)


def parse_swebench_instance(instance: Dict) -> Dict[str, str]:
    """
    Extrae campos relevantes de una instancia de SWE-bench.
    
    Args:
        instance: Dict con datos de SWE-bench
    
    Returns:
        Dict con instance_id, repo, problem_statement, test_patch, patch
    """
    return {
        "instance_id": instance["instance_id"],
        "repo": instance["repo"],
        "problem_statement": instance["problem_statement"],
        "test_patch": instance["test_patch"],
        "correct_patch": instance["patch"]
    }
