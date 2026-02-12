"""Engine layer — orchestration logic between DB and LLM.

Modules:
  composer     — Context assembly + relevance filtering
  renderer     — Template engine for prompt injection
  validator    — Integrity checks (coverage, cycles, deps)
  synthesizer  — Hybrid deterministic+LLM task generation
  executor     — Execution loop (pick → context → record)
  planner      — Planning phase helpers
"""

# Shared constants
MAX_RETRY_CYCLES = 3
