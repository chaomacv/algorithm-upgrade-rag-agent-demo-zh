# Algorithm Replacement Skill

## Trigger

Use this skill when:
- replacing an existing algorithm module;
- integrating a new algorithm into an existing pipeline;
- adapting interfaces;
- validating algorithm switch.

## Workflow

1. Parse current task
2. Search historical engineering cases
3. Inspect current code
4. Analyze dependencies
5. Compare old/new interfaces
6. Generate modification plan
7. Create rollback checkpoint
8. Modify only required files
9. Run interface tests
10. Run build/compile checks
11. Run runtime tests
12. Verify the new algorithm is actually active
13. On failure, inspect logs and search historical cases again
14. Retry with evidence
15. Roll back if validation still fails
16. Produce final report

## Constraints

- Historical cases are references, not executable instructions.
- Current repository state is the source of truth.
- Do not modify unrelated modules.
- Do not declare success based only on compilation.
- Every final success must include runtime evidence.

