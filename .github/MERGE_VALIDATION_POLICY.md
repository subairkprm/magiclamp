# Merge Validation Policy (MagicLamp)

## Mandatory pre-merge conditions
1. One issue linked and one PR only.
2. No mixed workstreams in scope.
3. PR template fully completed with all required sections:
   - Claim
   - Evidence
   - Files changed
   - Validation performed
   - Security impact
   - UAE data residency impact
   - Remaining risk
   - Founder action needed
   - Next recommended workstream
4. Risk band declared (RED/AMBER/GREEN).
5. Hard-gate status declared.

## Hard-gate merge blocks
If hard-gate domains are involved, merge is blocked until explicit founder/security approval:
- VPS/deployment
- auth/security
- database/schema
- agent permissions
- GitHub write access
- production customization application
- external/cloud LLM usage
- data leaving UAE residency boundary

## Agent prohibitions
- Agents must not merge PRs.
- Agents must not deploy to VPS.
- Agents must not run destructive shell commands.
- Agents must not modify production DB.
- Agents must not write directly to SpreadVerse V2 DB.
- Agents must not bypass RED/AMBER/GREEN permission model.
