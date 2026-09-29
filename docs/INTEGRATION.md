# Integrating an Agent

Bug2Eval does not know or care which model powers an agent. Integration is a process boundary.

## Environment variables

During `bug2eval run`, the agent receives:

- `BUG2EVAL_CASE_ID`
- `BUG2EVAL_WORKSPACE`
- `BUG2EVAL_TASK_FILE`
- `BUG2EVAL_PROMPT_FILE`
- `BUG2EVAL_VERIFY_COMMAND`

## Placeholders

`--agent-cmd` also supports:

- `{workspace}`
- `{task_file}`
- `{prompt_file}`

Example wrapper:

```python
import os
import subprocess

workspace = os.environ["BUG2EVAL_WORKSPACE"]
task = os.environ["BUG2EVAL_TASK_FILE"]
subprocess.run(["my-agent", "--cwd", workspace, "--task-file", task], check=False)
```

An adapter should return when the agent is finished editing the workspace. Bug2Eval then runs the captured verifier itself.
