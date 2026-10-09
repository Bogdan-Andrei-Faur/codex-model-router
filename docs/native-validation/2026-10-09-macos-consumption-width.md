# macOS consumption width — 2026-10-09

- Small local CSS change on main `c82e1ea`; inherited documentation changes retained.
- Consumption shares the 790px expanded width cap with Home, Agents, History and
  Settings, shrinking to the available viewport. Content-sized height is retained.
- Source-backed Mac monitor rebuilt/installed as `af7bc672a28ff37e`, product0.9.6,
  expected router `5aa7726ffeba863f`; bundled CSS and build stamp match source.
- Private installation backup retained outside Git; config bytes and semantic
  UI preferences preserved. Only the owned monitor relaunched; Desktop untouched.
- Readback: one monitor, one connection, loaded router `5aa7726ffeba863f`,
  mismatch=false, unknown=false. This supersedes the previous old-bridge readback;
  it does not prove natural event coverage or subsequent inference identity.
- Browser verification PASS: equal widths across all five screens at320/390/620/800px.
  Existing Consumption/Settings browser group PASS, including overflow/draft/action checks.
- Physical visual acceptance, natural observer states and existing unrelated
  native gates remain separate. No commit/push or CI success claim.
