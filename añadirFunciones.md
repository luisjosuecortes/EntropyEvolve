# Funciones

### 1. **`initialize_agent(state)`** - Crear Agente Inicial

**Input:** Cualquier estado (se ignora)

**Output:**
```python
{
    "agent_id": 0,
    "agent_prompt": "You are an expert...",
    "message": "✓ Agente inicial creado (ID: 0)"
}
```

**Uso en LangGraph:**
```python
graph.add_node("init", agent_funcs.initialize_agent)
```

---

### 2. **`generate_code(state)`** - Generar Parche de Código

**Input requerido:**
```python
{
    "instance_id": "django__django-12497",
    "repo": "django",
    "problem_statement": "Fix bug in...",
    "test_patch": "..."
}
```

**Output:**
```python
{
    "instance_id": "django__django-12497",
    "model_patch": "```diff\n...",
    "model_name": "model-0",
    "message": "✓ Código generado"
}
```

**Uso en LangGraph:**
```python
graph.add_node("generate", agent_funcs.generate_code)
```

---

### 3. **`analyze_errors(state)`** - Analizar Errores

**Input requerido:**
```python
{
    "problem_statement": "...",
    "test_patch": "...",
    "predicted_patch": "...",
    "agent_patch_log": "...",
    "correct_patch": "..."
}
```

**Output:**
```python
{
    "analysis": {
        "log_summarization": "...",
        "potential_improvements": [...],
        "improvement_proposal": "...",
        ...
    },
    "potential_improvements": [...],
    "message": "✓ Análisis completado"
}
```

**Uso en LangGraph:**
```python
graph.add_node("analyze", agent_funcs.analyze_errors)
```

---

### 4. **`consolidate_analysis(state)`** - Consolidar Análisis

**Input requerido:**
```python
{
    "analyses": [
        {"potential_improvements": ["A", "B"]},
        {"potential_improvements": ["C", "D"]}
    ]
}
```

**Output:**
```python
{
    "consolidated_analysis": "- A\n- B\n- C\n- D",
    "num_improvements": 4,
    "message": "✓ Consolidados 4 mejoras"
}
```

**Uso en LangGraph:**
```python
graph.add_node("consolidate", agent_funcs.consolidate_analysis)
```

---

### 5. **`evolve_agent(state)`** - Crear Nuevo Agente Mejorado

**Input requerido:**
```python
{
    "consolidated_analysis": "- Improve X\n- Add Y\n..."
}
```

**Output:**
```python
{
    "new_agent_id": 1,
    "new_agent_prompt": "You are an advanced...",
    "learning_summary": "This agent integrates...",
    "message": "✓ Nuevo agente creado (ID: 1)"
}
```

**Uso en LangGraph:**
```python
graph.add_node("evolve", agent_funcs.evolve_agent)
```

---

### 6. **`get_current_agent_info(state)`** - Info del Agente Actual

**Input:** Cualquier estado

**Output:**
```python
{
    "current_agent_id": 1,
    "current_agent_prompt": "...",
    "total_agents": 2,
    "message": "✓ Agente actual: ID 1"
}
```

**Uso en LangGraph:**
```python
graph.add_node("get_info", agent_funcs.get_current_agent_info)
```

---

### 7. **`get_agent_history(state)`** - Historial Completo

**Input:** Cualquier estado

**Output:**
```python
{
    "agent_history": [
        {"id": 0, "prompt": "..."},
        {"id": 1, "prompt": "..."}
    ],
    "total_agents": 2,
    "message": "✓ Historial de 2 agentes"
}
```

# Integrar con LangGraph

**Solo 3 pasos:**

```python
# 1. Importar
from agents import AgentFunctions

# 2. Crear instancia
funcs = AgentFunctions()

# 3. Conectar en LangGraph
graph.add_node("init", funcs.initialize_agent)
graph.add_node("generate", funcs.generate_code)
graph.add_node("analyze", funcs.analyze_errors)
graph.add_node("consolidate", funcs.consolidate_analysis)
graph.add_node("evolve", funcs.evolve_agent)
```

---

## Ejemplo de uso

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict
from agents import AgentFunctions

# 1. Definir el estado
class AgentState(TypedDict):
    instance_id: str
    repo: str
    problem_statement: str
    test_patch: str
    agent_id: int
    model_patch: str
    message: str

# 2. Crear funciones
agent_funcs = AgentFunctions()

# 3. Crear grafo
graph = StateGraph(AgentState)

# 4. Añadir nodos
graph.add_node("initialize", agent_funcs.initialize_agent)
graph.add_node("generate", agent_funcs.generate_code)
graph.add_node("get_info", agent_funcs.get_current_agent_info)

# 5. Definir flujo
graph.set_entry_point("initialize")
graph.add_edge("initialize", "generate")
graph.add_edge("generate", "get_info")
graph.add_edge("get_info", END)

# 6. Compilar
app = graph.compile()

# 7. Ejecutar
initial_state = {
    "instance_id": "test-001",
    "repo": "django",
    "problem_statement": "Fix bug X",
    "test_patch": "..."
}

result = app.invoke(initial_state)
print(result["message"])
```

---

## Ejemplo de Loop Evolutivo

```python
from langgraph.graph import StateGraph, END

def should_continue(state):
    """Decide si continuar evolucionando"""
    return state.get("iteration", 0) < 5

def increment_iteration(state):
    """Incrementa el contador de iteraciones"""
    return {"iteration": state.get("iteration", 0) + 1}

# Crear grafo con loop
graph = StateGraph(AgentState)

graph.add_node("init", agent_funcs.initialize_agent)
graph.add_node("generate", agent_funcs.generate_code)
graph.add_node("analyze", agent_funcs.analyze_errors)
graph.add_node("consolidate", agent_funcs.consolidate_analysis)
graph.add_node("evolve", agent_funcs.evolve_agent)
graph.add_node("increment", increment_iteration)

# Flujo
graph.set_entry_point("init")
graph.add_edge("init", "generate")
graph.add_edge("generate", "analyze")
graph.add_edge("analyze", "consolidate")
graph.add_edge("consolidate", "evolve")
graph.add_edge("evolve", "increment")

# Conditional edge para loop
graph.add_conditional_edges(
    "increment",
    should_continue,
    {
        True: "generate",  # Volver a generar con nuevo agente
        False: END         # Terminar
    }
)

app = graph.compile()
```

---

## Funciones Auxiliares

### `parse_swebench_instance(instance)`

Extrae campos de una instancia de SWE-bench:

```python
from agents import parse_swebench_instance

instance = swebench[0]  # Dataset de HuggingFace
parsed = parse_swebench_instance(instance)
# {
#     "instance_id": "...",
#     "repo": "...",
#     "problem_statement": "...",
#     "test_patch": "...",
#     "correct_patch": "..."
# }
```

### `format_predictions_for_evaluation(predictions)`

Formatea predicciones para guardar:

```python
from agents import format_predictions_for_evaluation

predictions = [
    {"instance_id": "...", "model_patch": "...", "model_name": "model-0"}
]
json_str = format_predictions_for_evaluation(predictions)
# JSON string formateado
```
