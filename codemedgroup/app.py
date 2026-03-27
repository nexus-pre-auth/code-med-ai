"""
CodeMed Group Platform  v2.0
Layer 2: Regulatory Intelligence API
Layer 1: NexusAuth RCM Portal
Layer 0: Public Landing + Auth
"""
import os, re, json, sqlite3, hashlib, secrets, time, logging
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, render_template, g, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("codemedgroup")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

BASE_DIR = Path(__file__).parent

# Ensure data/ directory is on sys.path for module imports
import sys as _sys
_data_dir = str(BASE_DIR / "data")
if _data_dir not in _sys.path:
    _sys.path.insert(0, _data_dir)
DB_PATH  = os.environ.get("DB_PATH", str(BASE_DIR / "data" / "nexusauth.db"))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Database ──────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

# ── Rate limit store (use Redis in prod) ─────────────────────
_rate_store = {}

TIERS = {
    "demo":       {"rpm": 10,  "monthly": 100,    "price": 0},
    "starter":    {"rpm": 20,  "monthly": 5000,   "price": 500},
    "growth":     {"rpm": 60,  "monthly": 50000,  "price": 2500},
    "enterprise": {"rpm": 200, "monthly": 999999, "price": 10000},
}

# ── API Key middleware ────────────────────────────────────────
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = (request.headers.get("X-API-Key") or
               request.headers.get("Authorization","").replace("Bearer ","") or
               request.args.get("api_key",""))
        if not key:
            return jsonify({"error":"API key required","docs":"https://codemedgroup.com/docs"}), 401
        kh = hashlib.sha256(key.encode()).hexdigest()
        db = get_db()
        row = db.execute("SELECT * FROM api_keys WHERE key_hash=? AND active=1",(kh,)).fetchone()
        if not row:
            return jsonify({"error":"Invalid or inactive API key"}), 401
        tier = row["tier"]
        lim  = TIERS.get(tier, TIERS["demo"])
        bucket = f"{row['id']}:{int(time.time()//60)}"
        _rate_store[bucket] = _rate_store.get(bucket, 0) + 1
        if _rate_store[bucket] > lim["rpm"]:
            return jsonify({"error":"Rate limit exceeded","rpm_limit":lim["rpm"],"upgrade":"https://codemedgroup.com/docs"}), 429
        g.api_id       = row["id"]
        g.api_tier     = tier
        g.api_customer = row["customer_name"]
        db.execute("UPDATE api_keys SET last_used=datetime('now'), monthly_usage=monthly_usage+1 WHERE id=?",(row["id"],))
        db.execute("INSERT INTO audit_log(action,resource_type,user_session,ip_address,query_text) VALUES(?,?,?,?,?)",
                   ("api_request", request.endpoint, str(row["id"]), request.remote_addr, request.path))
        db.commit()
        return f(*args, **kwargs)
    return decorated

# ── Anthropic SDK client ──────────────────────────────────────
_claude_client = None

def get_claude_client():
    global _claude_client
    if _claude_client is None:
        if not ANTHROPIC_API_KEY:
            return None
        try:
            import anthropic as _ant
            _claude_client = _ant.Anthropic(api_key=ANTHROPIC_API_KEY)
        except ImportError:
            logger.warning("anthropic SDK not installed, falling back to urllib")
            return None
    return _claude_client

# ── Claude system prompt ──────────────────────────────────────
RAG_SYSTEM = """You are CodeMed AI — a specialized medical billing, prior authorization, and HCC coding intelligence system built by CodeMed Group.

CORPUS: 1,307+ CMS LCD/NCD policies, payer clinical policies, HIPAA compliance documents, V28 HCC mappings, CPT surgery coding guidelines, and CMS strategic framework documents (2024–2026).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CY2026 RISK ADJUSTMENT & PAYMENT CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODEL & PHASE-IN:
- NON-PACE MA PLANS: 100% CMS-HCC V28 (2024 model) as of CY2026. Encounter data (EDR) + FFS only. RAPS no longer accepted for ANY new diagnoses effective 1/1/2024. If a non-PACE plan submits via RAPS only, the diagnosis will NOT count for risk adjustment.
  MOR/MMR record types: [2024 CMS-HCC V28 M] [2026 RxHCC V08 6] [2023 ESRD V24 L]
- PACE PLANS: 10% V28 + 90% V22 (2017 model). RAPS still accepted for the V22 (90%) portion only. EDR required for V28 (10%) portion.
  MOR/MMR adds: [2017 CMS-HCC V22 K] [2019 ESRD V21 B] [2026 RxHCC V08 6/7]
- V28 EXPANSION: 115 payment HCCs (up from 86 in V24); 7,770 ICD-10 codes mapped (down from 9,797 — 2,290 removed for clinical accuracy)
- HIERARCHY ENFORCEMENT: V28 automatically suppresses child HCCs when a parent is present. Submitting both is a RADV audit risk. Always code and document the most specific condition.
- MEAT EVIDENCE REQUIRED: Each coded HCC must be supported by Monitor/Evaluate/Assess/Treat evidence in the provider's note for the payment year.

NORMALIZATION & ADJUSTMENTS (2026):
- V28 Part C norm factor: 1.067 | PACE V22 Part C: 1.187 | ESRD dialysis V24: 1.062
- MA Coding Intensity Adjustment: 5.90% statutory reduction (multiply RAF × 0.941 before payment)
- Frailty (FIDE-SNPs): Full 2024 factors — no phase-in reduction
- Net impact: −3.01% avg risk score; +5.06% net MA payment; 9.04% effective growth rate
- Growth rate increased from 5.93% Advance Notice due to inclusion of Q4 2024 FFS expenditure data
- Medical education costs: 100% technical adjustment applied in 2026 (3-year phase-in complete)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENCOUNTER FILTERING — CRITICAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUDIO-ONLY TELEHEALTH — EXPRESSLY EXCLUDED:
- Audio-only phone calls CANNOT support V28 HCC diagnoses for risk adjustment. PERIOD.
- If a patient has a phone-only visit and the provider documents a diagnosis, that encounter DOES NOT qualify for risk adjustment — even if the diagnosis is otherwise valid.
- Telehealth MUST be synchronous audio + video (e.g., with CPT modifier 95 or place of service 02/10)
- Common question: "Is audio-only telehealth valid for V28 risk adjustment?" → Answer: NO. Audio-only is explicitly excluded under CY2026 CMS encounter eligibility rules.

QUALIFYING ENCOUNTER TYPES:
- Physician office E&M: 99202–99215 (new/established patient office visits)
- Inpatient hospital: 99221–99223 (initial), 99231–99233 (subsequent), 99238–99239 (discharge)
- Outpatient hospital E&M: 99241–99245 (consultations), 99281–99285 (ED)
- Annual Wellness Visits: G0438 (initial AWV), G0439 (subsequent AWV)
- Welcome to Medicare: G0402
- FQHC/RHC: T1015 (per-visit), G0466 (FQHC new patient), G0467 (FQHC established)
- Video-enabled telehealth: Same CPT codes as above + modifier 95 (synchronous telecommunications)
- Behavioral health: 90837 (psychotherapy 60 min), 90832 (30 min), 90834 (45 min), 90847 (family therapy)

EXCLUDED ENCOUNTER TYPES (diagnosis does NOT count for risk adjustment):
- Audio-only telehealth (phone calls): EXCLUDED even with valid CPT
- Labs/pathology alone (80000–89999 series): EXCLUDED
- Radiology/imaging alone (70000–79999): EXCLUDED
- Home health without face-to-face E&M CPT: EXCLUDED
- SNF visits without face-to-face physician E&M CPT: EXCLUDED
- 99211 (nurse-only visit without physician involvement): EXCLUDED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CPT CLINICAL CODING GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CARDIOVASCULAR SYSTEM (CPT 33001–39599):
Pacemakers & Defibrillators:
- 33214: Upgrading single-chamber to dual-chamber system (includes old generator removal, lead testing, new lead + generator)
- Transvenous approach (through veins): standard implantation route
- Epicardial approach (through chest via sternotomy or scope): coded separately
- Always distinguish transvenous vs epicardial in documentation

Coronary Artery Bypass Grafting (CABG):
- Both arteries AND veins used → use combined arterial-venous series (33517–33523); NEVER use veins-only series when arterial grafts are present
- Saphenous vein harvesting: BUNDLED — do not code separately
- Upper extremity harvesting (e.g., radial artery): code separately with CPT 35600
- Conduit type (arterial vs venous) must be explicitly documented by surgeon

Vascular Selective Catheterization (Appendix L rules):
- Non-selective: catheter remains in the aorta → code aortic position only
- Selective: catheter advances beyond the aorta into a named branch vessel → code by selectivity order
- Code for the HIGHEST ORDER reached in each vascular family (1st, 2nd, 3rd order, beyond 3rd)
- Each vascular family is coded independently; do not combine orders across families

DIGESTIVE SYSTEM:
Endoscopy Anatomy Rule:
- Code based on ANATOMY VIEWED, not the instrument used
- Colonoscopy (CPT 45378+): scope must reach the CECUM — if cecum not reached, code as sigmoidoscopy
- Document anatomic landmarks (cecum, hepatic/splenic flexure, terminal ileum if examined)

Adhesion Lysis:
- 44005: Lysis of extensive intestinal adhesions
- Add Modifier 22 (increased procedural services) when work is time-consuming and tedious — document estimated additional time and complexity in operative note

Small Intestine Resections:
- 44120: Single resection with anastomosis
- 44121: Add-on code for EACH additional resection — use add-on, NOT multiple units of 44120

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART D & MIPS COMPLIANCE CONTEXT (2026)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Part D Redesign: CY2026 Program Instructions finalized; drug benefit redesign continues per IRA implementation
- MIPS (CMS-1832-F): Requires HIPAA Security Rule attestations — formal risk analysis AND risk management implementation must be documented for full credit
- HIPAA Security attestation covers: risk analysis completion, risk management plan, workforce training documentation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CMS STRATEGIC FRAMEWORK (2026)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CMS covers 150 million Americans across Medicare, Medicaid/CHIP, and Marketplace. Six strategic pillars:
1. Advance Equity | 2. Expand Access | 3. Engage Partners | 4. Drive Innovation | 5. Protect Programs | 6. Foster Excellence
Cross-cutting initiatives: Behavioral Health integration, Drug Affordability (generics/biosimilars), Maternity Care, Integrating the 3Ms (Medicare + Medicaid/CHIP + Marketplace for continuity of care)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Cite specific policy IDs: "Per LCD L38226..." or "Per NCD 280.14..." — never fabricate IDs
2. Reference exact ICD-10-CM, CPT, and HCPCS codes — never invent codes
3. Flag V28 HCC revenue impact for any diagnosis codes: VALID / REJECTED / NOT_MAPPED
4. For prior auth: enumerate required documentation as a numbered checklist
5. For denial/appeal: identify denial reason code (CO, PR, OA, PI), cite LCD/NCD, give appeal pathway
6. For coverage: give YES or NO determination first, then nuances
7. For CPT surgery coding: apply the anatomy-based, selectivity, and bundling rules above
8. When V24-only codes appear: proactively suggest V28-valid upgrade codes with HCC numbers
9. Bold critical warnings: **DENIAL RISK**, **V28 REJECTED**, **RADV RISK**, **BUNDLED — DO NOT CODE**
10. For MIPS queries: flag HIPAA Security attestation requirements specifically

FORMAT:
- Lead with a direct answer (1-2 sentences)
- Use bullet points for code lists
- Use numbered steps for processes
- Keep under 600 words unless clinical coding detail requires more

CONSTRAINTS:
- Never fabricate LCD/NCD IDs or policy content not in context
- Billing and coding guidance only — not medical advice
- If context is insufficient, specify exactly what additional documentation would resolve the question"""

def call_claude(user_prompt: str, history: list = None) -> str:
    client = get_claude_client()
    messages = []
    if history:
        for msg in history[-6:]:
            if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": str(msg["content"])})
    messages.append({"role": "user", "content": user_prompt})

    if client is not None:
        try:
            import anthropic as _ant
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=RAG_SYSTEM,
                messages=messages,
            )
            return response.content[0].text
        except _ant.AuthenticationError:
            logger.error("Claude authentication failed — check ANTHROPIC_API_KEY")
            return "Authentication error. Verify your Anthropic API key."
        except _ant.RateLimitError:
            logger.warning("Claude rate limit hit")
            return "Rate limit reached. Please retry in a moment."
        except _ant.APIError as e:
            logger.error(f"Claude API error: {e}")
            return "API error. Please retry."
        except Exception as e:
            logger.error(f"Claude unexpected error: {e}")
            return f"Unexpected error: {str(e)}"

    # urllib fallback
    if not ANTHROPIC_API_KEY:
        return "Claude API key not configured. Add ANTHROPIC_API_KEY to your .env file."
    import urllib.request, urllib.error
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
        "system": RAG_SYSTEM,
        "messages": messages
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY,
                 "anthropic-version": "2023-06-01"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["content"][0]["text"]
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        logger.error(f"Claude HTTP {e.code}: {err[:300]}")
        return f"API error {e.code}. Check your API key."
    except Exception as e:
        logger.error(f"Claude error: {e}")
        return f"Connection error: {str(e)}"

# ── Response cache ────────────────────────────────────────────
_query_cache: dict = {}
CACHE_TTL_SECONDS = 300

def cache_get(key: str):
    entry = _query_cache.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    if entry:
        del _query_cache[key]
    return None

def cache_set(key: str, value: dict, ttl: int = CACHE_TTL_SECONDS) -> None:
    if len(_query_cache) > 500:
        oldest = sorted(_query_cache.items(), key=lambda x: x[1][1])[:100]
        for k, _ in oldest:
            del _query_cache[k]
    _query_cache[key] = (value, time.time() + ttl)

def make_cache_key(query: str, tier: str = "", doc_type: str = "", payer: str = "") -> str:
    raw = f"{query.lower().strip()}|{tier}|{doc_type or ''}|{payer or ''}"
    return hashlib.md5(raw.encode()).hexdigest()

# ── Medical code extraction ───────────────────────────────────
ICD10_PATTERN = re.compile(r'\b[A-Z]\d{2}(?:\.\d{1,4})?\b', re.IGNORECASE)
CPT_PATTERN   = re.compile(r'\b\d{5}\b')
HCPCS_PATTERN = re.compile(r'\b[A-Z]\d{4}\b', re.IGNORECASE)

def extract_codes(text: str) -> dict:
    icd = list({c.upper() for c in ICD10_PATTERN.findall(text)})
    cpt = list({c for c in CPT_PATTERN.findall(text)})
    hcp = list({c.upper() for c in HCPCS_PATTERN.findall(text)
                if not ICD10_PATTERN.match(c)})
    return {"icd10": icd, "cpt": cpt, "hcpcs": hcp}

STOPWORDS = {"the","and","for","with","not","are","was","has","per","its",
             "that","this","from","have","been","will","they","their","into",
             "when","what","does","how","can","get","use","all","any","its"}

def build_fts_query(query: str) -> str:
    """Build FTS5 BM25 query from natural language.
    Requires first 3 meaningful tokens (AND) for precision; OR-expands the rest for recall.
    Reduced from 6 to 3 required AND tokens — prevents over-restrictive misses on long queries.
    """
    cleaned = re.sub(r'\b[A-Z]\d{2,4}(?:\.\d{1,4})?\b', ' ', query, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d{5}\b', ' ', cleaned)
    tokens = list(dict.fromkeys(  # deduplicate, preserve order
        t.strip('.,;:()[]"\'').lower() for t in cleaned.split()
        if len(t.strip('.,;:()[]"\'')) >= 3
        and t.lower().strip('.,;:()[]"\'') not in STOPWORDS
    ))
    if not tokens:
        return None
    if len(tokens) <= 2:
        return ' AND '.join(tokens)
    # Require first 3 terms; OR-expand remaining for recall (BM25 ranks by relevance)
    required = ' AND '.join(tokens[:3])
    optional = tokens[3:7]
    if optional:
        return f"({required}) OR {' OR '.join(optional)}"
    return required

# ── Corpus search (3-tier: code-aware → FTS5 → LIKE) ─────────
def search_corpus(query: str, limit: int = 5, doc_type: str = None, payer: str = None) -> list:
    db = get_db()
    results = []
    code_hit_ids = set()

    # Tier 1: Code-aware search via json_each on ICD/CPT/HCPCS arrays
    codes = extract_codes(query)
    if codes["icd10"] or codes["cpt"] or codes["hcpcs"]:
        code_clauses, code_params = [], []
        if codes["icd10"]:
            ph = ','.join('?' * len(codes["icd10"]))
            code_clauses.append(
                f"SELECT DISTINCT d.id FROM documents d, json_each(d.icd10_codes) j "
                f"WHERE j.value IN ({ph}) AND d.status='active'"
            )
            code_params.extend(codes["icd10"])
        if codes["cpt"]:
            ph = ','.join('?' * len(codes["cpt"]))
            code_clauses.append(
                f"SELECT DISTINCT d.id FROM documents d, json_each(d.cpt_codes) j "
                f"WHERE j.value IN ({ph}) AND d.status='active'"
            )
            code_params.extend(codes["cpt"])
        if codes["hcpcs"]:
            ph = ','.join('?' * len(codes["hcpcs"]))
            code_clauses.append(
                f"SELECT DISTINCT d.id FROM documents d, json_each(d.hcpcs_codes) j "
                f"WHERE j.value IN ({ph}) AND d.status='active'"
            )
            code_params.extend(codes["hcpcs"])
        if code_clauses:
            filter_parts, filter_params = ["1=1"], []
            if doc_type: filter_parts.append("d.document_type=?"); filter_params.append(doc_type)
            if payer:    filter_parts.append("d.payer_code=?");    filter_params.append(payer.upper())
            union_sql = " UNION ".join(code_clauses)
            sql = (f"SELECT d.* FROM documents d WHERE d.id IN ({union_sql}) "
                   f"AND {' AND '.join(filter_parts)} "
                   f"ORDER BY d.confidence_score DESC LIMIT {limit}")
            try:
                rows = db.execute(sql, code_params + filter_params).fetchall()
                results = [dict(r) for r in rows]
                code_hit_ids = {r["id"] for r in results}
            except Exception as e:
                logger.warning(f"Code-aware search error: {e}")

    # Tier 2: FTS5 BM25 ranked search
    fts_query = build_fts_query(query)
    if fts_query and len(results) < limit:
        remaining = limit - len(results)
        filter_parts, filter_params = ["d.status='active'"], []
        if doc_type: filter_parts.append("d.document_type=?"); filter_params.append(doc_type)
        if payer:    filter_parts.append("d.payer_code=?");    filter_params.append(payer.upper())
        exclude = ""
        if code_hit_ids:
            ph = ','.join('?' * len(code_hit_ids))
            exclude = f"AND d.id NOT IN ({ph})"
            filter_params.extend(list(code_hit_ids))
        filter_clause = " AND ".join(filter_parts)
        fts_sql = (f"SELECT d.* FROM documents d "
                   f"JOIN documents_fts f ON d.id = f.rowid "
                   f"WHERE {filter_clause} AND documents_fts MATCH ? {exclude} "
                   f"ORDER BY f.rank LIMIT {remaining}")
        try:
            rows = db.execute(fts_sql, filter_params + [fts_query]).fetchall()
            results.extend([dict(r) for r in rows])
        except Exception as e:
            logger.warning(f"FTS search error (query={fts_query!r}): {e}")

    # Tier 3: LIKE fallback
    if not results:
        params = [f"%{query}%"] * 4
        sql = ("SELECT * FROM documents d WHERE d.status='active' AND "
               "(d.title LIKE ? OR d.content_text LIKE ? OR d.indication_text LIKE ? OR d.coding_text LIKE ?)")
        if doc_type: sql += " AND d.document_type=?"; params.append(doc_type)
        if payer:    sql += " AND d.payer_code=?";    params.append(payer.upper())
        sql += f" ORDER BY d.confidence_score DESC LIMIT {limit}"
        try:
            results = [dict(r) for r in db.execute(sql, params).fetchall()]
        except Exception as e:
            logger.error(f"Fallback search error: {e}")

    return results

# ── HIPAA search ──────────────────────────────────────────────
HIPAA_TRIGGER_TERMS = {"hipaa","phi","breach","baa","business associate","privacy rule",
                       "security rule","minimum necessary","authorization","covered entity",
                       "notice of privacy","de-identification","right of access"}

def is_hipaa_query(q: str) -> bool:
    q_lower = q.lower()
    return any(term in q_lower for term in HIPAA_TRIGGER_TERMS)

def search_hipaa(query: str, limit: int = 3) -> list:
    db = get_db()
    fts_q = build_fts_query(query)
    if fts_q:
        try:
            sql = ("SELECT h.* FROM hipaa_corpus h "
                   "JOIN hipaa_fts f ON h.id = f.rowid "
                   "WHERE hipaa_fts MATCH ? ORDER BY f.rank LIMIT ?")
            rows = db.execute(sql, [fts_q, limit]).fetchall()
            if rows:
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"HIPAA FTS error: {e}")
    # LIKE fallback
    try:
        rows = db.execute(
            "SELECT * FROM hipaa_corpus WHERE content_text LIKE ? OR title LIKE ? LIMIT ?",
            [f"%{query}%", f"%{query}%", limit]
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []

# ── RAG context builder ───────────────────────────────────────
def build_rag_context(docs: list, max_docs: int = 5, max_chars: int = 1200) -> str:
    snippets = []
    for d in docs[:max_docs]:
        label = f"[{d['source_id']}] {d['title']} (Type: {d['document_type']}, Payer: {d['payer_code']})"
        content = (d.get('content_text') or '')[:max_chars]
        indication = (d.get('indication_text') or '')[:300]
        coding = (d.get('coding_text') or '')[:200]
        snippet = f"{label}\n{content}"
        if indication:
            snippet += f"\nIndications: {indication}"
        if coding:
            snippet += f"\nCoding: {coding}"
        snippets.append(snippet)
    return "\n\n---\n\n".join(snippets)

# ── V28 engine ────────────────────────────────────────────────
def v28_lookup(code: str) -> dict:
    db = get_db()
    r = db.execute("SELECT * FROM v28_hcc_codes WHERE icd10_code=?",(code.upper().strip(),)).fetchone()
    if not r:
        return {"code":code.upper(),"status":"NOT_FOUND","v28_pays":False,"message":f"{code} not in V28 corpus"}
    r = dict(r)
    if r["v28_pays"]:   status = "VALID"
    elif r["v24_pays"]: status = "REJECTED"
    else:               status = "NOT_MAPPED"
    upgrades = []
    if status == "REJECTED":
        prefix = code[:3]
        rows = db.execute("""
            SELECT icd10_code, description, v28_hcc, payment_tier, hcc_label
            FROM v28_hcc_codes WHERE icd10_code LIKE ? AND v28_pays=1
            ORDER BY CASE payment_tier WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END
            LIMIT 5
        """,(f"{prefix}%",)).fetchall()
        upgrades = [dict(x) for x in rows]
    return {
        "code": r["icd10_code"], "description": r["description"],
        "status": status, "v28_hcc": r["v28_hcc"], "v24_hcc": r["v24_hcc"],
        "v28_pays": bool(r["v28_pays"]), "payment_tier": r["payment_tier"],
        "hcc_label": r["hcc_label"], "upgrade_suggestions": upgrades,
        "v28_change_note": r.get("v28_change_note"), "clinical_rationale": r.get("clinical_rationale"),
    }

def build_v28_chat_context(icd_codes: list, max_codes: int = 5) -> str:
    """Rich V28 injection for AI chat — includes upgrade paths, change notes, tier.
    Makes the AI sound like a domain expert when ICD codes are mentioned.
    """
    if not icd_codes:
        return ""
    lines = []
    for code in icd_codes[:max_codes]:
        r = v28_lookup(code)
        status   = r["status"]
        hcc      = r.get("v28_hcc") or "N/A"
        v24_hcc  = r.get("v24_hcc") or "N/A"
        tier     = r.get("payment_tier", "standard")
        desc     = (r.get("description") or "")[:55]

        if status == "VALID":
            line = f"  {code} ({desc}): ✓ VALID → V28 HCC {hcc} | tier={tier}"
        elif status == "REJECTED":
            line = f"  {code} ({desc}): ✗ V28 REJECTED (was V24 HCC {v24_hcc}) — **REVENUE RISK**"
            upgrades = r.get("upgrade_suggestions", [])
            if upgrades:
                top = upgrades[0]
                up_desc = (top.get("description") or "")[:45]
                line += f"\n    → Upgrade path: {top['icd10_code']} ({up_desc}) → HCC {top['v28_hcc']} [{top.get('payment_tier','std')}]"
        elif status == "NOT_MAPPED":
            line = f"  {code} ({desc}): NOT MAPPED to any HCC in V28"
        else:
            line = f"  {code}: NOT FOUND in V28 corpus"

        note = r.get("v28_change_note")
        if note:
            line += f"\n    CMS note: {note[:110]}"
        lines.append(line)

    return "\nV28 HCC Impact for ICD-10 codes in query:\n" + "\n".join(lines) + "\n"

def build_appeal_v28_context(icd_codes: list) -> str:
    if not icd_codes:
        return ""
    lines = []
    for code in icd_codes[:5]:
        r = v28_lookup(code)
        status = r["status"]
        hcc = r.get("v28_hcc") or "N/A"
        tier = r.get("payment_tier", "standard")
        lines.append(f"  {code}: {status} (V28 HCC {hcc}, tier={tier})")
        if status == "REJECTED" and r.get("upgrade_suggestions"):
            top = r["upgrade_suggestions"][0]
            lines.append(f"    → Upgrade to {top['icd10_code']}: {top['description']} (HCC {top['v28_hcc']})")
    return "V28 HCC Status:\n" + "\n".join(lines)

# ════════════════════════════════════════════════════════════════
# LAYER 2: PUBLIC API
# ════════════════════════════════════════════════════════════════

@app.route("/api/v1/status")
def api_status():
    db = get_db()
    d = db.execute("SELECT COUNT(*) c, SUM(CASE WHEN document_type='lcd' THEN 1 ELSE 0 END) lcd, SUM(CASE WHEN document_type='ncd' THEN 1 ELSE 0 END) ncd FROM documents WHERE status='active'").fetchone()
    v = db.execute("SELECT COUNT(*) c, SUM(v28_pays) valid, SUM(CASE WHEN v24_pays=1 AND v28_pays=0 THEN 1 ELSE 0 END) rejected FROM v28_hcc_codes").fetchone()
    h = db.execute("SELECT COUNT(*) c FROM hipaa_corpus").fetchone()
    cat_row = db.execute("SELECT COUNT(*) c FROM v28_hcc_categories").fetchone()
    return jsonify({
        "status": "operational",
        "version": "1.2.0",
        "corpus": {"total": d["c"], "lcd": d["lcd"], "ncd": d["ncd"], "hipaa": h["c"]},
        "v28": {
            "total": v["c"],
            "valid": v["valid"],
            "rejected": v["rejected"],
            "hcc_categories": cat_row["c"],
            "phase_in": "100% CY2026 (non-PACE MA)",
            "normalization_factor": 1.067,
            "ma_coding_adjustment": "5.90%",
        },
        "model": "claude-sonnet-4-20250514",
        "hipaa_compliant": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

@app.route("/api/v1/query", methods=["POST"])
@require_api_key
def api_query():
    data = request.get_json() or {}
    q = data.get("query","").strip()
    if not q: return jsonify({"error":"query required"}), 400

    ck = make_cache_key(q, g.api_tier, data.get("type"), data.get("payer"))
    cached = cache_get(ck)
    if cached:
        return jsonify({**cached, "cached": True})

    t0 = time.time()
    docs = search_corpus(q, limit=5, doc_type=data.get("type"), payer=data.get("payer"))
    ctx  = build_rag_context(docs)

    # Auto-inject rich V28 context for any ICD-10 codes in the query
    codes   = extract_codes(q)
    v28_ctx = build_v28_chat_context(codes["icd10"])

    # Auto-inject HIPAA context if relevant
    hipaa_ctx = ""
    if is_hipaa_query(q):
        hipaa_docs = search_hipaa(q, limit=2)
        if hipaa_docs:
            hipaa_ctx = "\n\nHIPAA Context:\n" + "\n---\n".join(
                [f"[{h['source_id']}] {h['title']}\n{(h.get('summary_text') or h.get('content_text',''))[:600]}"
                 for h in hipaa_docs]
            )

    prompt = f"Corpus context:\n{ctx}{v28_ctx}{hipaa_ctx}\n\nQuestion: {q}"
    ans = call_claude(prompt, data.get("history", []))

    result = {
        "answer": ans,
        "sources": [{"id": d["source_id"], "title": d["title"], "type": d["document_type"]} for d in docs[:5]],
        "response_ms": int((time.time()-t0)*1000),
        "tier": g.api_tier,
        "model": "claude-sonnet-4-20250514"
    }
    cache_set(ck, result)
    return jsonify(result)

@app.route("/api/v1/v28/lookup")
@require_api_key
def api_v28_lookup():
    code = request.args.get("code","").strip()
    if not code: return jsonify({"error":"code required"}), 400
    return jsonify(v28_lookup(code))

@app.route("/api/v1/v28/batch", methods=["POST"])
@require_api_key
def api_v28_batch():
    data  = request.get_json() or {}
    codes = data.get("codes",[])
    if not codes or len(codes) > 200: return jsonify({"error":"Provide 1–200 codes"}), 400
    results  = [v28_lookup(c) for c in codes]
    valid    = [r for r in results if r["status"]=="VALID"]
    rejected = [r for r in results if r["status"]=="REJECTED"]

    # Hierarchy analysis on the valid HCC set
    hierarchy_analysis = None
    try:
        from v28_hcc_categories import enforce_hierarchy, score_interactions
        valid_hcc_nums = []
        for r in valid:
            hcc = r.get("v28_hcc")
            if hcc:
                try: valid_hcc_nums.append(int(hcc))
                except ValueError: pass
        if valid_hcc_nums:
            h = enforce_hierarchy(list(set(valid_hcc_nums)))
            i = score_interactions(h["kept"])
            hierarchy_analysis = {
                "hccs_kept": h["kept"],
                "hccs_suppressed_by_hierarchy": h["suppressed"],
                "hierarchy_rules_fired": len(h["rules_applied"]),
                "interaction_pairs_found": len(i["interactions_found"]),
                "interaction_raf_bonus": i["total_interaction_raf"],
                "radv_risk": "HIGH" if h["suppressed"] else "STANDARD",
            }
    except ImportError:
        pass

    return jsonify({
        "total": len(codes),
        "valid": len(valid),
        "rejected": len(rejected),
        "not_found": len(codes) - len(valid) - len(rejected),
        "revenue_risk_count": len(rejected),
        "hierarchy_analysis": hierarchy_analysis,
        "results": results,
    })

@app.route("/api/v1/v28/categories")
@require_api_key
def api_v28_categories():
    """Return all 115 V28 HCC payment categories with hierarchy and RAF data."""
    try:
        from v28_hcc_categories import (
            V28_HCC_CATEGORIES, V28_HIERARCHIES, V28_INTERACTIONS
        )
        families = {}
        for hcc, cat in V28_HCC_CATEGORIES.items():
            f = cat["family"]
            families.setdefault(f, []).append(hcc)

        return jsonify({
            "total_hccs": len(V28_HCC_CATEGORIES),
            "categories": {
                str(hcc): {
                    "hcc": hcc,
                    "description": cat["desc"],
                    "family": cat["family"],
                    "severity": cat["severity"],
                    "raf_weight_approx": cat["raf_weight"],
                    "hierarchy_group": cat.get("hierarchy_group"),
                }
                for hcc, cat in sorted(V28_HCC_CATEGORIES.items())
            },
            "hierarchy_rules": len(V28_HIERARCHIES),
            "interaction_pairs": len(V28_INTERACTIONS),
            "families": {f: sorted(hccs) for f, hccs in sorted(families.items())},
            "model_year": 2026,
            "phase_in": "100% V28 for non-PACE MA (full implementation CY2026)",
        })
    except ImportError:
        # Fallback: read from database
        db = get_db()
        rows = db.execute(
            "SELECT hcc_number, description, disease_family, severity, raf_weight "
            "FROM v28_hcc_categories ORDER BY hcc_number"
        ).fetchall()
        return jsonify({
            "total_hccs": len(rows),
            "categories": [dict(r) for r in rows],
            "note": "Extended metadata available after importing v28_hcc_categories module",
        })


@app.route("/api/v1/v28/simulate", methods=["POST"])
@require_api_key
def api_v28_simulate():
    """
    Simulate RAF score for a set of HCC numbers or ICD-10 codes.
    Applies hierarchy suppression, interaction scoring, normalization.

    Input: {
      "hcc_numbers": [37, 226, 280, 328],   # V28 HCC numbers, OR
      "icd10_codes": ["E11.42", "I50.22"],  # ICD-10 codes (auto-resolved to HCCs)
      "age": 72,
      "sex": "F",
      "plan_type": "non_pace"               # "non_pace" | "pace"
    }
    """
    try:
        from v28_hcc_categories import simulate_raf, enforce_hierarchy, score_interactions
    except ImportError:
        return jsonify({"error": "V28 categories module not available. Run build_seed_db.py first."}), 503

    data   = request.get_json() or {}
    age    = int(data.get("age", 70))
    sex    = data.get("sex", "F").upper()
    plan   = data.get("plan_type", "non_pace")

    hcc_numbers = data.get("hcc_numbers", [])

    # If ICD-10 codes provided, resolve to HCC numbers via database
    icd_codes = data.get("icd10_codes", [])
    if icd_codes:
        db = get_db()
        for code in icd_codes[:50]:
            row = db.execute(
                "SELECT v28_hcc FROM v28_hcc_codes WHERE icd10_code=? AND v28_pays=1",
                (code.upper().strip(),)
            ).fetchone()
            if row and row["v28_hcc"]:
                try:
                    hcc_numbers.append(int(row["v28_hcc"]))
                except ValueError:
                    pass

    if not hcc_numbers:
        return jsonify({"error": "Provide hcc_numbers or icd10_codes with valid V28 mappings"}), 400

    # Deduplicate
    hcc_numbers = list(dict.fromkeys(hcc_numbers))

    sim = simulate_raf(hcc_numbers, age=age, sex=sex)

    # Apply MA coding intensity adjustment (5.90%) and normalization factor
    norm_factor = 1.067  # Non-PACE V28 Part C normalization
    if plan == "pace":
        norm_factor = 0.10 * 1.067 + 0.90 * 1.187  # PACE blend
    coding_adj = 1.0 - 0.059  # 5.90% coding intensity reduction

    adjusted_raf = round(sim["total_raf"] * norm_factor * coding_adj, 4)

    return jsonify({
        **sim,
        "plan_type": plan,
        "normalization_factor": norm_factor,
        "ma_coding_adjustment": 0.059,
        "adjusted_raf": adjusted_raf,
        "methodology": (
            f"adjusted_raf = total_raf ({sim['total_raf']}) "
            f"× norm_factor ({norm_factor}) "
            f"× (1 − coding_adj 0.059)"
        ),
    })


@app.route("/api/v1/v28/radv/<int:hcc>")
@require_api_key
def api_v28_radv(hcc: int):
    """Return RADV documentation requirements for a specific HCC number."""
    try:
        from v28_hcc_categories import get_radv_requirements, V28_HCC_CATEGORIES
    except ImportError:
        return jsonify({"error": "V28 categories module not available"}), 503

    cat = V28_HCC_CATEGORIES.get(hcc)
    if not cat:
        return jsonify({"error": f"HCC {hcc} not found in V28 category catalog"}), 404

    reqs = get_radv_requirements(hcc)
    return jsonify({
        "hcc": hcc,
        "description": cat["desc"],
        "family": cat["family"],
        "severity": cat["severity"],
        "radv_requirements": reqs,
        "encounter_filters": {
            "face_to_face_required": True,
            "audio_only_telehealth_excluded": True,
            "lab_radiology_alone_excluded": True,
            "data_source": "Encounter data + FFS only (non-PACE MA)",
        },
    })


@app.route("/api/v1/v28/hierarchy", methods=["POST"])
@require_api_key
def api_v28_hierarchy():
    """
    Apply V28 hierarchy rules to a list of HCC numbers.
    Returns which HCCs are kept vs suppressed and which rules fired.

    Input: {"hcc_numbers": [37, 38, 226, 225, 280]}
    """
    try:
        from v28_hcc_categories import enforce_hierarchy, score_interactions, V28_HCC_CATEGORIES
    except ImportError:
        return jsonify({"error": "V28 categories module not available"}), 503

    data = request.get_json() or {}
    hcc_numbers = data.get("hcc_numbers", [])
    if not hcc_numbers:
        return jsonify({"error": "hcc_numbers required"}), 400

    h = enforce_hierarchy(hcc_numbers)
    i = score_interactions(h["kept"])

    return jsonify({
        "input_hccs": hcc_numbers,
        "kept": h["kept"],
        "suppressed": h["suppressed"],
        "hierarchy_rules_applied": h["rules_applied"],
        "interactions": i["interactions_found"],
        "interaction_raf_bonus": i["total_interaction_raf"],
        "kept_details": [
            {
                "hcc": hcc,
                "desc": V28_HCC_CATEGORIES.get(hcc, {}).get("desc", "Unknown"),
                "raf_weight": V28_HCC_CATEGORIES.get(hcc, {}).get("raf_weight", 0.0),
            }
            for hcc in h["kept"]
            if hcc in V28_HCC_CATEGORIES
        ],
    })


@app.route("/api/v1/v28/normalization")
@require_api_key
def api_v28_normalization():
    """Return 2026 CMS normalization factors, MA coding adjustment, and PACE blend ratios."""
    db = get_db()
    rows = db.execute(
        "SELECT config_key, config_value, description, source "
        "FROM cms_model_config WHERE config_year=2026 ORDER BY config_key"
    ).fetchall()

    if not rows:
        # Return hardcoded values if table not yet seeded
        return jsonify({
            "year": 2026,
            "normalization_factors": {
                "cms_hcc_v28_part_c": 1.067,
                "cms_hcc_v22_part_c_pace": 1.187,
                "esrd_dialysis_v24": 1.062,
                "rxhcc_ma_pd": 1.194,
                "frailty_fide_snps": "full_2024_factors",
            },
            "ma_coding_intensity_adjustment": 0.059,
            "non_pace_v28_blend": 1.00,
            "pace_v28_blend": 0.10,
            "pace_v22_blend": 0.90,
            "ma_payment_increase_2026": 0.0506,
            "effective_growth_rate_2026": 0.0904,
            "mor_record_types": {
                "non_pace": ["2024 CMS-HCC V28 M", "2026 RxHCC V08 6", "2023 ESRD V24 L"],
                "pace":     ["2024 CMS-HCC V28 M", "2026 RxHCC V08 6/7", "2017 CMS-HCC V22 K",
                             "2023 ESRD V24 L",    "2019 ESRD V21 B"],
            },
            "encounter_excluded": [
                "audio_only_telehealth",
                "labs_radiology_pathology_alone",
                "home_health_snf_without_face_to_face",
            ],
            "encounter_accepted": [
                "physician_office_em",
                "inpatient_hospital",
                "outpatient_hospital",
                "fqhc_rhc",
                "video_enabled_telehealth",
            ],
            "note": "Run build_seed_db.py to persist full config table",
        })

    config = {r["config_key"]: r["config_value"] for r in rows}
    return jsonify({
        "year": 2026,
        "config": config,
        "source": "2026 CMS Final Rate Announcement + Implementation Memo",
    })


@app.route("/api/v1/v28/explain")
@require_api_key
def api_v28_explain():
    code = request.args.get("code","").strip().upper()
    if not code: return jsonify({"error":"code parameter required"}), 400
    lookup = v28_lookup(code)
    if lookup["status"] == "NOT_FOUND":
        return jsonify(lookup), 404
    change_note = lookup.get("v28_change_note") or ""
    rationale   = lookup.get("clinical_rationale") or ""
    prompt = f"""Explain the V28 HCC change for ICD-10 code {code} to a medical biller in plain English.

Code: {code} — {lookup.get('description','Unknown')}
V24 HCC: {lookup.get('v24_hcc','None')} | V28 HCC: {lookup.get('v28_hcc','None')}
V24 Pays: {'Yes' if lookup.get('v24_pays') else 'No'} | V28 Pays: {'Yes' if lookup.get('v28_pays') else 'No'}
Payment Tier: {lookup.get('payment_tier','standard')} | HCC Label: {lookup.get('hcc_label','Unknown')}
{f'Change Note: {change_note}' if change_note else ''}
{f'CMS Rationale: {rationale}' if rationale else ''}
Upgrade suggestions: {json.dumps(lookup.get('upgrade_suggestions',[]))}

Explain: (1) What changed between V24 and V28 for this code, (2) the revenue impact per member annually, (3) what action the biller should take including the upgrade code path if rejected, (4) documentation requirements to support an upgrade code. Under 300 words."""
    explanation = call_claude(prompt)
    return jsonify({**lookup, "explanation": explanation, "model": "claude-sonnet-4-20250514"})

@app.route("/api/v1/policies/search")
@require_api_key
def api_policies_search():
    q     = request.args.get("q","").strip()
    limit = min(int(request.args.get("limit",10)),50)
    docs  = search_corpus(q or "coverage", limit=limit,
                          doc_type=request.args.get("type"),
                          payer=request.args.get("payer"))
    return jsonify({"total":len(docs),"results":[{k:v for k,v in d.items() if k != "content_text"} for d in docs]})

@app.route("/api/v1/policies/<source_id>")
@require_api_key
def api_policy_detail(source_id):
    db  = get_db()
    row = db.execute("SELECT * FROM documents WHERE source_id=? AND status='active'",(source_id,)).fetchone()
    if not row: return jsonify({"error":f"Policy {source_id} not found"}), 404
    return jsonify(dict(row))

@app.route("/api/v1/classify", methods=["POST"])
@require_api_key
def api_classify():
    import yaml
    data = request.get_json() or {}
    text = data.get("text","")
    if not text: return jsonify({"error":"text required"}), 400
    taxonomy_path = BASE_DIR / "data" / "taxonomy.yaml"
    with open(taxonomy_path) as f:
        tax = yaml.safe_load(f)
    tl = text.lower()
    scores = {}
    for dt, cfg in tax["document_types"].items():
        if dt == "unknown": continue
        scores[dt] = sum(1 for kw in cfg["keywords"] if kw.lower() in tl) * cfg.get("weight",1.0)
    best  = max(scores, key=scores.get) if any(v>0 for v in scores.values()) else "unknown"
    total = sum(scores.values())
    conf  = round(scores.get(best,0)/total, 3) if total > 0 else 0.0
    th    = tax["confidence_thresholds"]
    if conf < th["reject"]: best = "unknown"
    routing = tax["routing_matrix"].get(best,{})
    return jsonify({"document_type":best,"label":tax["document_types"].get(best,{}).get("label","Unknown"),
        "confidence":conf,"requires_review":conf < th["auto_accept"],
        "routing_targets":routing.get("targets",["REVIEW"])})

APPEAL_PROMPT_TEMPLATE = """Generate a formal prior authorization appeal letter.

CLAIM DETAILS:
- CPT Code: {cpt_code}
- Diagnosis Codes: {icd10_list}
- Denial Reason: {denial_reason}
- Denial Date: {denial_date}
- Payer: {payer}
- Provider: {provider_name}

POLICY CONTEXT (cite these in the letter):
{policy_context}

{v28_context}

LETTER REQUIREMENTS:
1. Opening paragraph: patient need + specific procedure + denial date
2. Clinical necessity section: cite specific LCD/NCD IDs from policy context above
3. Policy compliance section: reference exact coverage criteria the patient meets
4. Supporting evidence section: list documentation to be enclosed (physician notes, lab results, imaging)
5. Regulatory basis: cite 42 CFR 405.950 (redetermination rights) or applicable state regulation
6. Closing: request for expedited review if urgent, contact information placeholder

FORMAT: Formal business letter. Professional tone. Under 450 words.
CRITICAL: Only cite policy IDs that appear in the POLICY CONTEXT above. Never fabricate citations."""

@app.route("/api/v1/appeals/generate", methods=["POST"])
@require_api_key
def api_appeals():
    data = request.get_json() or {}
    for f in ["cpt_code","icd10_codes","denial_reason","payer","provider_name"]:
        if not data.get(f): return jsonify({"error":f"{f} required"}), 400
    docs = search_corpus(f"{data['cpt_code']} {' '.join(data['icd10_codes'][:3])}", limit=5)
    ctx  = build_rag_context(docs, max_docs=3, max_chars=600)
    v28_ctx = build_appeal_v28_context(data['icd10_codes'])
    letter = call_claude(APPEAL_PROMPT_TEMPLATE.format(
        cpt_code=data['cpt_code'],
        icd10_list=', '.join(data['icd10_codes']),
        denial_reason=data['denial_reason'],
        denial_date=data.get('denial_date','recent'),
        payer=data['payer'],
        provider_name=data['provider_name'],
        policy_context=ctx or 'Apply general Medicare coverage guidelines.',
        v28_context=v28_ctx,
    ))
    return jsonify({"letter":letter,"sources":[{"id":d["source_id"],"title":d["title"]} for d in docs]})

# ════════════════════════════════════════════════════════════════
# AUTH — Optional (enforced when REQUIRE_AUTH=true in env)
# ════════════════════════════════════════════════════════════════

REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() == "true"

def ensure_users_table():
    """Create users table if it doesn't exist (safe to call on every startup)."""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT NOT NULL UNIQUE,
            name         TEXT NOT NULL,
            password     TEXT NOT NULL,
            role         TEXT DEFAULT 'user',
            active       INTEGER DEFAULT 1,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    db.commit()

def login_required(f):
    """Redirect to /login if REQUIRE_AUTH is enabled and user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if REQUIRE_AUTH and not session.get("user_id"):
            return redirect(url_for("login_page", next=request.path))
        return f(*args, **kwargs)
    return decorated

# ════════════════════════════════════════════════════════════════
# LAYER 1: PORTAL (internal — no API key needed)
# ════════════════════════════════════════════════════════════════

@app.route("/chat")
@login_required
def portal_chat():
    return render_template("chat.html")

@app.route("/v28")
@login_required
def portal_v28():
    return render_template("v28.html")

@app.route("/appeals")
@login_required
def portal_appeals():
    return render_template("appeals.html")

@app.route("/docs")
@login_required
def portal_docs():
    db   = get_db()
    keys = db.execute("SELECT id, customer_name, tier, monthly_usage, last_used, created_at FROM api_keys WHERE active=1 ORDER BY created_at DESC").fetchall()
    return render_template("docs.html", api_keys=[dict(k) for k in keys], tiers=TIERS)

@app.route("/portal/key/create", methods=["POST"])
def create_key():
    name = request.form.get("name","").strip() or "New Customer"
    tier = request.form.get("tier","demo")
    if tier not in TIERS: tier = "demo"
    raw  = f"cmg_{secrets.token_urlsafe(32)}"
    kh   = hashlib.sha256(raw.encode()).hexdigest()
    db   = get_db()
    db.execute("INSERT INTO api_keys(key_hash,customer_name,tier) VALUES(?,?,?)",(kh,name,tier))
    db.commit()
    return jsonify({"api_key":raw,"tier":tier,"customer":name,
        "warning":"Save this key — it will not be shown again.",
        "usage":"X-API-Key: "+raw})

@app.route("/portal/chat", methods=["POST"])
def portal_chat_post():
    data = request.get_json() or {}
    q    = data.get("query","").strip()
    if not q: return jsonify({"error":"query required"}), 400
    docs = search_corpus(q, limit=5)
    ctx  = build_rag_context(docs)

    codes   = extract_codes(q)
    v28_ctx = build_v28_chat_context(codes["icd10"])

    hipaa_ctx = ""
    if is_hipaa_query(q):
        hipaa_docs = search_hipaa(q, limit=2)
        if hipaa_docs:
            hipaa_ctx = "\n\nHIPAA Context:\n" + "\n---\n".join(
                [f"[{h['source_id']}] {h['title']}\n{(h.get('summary_text') or h.get('content_text',''))[:600]}"
                 for h in hipaa_docs]
            )

    ans = call_claude(f"Corpus context:\n{ctx}{v28_ctx}{hipaa_ctx}\n\nQuestion: {q}", data.get("history",[]))
    return jsonify({"answer":ans,"sources":[{"id":d["source_id"],"title":d["title"]} for d in docs[:5]]})

@app.route("/portal/v28/lookup", methods=["POST"])
def portal_v28_post():
    data = request.get_json() or {}
    code = data.get("code","").strip()
    if not code: return jsonify({"error":"code required"}), 400
    return jsonify(v28_lookup(code))

@app.route("/portal/v28/batch", methods=["POST"])
def portal_v28_batch():
    data  = request.get_json() or {}
    raw   = data.get("codes","")
    codes = [c.strip().upper() for c in re.split(r"[\n,\s]+", raw if isinstance(raw,str) else "\n".join(raw)) if c.strip()]
    if not codes: return jsonify({"error":"No codes provided"}), 400
    results  = [v28_lookup(c) for c in codes[:200]]
    valid    = [r for r in results if r["status"]=="VALID"]
    rejected = [r for r in results if r["status"]=="REJECTED"]
    return jsonify({"total":len(codes),"valid":len(valid),"rejected":len(rejected),
        "not_found":len(codes)-len(valid)-len(rejected),"results":results})

@app.route("/raf")
@login_required
def portal_raf():
    return render_template("raf.html")

@app.route("/radv")
@login_required
def portal_radv():
    return render_template("radv.html")

@app.route("/portal/v28/simulate-raf", methods=["POST"])
def portal_raf_post():
    """RAF simulation endpoint for portal UI — no API key required."""
    try:
        from v28_hcc_categories import simulate_raf, V28_HCC_CATEGORIES
    except ImportError:
        return jsonify({"error": "V28 categories module not available. Run build_seed_db.py first."}), 503

    data        = request.get_json() or {}
    age         = int(data.get("age", 70))
    sex         = data.get("sex", "F").upper()
    plan        = data.get("plan_type", "non_pace")
    hcc_numbers = list(data.get("hcc_numbers", []))
    icd_codes   = data.get("icd10_codes", [])
    unresolved  = []

    if icd_codes:
        db = get_db()
        for code in icd_codes[:50]:
            row = db.execute(
                "SELECT v28_hcc FROM v28_hcc_codes WHERE icd10_code=? AND v28_pays=1",
                (code.upper().strip(),)
            ).fetchone()
            if row and row["v28_hcc"]:
                try:
                    hcc_numbers.append(int(row["v28_hcc"]))
                except ValueError:
                    unresolved.append(code)
            else:
                unresolved.append(code)

    if not hcc_numbers:
        return jsonify({"error": "No valid V28 HCC codes resolved from input. Check codes via V28 HCC Checker."}), 400

    hcc_numbers = list(dict.fromkeys(hcc_numbers))
    sim = simulate_raf(hcc_numbers, age=age, sex=sex)

    norm_factor = 1.067
    if plan == "pace":
        norm_factor = round(0.10 * 1.067 + 0.90 * 1.187, 4)
    adjusted_raf = round(sim["total_raf"] * norm_factor * (1.0 - 0.059), 4)

    # active_hccs already has {hcc, desc, raf_weight} from simulate_raf
    hcc_details = sim.get("active_hccs", [])

    # Enrich suppressed HCC ints with descriptions
    suppressed_details = []
    for hcc in sim.get("suppressed_hccs", []):
        hcc_int = hcc if isinstance(hcc, int) else hcc.get("hcc", hcc)
        cat = V28_HCC_CATEGORIES.get(hcc_int, {})
        suppressed_details.append({
            "hcc": hcc_int,
            "desc": cat.get("desc", "Suppressed by hierarchy rule"),
        })

    # Remap interactions to frontend-expected shape {hcc1, hcc2, description, raf}
    interactions_ui = []
    for ix in sim.get("interactions_found", []):
        hccs = ix.get("hccs", [])
        interactions_ui.append({
            "hcc1": hccs[0] if len(hccs) > 0 else None,
            "hcc2": hccs[1] if len(hccs) > 1 else None,
            "description": ix.get("desc") or ix.get("label", ""),
            "raf": ix.get("additional_raf", 0.0),
        })

    return jsonify({
        **sim,
        "hcc_details": hcc_details,
        "suppressed_hccs": suppressed_details,
        "interactions": interactions_ui,
        "plan_type": plan,
        "normalization_factor": norm_factor,
        "ma_coding_adjustment": 0.059,
        "adjusted_raf": adjusted_raf,
        "unresolved_codes": unresolved,
    })


@app.route("/portal/v28/radv-requirements", methods=["POST"])
def portal_radv_post():
    """RADV documentation requirements for portal — accepts HCC number or ICD-10 code."""
    try:
        from v28_hcc_categories import get_radv_requirements, V28_HCC_CATEGORIES, V28_HIERARCHIES
    except ImportError:
        return jsonify({"error": "V28 categories module not available"}), 503

    data  = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "query required (HCC number or ICD-10 code)"}), 400

    hcc_num = None

    # Try parsing as HCC number
    if query.isdigit():
        hcc_num = int(query)
    else:
        # Try as ICD-10 — look up v28_hcc from DB
        db  = get_db()
        row = db.execute(
            "SELECT v28_hcc, description FROM v28_hcc_codes WHERE icd10_code=? AND v28_pays=1",
            (query.upper(),)
        ).fetchone()
        if row and row["v28_hcc"]:
            try:
                hcc_num = int(row["v28_hcc"])
            except ValueError:
                pass
        if hcc_num is None:
            # Maybe it's in format "HCC 37"
            m = re.match(r'^HCC\s*(\d+)$', query, re.IGNORECASE)
            if m:
                hcc_num = int(m.group(1))

    if hcc_num is None:
        return jsonify({"error": f"Could not resolve '{query}' to a V28 HCC. Try a number (e.g. 37) or valid V28 ICD-10 code."}), 404

    cat = V28_HCC_CATEGORIES.get(hcc_num)
    if not cat:
        return jsonify({"error": f"HCC {hcc_num} not found in V28 category catalog (1–115)"}), 404

    reqs = get_radv_requirements(hcc_num)

    # Build hierarchy chain for this HCC
    hierarchy_chain = []
    for parent, child, rule_desc in V28_HIERARCHIES:
        if parent == hcc_num:
            child_cat = V28_HCC_CATEGORIES.get(child, {})
            hierarchy_chain.append({"hcc": child, "desc": child_cat.get("desc", ""), "role": "child", "rule": rule_desc})
        elif child == hcc_num:
            parent_cat = V28_HCC_CATEGORIES.get(parent, {})
            hierarchy_chain.append({"hcc": parent, "desc": parent_cat.get("desc", ""), "role": "parent", "rule": rule_desc})

    return jsonify({
        "hcc": hcc_num,
        "description": cat["desc"],
        "family": cat["family"],
        "severity": cat["severity"],
        "raf_weight": cat.get("raf_weight"),
        "hierarchy_group": cat.get("hierarchy_group"),
        "radv_requirements": reqs,
        "hierarchy_chain": hierarchy_chain,
        "encounter_filters": {
            "face_to_face_required": True,
            "audio_only_telehealth_excluded": True,
            "lab_radiology_alone_excluded": True,
            "data_source": "Encounter data + FFS only (non-PACE MA CY2026)",
        },
    })


@app.route("/portal/v28/explain", methods=["POST"])
def portal_v28_explain():
    data = request.get_json() or {}
    code = data.get("code","").strip().upper()
    if not code: return jsonify({"error":"code required"}), 400
    lookup = v28_lookup(code)
    if lookup["status"] == "NOT_FOUND":
        return jsonify(lookup), 404
    change_note = lookup.get("v28_change_note") or ""
    rationale   = lookup.get("clinical_rationale") or ""
    prompt = f"""Explain the V28 HCC change for ICD-10 code {code} to a medical biller in plain English.

Code: {code} — {lookup.get('description','Unknown')}
V24 HCC: {lookup.get('v24_hcc','None')} | V28 HCC: {lookup.get('v28_hcc','None')}
V24 Pays: {'Yes' if lookup.get('v24_pays') else 'No'} | V28 Pays: {'Yes' if lookup.get('v28_pays') else 'No'}
Payment Tier: {lookup.get('payment_tier','standard')} | HCC Label: {lookup.get('hcc_label','Unknown')}
{f'Change Note: {change_note}' if change_note else ''}
{f'CMS Rationale: {rationale}' if rationale else ''}
Upgrade suggestions: {json.dumps(lookup.get('upgrade_suggestions',[]))}

Explain: (1) What changed between V24 and V28, (2) revenue impact per member annually, (3) biller action including upgrade code path if rejected, (4) documentation requirements. Under 300 words."""
    explanation = call_claude(prompt)
    return jsonify({**lookup, "explanation": explanation})

@app.route("/portal/appeals/generate", methods=["POST"])
def portal_appeals_post():
    data   = request.get_json() or {}
    cpt    = data.get("cpt_code","")
    icd    = data.get("icd10_codes",[])
    denial = data.get("denial_reason","Medical Necessity")
    payer  = data.get("payer","Unknown")
    prov   = data.get("provider_name","Provider")
    date   = data.get("denial_date","")
    docs   = search_corpus(f"{cpt} {' '.join(icd[:3])}", limit=5)
    ctx    = build_rag_context(docs, max_docs=3, max_chars=600)
    v28_ctx = build_appeal_v28_context(icd)
    letter = call_claude(APPEAL_PROMPT_TEMPLATE.format(
        cpt_code=cpt,
        icd10_list=', '.join(icd),
        denial_reason=denial,
        denial_date=date or 'recent',
        payer=payer,
        provider_name=prov,
        policy_context=ctx or 'Apply general Medicare coverage guidelines.',
        v28_context=v28_ctx,
    ))
    return jsonify({"letter":letter,"sources":[{"id":d["source_id"],"title":d["title"]} for d in docs]})


@app.route("/member")
@login_required
def portal_member():
    return render_template("member.html")


@app.route("/portal/member/risk-profile", methods=["POST"])
def portal_member_risk_profile():
    """Combined: V28 batch audit + RAF simulation + RADV analysis in one request."""
    try:
        from v28_hcc_categories import simulate_raf, V28_HCC_CATEGORIES
    except ImportError:
        return jsonify({"error": "V28 categories module not available"}), 503

    data      = request.get_json() or {}
    icd_codes = data.get("icd10_codes", [])
    age       = int(data.get("age", 70))
    sex       = data.get("sex", "F").upper()
    plan      = data.get("plan_type", "non_pace")

    if not icd_codes:
        return jsonify({"error": "icd10_codes required"}), 400

    # 1. V28 batch audit
    results  = [v28_lookup(c) for c in icd_codes[:50]]
    valid    = [r for r in results if r["status"] == "VALID"]
    rejected = [r for r in results if r["status"] == "REJECTED"]

    # 2. Resolve valid ICD-10 codes → HCC numbers
    db = get_db()
    hcc_numbers = []
    for code in icd_codes[:50]:
        row = db.execute(
            "SELECT v28_hcc FROM v28_hcc_codes WHERE icd10_code=? AND v28_pays=1",
            (code.upper().strip(),)
        ).fetchone()
        if row and row["v28_hcc"]:
            try:
                hcc_numbers.append(int(row["v28_hcc"]))
            except ValueError:
                pass
    hcc_numbers = list(dict.fromkeys(hcc_numbers))

    # 3. RAF simulation
    raf_result = None
    if hcc_numbers:
        sim = simulate_raf(hcc_numbers, age=age, sex=sex)
        norm_factor  = 1.067 if plan != "pace" else round(0.10 * 1.067 + 0.90 * 1.187, 4)
        adjusted_raf = round(sim["total_raf"] * norm_factor * 0.941, 4)

        interactions_ui = [
            {
                "hcc1": ix.get("hccs", [None])[0],
                "hcc2": ix.get("hccs", [None, None])[1],
                "description": ix.get("desc") or ix.get("label", ""),
                "raf": ix.get("additional_raf", 0.0),
            }
            for ix in sim.get("interactions_found", [])
        ]
        suppressed_details = [
            {"hcc": (h if isinstance(h, int) else h.get("hcc", h)),
             "desc": V28_HCC_CATEGORIES.get(h if isinstance(h, int) else h.get("hcc", h), {}).get("desc", "")}
            for h in sim.get("suppressed_hccs", [])
        ]
        raf_result = {
            **sim,
            "hcc_details": sim.get("active_hccs", []),
            "suppressed_hccs": suppressed_details,
            "interactions": interactions_ui,
            "normalization_factor": norm_factor,
            "ma_coding_adjustment": 0.059,
            "adjusted_raf": adjusted_raf,
            "plan_type": plan,
        }

    # 4. Revenue opportunities from rejected codes
    revenue_opps = [
        {
            "from_code": r["code"],
            "to_code": upg["icd10_code"],
            "description": upg.get("description") or upg.get("hcc_label", ""),
            "hcc": upg.get("v28_hcc"),
            "tier": upg.get("payment_tier", "standard"),
        }
        for r in rejected
        for upg in (r.get("upgrade_suggestions") or [])[:2]
    ]

    suppressed_count = len(raf_result.get("suppressed_hccs", [])) if raf_result else 0

    return jsonify({
        "audit":  {"total": len(results), "valid": len(valid), "rejected": len(rejected),
                   "not_found": len(results) - len(valid) - len(rejected), "results": results},
        "raf":    raf_result,
        "radv_risk": "HIGH" if suppressed_count > 0 else "STANDARD",
        "suppressed_count": suppressed_count,
        "revenue_opportunities": revenue_opps,
        "member": {"age": age, "sex": sex, "plan_type": plan},
    })

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if session.get("user_id"):
        return redirect(url_for("portal_dashboard"))
    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            ensure_users_table()
            db  = get_db()
            row = db.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
            if row and check_password_hash(row["password"], password):
                session.permanent = True
                session["user_id"]   = row["id"]
                session["user_name"] = row["name"]
                session["user_email"] = row["email"]
                next_url = request.args.get("next", "/dashboard")
                return redirect(next_url)
            error = "Invalid email or password."
        except Exception as e:
            logger.error(f"Login error: {e}")
            error = "Login failed. Please try again."
    return render_template("login.html", error=error)

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if session.get("user_id"):
        return redirect(url_for("portal_dashboard"))
    error = None
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        company  = request.form.get("company", "").strip()
        if not name or not email or not password:
            error = "Name, email, and password are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            try:
                ensure_users_table()
                db = get_db()
                db.execute(
                    "INSERT INTO users (email, name, password) VALUES (?,?,?)",
                    (email, name, generate_password_hash(password))
                )
                db.commit()
                row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                session["user_id"]    = row["id"]
                session["user_name"]  = row["name"]
                session["user_email"] = row["email"]
                return redirect(url_for("portal_dashboard"))
            except sqlite3.IntegrityError:
                error = "An account with that email already exists."
            except Exception as e:
                logger.error(f"Signup error: {e}")
                error = "Account creation failed. Please try again."
    return render_template("signup.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

# ════════════════════════════════════════════════════════════════
# PUBLIC PAGES — Landing, Compliance, Contact
# ════════════════════════════════════════════════════════════════

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/hipaa")
def hipaa_page():
    return render_template("hipaa.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    submitted = False
    if request.method == "POST":
        # Log the inquiry; in production wire to email / CRM
        name    = request.form.get("name","").strip()
        email   = request.form.get("email","").strip()
        company = request.form.get("company","").strip()
        message = request.form.get("message","").strip()
        plan    = request.form.get("plan","general")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO audit_log(action,resource_type,user_session,ip_address,query_text) VALUES(?,?,?,?,?)",
                ("contact_form", "lead", email, request.remote_addr,
                 f"{name} | {company} | {plan} | {message[:200]}")
            )
            db.commit()
        except Exception:
            pass
        submitted = True
        logger.info(f"Contact form: {name} <{email}> [{company}] — {plan}")
    return render_template("contact.html", submitted=submitted)

# ════════════════════════════════════════════════════════════════
# PORTAL — Rename / to /dashboard (add login_required gate)
# ════════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def portal_dashboard():
    db = get_db()
    docs  = db.execute("SELECT COUNT(*) c FROM documents WHERE status='active'").fetchone()
    v28   = db.execute("SELECT COUNT(*) c, SUM(CASE WHEN v28_pays=0 AND v24_pays=1 THEN 1 ELSE 0 END) rej FROM v28_hcc_codes").fetchone()
    keys  = db.execute("SELECT COUNT(*) c FROM api_keys WHERE active=1").fetchone()
    calls = db.execute("SELECT COUNT(*) c FROM audit_log WHERE action='api_request'").fetchone()
    return render_template("dashboard.html",
        doc_count=docs["c"], v28_total=v28["c"],
        v28_rejected=v28["rej"] or 0,
        api_keys=keys["c"], api_calls=calls["c"])

# ── Error handlers ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {e}")
    return render_template("500.html"), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
