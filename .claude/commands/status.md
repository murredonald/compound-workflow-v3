# /status — Pipeline Progress Dashboard

Display the current pipeline progress across all workflow phases.

## Procedure

1. Run the pipeline tracker dashboard:

```bash
python .claude/tools/pipeline_tracker.py status
```

2. Display the output to the user verbatim — it's already formatted.

3. If the pipeline has not been initialized yet (file missing), inform the user:
   - Greenfield projects: `/plan` will initialize the tracker automatically
   - Evolution projects: `/intake` will initialize the tracker automatically

This command is **read-only** — it does not modify any state.
