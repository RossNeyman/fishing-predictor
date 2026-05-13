# Agent Instructions (Execution Contract)

## Read Order (mandatory)
1. context.md
2. agent-instructions.md (this file)
3. task-checklist.md

## Required Behavior For Every Run
1. Find the first incomplete task in task-checklist.md (first `- [ ] Txx ...` item).
2. Complete only that task efficiently and professionally.
3. Keep implementation pragmatic; avoid unnecessary comments.
4. Write unit tests and/or integration tests for the implemented task.
5. Run tests and ensure they pass before finishing.
6. If tests fail and cannot be fixed safely in this run, stop and report issues to the user with exact failures and proposed options.
7. Update task-checklist.md:
   - Mark completed task as `[x]` so it is no longer incomplete.
   - If blocked, leave as `[ ]` and append `BLOCKED: <reason>` directly under the task.
   - Add a line to the Completion Log.
8. Generate the ideal prompt for the next task (the next first incomplete item).
9. In the generated next prompt, instruct the next agent to read context.md, agent-instructions.md, and task-checklist.md before coding.

## Quality Standard
- Prefer small, verifiable increments.
- Do not change scope beyond the active task.
- Do not defer testing.
- Any operation that can affect cost or cloud resources must include safe defaults.

## Required Response Template
Use this structure in your final message each run:

1. Task completed: `Txx <title>`
2. What changed: short implementation summary
3. Tests added: list
4. Test results: pass/fail summary
5. Checklist update: task status + completion log line
6. Next prompt: ready-to-copy prompt for the next agent

## Next Prompt Template
Use this template to generate the next prompt:

"You are continuing the Frontend implementation. First read context.md, then agent-instructions.md, then task-checklist.md. Execute only the first incomplete task and do not work ahead. Implement it efficiently (no unnecessary comments), add unit/integration tests, run them, and ensure they pass. If tests fail, stop and report issues with options. Update task-checklist.md (mark completed task as [x], or add BLOCKED note if needed), append to Completion Log, and then generate the next prompt for the following task."
