# Vuls

Vuls is a Telegram-first AI Product Builder. The current implementation is a Python 3.13 FastAPI and aiogram codebase with deterministic product, reference, design, agent workflow, and generation-context layers.

## Current Implementation

The current implemented pipeline is:

```text
Product Intelligence
-> Reference Image Intelligence
-> Reference Analysis
-> Design Intelligence
-> Agent Workflow
-> Agent Execution
-> Generation Context
```

Runtime project and Telegram services create project briefs, persist deterministic intelligence artifacts, assemble generation context, call the generation orchestrator, and optionally export generated output as ZIP or GitHub after generation.

LLM-backed Product Manager, UX Designer, UI Designer, Frontend Engineer, Backend Engineer, and QA Engineer agents are future roadmap components. They are documented, but they are not currently active specialized agents in the deterministic workflow.

## Local Checks

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```
