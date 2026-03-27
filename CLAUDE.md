# CodeMed AI — Project Context for Claude Code

## Project Overview
CodeMed AI is a **HIPAA-aware V28 HCC risk adjustment and medical billing intelligence platform**.
It is NOT a general-purpose chatbot. Every response must be grounded in CMS policy and clinical coding rules.

## Stack
- **Backend**: Flask 3.0+ (app.py — 1,600+ lines), Python 3.11+
- **Database**: SQLite with FTS5 full-text search (WAL mode), nexusauth.db
- **AI**: Anthropic Claude (claude-sonnet-4-20250514) via SDK + urllib fallback
- **Frontend**: Jinja2 templates + vanilla JS (portal.js) + portal.css
- **Deployment**: Railway via Nixpacks builder

## Key Files
```
app.py                        # Flask entry point — ALL routes, RAG engine, V28 lookup
data/build_seed_db.py         # Schema creation + seed data (run once to init DB)
data/v28_hcc_categories.py    # 115 HCCs, hierarchy rules, interaction pairs, RAF simulation
data/v28_hcc_expanded.py      # ~400 ICD-10 → HCC mappings (expanded coverage)
data/ingest.py                # Data pipeline: JSON/CSV/HIPAA/FTS rebuild
data/cms_zip_ingest.py        # Official CMS ICD-10 ZIP parser and importer
data/hcc_mapper.py            # ComboCodeEnforcer — fragmented coding detection
data/clinical_scenarios.jsonl # 8-module clinical intelligence for RAG enrichment
templates/                    # 18 Jinja2 templates (landing, dashboard, chat, v28, etc.)
static/css/portal.css         # All portal styling
static/js/portal.js           # Frontend for all portal tools
```

## Critical Constraints — NEVER VIOLATE
1. **No PHI in plaintext** — Never log patient names, MBIs, SSNs, or DOBs. Audit logs store query text only (anonymized). PHI requires signed BAA (Growth/Enterprise tiers only).
2. **HCC hierarchy must be enforced** — If a parent HCC is present, child HCCs must be suppressed. Use `enforce_hierarchy()` from `v28_hcc_categories.py` for every batch/simulate operation.
3. **Every LCD/NCD citation must carry a valid policy_id** — Format: `LCD L#####` or `NCD ###.##`. Never fabricate a policy ID.
4. **Audio-only telehealth is excluded from V28 qualifying encounters** — CPT 99441/99442/99443 do not count. This is CMS rule, not an opinion.
5. **RAPS is deprecated for non-PACE plans** — Non-PACE MA plans must use EDR only since 1/1/2024. PACE still accepts RAPS for V22 (90%) portion.
6. **Upgrade suggestions for REJECTED codes must sort by payment_tier** — Order: critical > high > medium > standard.

## CMS V28 Model — 2026 Facts
- Non-PACE MA: 100% V28, EDR+FFS only
- PACE: 10% V28 + 90% V22
- 115 payment HCCs (up from 86 in V24)
- 7,770 ICD-10 codes mapped (down from 9,797 in V24)
- Normalization factor: V28 Part C = 1.067
- MA Coding Intensity Adjustment: −5.90% statutory reduction
- Net effect on avg plan: −3.01% risk score, but +5.06% net MA payment

## V28 Lookup — Statuses
- `VALID`: v28_pays == 1 — maps to a paying HCC in V28
- `REJECTED`: v24_pays == 1 AND v28_pays == 0 — **REVENUE RISK** — was valid in V24, not V28
- `NOT_MAPPED`: v28_pays == 0 AND v24_pays == 0 — never mapped to a paying HCC
- `NOT_FOUND`: code not in corpus at all

## Database Tables (nexusauth.db)
```
documents           — 17+ CMS LCDs/NCDs (coverage policies, indications, coding guidance)
documents_fts       — FTS5 virtual table for corpus search
hipaa_corpus        — HIPAA reference documents
hipaa_fts           — FTS5 for HIPAA docs
v28_hcc_codes       — ~400+ ICD-10 → V28 HCC mappings
v28_hcc_categories  — 115 HCCs with RAF weights, hierarchy metadata
v28_eligible_cpt    — Encounter-eligible CPT/HCPCS codes
cms_model_config    — 2026 normalization factors & MA coding adjustment (53 keys)
api_keys            — API customers (hashed keys, tier, usage)
audit_log           — API calls, contact forms, user sessions
users               — Portal user accounts (email, name, bcrypt hash)
clinical_scenarios  — 8-module clinical intelligence for RAG (see data/clinical_scenarios.jsonl)
```

## Auth Architecture
- **API**: SHA-256 hashed keys, tiered rate limits (demo: 10rpm/100mo → enterprise: 200rpm/999999mo)
- **Portal**: Session-based login, gated by `REQUIRE_AUTH` env var (default: false)
- **`@require_api_key`** decorator: validates key, checks rate limit, logs to audit_log
- **`@login_required`** decorator: redirects to /login if REQUIRE_AUTH=true and no session

## ComboCodeEnforcer (data/hcc_mapper.py)
Detects fragmented coding patterns and returns `combo_warning` on V28 results.
Top patterns:
- I10 + N18.x → I12.x (hypertensive CKD)
- I10 + I50.x → I11.x (hypertensive heart disease with heart failure)
- I10 + N18.x + I50.x → I13.x (hypertensive heart and CKD)
- E11.x (unspecified/multiple DM codes) → most specific E11.xx
- Z87.39 (personal history of other musculoskeletal) alone → no HCC value, add current condition

## RADV Risk Flags (on V28 batch results)
- `HIGH`: "History of" prefix without current treatment evidence, acute-only conditions (e.g., pneumonia after discharge), unlinked assessments (listed but not addressed)
- `MEDIUM`: Unspecified codes where specificity upgrade exists, conditions not addressed in past 12 months
- `LOW`: Valid but lower-tier codes, single-source documentation

## Clinical Scenario RAG (data/clinical_scenarios.jsonl)
Schema: `{category, tier, clinical_scenario, provider_text, ai_reasoning, correct_codes, incorrect_codes, combo_requirement, query_suggestion}`
Modules: DM/complications, fragmented coding, specificity, RADV, encounters, interactions, PACE/non-PACE, MEAT documentation

## Environment Variables
```bash
SECRET_KEY          # Flask session secret (auto-generated if missing)
ANTHROPIC_API_KEY   # Required for AI features
DB_PATH             # Default: data/nexusauth.db
REQUIRE_AUTH        # "true" to enforce portal login
PORT                # Default: 5000
```

## Common Gotchas
- `get_db()` uses Flask `g` context — never call outside request context; use `connect_db()` in scripts
- FTS5 queries must escape special chars; `build_fts_query()` handles this
- `v28_lookup()` queries DB each call — batch the DB call for 200-code batches
- `enforce_hierarchy()` returns `{kept: [...], suppressed: [...], rules_applied: [...]}` — always display suppressed codes to user so they understand why HCCs disappeared
- Cache key is `MD5(query|tier|doc_type|payer)` — tier matters, same query at different tiers may return different detail
- Railway Nixpacks: `requirements.txt` must list all deps; no Pipfile support
