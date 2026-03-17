"""
CodeMed Group — Data Ingestion Pipeline
Populates nexusauth.db with CMS LCD/NCD policies, payer policies, and HIPAA documents.

Usage:
  python ingest.py --type cms-api  --db data/nexusauth.db
  python ingest.py --type json     --file lcd_export.json --db data/nexusauth.db
  python ingest.py --type csv      --file policies.csv --db data/nexusauth.db
  python ingest.py --type payer    --file aetna_policies.csv --payer AETNA
  python ingest.py --type hipaa    --file hipaa_privacy_rule.txt
  python ingest.py --type rebuild-fts --db data/nexusauth.db
"""
import argparse, csv, hashlib, json, logging, re, sqlite3, time, xml.etree.ElementTree as ET
import urllib.request, urllib.error
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("codemedgroup.ingest")

DEFAULT_DB = Path(__file__).parent / "nexusauth.db"


# ── Database helpers ──────────────────────────────────────────

def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def insert_document(conn: sqlite3.Connection, doc: dict) -> bool:
    """Insert a document. Returns True if inserted, False if duplicate."""
    content = doc.get("content_text") or ""
    h = compute_hash(content)
    try:
        conn.execute("""
            INSERT OR IGNORE INTO documents
            (source_id, source_type, title, document_type, payer_code, source_url,
             content_text, indication_text, coding_text, cpt_codes, icd10_codes,
             hcpcs_codes, specialties, confidence_score, effective_date, content_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            doc.get("source_id","UNKNOWN"),
            doc.get("source_type","lcd"),
            doc.get("title","Untitled"),
            doc.get("document_type","prior_auth_criteria"),
            doc.get("payer_code","CMS"),
            doc.get("source_url",""),
            content,
            doc.get("indication_text",""),
            doc.get("coding_text",""),
            json.dumps(doc.get("cpt_codes") or []),
            json.dumps(doc.get("icd10_codes") or []),
            json.dumps(doc.get("hcpcs_codes") or []),
            json.dumps(doc.get("specialties") or []),
            doc.get("confidence_score", 0.85),
            doc.get("effective_date","2024-01-01"),
            h,
        ))
        return conn.total_changes > 0
    except sqlite3.Error as e:
        logger.warning(f"Insert error for {doc.get('source_id')}: {e}")
        return False


def insert_hipaa(conn: sqlite3.Connection, doc: dict) -> bool:
    content = doc.get("content_text") or ""
    h = compute_hash(content)
    try:
        conn.execute("""
            INSERT OR IGNORE INTO hipaa_corpus
            (source_id, title, section, category, content_text, summary_text, effective_date, content_hash)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            doc.get("source_id","HIPAA-UNKNOWN"),
            doc.get("title","HIPAA Document"),
            doc.get("section",""),
            doc.get("category","general"),
            content,
            doc.get("summary_text",""),
            doc.get("effective_date","2024-01-01"),
            h,
        ))
        return conn.total_changes > 0
    except sqlite3.Error as e:
        logger.warning(f"HIPAA insert error: {e}")
        return False


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Rebuild both FTS indexes from scratch."""
    logger.info("Rebuilding FTS indexes...")
    try:
        conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")
        logger.info("documents_fts rebuilt")
    except sqlite3.Error as e:
        logger.warning(f"documents_fts rebuild error: {e}")
    try:
        conn.execute("INSERT INTO hipaa_fts(hipaa_fts) VALUES('rebuild')")
        logger.info("hipaa_fts rebuilt")
    except sqlite3.Error as e:
        logger.warning(f"hipaa_fts rebuild error (may not exist yet): {e}")
    conn.commit()


def ensure_fts_populated(conn: sqlite3.Connection) -> None:
    """Backfill FTS index if it has fewer rows than the documents table."""
    try:
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        fts_count = conn.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
        if fts_count < doc_count:
            logger.info(f"FTS index behind ({fts_count} vs {doc_count} docs) — rebuilding")
            rebuild_fts(conn)
    except sqlite3.Error as e:
        logger.warning(f"FTS check failed: {e}")


# ── CMS API scraper ───────────────────────────────────────────
CMS_API_BASE = "https://api.coverage-advisor.cms.gov/api/v1"

def _cms_api_fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "CodeMedGroup/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def scrape_cms_api(conn: sqlite3.Connection, doc_type: str = "lcd", max_pages: int = 100) -> int:
    """
    Fetch from CMS Coverage Advisor public API.
    Falls back to a curated set of high-value LCDs if the API is unavailable.
    """
    endpoint_map = {"lcd": "/lcd-policies", "ncd": "/ncd-policies"}
    endpoint = endpoint_map.get(doc_type, "/lcd-policies")
    inserted = 0
    page = 1

    logger.info(f"Fetching CMS {doc_type.upper()} policies from Coverage Advisor API...")
    while page <= max_pages:
        url = f"{CMS_API_BASE}{endpoint}?page={page}&size=50"
        try:
            data = _cms_api_fetch(url)
        except Exception as e:
            logger.warning(f"CMS API unavailable (page {page}): {e}")
            logger.info("Falling back to bundled high-value LCD/NCD seed data...")
            inserted += _ingest_bundled_policies(conn, doc_type)
            break

        items = data.get("items") or data.get("results") or data.get("data") or []
        if not items:
            break

        for item in items:
            doc = _parse_cms_api_item(item, doc_type)
            if doc and insert_document(conn, doc):
                inserted += 1

        total_pages = data.get("totalPages") or data.get("total_pages") or 1
        logger.info(f"  Page {page}/{total_pages} — {inserted} inserted so far")
        if page >= total_pages:
            break
        page += 1
        time.sleep(1)  # Rate limit: 1 request/second

    conn.commit()
    logger.info(f"CMS {doc_type.upper()} ingest complete: {inserted} new documents")
    return inserted


def _parse_cms_api_item(item: dict, doc_type: str) -> dict:
    source_id = (item.get("lcdId") or item.get("ncdId") or item.get("id") or
                 item.get("source_id") or "")
    if not source_id:
        return None
    title = item.get("title") or item.get("name") or f"{doc_type.upper()} {source_id}"
    content_parts = []
    for field in ["indicationsAndLimitations","coverageIndications","description",
                  "content","policyText","body"]:
        val = item.get(field)
        if val and isinstance(val, str):
            content_parts.append(val)
            break
    content_text = "\n\n".join(content_parts) or title

    icd10_codes = []
    for code_item in (item.get("icdCodes") or item.get("icd10Codes") or []):
        if isinstance(code_item, dict):
            icd10_codes.append(code_item.get("code",""))
        elif isinstance(code_item, str):
            icd10_codes.append(code_item)

    cpt_codes = []
    for code_item in (item.get("cptCodes") or item.get("cpt") or []):
        if isinstance(code_item, dict):
            cpt_codes.append(code_item.get("code",""))
        elif isinstance(code_item, str):
            cpt_codes.append(code_item)

    return {
        "source_id": source_id,
        "source_type": doc_type,
        "title": title,
        "document_type": doc_type,
        "payer_code": "CMS",
        "source_url": item.get("url") or item.get("sourceUrl") or "",
        "content_text": content_text,
        "indication_text": item.get("indications") or item.get("coveredIndications") or "",
        "coding_text": item.get("codingGuidance") or "",
        "icd10_codes": [c for c in icd10_codes if c],
        "cpt_codes": [c for c in cpt_codes if c],
        "hcpcs_codes": [],
        "specialties": [],
        "confidence_score": 0.90,
        "effective_date": (item.get("revisionEffectiveDate") or
                           item.get("effectiveDate") or "2024-01-01")[:10],
    }


def _ingest_bundled_policies(conn: sqlite3.Connection, doc_type: str) -> int:
    """
    Insert a curated set of additional high-value CMS policies when the live API
    is unavailable. These represent the most-queried LCD/NCD categories.
    """
    BUNDLED = [
        {
            "source_id": "L37523", "source_type": "lcd", "document_type": "lcd",
            "title": "Spinal Cord Stimulation (Dorsal Column Stimulation) (L37523)",
            "payer_code": "CMS",
            "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L37523",
            "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Covered Indications:
Spinal cord stimulation (SCS) is covered for:
1. Failed Back Surgery Syndrome (FBSS) with chronic intractable pain of the trunk and/or limbs
2. Complex Regional Pain Syndrome (CRPS) Type I and II
3. Intractable low back and leg pain where conservative treatment has failed (≥6 months)
4. Peripheral neuropathy with intractable pain

Required Documentation:
- Failure of conservative treatment: physical therapy, medications (opioids, non-opioids, adjuvants), injections
- Psychological evaluation clearance
- Absence of untreated drug habituation
- No surgical contraindications

Trial Period Required:
- Minimum 3-7 day trial stimulation demonstrating ≥50% pain reduction before permanent implant
- Trial response must be documented by treating physician

ICD-10 Codes:
M54.50 - Low back pain, unspecified
M54.41 - Lumbago with sciatica, right
M54.42 - Lumbago with sciatica, left
G89.29 - Other chronic pain
G90.521 - Complex regional pain syndrome I, right upper limb
G90.522 - Complex regional pain syndrome I, left upper limb
M47.816 - Spondylosis with radiculopathy, lumbar region

CPT Codes:
63650 - Percutaneous implantation of neurostimulator electrode
63655 - Laminectomy for implantation of neurostimulator electrodes, plate/paddle
63685 - Insertion of spinal neurostimulator pulse generator
63688 - Revision/removal of implanted spinal neurostimulator pulse generator""",
            "indication_text": "Failed back surgery syndrome, CRPS, intractable low back/leg pain, 6+ months conservative treatment failure",
            "coding_text": "CPT 63650-63688; ICD-10 M54.x, G89.29, G90.5xx",
            "cpt_codes": ["63650","63655","63661","63663","63685","63688"],
            "icd10_codes": ["M54.50","M54.41","M54.42","G89.29","G90.521","G90.522","M47.816"],
            "specialties": ["pain_management","neurosurgery"],
            "confidence_score": 0.94, "effective_date": "2024-01-01",
        },
        {
            "source_id": "L34102", "source_type": "lcd", "document_type": "lcd",
            "title": "Infusion Pump — External (L34102)",
            "payer_code": "CMS",
            "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L34102",
            "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

External Infusion Pump Coverage:
An external infusion pump is covered when used to administer:
1. Chemotherapy for cancer (antineoplastic drugs)
2. Morphine for intractable cancer pain or AIDS pain
3. Dobutamine for congestive heart failure
4. Tocolysis for premature labor (non-Medicare typically)
5. Continuous subcutaneous insulin infusion (see NCD 280.14)

Documentation Requirements:
- Physician certification of medical necessity
- Drug being administered must be FDA-approved for the indication
- Patient must be unable to self-administer via other means

HCPCS Codes:
E0781 - Ambulatory infusion pump, single or multiple channels, electric or battery operated
A9274 - External ambulatory insulin delivery system
B9004 - Insulin used with external infusion pump
B9006 - Insulin used with insulin infusion pump

ICD-10 Codes:
C34.10 - Malignant neoplasm lung
Z51.11 - Antineoplastic chemotherapy
I50.22 - Chronic systolic heart failure
E10.9  - Type 1 diabetes""",
            "indication_text": "Chemotherapy delivery, intractable pain, CHF dobutamine, insulin infusion",
            "coding_text": "HCPCS E0781, A9274, B9004, B9006; ICD-10 C-codes, Z51.11, I50.22",
            "cpt_codes": [],
            "icd10_codes": ["C34.10","Z51.11","I50.22","E10.9"],
            "hcpcs_codes": ["E0781","A9274","B9004","B9006"],
            "specialties": ["oncology","endocrinology","cardiology"],
            "confidence_score": 0.92, "effective_date": "2024-01-01",
        },
        {
            "source_id": "L33393", "source_type": "lcd", "document_type": "lcd",
            "title": "Mammography (L33393)",
            "payer_code": "CMS",
            "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L33393",
            "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Screening Mammography (G0202):
Covered annually for women age 40 and over. For women 35-39: one baseline screening covered.

Diagnostic Mammography (77065, 77066, 77067):
Covered when:
1. New lump or breast symptom (pain, skin changes, nipple discharge)
2. Follow-up of abnormal screening mammogram (BI-RADS 0, 3, 4, 5)
3. Personal history of breast cancer (surveillance)
4. High-risk patients: BRCA1/2 mutation, first-degree relative with BRCA
5. Post-surgical evaluation of breast tissue

3D Mammography (Tomosynthesis):
Covered with G0279 when performed in conjunction with standard mammography.

Limitations:
- Screening mammography limited to one per year (every 11 months)
- Baseline mammogram (35-39) limited to once per lifetime

ICD-10/HCPCS Codes:
Z12.31 - Encounter for screening mammogram
N63.10 - Unspecified lump in unspecified breast
Z80.3  - Family history of malignant neoplasm of breast
Z85.3  - Personal history of malignant neoplasm of breast
C50.911 - Malignant neoplasm, breast unspecified

CPT/HCPCS Codes:
G0202 - Screening mammography (Medicare)
77065 - Diagnostic mammography, unilateral
77066 - Diagnostic mammography, bilateral
G0279 - Tomosynthesis (3D mammography)""",
            "indication_text": "Breast cancer screening age 40+, breast symptoms, abnormal screening follow-up, high-risk patients",
            "coding_text": "HCPCS G0202, G0279; CPT 77065-77067; ICD-10 Z12.31, N63.x, Z80.3",
            "cpt_codes": ["77065","77066","77067"],
            "icd10_codes": ["Z12.31","N63.10","Z80.3","Z85.3","C50.911"],
            "hcpcs_codes": ["G0202","G0279"],
            "specialties": ["radiology","oncology"],
            "confidence_score": 0.96, "effective_date": "2024-01-01",
        },
        {
            "source_id": "L35396", "source_type": "lcd", "document_type": "lcd",
            "title": "Cardiac Catheterization (L35396)",
            "payer_code": "CMS",
            "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L35396",
            "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Left Heart Catheterization — Covered For:
1. Known or suspected coronary artery disease with symptoms or positive stress test
2. Unstable angina or acute coronary syndrome
3. Pre-operative evaluation for valvular or congenital heart disease
4. Evaluation of aortic stenosis severity (pre-TAVR or pre-surgical)
5. Heart failure with unknown etiology

Right Heart Catheterization — Covered For:
1. Pulmonary arterial hypertension evaluation
2. Management of complex heart failure (hemodynamic assessment)
3. Pre-transplant evaluation

Required Documentation:
- Clinical indication with symptoms or objective evidence
- Prior non-invasive testing results (stress test, echo, nuclear imaging)
- Physician order with specific indication

ICD-10 Codes:
I25.10 - Atherosclerotic heart disease, unspecified vessel
I20.9  - Angina pectoris, unspecified
I21.9  - Acute MI, unspecified
I35.0  - Nonrheumatic aortic stenosis
I27.0  - Primary pulmonary hypertension
I50.22 - Chronic systolic heart failure
I50.32 - Chronic diastolic heart failure

CPT Codes:
93451 - Right heart catheterization
93452 - Left heart catheterization
93453 - Combined right and left heart catheterization
93454 - Coronary angiography, without left heart cath
93455 - Coronary angiography with right heart cath
93458 - Left heart cath with coronary angiography
93459 - Left heart cath, coronary angio, bypass graft angio""",
            "indication_text": "CAD evaluation, ACS, valvular disease pre-op, heart failure workup, pulmonary hypertension",
            "coding_text": "CPT 93451-93461; ICD-10 I25.x, I20.x, I35.0, I27.0, I50.x",
            "cpt_codes": ["93451","93452","93453","93454","93455","93456","93457","93458","93459","93460","93461"],
            "icd10_codes": ["I25.10","I20.9","I21.9","I35.0","I27.0","I50.22","I50.32"],
            "specialties": ["cardiology","interventional_cardiology"],
            "confidence_score": 0.95, "effective_date": "2024-01-01",
        },
        {
            "source_id": "L35049", "source_type": "lcd", "document_type": "lcd",
            "title": "Bone Density Studies (DEXA) (L35049)",
            "payer_code": "CMS",
            "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L35049",
            "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

DEXA (DXA) Bone Density Studies — Covered For:
1. Women age 65+ (Medicare benefit — every 24 months)
2. Postmenopausal women under 65 with osteoporosis risk factors
3. Men age 70+ or men with osteoporosis risk factors
4. Patients on long-term glucocorticoid therapy (≥3 months prednisone equivalent ≥5mg/day)
5. Patients with radiographic osteopenia
6. Monitoring response to osteoporosis therapy (every 24 months)
7. Hyperparathyroidism

Documentation Requirements:
- Clinical indication matching covered criteria
- For monitoring: prior DEXA result and current treatment

Limitations:
- Limited to once every 24 months (Medicare)
- Peripheral DEXA (pDXA) of wrist/heel: covered only when central DEXA not available

ICD-10 Codes:
M81.0  - Age-related osteoporosis without pathological fracture
M81.8  - Other osteoporosis without pathological fracture
Z79.52 - Long-term use of systemic steroids
Z87.310 - Personal history of osteoporosis
E21.0  - Primary hyperparathyroidism

CPT/HCPCS Codes:
77080 - DXA bone density, axial skeleton (hip/spine)
77081 - DXA bone density, appendicular skeleton
G0130 - Single energy x-ray absorptiometry (SEXA)""",
            "indication_text": "Osteoporosis screening women 65+, steroid therapy, osteopenia on x-ray, hyperparathyroidism",
            "coding_text": "CPT 77080-77082; ICD-10 M81.x, Z79.52, E21.0",
            "cpt_codes": ["77080","77081","77082"],
            "icd10_codes": ["M81.0","M81.8","Z79.52","Z87.310","E21.0"],
            "hcpcs_codes": ["G0130"],
            "specialties": ["endocrinology","rheumatology","radiology"],
            "confidence_score": 0.95, "effective_date": "2024-01-01",
        },
        {
            "source_id": "NCD50.1", "source_type": "ncd", "document_type": "ncd",
            "title": "Intravenous Immune Globulin (IVIG) in the Home (NCD 50.1)",
            "payer_code": "CMS",
            "source_url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=98",
            "content_text": """National Coverage Determination — Home IVIG

Coverage:
Home IVIG is covered under Medicare Part B for:
1. Primary immune deficiency disease (PIDD) — documented IgG level < 400 mg/dL
   - Common variable immunodeficiency (CVID)
   - X-linked agammaglobulinemia
   - Severe combined immunodeficiency
   - Wiskott-Aldrich syndrome
2. ONLY when the patient has a diagnosis of primary immune deficiency disease

NOT Covered:
- Secondary immunodeficiencies (HIV, chemotherapy-related)
- Autoimmune conditions (CIDP, ITP, myasthenia gravis) — covered under other NCDs
- Hypogammaglobulinemia not meeting primary deficiency criteria

Documentation Requirements:
- Laboratory evidence of IgG deficiency (< 400 mg/dL)
- Diagnosis of primary immune deficiency
- Physician order with medical necessity statement
- Patient unable to receive in physician office or outpatient setting

ICD-10 Codes:
D83.9 - Common variable immunodeficiency, unspecified
D80.0 - Hereditary hypogammaglobulinemia
D80.1 - Nonfamilial hypogammaglobulinemia
D81.9 - Combined immunodeficiency, unspecified
D82.0 - Wiskott-Aldrich syndrome

HCPCS Codes:
J1459 - Injection, immune globulin, intravenous, non-lyophilized, 500 mg
J1560 - Injection, immune globulin, subcutaneous, 100 mg
S9359 - Home IV IVIG infusion therapy""",
            "indication_text": "Primary immune deficiency disease, IgG < 400 mg/dL, CVID, agammaglobulinemia",
            "coding_text": "HCPCS J1459, J1560; ICD-10 D83.9, D80.x, D81.9, D82.0",
            "cpt_codes": [],
            "icd10_codes": ["D83.9","D80.0","D80.1","D81.9","D82.0"],
            "hcpcs_codes": ["J1459","J1560","S9359"],
            "specialties": ["immunology","allergy"],
            "confidence_score": 0.95, "effective_date": "2024-01-01",
        },
    ]
    inserted = 0
    for policy in BUNDLED:
        if insert_document(conn, policy):
            inserted += 1
    return inserted


# ── JSON importer ─────────────────────────────────────────────

def ingest_cms_json(conn: sqlite3.Connection, filepath: str) -> int:
    inserted = 0
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else (data.get("items") or data.get("results") or [data])
    for item in items:
        doc_type = "ncd" if (item.get("ncdId") or "ncd" in str(item.get("id","")).lower()) else "lcd"
        doc = _parse_cms_api_item(item, doc_type)
        if doc and insert_document(conn, doc):
            inserted += 1
    conn.commit()
    logger.info(f"JSON ingest: {inserted} new documents from {filepath}")
    return inserted


# ── CSV importer ──────────────────────────────────────────────

def ingest_cms_csv(conn: sqlite3.Connection, filepath: str) -> int:
    inserted = 0
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Auto-detect LCD vs NCD
            doc_type = "ncd" if any(k for k in row if "ncd" in k.lower()) else "lcd"
            source_id = (row.get("LCD ID") or row.get("NCD ID") or row.get("id") or
                         row.get("source_id") or row.get("PolicyID",""))
            if not source_id:
                continue
            title = row.get("Title") or row.get("PolicyName") or row.get("title","")
            content = (row.get("Content") or row.get("PolicyText") or
                       row.get("IndicationsAndLimitations") or row.get("content",""))
            if not content:
                content = title
            icd_raw = row.get("ICD10Codes") or row.get("DiagnosisCodes") or ""
            cpt_raw = row.get("CPTCodes") or row.get("ProcedureCodes") or ""
            icd_codes = [c.strip() for c in re.split(r"[;,|]", icd_raw) if c.strip()] if icd_raw else []
            cpt_codes = [c.strip() for c in re.split(r"[;,|]", cpt_raw) if c.strip()] if cpt_raw else []
            doc = {
                "source_id": source_id,
                "source_type": doc_type,
                "title": title,
                "document_type": doc_type,
                "payer_code": row.get("Payer","CMS").upper(),
                "source_url": row.get("URL") or row.get("SourceURL",""),
                "content_text": content,
                "indication_text": row.get("Indications",""),
                "coding_text": row.get("CodingGuidance",""),
                "icd10_codes": icd_codes,
                "cpt_codes": cpt_codes,
                "hcpcs_codes": [],
                "specialties": [],
                "confidence_score": float(row.get("confidence_score",0.85)),
                "effective_date": row.get("EffectiveDate","2024-01-01"),
            }
            if insert_document(conn, doc):
                inserted += 1
    conn.commit()
    logger.info(f"CSV ingest: {inserted} new documents from {filepath}")
    return inserted


# ── XML importer ──────────────────────────────────────────────

def ingest_cms_xml(conn: sqlite3.Connection, filepath: str) -> int:
    inserted = 0
    tree = ET.parse(filepath)
    root = tree.getroot()
    # Strip namespace if present
    ns_pattern = re.compile(r'\{[^}]+\}')

    def tag(el):
        return ns_pattern.sub('', el.tag).lower()

    def find_text(el, *tags):
        for t in tags:
            child = el.find(".//" + t)
            if child is not None and child.text:
                return child.text.strip()
        return ""

    policies = [root] if tag(root) not in ("policies","lcds","ncds","root") else list(root)
    for policy in policies:
        source_id = (find_text(policy,"lcdId","ncdId","id","sourceId") or
                     policy.get("id",""))
        if not source_id:
            continue
        doc_type = "ncd" if "ncd" in tag(policy) else "lcd"
        content_parts = []
        for field in ("indicationsAndLimitations","coverageText","content","description","body"):
            val = find_text(policy, field)
            if val:
                content_parts.append(val)
                break
        icd_codes = [el.text.strip() for el in policy.findall(".//icdCode")
                     if el.text and el.text.strip()]
        cpt_codes = [el.text.strip() for el in policy.findall(".//cptCode")
                     if el.text and el.text.strip()]
        doc = {
            "source_id": source_id,
            "source_type": doc_type,
            "title": find_text(policy,"title","name","policyTitle"),
            "document_type": doc_type,
            "payer_code": "CMS",
            "source_url": find_text(policy,"url","sourceUrl"),
            "content_text": "\n\n".join(content_parts) or find_text(policy,"title"),
            "indication_text": find_text(policy,"indications","coveredIndications"),
            "coding_text": find_text(policy,"codingGuidance","codes"),
            "icd10_codes": icd_codes,
            "cpt_codes": cpt_codes,
            "hcpcs_codes": [],
            "specialties": [],
            "confidence_score": 0.88,
            "effective_date": find_text(policy,"effectiveDate","revisionDate") or "2024-01-01",
        }
        if insert_document(conn, doc):
            inserted += 1
    conn.commit()
    logger.info(f"XML ingest: {inserted} new documents from {filepath}")
    return inserted


# ── Payer policy importer ─────────────────────────────────────

def ingest_payer_policy_file(conn: sqlite3.Connection, filepath: str,
                              payer_code: str, document_type: str = "payer_policy") -> int:
    path = Path(filepath)
    inserted = 0
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        content = path.read_text(encoding="utf-8", errors="replace")
        # Use first non-empty line as title
        title = next((l.strip().lstrip("#").strip() for l in content.splitlines() if l.strip()), path.stem)
        source_id = f"{payer_code}-{path.stem[:40]}"
        doc = {
            "source_id": source_id, "source_type": "payer_policy",
            "title": title, "document_type": document_type,
            "payer_code": payer_code.upper(),
            "content_text": content,
            "confidence_score": 0.82, "effective_date": "2024-01-01",
        }
        if insert_document(conn, doc):
            inserted += 1

    elif suffix == ".json":
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else [data]
        for item in items:
            item.setdefault("payer_code", payer_code.upper())
            item.setdefault("document_type", document_type)
            item.setdefault("source_type", "payer_policy")
            if insert_document(conn, item):
                inserted += 1

    elif suffix == ".csv":
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_id = row.get("source_id") or row.get("PolicyID") or row.get("id","")
                if not source_id:
                    continue
                doc = {
                    "source_id": source_id,
                    "source_type": "payer_policy",
                    "title": row.get("title") or row.get("Title",""),
                    "document_type": document_type,
                    "payer_code": payer_code.upper(),
                    "content_text": row.get("content") or row.get("Content",""),
                    "indication_text": row.get("indication_text",""),
                    "coding_text": row.get("coding_text",""),
                    "icd10_codes": [c.strip() for c in str(row.get("icd10_codes","")).split(",") if c.strip()],
                    "cpt_codes": [c.strip() for c in str(row.get("cpt_codes","")).split(",") if c.strip()],
                    "confidence_score": 0.82, "effective_date": "2024-01-01",
                }
                if insert_document(conn, doc):
                    inserted += 1

    conn.commit()
    logger.info(f"Payer policy ingest ({payer_code}): {inserted} new documents from {filepath}")
    return inserted


# ── HIPAA document importer ───────────────────────────────────

HIPAA_SEED = [
    {
        "source_id": "HIPAA-PRIVACY-164.502",
        "title": "HIPAA Privacy Rule — Uses and Disclosures of PHI (45 CFR §164.502)",
        "section": "45 CFR §164.502",
        "category": "privacy_rule",
        "effective_date": "2013-03-26",
        "summary_text": "Covered entities may use or disclose PHI only as permitted or required by the Privacy Rule. Permitted uses include treatment, payment, and healthcare operations (TPO) without patient authorization.",
        "content_text": """45 CFR §164.502 — Uses and Disclosures of Protected Health Information

General Rules:
A covered entity may not use or disclose PHI except as permitted or required by this subpart.

Permitted Without Authorization (TPO):
1. Treatment: providing, coordinating, or managing health care
2. Payment: obtaining reimbursement, determining coverage, billing and collections
3. Healthcare Operations: quality assessment, competency assurance, business management

Minimum Necessary Standard:
- When using or disclosing PHI, make reasonable efforts to use/disclose only the minimum necessary
- Does not apply to disclosures to the individual, for treatment, pursuant to an authorization, or required by law

De-identification:
PHI is de-identified (and not subject to the Privacy Rule) when either:
- Expert Determination Method: qualified statistical/scientific expert certifies very small risk of identification
- Safe Harbor Method: 18 specific identifiers removed (name, address, dates except year, phone, fax, email, SSN, MRN, health plan numbers, account numbers, certificate/license numbers, URLs, IP addresses, device identifiers, biometric identifiers, full-face photos, any unique code)

Business Associate Agreements (BAA):
Required when disclosing PHI to business associates. BAA must specify:
- Permitted uses/disclosures of PHI
- Safeguards required
- Reporting of breaches and violations
- Return or destruction of PHI at contract termination""",
    },
    {
        "source_id": "HIPAA-SECURITY-164.312",
        "title": "HIPAA Security Rule — Technical Safeguards (45 CFR §164.312)",
        "section": "45 CFR §164.312",
        "category": "security_rule",
        "effective_date": "2013-03-26",
        "summary_text": "Covered entities must implement technical policies and procedures to allow access only to authorized persons and software programs. Includes access controls, audit controls, integrity controls, and transmission security.",
        "content_text": """45 CFR §164.312 — Technical Safeguards

Access Controls (Required):
- Unique user identification: assign each user a unique ID for tracking
- Emergency access procedure: obtain necessary ePHI during emergency
- Automatic logoff: addressable — terminate session after inactivity
- Encryption and decryption: addressable — mechanism to encrypt/decrypt ePHI

Audit Controls (Required):
- Hardware, software, and procedural mechanisms to record/examine activity in systems containing ePHI

Integrity Controls:
- Authenticate ePHI: addressable — corroborate that ePHI has not been altered or destroyed improperly
- Electronic mechanisms to confirm ePHI not altered or destroyed without authorization

Person/Entity Authentication (Required):
- Verify that persons/entities seeking access to ePHI are who they claim to be

Transmission Security (Required):
- Guard against unauthorized access to ePHI transmitted over electronic communications networks
- Encryption: addressable — encrypt ePHI when deemed appropriate

Risk Analysis (Required under §164.308):
- Conduct accurate and thorough assessment of potential risks to ePHI confidentiality, integrity, availability
- Implement security measures to reduce risks to a reasonable and appropriate level""",
    },
    {
        "source_id": "HIPAA-BREACH-164.400",
        "title": "HIPAA Breach Notification Rule (45 CFR §164.400–414)",
        "section": "45 CFR §164.400-414",
        "category": "breach_notification",
        "effective_date": "2013-03-26",
        "summary_text": "Covered entities must notify affected individuals, HHS, and sometimes media of breaches of unsecured PHI. 60-day notification deadline for individuals; HHS notification varies by breach size.",
        "content_text": """45 CFR §164.400-414 — Breach Notification Rule

Definition of Breach:
Impermissible acquisition, access, use, or disclosure of PHI that compromises security or privacy of PHI.

Exceptions to Breach Definition:
1. Unintentional acquisition by workforce member acting in good faith within scope
2. Inadvertent disclosure between authorized persons at covered entity
3. Unauthorized disclosure where covered entity believes unauthorized person could not retain PHI

Presumption:
Every impermissible use/disclosure is presumed a breach UNLESS low probability PHI was compromised (4-factor risk assessment):
1. Nature and extent of PHI involved (identifiers, sensitivity)
2. Who used/received PHI
3. Was PHI actually acquired/viewed
4. Extent to which risk has been mitigated

Notification Deadlines:
- To individuals: without unreasonable delay, no later than 60 calendar days after discovery
- To HHS (large breach ≥500 individuals): same 60-day timeline
- To HHS (small breach <500 individuals): annual log submitted by 60 days after end of calendar year
- To media (breaches ≥500 in state/jurisdiction): same 60-day timeline

Content of Notification:
- Description of what happened (approximate date of breach)
- Types of PHI involved
- Steps individuals should take to protect themselves
- Description of covered entity investigation and mitigation steps
- Contact information

Business Associate Obligations:
Must notify covered entity without unreasonable delay and within 60 days of discovering a breach.""",
    },
    {
        "source_id": "HIPAA-MINIMUM-NECESSARY",
        "title": "HIPAA Minimum Necessary Standard — Billing and Prior Authorization",
        "section": "45 CFR §164.514(d)",
        "category": "privacy_rule",
        "effective_date": "2013-03-26",
        "summary_text": "For billing and prior authorization, only the PHI required to obtain reimbursement or authorization may be disclosed. Clinical notes beyond what the payer requires are NOT minimum necessary.",
        "content_text": """Minimum Necessary Standard — Application to Revenue Cycle Management

For Payment Purposes (including Prior Authorization):
- Covered entities must limit PHI disclosed to what is reasonably necessary for payment
- Diagnosis codes (ICD-10), procedure codes (CPT/HCPCS), dates of service, provider NPI, and plan member ID are generally minimum necessary for claims submission
- Full clinical notes, psychotherapy notes, and sensitive PHI categories should NOT be submitted unless specifically required by the payer

Prior Authorization Submissions:
- Submit only the clinical documentation the payer specifies in their criteria
- Do not include full medical records if treatment notes summary suffices
- Psychotherapy notes require separate, specific authorization (§164.508)
- HIV/AIDS, substance use disorder (42 CFR Part 2), and reproductive health records require heightened protections

Sensitive PHI Categories Requiring Extra Protection:
1. Mental health/behavioral health records
2. HIV/AIDS status
3. Substance use disorder records (42 CFR Part 2 applies independently)
4. Reproductive health (state laws may be stricter post-Dobbs)
5. Genetic information (GINA applies separately)

Business Associate Agreements for Clearinghouses:
- Billing clearinghouses (Availity, Change Healthcare, Waystar) must have BAA
- Include minimum necessary provisions in the BAA
- Clearinghouse breach reporting obligations flow back to covered entity

Workforce Training Requirements:
- All staff with access to PHI must be trained on minimum necessary
- Training documentation required
- Sanctions policy required for violations""",
    },
]


def ingest_hipaa_document(conn: sqlite3.Connection, filepath: str) -> int:
    path = Path(filepath)
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    title = next((l.strip().lstrip("#").strip() for l in lines if l.strip()), path.stem)
    source_id = f"HIPAA-{path.stem[:40].upper().replace(' ','-')}"
    doc = {
        "source_id": source_id,
        "title": title,
        "section": "",
        "category": "general",
        "content_text": content,
        "summary_text": content[:500],
        "effective_date": "2024-01-01",
    }
    inserted = 1 if insert_hipaa(conn, doc) else 0
    conn.commit()
    logger.info(f"HIPAA doc ingest: {inserted} new document from {filepath}")
    return inserted


def _ingest_hipaa_seed(conn: sqlite3.Connection) -> int:
    inserted = 0
    for doc in HIPAA_SEED:
        if insert_hipaa(conn, doc):
            inserted += 1
    conn.commit()
    logger.info(f"HIPAA seed ingest: {inserted} new documents")
    return inserted


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CodeMed Group Data Ingestion Pipeline")
    parser.add_argument("--type", required=True,
                        choices=["cms-api","json","csv","xml","payer","hipaa","rebuild-fts","seed-hipaa"],
                        help="Ingest type")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to nexusauth.db")
    parser.add_argument("--file", help="Input file path (for json/csv/xml/payer/hipaa)")
    parser.add_argument("--payer", default="CMS", help="Payer code (for payer type)")
    parser.add_argument("--doc-type", default="lcd", choices=["lcd","ncd"],
                        help="Document type for cms-api fetch")
    parser.add_argument("--max-pages", type=int, default=100,
                        help="Max pages to fetch from CMS API")
    args = parser.parse_args()

    conn = connect_db(args.db)
    total = 0

    if args.type == "cms-api":
        total += scrape_cms_api(conn, args.doc_type, args.max_pages)
    elif args.type == "json":
        if not args.file: parser.error("--file required for json type")
        total += ingest_cms_json(conn, args.file)
    elif args.type == "csv":
        if not args.file: parser.error("--file required for csv type")
        total += ingest_cms_csv(conn, args.file)
    elif args.type == "xml":
        if not args.file: parser.error("--file required for xml type")
        total += ingest_cms_xml(conn, args.file)
    elif args.type == "payer":
        if not args.file: parser.error("--file required for payer type")
        total += ingest_payer_policy_file(conn, args.file, args.payer)
    elif args.type == "hipaa":
        if args.file:
            total += ingest_hipaa_document(conn, args.file)
        else:
            total += _ingest_hipaa_seed(conn)
    elif args.type == "seed-hipaa":
        total += _ingest_hipaa_seed(conn)
    elif args.type == "rebuild-fts":
        rebuild_fts(conn)
        print("FTS indexes rebuilt successfully.")
        conn.close()
        return

    ensure_fts_populated(conn)
    doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    hipaa_count = conn.execute("SELECT COUNT(*) FROM hipaa_corpus").fetchone()[0]
    conn.close()

    print(f"\n✅ Ingest complete: {total} new documents inserted")
    print(f"   Total documents: {doc_count}")
    print(f"   HIPAA corpus: {hipaa_count}")


if __name__ == "__main__":
    main()
