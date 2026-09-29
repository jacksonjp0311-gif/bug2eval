---
name: bug2eval
description: Capture a real fixed bug as a portable regression eval, validate the before/after contract, and replay it against coding agents.
---

# Bug2Eval Skill

Use this skill after fixing a reproducible software bug when the failure should become a permanent evaluation case.

## Trigger

Use Bug2Eval when all of the following are true:

- there is a concrete bug or regression;
- a verifier/test can distinguish broken from fixed behavior;
- both a broken state and a fixed state are available.

Do not create an eval from an unverified claim.

## Preferred Git flow

```bash
bug2eval capture --id <ID> --title "<TITLE>" --before-ref <BROKEN_REF> --after-ref <FIXED_REF> --verify "<COMMAND>"
bug2eval validate .bug2eval/cases/<ID> --json
```

## Directory flow

```bash
bug2eval capture --id <ID> --title "<TITLE>" --before-dir <BROKEN_DIR> --after-dir <FIXED_DIR> --verify "<COMMAND>"
```

## Acceptance gate

Accept a case only if `bug2eval validate` reports:

- before verification exits non-zero;
- after verification exits zero;
- all artifact checksums match.

## Replaying against an agent

```bash
bug2eval run <CASE> --agent-cmd '<AGENT COMMAND USING {workspace} AND/OR {task_file}>' --json
```

Never edit the captured case while evaluating an agent. The agent should only modify its isolated workspace.
