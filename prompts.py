from string import Template
import re
import json

BASE_AGENT_PROMPT = """# Coding Agent Prompt

## Role
You are an expert **coding agent** responsible for analyzing and fixing problems in existing source code.  
Your mission is to **analyze**, **reason step-by-step**, and **propose a code modification** that resolves the issue described.

---
## Problem Definition

You are provided with the following problem statement:
<problem_statement>
$problem_statement
</problem_statement>

The problem describes a specific bug, failing test, or feature request.  
Your goal is to modify the codebase to address this issue **while preserving existing functionality**.

You are also provided with test patch that refers to a set of modifications or additions to the repository's test suite that are designed to verify a specific bug. 
Its main purpose is to ensure that the bug is detectable and can be validated when evaluating patches.

<test_patch>
$test_patch
</test_patch>

---

## Instructions

1. **Understand the problem** carefully.  
2. **Reason step-by-step** (using chain-of-thought reasoning) about:
   - What is causing the issue.  
   - What parts of the code need to change.  
   - How to fix it safely.  
3. Then, produce a **code patch** that solves the issue.  
4. The output **must be in unified diff format** (`diff --git`) so it can be directly applied using `git apply`.

---

## 🧩 Chain of Thought (Reasoning)

Think step-by-step before producing the patch.

Explain:
- Root cause analysis of the problem.  
- Files or functions involved.  
- Your detailed plan for the fix.  

Then, **output only** the `diff` of the final corrected code.

---

## Output Format

Your final answer **must follow this exact structure**:

````markdown
# Reasoning
<your step-by-step reasoning here>

# Patch
```diff
<your unified diff patch here>
```
````
---

## Example Output

````markdown
# Reasoning
The bug occurs because the function `get_user_info` does not handle the case
where `user_id` is None. We fix this by adding a guard clause before accessing the database.

# Patch
```diff
diff --git a/app/user.py b/app/user.py
index 3f5a3e4..b72c9d0 100644
--- a/app/user.py
+++ b/app/user.py
@@ -42,6 +42,9 @@ def get_user_info(user_id):
     # Fetch user info from database
     conn = get_db_connection()
 
+    if user_id is None:
+        return None
+
     cursor = conn.cursor()
     cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
     return cursor.fetchone()
```
````
## Notes

* Do not output explanations outside the specified structure.

* The diff must be syntactically valid and minimal.

* Do not include unrelated changes or formatting fixes.

* Maintain the existing code style and indentation.

* Assume access to the full repository unless otherwise specified.
"""

TASK_ANALIZER = """# Initial Context
You are an error analyzer specialized in code agents. 
Your task is to review how an agent attempted to solve a programming problem, based on logs, the predicted patch, and the official tests. 
You should evaluate both the agent's problem-solving strategy and the quality of its solution, and propose general improvements that could increase its effectiveness in future problems. 
Consider debugging tools, log analysis, testing strategies, code generation techniques, and any other skills that could improve an agent's ability to autonomously produce correct code. 
Your want to analyze the errors of the agent for giving potential improments focusing on the agent's general coding abilities.
You do not have access to the "correct patch" during the analysis; it is only used for comparison afterward.

After this context, process the information in the following sections:

# Problem Statement
The Problem Statement that the agent is trying to solve.
----- Problem Statement Start -----
$problem_statement
----- Problem Statement End -----

# Test Patch
SWE-bench's official tests to detect whether the issue is solved.
----- Private Test Patch Start -----
$test_patch
----- Private Test Patch End -----

# Predicted Patch
The agent's predicted patch to solve the issue.
----- Predicted Patch Start -----
$predicted_patch
----- Predicted Patch End -----

# Agent Patch Log
Part of the log that has been generated after aplying the agent's patch.
----- Agent Running Log Start -----
$agent_patch_log
----- Agent Running Log End -----

# Correct Patch
This is the correct path provide by SWE-bech. This is not available to the agent during coding generation. The agent should try to implement a solution like this by his own.
Respond precisely in the following format including the JSON start and end markers:
----- Correct Patch Start -----
$patch
----- Correct Patch End -----

Provide a JSON response with the following field:
- "potential_improvements": Must be a python list. Identify potential improvements to the coding agent that could enhance its coding capabilities. Focus on the agent's general coding abilities (e.g., better or new tools usable across any repository) rather than issue-specific fixes (e.g., tools only usable in one framework). All necessary dependencies and environment setup have already been handled, so do not focus on these aspects.
Your response will be automatically parsed, so ensure that the string response is precisely in the correct format. Do NOT include the `<JSON>` tag in your output."""

META_IMPROMENT_GENERATOR = """# ADVANCED META_IMPROVEMENT_GENERATOR

# Initial Context
You are a meta-level agent improvement generator. 
Your goal is to create **new and improved coding agents** by analyzing previous agents and their evaluations. 
You will take as input:

1. The agents codes that we want to improve.
1. The **analysis from an error analyzer** that reviewed the best agent's attempts to solve GitHub issues, and gived some potential improvements.    

Your task is to synthesize these insights to produce a more **new agent designs** that combines the best strategies, fixes weaknesses, and integrates new tools or features to improve coding capabilities across any repository.  
Focus on **general improvements** such as debugging strategies, log analysis, test generation, code synthesis, learning from failures, or multi-agent coordination.  
Do not focus on issue-specific fixes; the output should enhance **overall agent intelligence and performance**.

---

# Inputs

Error Analyzer Potential Improvements.
Analysis produced by the error analyzers for the first agent.
----- Original Agent Analysis Start -----
$error_analyzer_analysis
----- Original Agent Analysis End -----

Past agents
Paste agents codes.
----- Subsequent Agent Codes Start -----
$subsequent_agent_codes
----- Subsequent Agent Codes End -----

---

Remember, your task is to create a general code agents, with CoT strategies, do not create a solution for specific issues.

# Important Instruction
Keep Output Format **exactly as written** with the delimited areas, and  keep Notes exactly as written: 
---

# Task
Using the above inputs and instructions, generate a **new improved agents specification**. Include the following sections in a **single valid JSON block**:

Provide a JSON response with the following field:
- "A": New agent code, with improvements. Directly obtained by "A" key.
- "B": String, new agent code, different agent with improvements. Directly obtained by "B" key.
- "C": String, another agent code, with improvements. DIrectly obtained by "C" key.

Your response will be automatically parsed, so ensure that the string response is precisely in the correct format. Do NOT include the `<JSON>` tag in your output.
"""



def create_task_agent_prompt(instance,prompt_template):
    values = {'test_patch':instance['test_patch'],'problem_statement':instance["problem_statement"]}

    template_prompt = Template(prompt_template)
    prompt = template_prompt.substitute(values)
    
    return prompt

def parse_task_response(md_text):
    """Parse a Markdown document with sections like 'Reasoning' and 'Patch'.
    Returns a dictionary:
    {
        "Reasoning": "...",
        "Patch": {
            "diff_code": "..."
        }
    }
    """
    # Separar secciones por encabezados de nivel 1
    sections = re.split(r'^#\s+', md_text, flags=re.MULTILINE)
    parsed = {}
    
    for sec in sections:
        if not sec.strip():
            continue
        lines = sec.splitlines()
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        
        if title.lower() == 'patch':
            # Extraer solo el código dentro de ```diff ... ```
            diff_match = re.search(r'```diff\n(.*?)```', content, re.DOTALL)
            parsed['Patch'] = {
                'diff_code': diff_match.group(1).strip() if diff_match else ''
            }
        else:
            parsed[title] = content
    
    return parsed

def get_log(log_file):
    with open(log_file, "r") as f:
        lineas = f.readlines()
    return "\n".join(lineas[:50])

def create_task_evaluator_agent_prompt(instance,predictions,log_file):
    instance_id = instance["instance_id"]
    problem_statement = instance['problem_statement']
    test_patch = instance['test_patch']
    predicted_patch = next((x for x in predictions if x["instance_id"] == instance_id), None)["model_patch"]
    
    agent_patch_log = get_log(log_file)
    correct_patch =  instance['patch']

    template = Template(TASK_ANALIZER)
    prompt = template.substitute(problem_statement=problem_statement,test_patch=test_patch,predicted_patch=predicted_patch,agent_patch_log=agent_patch_log,patch=correct_patch)
    
    return prompt

def parse_meta_agent_generator(response):
    response_json = json.loads(response)
    return response_json

def create_generator_prompt(feedback,past_agents):
    prompt_template = Template(META_IMPROMENT_GENERATOR)

    prompt = prompt_template.substitute(error_analyzer_analysis=feedback,subsequent_agent_codes=past_agents)
    return prompt