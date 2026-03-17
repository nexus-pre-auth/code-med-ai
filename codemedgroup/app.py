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

# ── Claude ────────────────────────────────────────────────────
RAG_SYSTEM = """You are CodeMed AI — a medical billing, prior authorization, and HCC coding expert built by CodeMed Group.

Your corpus includes 1,307+ CMS LCD/NCD policies, payer clinical policies, and V28 HCC mappings updated for 2026.

Rules:
- Cite specific LCD/NCD IDs when relevant: "Per LCD L38226..."
- Reference exact ICD-10 and CPT codes from context
- Flag V28 HCC revenue risk when diagnosis codes are involved
- Be direct and actionable. Billers need clear yes/no answers and specific steps.
- If a claim will likely be denied, say so clearly with the reason
- For prior auth: list exact documentation required
- Keep responses focused and under 500 words unless detail is critical
- Format with clear sections and bullet points for code lists"""

def call_claude(user_prompt: str, history: list = None) -> str:
    import urllib.request, urllib.error
    if not ANTHROPIC_API_KEY:
        return "⚠️ Claude API key not configured. Add ANTHROPIC_API_KEY to your .env file."
    messages = []
    if history:
        for msg in history[-6:]:
            if isinstance(msg, dict) and msg.get("role") in ("user","assistant"):
                messages.append(msg)
    messages.append({"role":"user","content":user_prompt})
    payload = json.dumps({
        "model":"claude-sonnet-4-20250514",
        "max_tokens":1500,
        "system":RAG_SYSTEM,
        "messages":messages
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type":"application/json","x-api-key":ANTHROPIC_API_KEY,"anthropic-version":"2023-06-01"}
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

# ── Corpus search ─────────────────────────────────────────────
def search_corpus(query: str, limit=5, doc_type=None, payer=None) -> list:
    db = get_db()
    terms = [f"%{t}%" for t in query.split()[:4] if len(t) > 2]
    if not terms:
        terms = [f"%{query}%"]
    cond = " OR ".join(["d.title LIKE ?","d.content_text LIKE ?","d.indication_text LIKE ?","d.coding_text LIKE ?"])
    params = [f"%{query}%"] * 4
    sql = f"SELECT * FROM documents d WHERE d.status='active' AND ({cond})"
    if doc_type: sql += " AND d.document_type=?"; params.append(doc_type)
    if payer:    sql += " AND d.payer_code=?";    params.append(payer.upper())
    sql += f" ORDER BY d.confidence_score DESC LIMIT {limit}"
    try:
        return [dict(r) for r in db.execute(sql, params).fetchall()]
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

# ── V28 engine ────────────────────────────────────────────────
def v28_lookup(code: str) -> dict:
    db = get_db()
    r = db.execute("SELECT * FROM v28_hcc_codes WHERE icd10_code=?",(code.upper().strip(),)).fetchone()
    if not r:
        return {"code":code.upper(),"status":"NOT_FOUND","v28_pays":False,"message":f"{code} not in V28 corpus"}
    r = dict(r)
    if r["v28_pays"]:     status = "VALID"
    elif r["v24_pays"]:   status = "REJECTED"
    else:                 status = "NOT_MAPPED"
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
        "code":r["icd10_code"], "description":r["description"],
        "status":status, "v28_hcc":r["v28_hcc"], "v24_hcc":r["v24_hcc"],
        "v28_pays":bool(r["v28_pays"]), "payment_tier":r["payment_tier"],
        "hcc_label":r["hcc_label"], "upgrade_suggestions":upgrades
    }

# ════════════════════════════════════════════════════════════════
# LAYER 2: PUBLIC API
# ════════════════════════════════════════════════════════════════

@app.route("/api/v1/status")
def api_status():
    db = get_db()
    d = db.execute("SELECT COUNT(*) c, SUM(CASE WHEN document_type='lcd' THEN 1 ELSE 0 END) lcd, SUM(CASE WHEN document_type='ncd' THEN 1 ELSE 0 END) ncd FROM documents WHERE status='active'").fetchone()
    v = db.execute("SELECT COUNT(*) c, SUM(v28_pays) valid, SUM(CASE WHEN v24_pays=1 AND v28_pays=0 THEN 1 ELSE 0 END) rejected FROM v28_hcc_codes").fetchone()
    return jsonify({"status":"operational","version":"1.0.0",
        "corpus":{"total":d["c"],"lcd":d["lcd"],"ncd":d["ncd"]},
        "v28":{"total":v["c"],"valid":v["valid"],"rejected":v["rejected"]},
        "model":"claude-sonnet-4-20250514","hipaa_compliant":True,
        "timestamp":datetime.utcnow().isoformat()+"Z"})

@app.route("/api/v1/query", methods=["POST"])
@require_api_key
def api_query():
    data = request.get_json() or {}
    q = data.get("query","").strip()
    if not q: return jsonify({"error":"query required"}), 400
    t0 = time.time()
    docs = search_corpus(q, limit=5)
    ctx  = "\n\n---\n\n".join([f"[{d['source_id']}] {d['title']}\n{d['content_text'][:800]}" for d in docs[:3]])
    ans  = call_claude(f"Corpus context:\n{ctx}\n\nQuestion: {q}", data.get("history",[]))
    return jsonify({"answer":ans,
        "sources":[{"id":d["source_id"],"title":d["title"],"type":d["document_type"]} for d in docs[:3]],
        "response_ms":int((time.time()-t0)*1000),"tier":g.api_tier,"model":"claude-sonnet-4-20250514"})

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
    return jsonify({"total":len(codes),"valid":len(valid),"rejected":len(rejected),
        "not_found":len(codes)-len(valid)-len(rejected),"revenue_risk_count":len(rejected),"results":results})

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
    with open(BASE_DIR/"data"/"taxonomy.yaml") as f:
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

@app.route("/api/v1/appeals/generate", methods=["POST"])
@require_api_key
def api_appeals():
    data = request.get_json() or {}
    for f in ["cpt_code","icd10_codes","denial_reason","payer","provider_name"]:
        if not data.get(f): return jsonify({"error":f"{f} required"}), 400
    docs = search_corpus(f"{data['cpt_code']} {' '.join(data['icd10_codes'][:3])}", limit=3)
    ctx  = "\n".join([f"[{d['source_id']}] {d['title']}: {d.get('indication_text','')}" for d in docs])
    letter = call_claude(f"""Write a formal prior auth appeal letter.
CPT: {data['cpt_code']} | ICD-10: {', '.join(data['icd10_codes'])}
Denial reason: {data['denial_reason']} | Date: {data.get('denial_date','recent')}
Payer: {data['payer']} | Provider: {data['provider_name']}
Policy context:\n{ctx}\nKeep under 400 words, cite LCD/NCD IDs.""")
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

# Portal endpoints (no API key — portal only)
@app.route("/portal/chat", methods=["POST"])
def portal_chat_post():
    data = request.get_json() or {}
    q    = data.get("query","").strip()
    if not q: return jsonify({"error":"query required"}), 400
    docs = search_corpus(q, limit=5)
    ctx  = "\n\n---\n\n".join([f"[{d['source_id']}] {d['title']}\n{d['content_text'][:800]}" for d in docs[:3]])
    ans  = call_claude(f"Corpus context:\n{ctx}\n\nQuestion: {q}", data.get("history",[]))
    return jsonify({"answer":ans,"sources":[{"id":d["source_id"],"title":d["title"]} for d in docs[:3]]})

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

@app.route("/portal/appeals/generate", methods=["POST"])
def portal_appeals_post():
    data   = request.get_json() or {}
    cpt    = data.get("cpt_code","")
    icd    = data.get("icd10_codes",[])
    denial = data.get("denial_reason","Medical Necessity")
    payer  = data.get("payer","Unknown")
    prov   = data.get("provider_name","Provider")
    date   = data.get("denial_date","")
    docs   = search_corpus(f"{cpt} {' '.join(icd[:3])}", limit=3)
    ctx    = "\n".join([f"[{d['source_id']}] {d['title']}: {d.get('indication_text','')}" for d in docs])
    letter = call_claude(f"""Write a formal prior auth appeal letter.
CPT: {cpt} | ICD-10: {', '.join(icd)} | Denial: {denial}
Date: {date or 'recent'} | Payer: {payer} | Provider: {prov}
Policy context:\n{ctx or 'Apply general Medicare coverage guidelines.'}
Professional, under 400 words, cite policy IDs.""")
    return jsonify({"letter":letter,"sources":[{"id":d["source_id"],"title":d["title"]} for d in docs]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
