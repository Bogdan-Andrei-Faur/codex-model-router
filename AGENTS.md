# Codex Model Router workspace

Canonical project: `codex-model-router`.
Canonical repository: `https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`.

## Repository-owned continuity

- Start with `docs/HANDOFF.md`. For real-machine acceptance, follow
  `docs/NATIVE-VALIDATION.md` and `docs/native-validation/STATUS.md`.
- These files must be sufficient for a fresh agent with only this checkout.
  Do not require Atlas, Knowledge, personal memories or previous chat access.
- Do not use Atlas or contact agents on other machines. Each machine's agent
  works independently; coordinate through the repository or the owner.
- Preserve unrelated local work. Do not restart Desktop, suspend the computer,
  replace an active installation or interrupt owner tasks merely to validate it.
  Coordinate disruptive checks with the owner first.
- Keep source revision, installed artifact, loaded bridge and human acceptance
  distinct. CI or another machine's results do not close a local acceptance gate.
- Record safe native results using `docs/native-validation/REPORT-TEMPLATE.md`.
  Never commit private state, raw logs, prompts, conversation identifiers or keys.
- Write agent instruction files in English; respond to the owner in Spanish.
