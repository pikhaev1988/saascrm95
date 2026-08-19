# Stage 9 blocker log (pre-fix)

## BLOCKER-1: HTML technical metadata leak

- protocol: all (template-level)
- section: HTML / technical metadata (§13)
- stage: HTML render
- error: literal token `SYSTEM_ANALYTICS:` in user-facing HTML
- evidence: `apps/vpr/templates/vpr/protocol_overview.html` line with `SYSTEM_ANALYTICS: {{ report.system_analytics_notes|join:" " }}`
- severity: Critical
- recommended_fix: replace hardcoded enum prefix with user-facing label (same wording as DOCX)

## BLOCKER-2: technical tokens in management recommendations

- section: HTML/DOCX technical metadata (§13)
- stage: render management_recommendations.control_metric
- error: `completion_percent`, `journal_gap_ge_2`, `boundary_peak_flags`, `FIOKO` in user text
- evidence: `apps/vpr/fioko_2026/management.py` control_metric strings
- severity: Critical
- fix: user-facing Russian metric labels + sanitize management_recommendations dicts

## BLOCKER-3: DOCX heading leaked FIOKO_2026 token family

- section: DOCX §16
- error: heading `Управленческие решения (FIOKO 2026)`
- fix: `методология ФИОКО 2026`

## BLOCKER-5: DOCX deficit section leaked EvidenceStatus enum

- section: DOCX §9
- error: `evidence=EvidenceStatus.INFORMATIVE` via `overview_docx.py`
- severity: Critical
- fix: render `user_label(evidence_status.value)` as «статус доказательности»


