# Entropy Evolve
We propose the EntropyEvolve.

This architecture is a general framework for agents self-improvement, applicable to any complex domain such as science or medicine. However, we have chosen software engineering as our initial testing ground.

## Problem description
We have a base coding agent that we want to improve. Using a continuous improvement cycle, EntropyEvolve is able to continually improve itself with feedback from its errors.
## Architecture
![EntropyEvolve](EntropyEvolveArch.jpeg)
## Instructions
git clone https://github.com/luisjosuecortes/EntropyEvolve.git

git clone https://github.com/SWE-bench/SWE-bench.git

cd SWE-bench

pip install -e .

cd ..

pip install langgraph

pip install openai

python cycle_graph.py

## Self improvement explication
This project develops a self-improving agent system designed to optimize its performance in solving programming problems.  
- The system consists of three coding agents, each assigned tasks from the SWE-Bench benchmark.
- An evaluation node executes their solutions, collects the results, and generates logs detailing any detected errors.
- These logs are analyzed by an evaluation agent, which extracts key insights about performance and mistakes.
- Based on this analysis, an optimization agent adjusts the prompts of the coding agents, thereby restarting the continuous improvement cycle.
- The entire system is implemented using a LangGraph graph structure, while the agents themselves are powered by OpenAI’s large language models (LLMs).

## Metric.
We used SWE-bench for testing and having a quantitative evaluation.