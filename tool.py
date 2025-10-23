from datasets import load_dataset,disable_progress_bar
import random
from string import Template
from prompts import create_task_agent_prompt
from openai import OpenAI
import os
import json
import subprocess
from prompts import create_task_evaluator_agent_prompt,create_generator_prompt
disable_progress_bar()

def select_problem():
    swebench = load_dataset('princeton-nlp/SWE-bench_Lite', split='test')
    problems = swebench.select([random.randint(0,len(swebench)-1)for _ in range(9)])
    return problems

def run_agent(problem,prompt,model):

    results = []

    for instance in problem:
        prompt = create_task_agent_prompt(instance,prompt)

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        try:
            resp =  client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            code = resp.choices[0].message.content
            results.append({"instance_id": instance["instance_id"], "model_patch": code,"model_name_or_path":model})
        except Exception as e:
            return results.append({"instance_id": instance["instance_id"], "error": str(e)})
    
    with open("predictions/"+model+".json", "w") as f:
            json.dump(results, f)
    return "predictions/"+model+".json"

def run_swebench_eval(path):
      cmd = [
            "python", "-m", "swebench.harness.run_evaluation",
            "--dataset_name", "princeton-nlp/SWE-bench_Lite",
            "--predictions_path", path,
            "--max_workers", "20",
            "--run_id", "improve_process",
            "--report_dir", "reports"
            ]
      result = subprocess.run(cmd, capture_output=True, text=True)

def run_meta_evaluator(problem,outputs,logs):
    #$problem_statement

    with open(outputs) as f:
        predictions = json.load(f)
    
    feedback = []
    for instance in problem:
        prompt = create_task_evaluator_agent_prompt(instance,predictions,logs+instance["instance_id"]+".json")

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        try:
            resp =  client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            result = resp.choices[0].message.content
            
            result_json = json.loads(result)
            feedback.extend(result_json["potential_improvements"])
        except Exception as e:
            result = '{"potential_improvements":[]}'
            result_json = json.loads(result)
            feedback.extend(result_json["potential_improvements"])
    return feedback

def run_prompt_optimizer(feedback,prompts):
     
    completed_feed_back = []
    for model in feedback.keys():
        joined_analyses = "\n".join(f"- {a}" for a in feedback[model])
        joined_analyses ="---------------Model "+model+" feedback-------------\n"
        completed_feed_back.append(joined_analyses)
    
    final_feedback = "\n".join(f"{a}" for a in completed_feed_back)
    past_agents = "\n".join(f"------Code Agent-------\n{a}" for a in prompts.values())

    prompt = create_generator_prompt(feedback,past_agents)

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        resp =  client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        result = resp.choices[0].message.content
            
        result_json = json.loads(result)
    except Exception as e:
        result_json = prompts
    
    return result_json


