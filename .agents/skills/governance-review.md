# Skill: Governance Review

## Goal
Provide a repeatable checklist for governance-only changes in MagicLamp.

## Checklist
1. Confirm scope is documentation/governance only.
2. Confirm one issue = one PR and no mixed workstreams.
3. Ensure PR includes all mandatory evidence sections.
4. Flag hard-gate domains when touched.
5. Verify no prohibited operations are requested:
   - merge by agent
   - deploy by agent
   - destructive shell commands
   - production DB modification
   - direct SpreadVerse V2 DB write
   - RED/AMBER/GREEN bypass
6. Confirm UAE residency impact is explicitly documented.

## Output standard
Return pass/fail per checklist item and list founder actions needed.
