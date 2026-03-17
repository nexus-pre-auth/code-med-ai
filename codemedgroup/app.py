"""
CodeMed Group Platform
Layer 2: Regulatory Intelligence API
Layer 1: NexusAuth RCM Portal
"""
import os, re, json, sqlite3, hashlib, secrets, time, logging
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, request, jsonify, render_template, g

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

CORPUS: 1,307+ CMS LCD/NCD policies, payer clinical policies, HIPAA compliance documents, and V28 HCC mappings (2024–2026 Medicare Advantage risk adjustment).

RESPONSE RULES:
1. Cite specific policy IDs in every relevant answer: "Per LCD L38226..." or "Per NCD 280.14..."
2. Reference exact ICD-10-CM, CPT, and HCPCS codes from the context — never invent codes
3. Flag V28 HCC revenue impact when diagnosis codes are discussed: identify VALID vs REJECTED status
4. For prior auth queries: enumerate required documentation as a numbered checklist
5. For denial/appeal queries: identify the denial reason code category (CO, PR, OA, PI), cite the relevant LCD/NCD, and provide the appeal pathway
6. For coverage questions: give a direct YES or NO coverage determination before explaining nuances
7. If a claim will be denied, state it clearly with the specific LCD limitation or exclusion that applies
8. When V24-only codes appear, proactively suggest V28-valid upgrade codes with their HCC numbers
9. Bold critical warnings using **DENIAL RISK** or **V28 REJECTED** formatting

FORMAT:
- Lead with a direct answer (1-2 sentences)
- Use bullet points for code lists
- Use numbered steps for processes
- Keep under 600 words unless clinical detail is critical

CONSTRAINTS:
- Never fabricate LCD/NCD IDs or policy content not present in context
- Do not provide actual medical advice — this is billing and coding guidance only
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
    cleaned = re.sub(r'\b[A-Z]\d{2,4}(?:\.\d{1,4})?\b', ' ', query, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b\d{5}\b', ' ', cleaned)
    tokens = [t.strip('.,;:()[]"\'') for t in cleaned.split()
              if len(t.strip('.,;:()[]"\'')) >= 3
              and t.lower().strip('.,;:()[]"\'') not in STOPWORDS]
    if not tokens:
        return None
    return ' AND '.join(tokens[:6])

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

    # Auto-inject V28 status for any ICD-10 codes in the query
    codes = extract_codes(q)
    v28_ctx = ""
    if codes["icd10"]:
        v28_results = [v28_lookup(c) for c in codes["icd10"][:5]]
        v28_lines = [f"  {r['code']}: {r['status']} (HCC {r.get('v28_hcc','N/A')}, tier={r.get('payment_tier','N/A')})"
                     for r in v28_results]
        v28_ctx = "\nV28 HCC Status for codes in query:\n" + "\n".join(v28_lines) + "\n"

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
            },
            "ma_coding_intensity_adjustment": 0.059,
            "non_pace_v28_blend": 1.00,
            "pace_v28_blend": 0.10,
            "pace_v22_blend": 0.90,
            "ma_payment_increase_2026": 0.0506,
            "effective_growth_rate_2026": 0.0904,
            "note": "Run build_seed_db.py to persist config table",
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
# LAYER 1: PORTAL (internal — no API key needed)
# ════════════════════════════════════════════════════════════════

@app.route("/")
def portal_index():
    db = get_db()
    docs  = db.execute("SELECT COUNT(*) c FROM documents WHERE status='active'").fetchone()
    v28   = db.execute("SELECT COUNT(*) c, SUM(CASE WHEN v28_pays=0 AND v24_pays=1 THEN 1 ELSE 0 END) rej FROM v28_hcc_codes").fetchone()
    keys  = db.execute("SELECT COUNT(*) c FROM api_keys WHERE active=1").fetchone()
    calls = db.execute("SELECT COUNT(*) c FROM audit_log WHERE action='api_request'").fetchone()
    return render_template("dashboard.html",
        doc_count=docs["c"], v28_total=v28["c"],
        v28_rejected=v28["rej"] or 0,
        api_keys=keys["c"], api_calls=calls["c"])

@app.route("/chat")
def portal_chat():
    return render_template("chat.html")

@app.route("/v28")
def portal_v28():
    return render_template("v28.html")

@app.route("/appeals")
def portal_appeals():
    return render_template("appeals.html")

@app.route("/docs")
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

    codes = extract_codes(q)
    v28_ctx = ""
    if codes["icd10"]:
        v28_results = [v28_lookup(c) for c in codes["icd10"][:5]]
        v28_lines = [f"  {r['code']}: {r['status']} (HCC {r.get('v28_hcc','N/A')}, tier={r.get('payment_tier','N/A')})"
                     for r in v28_results]
        v28_ctx = "\nV28 HCC Status for codes in query:\n" + "\n".join(v28_lines) + "\n"

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
