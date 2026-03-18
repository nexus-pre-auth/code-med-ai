"""
CodeMed Group — Database Builder
Run once: python data/build_seed_db.py
Builds nexusauth.db with schema + seeded CMS LCD/NCD data + V28 codes
"""
import sys, sqlite3, json, hashlib, secrets
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

DB_PATH = Path(__file__).parent / "nexusauth.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id        TEXT NOT NULL,
    source_type      TEXT NOT NULL DEFAULT 'lcd',
    title            TEXT NOT NULL,
    document_type    TEXT NOT NULL DEFAULT 'prior_auth_criteria',
    payer_code       TEXT DEFAULT 'CMS',
    source_url       TEXT,
    content_text     TEXT,
    indication_text  TEXT,
    coding_text      TEXT,
    evidence_text    TEXT,
    cpt_codes        TEXT DEFAULT '[]',
    icd10_codes      TEXT DEFAULT '[]',
    hcpcs_codes      TEXT DEFAULT '[]',
    specialties      TEXT DEFAULT '[]',
    routing_targets  TEXT DEFAULT '["NexusAuth"]',
    confidence_score REAL DEFAULT 0.85,
    effective_date   TEXT,
    status           TEXT DEFAULT 'active',
    content_hash     TEXT UNIQUE,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v28_hcc_codes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    icd10_code         TEXT NOT NULL UNIQUE,
    description        TEXT,
    v28_hcc            TEXT,
    v24_hcc            TEXT,
    v28_pays           INTEGER DEFAULT 0,
    v24_pays           INTEGER DEFAULT 0,
    hcc_label          TEXT,
    payment_tier       TEXT DEFAULT 'standard',
    v28_change_note    TEXT,
    clinical_rationale TEXT
);

CREATE TABLE IF NOT EXISTS api_keys (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash      TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    tier          TEXT DEFAULT 'demo',
    active        INTEGER DEFAULT 1,
    monthly_usage INTEGER DEFAULT 0,
    last_used     TEXT,
    notes         TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    action           TEXT NOT NULL,
    resource_type    TEXT,
    user_session     TEXT,
    ip_address       TEXT,
    query_text       TEXT,
    response_time_ms INTEGER,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hipaa_corpus (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    section         TEXT,
    category        TEXT,
    content_text    TEXT,
    summary_text    TEXT,
    effective_date  TEXT,
    content_hash    TEXT UNIQUE,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    source_id UNINDEXED,
    title,
    content_text,
    indication_text,
    coding_text,
    content=documents,
    content_rowid=id,
    tokenize='unicode61 remove_diacritics 2'
);

CREATE VIRTUAL TABLE IF NOT EXISTS hipaa_fts USING fts5(
    source_id UNINDEXED,
    title,
    section,
    content_text,
    summary_text,
    content=hipaa_corpus,
    content_rowid=id,
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, source_id, title, content_text, indication_text, coding_text)
    VALUES (new.id, new.source_id, new.title, new.content_text, new.indication_text, new.coding_text);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, source_id, title, content_text, indication_text, coding_text)
    VALUES ('delete', old.id, old.source_id, old.title, old.content_text, old.indication_text, old.coding_text);
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, source_id, title, content_text, indication_text, coding_text)
    VALUES ('delete', old.id, old.source_id, old.title, old.content_text, old.indication_text, old.coding_text);
    INSERT INTO documents_fts(rowid, source_id, title, content_text, indication_text, coding_text)
    VALUES (new.id, new.source_id, new.title, new.content_text, new.indication_text, new.coding_text);
END;

CREATE TRIGGER IF NOT EXISTS hipaa_ai AFTER INSERT ON hipaa_corpus BEGIN
    INSERT INTO hipaa_fts(rowid, source_id, title, section, content_text, summary_text)
    VALUES (new.id, new.source_id, new.title, new.section, new.content_text, new.summary_text);
END;

-- V28 HCC category reference (115 payment HCCs with metadata)
CREATE TABLE IF NOT EXISTS v28_hcc_categories (
    hcc_number       INTEGER PRIMARY KEY,
    description      TEXT NOT NULL,
    disease_family   TEXT,
    severity         TEXT DEFAULT 'standard',
    raf_weight       REAL DEFAULT 0.0,
    hierarchy_group  TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

-- CMS model configuration: normalization factors, MA coding adjustment, PACE blend
CREATE TABLE IF NOT EXISTS cms_model_config (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    config_year      INTEGER NOT NULL,
    config_key       TEXT NOT NULL,
    config_value     TEXT NOT NULL,
    description      TEXT,
    source           TEXT,
    UNIQUE(config_year, config_key)
);

-- Encounter-eligible CPT/HCPCS codes for V28 encounter filtering
-- Loaded from CMS ZIP: 2026-medicare-advantage-risk-adjustment-eligible-cpt-hcpcs-codes.zip
CREATE TABLE IF NOT EXISTS v28_eligible_cpt (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    code             TEXT NOT NULL UNIQUE,
    code_type        TEXT DEFAULT 'CPT',
    description      TEXT,
    eligible_year    INTEGER DEFAULT 2026
);
"""

DOCUMENTS = [
    {
        "source_id": "L38226", "source_type": "lcd",
        "title": "Cardiac Monitoring — Holter and Mobile Cardiac Telemetry (L38226)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L38226",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Covered Indications:
Ambulatory cardiac monitoring is covered when medically necessary for evaluation of symptoms possibly related to intermittent cardiac arrhythmias including:
1. Palpitations, syncope, near-syncope, dizziness, or unexplained shortness of breath
2. Evaluation of antiarrhythmic drug therapy efficacy
3. Evaluation of pacemaker or ICD function
4. Detection of silent myocardial ischemia in high-risk patients

Limitations:
- Holter monitoring limited to single continuous recording not exceeding 48 hours per episode
- Mobile cardiac telemetry limited to 30 days per episode of care
- Routine screening without documented symptoms is not covered
- Repeat monitoring within 90 days requires documented clinical change

Documentation Requirements:
Medical record must include: clinical indication, symptom history, prior workup results, and treating physician order.

ICD-10-CM Codes that Support Medical Necessity:
R00.0 - Tachycardia, unspecified
R00.1 - Bradycardia, unspecified
R00.8 - Other abnormalities of heart beat
R00.9 - Unspecified abnormalities of heart beat
R55 - Syncope and collapse
I49.9 - Cardiac arrhythmia, unspecified
I48.0 - Paroxysmal atrial fibrillation
I48.11 - Longstanding persistent atrial fibrillation
I48.19 - Other persistent atrial fibrillation
Z95.0 - Presence of cardiac pacemaker""",
        "indication_text": "Palpitations, syncope, near-syncope, arrhythmia evaluation, pacemaker/ICD function",
        "coding_text": "CPT 93224-93229; ICD-10 R00.0, R00.1, R55, I48.x, I49.x",
        "cpt_codes": json.dumps(["93224","93225","93226","93227","93228","93229"]),
        "icd10_codes": json.dumps(["R00.0","R00.1","R00.8","R00.9","R55","I49.9","I48.0","I48.11","I48.19"]),
        "specialties": json.dumps(["cardiology"]),
        "confidence_score": 0.96, "effective_date": "2024-01-01",
    },
    {
        "source_id": "L33797", "source_type": "lcd",
        "title": "MRI of the Spine (L33797)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L33797",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Covered Indications:
MRI of the spine is covered when medically necessary for:
1. Myelopathy or radiculopathy with neurological deficit not resolving after 4-6 weeks conservative treatment
2. Suspected spinal cord compression, tumor, abscess, or infection
3. New neurological deficits following trauma
4. Pre-surgical evaluation for spinal procedures
5. Post-surgical evaluation for complications (e.g., infection, hardware failure)
6. Inflammatory conditions affecting the spine (MS, transverse myelitis)
7. Evaluation of congenital spinal anomalies

Limitations:
- Routine low back pain screening without neurological deficit NOT covered
- Repeat MRI within 3 months requires documented significant clinical change
- Open/upright MRI covered only when standard MRI is contraindicated (claustrophobia, body habitus)
- CT myelogram is an acceptable alternative when MRI is contraindicated

ICD-10-CM Codes:
M54.50 - Low back pain, unspecified
M54.41 - Lumbago with sciatica, right side
M54.42 - Lumbago with sciatica, left side
M50.10 - Cervical disc degeneration, unspecified
M51.16 - Intervertebral disc degeneration, lumbar
G35 - Multiple sclerosis
M47.816 - Spondylosis with radiculopathy, lumbar
M47.812 - Spondylosis with radiculopathy, cervical
S14.109A - Unspecified cervical spinal cord injury""",
        "indication_text": "Myelopathy, radiculopathy with neuro deficit, cord compression, pre-surgical evaluation",
        "coding_text": "CPT 72141-72158; ICD-10 M54.x, M50.x, M51.x, G35, M47.x",
        "cpt_codes": json.dumps(["72141","72142","72146","72147","72148","72149","72156","72157","72158"]),
        "icd10_codes": json.dumps(["M54.50","M54.41","M54.42","M50.10","M51.16","G35","M47.816","M47.812"]),
        "specialties": json.dumps(["radiology","orthopedics","neurology"]),
        "confidence_score": 0.94, "effective_date": "2024-01-01",
    },
    {
        "source_id": "NCD280.14", "source_type": "ncd",
        "title": "Continuous Subcutaneous Insulin Infusion (NCD 280.14)",
        "document_type": "ncd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=57",
        "content_text": """National Coverage Determination — Insulin Infusion Pumps

Coverage:
External insulin infusion pumps and supplies are covered under Medicare Part B when:

Type I Diabetes:
- Patient has Type I (insulin-dependent) diabetes
- Patient has been on intensive insulin therapy (3+ injections/day or pump)
- HbA1c > 7.0% documented within prior 6 months

Type II Diabetes (additional requirements):
- Patient optimally managed on MDI (multiple daily injections) but not achieving glycemic control
- HbA1c > 7.0% despite documented MDI therapy
- Treatment by endocrinologist or physician specializing in diabetes management
- Patient completed comprehensive diabetes self-management training

Documentation Required:
- HbA1c within 6 months prior to initiation
- Detailed history of insulin therapy with poor control
- Physician attestation of medical necessity
- Evidence of diabetes education completion

ICD-10 Codes:
E10.9 - Type 1 diabetes mellitus without complications
E10.65 - Type 1 diabetes with hyperglycemia
E10.649 - Type 1 diabetes with hypoglycemia without coma
E11.9 - Type 2 diabetes mellitus without complications
E11.65 - Type 2 diabetes with hyperglycemia
E11.649 - Type 2 diabetes with hypoglycemia without coma

HCPCS Codes:
E0784 - External ambulatory infusion pump, insulin
A9274 - External ambulatory insulin delivery system, disposable
K0552 - Supplies for external infusion pump, insulin""",
        "indication_text": "Type 1 or Type 2 diabetes with poor glycemic control on MDI, HbA1c > 7.0%",
        "coding_text": "HCPCS E0784, A9274, K0552; ICD-10 E10.x, E11.x",
        "cpt_codes": json.dumps([]),
        "icd10_codes": json.dumps(["E10.9","E10.65","E10.649","E11.9","E11.65","E11.649"]),
        "hcpcs_codes": json.dumps(["E0784","A9274","K0552"]),
        "specialties": json.dumps(["endocrinology"]),
        "confidence_score": 0.97, "effective_date": "2024-01-01",
    },
    {
        "source_id": "L35062", "source_type": "lcd",
        "title": "Electroencephalography (EEG) (L35062)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L35062",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Covered Indications:
EEG is covered for:
1. Initial evaluation of seizure disorder or epilepsy
2. Monitoring of known seizure disorder — treatment response evaluation
3. Evaluation of altered consciousness, coma, or encephalopathy
4. Pre-surgical evaluation for epilepsy surgery candidates
5. Brain death determination
6. Evaluation of specific sleep disorders (when PSG not definitive)
7. Evaluation of dementia or encephalitis

Limitations:
- Routine screening EEG without clinical indication NOT covered
- Repeat EEG for stable, well-controlled epilepsy requires clinical justification
- Ambulatory EEG (95950) covered for capture of suspected seizure events

ICD-10 Codes:
G40.009 - Localization-related epilepsy, not intractable
G40.019 - Localization-related epilepsy, intractable
G40.309 - Generalized epilepsy, not intractable
G40.319 - Generalized epilepsy, intractable
R56.9 - Unspecified convulsions
G93.40 - Encephalopathy, unspecified
R41.3 - Other amnesia
G20 - Parkinson's disease

CPT Codes:
95812 - EEG, 41-60 minutes
95813 - EEG, over 1 hour
95816 - EEG, awake and drowsy
95819 - EEG, awake and asleep
95822 - EEG, sleep only
95950 - Ambulatory EEG""",
        "indication_text": "Seizure disorder, epilepsy evaluation, altered consciousness, encephalopathy, pre-surgical epilepsy workup",
        "coding_text": "CPT 95812-95950; ICD-10 G40.x, R56.9, G93.40",
        "cpt_codes": json.dumps(["95812","95813","95816","95819","95822","95950"]),
        "icd10_codes": json.dumps(["G40.009","G40.019","G40.309","G40.319","R56.9","G93.40","G20"]),
        "specialties": json.dumps(["neurology"]),
        "confidence_score": 0.93, "effective_date": "2024-01-01",
    },
    {
        "source_id": "L34568", "source_type": "lcd",
        "title": "Colonoscopy and Sigmoidoscopy (L34568)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L34568",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Diagnostic Colonoscopy — Covered For:
1. Evaluation of unexplained GI bleeding, iron-deficiency anemia
2. Surveillance in patients with prior colorectal cancer or adenomatous polyps
3. Evaluation of inflammatory bowel disease extent and activity
4. Surveillance in patients with familial adenomatous polyposis (FAP) or Lynch syndrome
5. Evaluation of abnormal findings on barium enema or CT colonography
6. Diarrhea, persistent and unexplained

Screening Colonoscopy:
- High risk: every 2 years (strong family history, prior polyps)
- Average risk (G0105 / G0121): every 10 years age 45+

Limitations:
- Screening interval limitations apply
- Repeat colonoscopy within 3 years requires documentation of medical necessity
- Virtual colonoscopy (CT colonography) not covered as screening by Medicare

ICD-10 Codes:
K92.1 - Melena
K57.30 - Diverticulosis of large intestine
K50.90 - Crohn's disease, unspecified
K51.90 - Ulcerative colitis, unspecified
Z12.11 - Encounter for screening for malignant neoplasm of colon
D12.6 - Benign neoplasm of colon, unspecified

CPT/HCPCS Codes:
45378 - Colonoscopy, diagnostic
45380 - Colonoscopy with biopsy
45385 - Colonoscopy with polypectomy
G0105 - Colorectal cancer screening, high risk individual
G0121 - Colorectal cancer screening, average risk""",
        "indication_text": "GI bleeding, iron deficiency anemia, IBD surveillance, colorectal cancer screening, polyp follow-up",
        "coding_text": "CPT 45378-45385, HCPCS G0105, G0121; ICD-10 K92.1, K57.x, K50.x, K51.x",
        "cpt_codes": json.dumps(["45378","45380","45382","45384","45385","45386"]),
        "icd10_codes": json.dumps(["K92.1","K57.30","K50.90","K51.90","Z12.11","D12.6"]),
        "hcpcs_codes": json.dumps(["G0105","G0121"]),
        "specialties": json.dumps(["gastroenterology"]),
        "confidence_score": 0.95, "effective_date": "2024-01-01",
    },
    {
        "source_id": "L36544", "source_type": "lcd",
        "title": "Chemotherapy Administration — Outpatient (L36544)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L36544",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Covered Services:
Outpatient chemotherapy administration is covered when:
1. Patient has a confirmed malignant neoplasm diagnosis
2. Treatment plan developed by or in consultation with a medical oncologist
3. Chemotherapy agent is FDA-approved or supported by peer-reviewed literature for the specific indication
4. Patient has adequate organ function to tolerate chemotherapy (documented)

Prior Authorization Requirements:
- Written treatment plan required including: diagnosis, drug regimen, dosing, schedule, and expected duration
- Pathology report confirming malignancy
- Performance status documentation (ECOG or Karnofsky)

Limitations:
- Investigational agents covered only under approved clinical trials
- Home infusion covered only for agents with specific home infusion coverage (e.g., oral chemotherapy via Part D)

ICD-10 Codes:
C34.10 - Malignant neoplasm of upper lobe bronchus/lung
C50.911 - Malignant neoplasm of breast, unspecified
C18.9 - Malignant neoplasm of colon, unspecified
C61 - Malignant neoplasm of prostate
C25.9 - Malignant neoplasm of pancreas, unspecified
Z51.11 - Encounter for antineoplastic chemotherapy

CPT Codes:
96413 - Chemotherapy administration, IV infusion, up to 1 hour
96415 - Each additional hour
96409 - Chemotherapy, IV push, single drug
96401 - Chemotherapy, non-hormonal, subcutaneous or intramuscular""",
        "indication_text": "Confirmed malignancy, oncologist-directed treatment, FDA-approved or literature-supported regimen",
        "coding_text": "CPT 96401-96549; ICD-10 C-codes (malignancies), Z51.11",
        "cpt_codes": json.dumps(["96401","96409","96413","96415","96416","96417","96423","96425"]),
        "icd10_codes": json.dumps(["C34.10","C50.911","C18.9","C61","C25.9","Z51.11"]),
        "specialties": json.dumps(["oncology"]),
        "confidence_score": 0.94, "effective_date": "2024-01-01",
    },
    {
        "source_id": "L38394", "source_type": "lcd",
        "title": "Sleep Testing for Obstructive Sleep Apnea (L38394)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L38394",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Polysomnography (PSG) — Covered For:
1. Evaluation of suspected obstructive sleep apnea (OSA) in patients with:
   - Excessive daytime sleepiness (Epworth score ≥ 10)
   - Witnessed apneas by bed partner
   - BMI > 35
   - Large neck circumference (>17 inches men, >16 inches women)
2. Evaluation of CPAP titration in diagnosed OSA patients
3. Evaluation for narcolepsy, REM sleep behavior disorder, parasomnias

Home Sleep Testing (HST):
Covered as alternative to PSG for uncomplicated suspected OSA when:
- No significant comorbid sleep disorder suspected
- No significant comorbid medical conditions that would affect sleep study interpretation

CPAP Coverage (E0601):
Covered after documented AHI ≥ 5 on qualifying sleep study, with:
- AHI 5-14 with symptoms documented
- AHI ≥ 15 regardless of symptoms
- Follow-up visit at 31-91 days confirming compliance and benefit

ICD-10 Codes:
G47.33 - Obstructive sleep apnea, adult
G47.30 - Sleep apnea, unspecified
G47.419 - Narcolepsy without cataplexy
R06.83 - Snoring

CPT/HCPCS Codes:
95800 - Home sleep test, unattended
95801 - Home sleep test, minimal
95808 - Polysomnography, 1-3 stages
95810 - Polysomnography, 4+ stages
95811 - Polysomnography with CPAP
E0601 - CPAP device""",
        "indication_text": "Obstructive sleep apnea evaluation, excessive daytime sleepiness, BMI>35, witnessed apneas",
        "coding_text": "CPT 95800-95811, HCPCS E0601; ICD-10 G47.33, G47.30",
        "cpt_codes": json.dumps(["95800","95801","95808","95810","95811"]),
        "icd10_codes": json.dumps(["G47.33","G47.30","G47.419","R06.83"]),
        "hcpcs_codes": json.dumps(["E0601"]),
        "specialties": json.dumps(["pulmonology","sleep_medicine"]),
        "confidence_score": 0.95, "effective_date": "2024-01-01",
    },
    {
        "source_id": "L35062B", "source_type": "lcd",
        "title": "Joint Replacement — Hip and Knee Arthroplasty (L35062B)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L35062",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Total Hip Arthroplasty (THA) — Covered When:
1. Severe hip pain and functional impairment from osteoarthritis, rheumatoid arthritis, or avascular necrosis
2. Conservative therapy failed (minimum 3 months of: NSAIDs, PT, weight loss if applicable, activity modification)
3. Radiographic evidence of joint space narrowing, osteophytes, or subchondral sclerosis
4. Patient medically cleared for surgery

Total Knee Arthroplasty (TKA) — Covered When:
1. Severe knee pain limiting activities of daily living
2. Documented failure of conservative management (≥ 3 months)
3. Radiographic evidence of significant joint disease
4. Functional impairment documented by physician

Required Documentation:
- X-rays within 12 months showing joint pathology
- Documentation of failed conservative therapies (dates, duration, response)
- Surgical clearance and ASA classification
- Functional assessment (pain scale, ROM measurements)

ICD-10 Codes:
M16.11 - Primary osteoarthritis, right hip
M16.12 - Primary osteoarthritis, left hip
M17.11 - Primary osteoarthritis, right knee
M17.12 - Primary osteoarthritis, left knee
M05.70 - Rheumatoid arthritis with rheumatoid factor
M87.050 - Idiopathic aseptic necrosis of femur

CPT Codes:
27447 - Total knee arthroplasty
27130 - Total hip arthroplasty
27134 - Revision hip arthroplasty""",
        "indication_text": "Severe OA hip/knee, failed conservative therapy 3+ months, radiographic evidence of joint disease",
        "coding_text": "CPT 27130, 27447; ICD-10 M16.x, M17.x, M05.x, M87.x",
        "cpt_codes": json.dumps(["27130","27132","27134","27447","27486","27487"]),
        "icd10_codes": json.dumps(["M16.11","M16.12","M17.11","M17.12","M05.70","M87.050"]),
        "specialties": json.dumps(["orthopedics"]),
        "confidence_score": 0.94, "effective_date": "2024-01-01",
    },
    {
        "source_id": "NCD220.6.17", "source_type": "ncd",
        "title": "Transcatheter Aortic Valve Replacement (TAVR) (NCD 20.32)",
        "document_type": "ncd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=355",
        "content_text": """National Coverage Determination — TAVR

Coverage:
Transcatheter Aortic Valve Replacement (TAVR) is covered under Medicare when performed at a CMS-approved facility for:

Indications:
1. Symptomatic aortic stenosis with AVA < 1.0 cm² or mean gradient > 40 mmHg
2. High or prohibitive surgical risk as determined by heart team (STS score ≥ 8% or prohibitive risk factors)
3. Intermediate surgical risk (STS score 4-8%) — covered with conditions
4. Low surgical risk — covered following 2019 FDA expanded indication

Facility Requirements:
- Hospital must have cardiac surgery program
- Minimum annual TAVR volume requirements per CMS
- Must maintain National Cardiovascular Data Registry (NCDR) participation

Heart Team Requirements:
- Joint decision by cardiac surgeon and interventional cardiologist
- Documented Heart Team meeting notes
- Patient and family education and shared decision making documented

ICD-10 Codes:
I35.0 - Nonrheumatic aortic stenosis
I35.2 - Nonrheumatic aortic stenosis with insufficiency
I06.0 - Rheumatic aortic stenosis

CPT Codes:
33361 - TAVR, transfemoral approach
33362 - TAVR, transapical approach
33363 - TAVR, transaortic approach
33364 - TAVR, transaxillary/subclavian""",
        "indication_text": "Symptomatic aortic stenosis AVA<1.0cm², high/intermediate/low surgical risk, Heart Team evaluation",
        "coding_text": "CPT 33361-33366; ICD-10 I35.0, I35.2, I06.0",
        "cpt_codes": json.dumps(["33361","33362","33363","33364","33365","33366"]),
        "icd10_codes": json.dumps(["I35.0","I35.2","I06.0"]),
        "specialties": json.dumps(["cardiology","cardiac_surgery"]),
        "confidence_score": 0.97, "effective_date": "2024-01-01",
    },
    {
        "source_id": "L34080", "source_type": "lcd",
        "title": "Psychological and Neuropsychological Testing (L34080)",
        "document_type": "lcd", "payer_code": "CMS",
        "source_url": "https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdid=L34080",
        "content_text": """Coverage Indications, Limitations, and/or Medical Necessity

Covered Indications:
Psychological and neuropsychological testing is covered when:
1. Evaluation of cognitive impairment, dementia workup
2. Assessment for psychiatric conditions affecting treatment planning (depression, anxiety, PTSD, psychosis)
3. Evaluation of learning disabilities or developmental delays
4. Pre-surgical psychological evaluation (bariatric surgery, chronic pain procedures, organ transplant)
5. Brain injury rehabilitation planning
6. Differentiation of neurological vs. psychiatric etiology

Limitations:
- Educational testing for school placement NOT covered
- Testing for vocational or employment purposes NOT covered
- Retesting within 12 months requires clinical justification

ICD-10 Codes:
F03.90 - Unspecified dementia without behavioral disturbance
G31.84 - Mild cognitive impairment, so stated
F32.9 - Major depressive disorder, unspecified
F41.9 - Anxiety disorder, unspecified
F43.10 - Post-traumatic stress disorder, unspecified
F90.9 - ADHD, unspecified type
S06.9X9A - Unspecified intracranial injury

CPT Codes:
96130 - Psychological testing evaluation, first hour
96131 - Psychological testing, each additional hour
96132 - Neuropsychological testing evaluation, first hour
96133 - Neuropsychological testing, each additional hour
96136 - Psychological testing administration, first 30 min
96138 - Psychological testing administration by tech, first 30 min""",
        "indication_text": "Cognitive impairment workup, psychiatric evaluation, pre-surgical psych clearance, brain injury assessment",
        "coding_text": "CPT 96130-96146; ICD-10 F03.x, G31.x, F32.x, F41.x, F43.x",
        "cpt_codes": json.dumps(["96130","96131","96132","96133","96136","96137","96138","96139"]),
        "icd10_codes": json.dumps(["F03.90","G31.84","F32.9","F41.9","F43.10","F90.9"]),
        "specialties": json.dumps(["behavioral_health","neurology"]),
        "confidence_score": 0.92, "effective_date": "2024-01-01",
    },
    # ── Cardiovascular Surgery Coding (CABG, Pacemakers, Vascular) ─────────────
    {
        "source_id": "CMS-CV-CODING-2026", "source_type": "coding_guide",
        "title": "Cardiovascular Surgery CPT Coding Guidelines — CABG, Pacemakers, Vascular (2026)",
        "document_type": "coding_guide", "payer_code": "CMS",
        "content_text": """Cardiovascular Surgery CPT Coding Guidelines — CY2026

PACEMAKERS & DEFIBRILLATORS (CPT 33202–33249):

Implantation Approach — Always Distinguish:
- Transvenous: catheter threaded through veins into the heart (standard; lower morbidity)
- Epicardial: direct access through chest wall via sternotomy or thoracoscope (used when transvenous not feasible)
- Code selection depends on approach; documentation must state transvenous vs epicardial explicitly

Key Pacemaker Codes:
- 33206: Insertion of new or replacement pacemaker — atrial
- 33207: Insertion of new or replacement pacemaker — ventricular
- 33208: Insertion of new or replacement pacemaker — dual-chamber
- 33213: Insertion of pacemaker pulse generator — dual-chamber
- 33214: Upgrade from single-chamber to dual-chamber system — includes removal of old generator, lead testing, new lead and generator insertion. Do not unbundle.
- 33227: Removal and replacement of pacemaker pulse generator — single lead
- 33228: Removal and replacement — dual lead
- 33229: Removal and replacement — multiple leads

CORONARY ARTERY BYPASS GRAFTING (CABG) (CPT 33510–33536):

Critical Coding Rule — Conduit Types Determine Code Family:
- Arterial grafts only → 33533–33536 series (per artery)
- Venous grafts only → 33510–33516 series (per vein)
- BOTH arterial AND venous → Combined arterial-venous series 33517–33523
  WARNING: NEVER use veins-only series (33510–33516) when arterial conduit is also present. This is a common audit trigger.

Harvesting Rules:
- Lower extremity vein (saphenous): BUNDLED into primary CABG code — do NOT add separately
- Upper extremity artery (radial artery, 35600): separately reportable add-on — document explicitly
- Endoscopic harvest (33508): separately reportable for vein; document approach

CPT Reference:
- 33517: Single vein with single arterial
- 33518: Two veins with single arterial
- 33519: Three veins with single arterial
- 33521: Single vein with two arterials
- 33522: Two veins with two arterials
- 33523: Three or more veins with two or more arterials
- 33533: Arterial graft, single
- 33534: Arterial graft, two
- 33535: Arterial graft, three
- 33536: Arterial graft, four or more
- 35600: Harvest of upper extremity artery (add-on)
- 33508: Endoscopic harvest of vein (add-on)

VASCULAR SELECTIVE CATHETERIZATION (CPT 36100–37799):
CMS Appendix L — Order-Based Selectivity Rules:
- Non-selective: catheter tip remains in aorta, vena cava, or the vessel punctured → code 36200 (aorta)
- 1st-order selective: catheter tip in main branch directly off aorta (e.g., celiac axis, SMA, renal artery) → code 36245 (1st order)
- 2nd-order selective: catheter moved into a branch of a 1st-order vessel (e.g., left hepatic from celiac) → code 36246
- 3rd-order selective: moved into a branch of a 2nd-order vessel → code 36247
- Beyond 3rd order: 36248 (add-on for each beyond 3rd within same family)

Key Rules:
1. Code the HIGHEST order reached within each vascular family
2. Code each vascular family INDEPENDENTLY — do not mix orders across families
3. Supervision and interpretation of fluoroscopy (76000) may be separately reportable
4. Roadmap or documentation of catheter position required for selective code justification

ICD-10 Codes Supporting Cardiovascular Procedures:
I25.10 - Atherosclerotic heart disease, native vessel
I25.110 - Atherosclerotic heart disease, native vessel with unstable angina
I21.3 - ST elevation MI, unspecified
Z95.1 - Presence of aortocoronary bypass graft
Z95.0 - Presence of cardiac pacemaker
I49.9 - Cardiac arrhythmia, unspecified
I50.9 - Heart failure, unspecified""",
        "indication_text": "CABG coronary bypass graft arterial venous pacemaker defibrillator ICD cardiovascular vascular catheterization selective upgrade",
        "coding_text": "CPT 33206-33249 pacemakers; CPT 33510-33536 CABG; CPT 35600 radial harvest; CPT 33508 endoscopic vein; CPT 36200-36248 vascular selective catheterization; Modifier 22 increased services",
        "cpt_codes": json.dumps(["33206","33207","33208","33213","33214","33227","33228","33229",
                                  "33510","33511","33512","33513","33514","33516",
                                  "33517","33518","33519","33521","33522","33523",
                                  "33533","33534","33535","33536",
                                  "33508","35600",
                                  "36200","36245","36246","36247","36248"]),
        "icd10_codes": json.dumps(["I25.10","I25.110","I21.3","Z95.1","Z95.0","I49.9","I50.9"]),
        "specialties": json.dumps(["cardiac_surgery","cardiology","vascular_surgery","interventional_radiology"]),
        "confidence_score": 0.97, "effective_date": "2026-01-01",
    },
    # ── Digestive System Coding (Endoscopy, Resection, Adhesions) ───────────────
    {
        "source_id": "CMS-GI-CODING-2026", "source_type": "coding_guide",
        "title": "Digestive System CPT Coding Guidelines — Endoscopy, Resection, Adhesions (2026)",
        "document_type": "coding_guide", "payer_code": "CMS",
        "content_text": """Digestive System CPT Coding Guidelines — CY2026

ENDOSCOPY — ANATOMY GOVERNS THE CODE, NOT THE INSTRUMENT:

Key Principle: Code based on the ANATOMY VIEWED and REACHED, not the name of the scope used.

Colonoscopy (CPT 45378–45398):
- DEFINITION: Colonoscopy = scope reaches the CECUM (or the anastomosis in resected colon cases)
- If cecum is NOT reached → code as flexible sigmoidoscopy (45330 series), not colonoscopy
- Documentation MUST include: anatomic landmarks (cecum confirmed, hepatic flexure, splenic flexure, terminal ileum if examined)
- 45378: Colonoscopy, diagnostic
- 45379: Colonoscopy, with removal of foreign body
- 45380: Colonoscopy, with biopsy
- 45381: Colonoscopy, with directed submucosal injection
- 45382: Colonoscopy, with control of bleeding
- 45384: Colonoscopy, with removal of lesion by hot biopsy
- 45385: Colonoscopy, with removal of polyp by snare
- 45386: Colonoscopy, with balloon dilation
- 45388: Colonoscopy, with ablation of tumor/polyp/lesion
- 45390: Colonoscopy, with endoscopic mucosal resection (EMR)
- 45398: Colonoscopy, with band ligation

Flexible Sigmoidoscopy (CPT 45330–45342):
- Scope reaches sigmoid colon / descending colon — cecum NOT required
- 45330: Diagnostic sigmoidoscopy
- 45331: Sigmoidoscopy with biopsy

Upper GI Endoscopy (Esophagogastroduodenoscopy, EGD) (CPT 43235–43259):
- Scope passes through esophagus into duodenum
- 43235: EGD, diagnostic
- 43239: EGD, with biopsy
- 43255: EGD, with control of bleeding (thermal/injection)

ADHESION LYSIS (CPT 44005):
- 44005: Enterolysis — lysis of extensive intestinal adhesions
- Add Modifier 22 (Increased Procedural Services) when:
  • Work is unusually time-consuming and tedious
  • Documentation: operative note must describe the extent of adhesions, estimated extra time, and complexity relative to a typical case
  • Modifier 22 without supporting documentation is a frequent audit denial target
- Bundling: Do not separately code adhesiolysis if performed as a necessary component of the primary procedure (e.g., bowel resection) unless it constitutes a distinct, time-consuming service

SMALL INTESTINE RESECTIONS (CPT 44120–44128):
- 44120: Enterectomy, resection of small intestine, single resection and anastomosis
- 44121: Each additional resection and anastomosis (ADD-ON — use with 44120)
  RULE: For multiple resections, use 44120 once + 44121 × (n−1) additional resections
  WRONG: Multiple units of 44120
  RIGHT: 44120 (first) + 44121 (each additional)
- 44125: Enterectomy with cutaneous enterostomy (no anastomosis)
- 44126: Enterectomy with enteric anastomosis — reduction of congenital atresia

APPENDECTOMY:
- 44950: Appendectomy
- 44955: Appendectomy — for indicated purpose, performed at time of another procedure (add-on)
- 44960: Appendectomy — ruptured appendix with abscess or generalized peritonitis

Modifier Rules for Digestive:
- Modifier 51 (Multiple Procedures): Apply to secondary procedures in same session; do not apply to add-on codes
- Modifier 22: Use for increased complexity — must document rationale
- Modifier 58: Staged/related procedure during postoperative period

ICD-10 Codes — Digestive:
K57.30 - Diverticulosis, large intestine, without perforation/abscess
K92.1 - Melena (lower GI bleeding)
K63.5 - Polyp of colon
Z12.11 - Encounter for screening for malignant neoplasm of colon
K56.60 - Unspecified intestinal obstruction
K65.0 - Generalized acute peritonitis""",
        "indication_text": "colonoscopy cecum sigmoidoscopy EGD endoscopy digestive bowel resection adhesions enterolysis small intestine anastomosis appendectomy",
        "coding_text": "CPT 45378-45398 colonoscopy; CPT 45330 sigmoidoscopy; CPT 43235-43259 EGD; CPT 44005 enterolysis Modifier 22; CPT 44120-44121 small intestine resection add-on",
        "cpt_codes": json.dumps(["45378","45379","45380","45381","45382","45384","45385","45386",
                                  "45388","45390","45398","45330","45331",
                                  "43235","43239","43255",
                                  "44005","44120","44121","44125","44126",
                                  "44950","44955","44960"]),
        "icd10_codes": json.dumps(["K57.30","K92.1","K63.5","Z12.11","K56.60","K65.0"]),
        "specialties": json.dumps(["gastroenterology","colorectal_surgery","general_surgery"]),
        "confidence_score": 0.96, "effective_date": "2026-01-01",
    },
    # ── MIPS & HIPAA Security Rule (CMS-1832-F 2026) ────────────────────────────
    {
        "source_id": "CMS-MIPS-HIPAA-2026", "source_type": "compliance_guide",
        "title": "MIPS HIPAA Security Rule Attestation Requirements — CMS-1832-F 2026",
        "document_type": "compliance_guide", "payer_code": "CMS",
        "content_text": """MIPS HIPAA Security Rule Attestation — CY2026 Physician Fee Schedule (CMS-1832-F)

REQUIREMENT OVERVIEW:
The CY2026 Physician Fee Schedule (CMS-1832-F) mandates HIPAA Security Rule attestations as a MIPS measure. Eligible clinicians must formally attest to completing a risk analysis and implementing a risk management plan.

TWO MANDATORY ATTESTATION COMPONENTS:
1. Risk Analysis Completion
   - A formal, documented Security Risk Analysis (SRA) must be completed
   - Must assess threats and vulnerabilities to all ePHI (electronic Protected Health Information)
   - Must cover all systems, applications, and devices that create, receive, maintain, or transmit ePHI
   - Frequency: must be current — conducted within the performance year or documented update

2. Risk Management Plan Implementation
   - A written Risk Management Plan addressing identified risks must be in place
   - Plan must document security measures implemented to reduce risks to reasonable and appropriate levels
   - Workforce training records documenting HIPAA Security Rule training

AUDIT DOCUMENTATION REQUIREMENTS:
- Signed attestation in MIPS submission portal
- Evidence of SRA completion date and methodology
- Risk Management Plan document with implementation status
- Workforce training logs showing completion dates

DENIAL / NON-COMPLIANCE CONSEQUENCES:
- Missing HIPAA Security attestation in MIPS = MIPS penalty (negative payment adjustment)
- CY2026: MIPS negative adjustment for low performers up to −9%
- OIG audits can independently cite missing SRA as HIPAA Security Rule violation (45 CFR §164.308(a)(1))

RELEVANT REGULATIONS:
- 45 CFR §164.308(a)(1): Administrative safeguards — risk analysis required
- 45 CFR §164.308(a)(2): Risk management — must implement measures to reduce identified risks
- CMS-1832-F: Final rule mandating MIPS attestation for HIPAA Security compliance
- HIPAA Security Rule (45 CFR Part 164, Subpart C)

PRACTICAL CHECKLIST FOR COMPLIANCE:
1. Complete or update Security Risk Analysis (SRA) — use ONC SRA Tool or equivalent
2. Document all ePHI systems (EHR, billing software, cloud storage, mobile devices)
3. Create/update Risk Management Plan with prioritized remediation steps
4. Complete staff HIPAA Security training — retain sign-in sheets or LMS completion records
5. Attest in MIPS Quality Payment Program (QPP) portal before submission deadline

ICD-10/CPT: Not applicable — compliance measure, not a clinical code set""",
        "indication_text": "MIPS HIPAA Security Rule attestation risk analysis risk management plan CMS-1832-F PHI ePHI compliance penalty QPP Quality Payment Program",
        "coding_text": "MIPS compliance measure — no CPT/ICD codes. References 45 CFR §164.308; CMS-1832-F; ONC SRA Tool",
        "cpt_codes": json.dumps([]),
        "icd10_codes": json.dumps([]),
        "specialties": json.dumps(["compliance","health_it","practice_management"]),
        "confidence_score": 0.95, "effective_date": "2026-01-01",
    },
    # ── Part D Redesign 2026 ─────────────────────────────────────────────────────
    {
        "source_id": "CMS-PARTD-REDESIGN-2026", "source_type": "policy_guidance",
        "title": "CY2026 Part D Drug Benefit Redesign — Program Instructions & IRA Implementation",
        "document_type": "policy_guidance", "payer_code": "CMS",
        "content_text": """CY2026 Part D Drug Benefit Redesign — Program Instructions

BACKGROUND:
The Inflation Reduction Act (IRA) significantly restructured the Medicare Part D drug benefit. CY2026 Part D Redesign Program Instructions continue the phased implementation.

KEY 2026 CHANGES:
1. $2,000 Annual Out-of-Pocket Cap (effective 2025, continuing 2026)
   - Medicare beneficiaries' annual out-of-pocket drug costs capped at $2,000
   - Eliminates the previous "donut hole" / coverage gap phase
   - Medicare Prescription Payment Plan (M3P): allows beneficiaries to spread OOP costs across the year in monthly installments

2. Drug Manufacturer Price Negotiation
   - CMS negotiating prices for high-expenditure drugs (Initial Price Applicability Year 2026 drugs added to negotiation list)
   - Negotiated Maximum Fair Prices (MFPs) apply at point of sale

3. Inflation Rebates
   - Manufacturers must pay rebates if drug prices increase faster than inflation
   - Passed through as benefit enhancements

4. Enhanced Low-Income Subsidy (LIS/Extra Help)
   - Expanded eligibility thresholds continue in 2026
   - Full LIS (benchmark) beneficiaries have $0 copays for generics

5. Formulary & Coverage Guidance
   - Plans must cover all Part D covered drugs (except excluded) or provide meaningful therapeutic alternative
   - Generic/biosimilar utilization initiatives incentivized
   - Step therapy and prior authorization rules subject to CMS oversight

PLAN DESIGN REQUIREMENTS:
- TrOOP (True Out-of-Pocket) tracking modified to reflect $2,000 cap
- Catastrophic phase: beneficiary 0% cost sharing after OOP cap reached
- Sponsor liability increases in catastrophic phase
- DIR (Direct and Indirect Remuneration) fees: point-of-sale pass-through required

BILLING IMPLICATIONS:
- PDE (Prescription Drug Event) records must accurately reflect negotiated prices and rebates
- Formulary exception requests: plans must process within 24 hours (urgent) or 72 hours (standard)
- Prior authorization denials for covered Part D drugs: use coverage determination process, then redetermination, then IRE appeal

PART D RxHCC CONTEXT (V28 integration):
- Non-PACE MA-PD plans: RxHCC V08 record type 6 in MOR/MMR
- PACE plans: RxHCC V08 records 6 and 7
- RxHCC normalization factor (2026): 1.194 (MA-PD)""",
        "indication_text": "Part D drug benefit redesign IRA Inflation Reduction Act out of pocket cap OOP $2000 Medicare prescription payment plan formulary prior authorization step therapy generic biosimilar LIS extra help",
        "coding_text": "Part D coverage determination; formulary exception; PDE records; TrOOP tracking; RxHCC V08; HCPCS J-codes for drugs",
        "cpt_codes": json.dumps([]),
        "icd10_codes": json.dumps([]),
        "specialties": json.dumps(["pharmacy","part_d","managed_care"]),
        "confidence_score": 0.94, "effective_date": "2026-01-01",
    },
    # ── CMS Strategic Framework 2026 ────────────────────────────────────────────
    {
        "source_id": "CMS-STRATEGY-2026", "source_type": "strategic_framework",
        "title": "CMS Strategic Framework — 150 Million Beneficiaries, 6 Pillars, Cross-Cutting Initiatives (2026)",
        "document_type": "strategic_framework", "payer_code": "CMS",
        "content_text": """CMS Strategic Framework & Operational Context — CY2026

SCALE & SCOPE:
- CMS administers coverage for 150 million Americans
- Programs: Medicare (Part A, B, C, D), Medicaid, CHIP, Marketplace (ACA plans)
- Budget: largest payer in the US healthcare system

SIX STRATEGIC PILLARS:
1. Advance Equity
   - Address disparities in care by race, ethnicity, disability, language, geography
   - Health equity data collection mandates in claims and quality reporting
   - Special needs plans (D-SNPs, C-SNPs, I-SNPs) focus on vulnerable populations

2. Expand Access
   - Telehealth expansion (video-enabled) maintained post-COVID permanently in MA
   - FQHC and RHC reimbursement enhancement
   - Behavioral health integration requirements in MA plan benefits

3. Engage Partners
   - Value-based care models (ACO REACH, MSSP, CMMI models)
   - State Medicaid partnerships and 1115 waiver support
   - Provider enrollment and credentialing modernization

4. Drive Innovation
   - CMMI Center for Medicare and Medicaid Innovation — mandatory/voluntary payment models
   - AI/ML in clinical decision support: CMS transparency rules for algorithm-assisted PA decisions
   - Digital health coverage policies evolving

5. Protect Programs
   - Program integrity: RAC audits, UPIC investigations, MAC reviews
   - RADV audits: PY2020+ annual for ALL MA plans
   - MIPS anti-gaming provisions
   - HIPAA Security attestation in MIPS (see CMS-1832-F)

6. Foster Excellence
   - Quality measurement: STAR ratings for MA, HEDIS, CAHPS
   - Value-Based Insurance Design (VBID): targeted benefit enhancements for high-value services
   - Workforce training and provider education

CROSS-CUTTING STRATEGIC INITIATIVES:

Behavioral Health Integration:
- MA plans required to offer mental health and SUD benefits comparable to medical/surgical
- Mental Health Parity and Addiction Equity Act (MHPAEA) enforcement increased
- Collaborative care management codes (CPT 99492–99494) covered
- ICD-10 codes: F-codes (F20–F99) must be V28-compliant for risk adjustment

Drug Affordability:
- Generic first / step therapy protocols encouraged (not required for protected drug classes)
- Biosimilar interchangeability: dispensing permitted without separate prescriber authorization
- Part D rebate transparency to beneficiaries

Maternity Care:
- Extended postpartum Medicaid coverage (12 months) per ARP
- Maternal mortality disparities initiative — SDOH Z-codes encouraged in claims
- ICD-10: Z34.x (supervision of normal pregnancy), O codes (obstetric complications)

Integrating the 3Ms (Medicare + Medicaid/CHIP + Marketplace):
- Seamless transitions as beneficiaries move between programs (ACA→Medicaid, Medicaid→Medicare)
- Dual eligible beneficiaries (D-SNPs): integrated care models expanding
- Continuity of care protections: must maintain access to current providers during plan transitions

Transparency in Coverage (TC-PUF):
- PY2026 public use file contains issuer and plan-level data on claims, appeals, and active URL data from PY2024
- Machine-readable files (MRFs) required for in-network rates and allowed amounts

PMC CLOUD TRANSITION (Technical Note for API Users):
- PMC FTP Service → PMC Cloud Service on AWS by August 2026
- Dual availability transition period: February 2026 – August 2026
- After August 2026: FTP service discontinued; all full-text article access via AWS Cloud Service""",
        "indication_text": "CMS strategic framework Medicare Medicaid CHIP Marketplace equity access innovation program integrity RADV STAR ratings behavioral health drug affordability maternity dual eligible D-SNP",
        "coding_text": "Strategic guidance — no specific CPT/ICD codes. References STAR ratings, HEDIS, CAHPS, MHPAEA, V28 HCC, RADV, MIPS",
        "cpt_codes": json.dumps(["99492","99493","99494"]),
        "icd10_codes": json.dumps(["Z34.00","F32.9","F20.9"]),
        "specialties": json.dumps(["managed_care","compliance","population_health","policy"]),
        "confidence_score": 0.93, "effective_date": "2026-01-01",
    },
]

# V28 HCC seed data — real codes, real statuses
V28_CODES = [
    # Diabetes — major V28 changes
    ("E11.9",  "Type 2 diabetes mellitus without complications",           "19",  "19",  1, 1, "Diabetes without Complication",          "standard"),
    ("E11.65", "Type 2 diabetes with hyperglycemia",                       "19",  "19",  1, 1, "Diabetes without Complication",          "standard"),
    ("E11.40", "Type 2 diabetes with diabetic neuropathy, unspecified",    "18",  "18",  1, 1, "Diabetes with Neurological Manifestation","medium"),
    ("E11.22", "Type 2 diabetes with diabetic CKD stage 3",                "18",  "18",  1, 1, "Diabetes with Chronic Complication",     "high"),
    ("E11.311","Type 2 diabetes with unspecified diabetic retinopathy",     None,  "18",  0, 1, "Diabetes with Ophthalmic Manifestation", "standard"),
    ("E10.9",  "Type 1 diabetes mellitus without complications",           "19",  "19",  1, 1, "Diabetes without Complication",          "standard"),
    ("E10.65", "Type 1 diabetes with hyperglycemia",                       "17",  "17",  1, 1, "Diabetes with Acute Complication",       "high"),
    ("E13.9",  "Other specified diabetes mellitus without complications",  None,  "19",  0, 1, "Diabetes without Complication",          "standard"),
    # Heart failure
    ("I50.9",  "Heart failure, unspecified",                               None,  "85",  0, 1, "Heart Failure",                          "high"),
    ("I50.23", "Acute on chronic systolic heart failure",                  "87",  "86",  1, 1, "Systolic Heart Failure",                 "critical"),
    ("I50.43", "Acute on chronic combined systolic and diastolic HF",      "87",  "86",  1, 1, "Combined Systolic/Diastolic HF",         "critical"),
    ("I50.32", "Chronic diastolic heart failure",                          "88",  "86",  1, 1, "Diastolic Heart Failure",                "high"),
    ("I50.22", "Chronic systolic heart failure",                           "87",  "86",  1, 1, "Systolic Heart Failure",                 "high"),
    # CKD
    ("N18.3",  "Chronic kidney disease, stage 3 unspecified",              "137", "137", 1, 1, "Chronic Kidney Disease, Moderate",       "medium"),
    ("N18.4",  "Chronic kidney disease, stage 4",                          "136", "136", 1, 1, "Chronic Kidney Disease, Severe",         "high"),
    ("N18.5",  "Chronic kidney disease, stage 5",                          "135", "135", 1, 1, "Chronic Kidney Disease, Stage 5",        "critical"),
    ("N18.6",  "End stage renal disease",                                  "134", "134", 1, 1, "End Stage Renal Disease",                "critical"),
    ("N18.1",  "Chronic kidney disease, stage 1",                         None,  None,  0, 0, "CKD Stage 1 — Not HCC Mapped",           "standard"),
    ("N18.2",  "Chronic kidney disease, stage 2",                         None,  None,  0, 0, "CKD Stage 2 — Not HCC Mapped",           "standard"),
    # COPD
    ("J44.9",  "COPD, unspecified",                                        None,  "111", 0, 1, "COPD",                                   "medium"),
    ("J44.1",  "COPD with acute exacerbation",                             "111", "111", 1, 1, "COPD with Exacerbation",                 "high"),
    ("J44.0",  "COPD with acute lower respiratory infection",              "111", "111", 1, 1, "COPD with Infection",                    "high"),
    # Depression/Behavioral Health — V28 MAJOR CHANGES
    ("F32.9",  "Major depressive disorder, unspecified",                   None,  "59",  0, 1, "Major Depression",                       "medium"),
    ("F33.9",  "Major depressive disorder, recurrent, unspecified",        None,  "59",  0, 1, "Major Depression, Recurrent",            "medium"),
    ("F32.0",  "Major depressive disorder, single episode, mild",          None,  "59",  0, 1, "Major Depression, Mild",                 "medium"),
    ("F33.0",  "Major depressive disorder, recurrent, mild",               None,  "59",  0, 1, "Recurrent Depression, Mild",             "medium"),
    ("F33.1",  "Major depressive disorder, recurrent, moderate",           "155", "59",  1, 1, "Recurrent Depression, Moderate",         "medium"),
    ("F33.2",  "Major depressive disorder, recurrent, severe",             "155", "59",  1, 1, "Recurrent Depression, Severe",           "high"),
    # Atrial Fibrillation
    ("I48.0",  "Paroxysmal atrial fibrillation",                           "96",  "96",  1, 1, "Atrial Fibrillation/Flutter",            "medium"),
    ("I48.11", "Longstanding persistent atrial fibrillation",              "96",  "96",  1, 1, "Atrial Fibrillation, Persistent",        "medium"),
    ("I48.19", "Other persistent atrial fibrillation",                     "96",  "96",  1, 1, "Atrial Fibrillation, Persistent",        "medium"),
    ("I48.20", "Chronic atrial fibrillation, unspecified",                 "96",  "96",  1, 1, "Atrial Fibrillation, Chronic",           "medium"),
    # Stroke/Neurological
    ("I63.9",  "Cerebral infarction, unspecified",                         "100", "100", 1, 1, "Ischemic Stroke",                        "critical"),
    ("G35",    "Multiple sclerosis",                                        "78",  "78",  1, 1, "Multiple Sclerosis",                     "high"),
    ("G20",    "Parkinson's disease",                                       "79",  "79",  1, 1, "Parkinson's Disease",                    "high"),
    ("G30.9",  "Alzheimer's disease, unspecified",                          "52",  "52",  1, 1, "Dementia, Alzheimer's",                  "high"),
    # Obesity
    ("E66.9",  "Obesity, unspecified",                                     None,  None,  0, 0, "Obesity — Not V28 HCC Mapped",           "standard"),
    ("E66.01", "Morbid obesity due to excess calories",                    "48",  "48",  1, 1, "Morbid Obesity",                         "medium"),
    # Cancer
    ("C34.10", "Malignant neoplasm, upper lobe bronchus/lung, unspec",    "9",   "9",   1, 1, "Lung Cancer",                            "critical"),
    ("C50.911","Malignant neoplasm, breast, unspecified",                  "12",  "12",  1, 1, "Breast Cancer",                          "high"),
    ("C18.9",  "Malignant neoplasm of colon, unspecified",                 "11",  "11",  1, 1, "Colorectal Cancer",                      "high"),
    ("C61",    "Malignant neoplasm of prostate",                           "12",  "12",  1, 1, "Prostate Cancer",                        "high"),
    # Rheumatoid Arthritis
    ("M05.70", "Rheumatoid arthritis with rheumatoid factor, unspec",     "40",  "40",  1, 1, "Rheumatoid Arthritis",                   "medium"),
    ("M06.9",  "Rheumatoid arthritis, unspecified",                        None,  "40",  0, 1, "Rheumatoid Arthritis, Unspecified",      "medium"),
]

def build():
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    # Insert documents
    for doc in DOCUMENTS:
        h = hashlib.sha256(doc["content_text"].encode()).hexdigest()
        conn.execute("""
            INSERT OR IGNORE INTO documents
            (source_id, source_type, title, document_type, payer_code, source_url,
             content_text, indication_text, coding_text, cpt_codes, icd10_codes,
             hcpcs_codes, specialties, confidence_score, effective_date, content_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            doc["source_id"], doc["source_type"], doc["title"], doc["document_type"],
            doc.get("payer_code","CMS"), doc.get("source_url",""),
            doc["content_text"], doc.get("indication_text",""), doc.get("coding_text",""),
            doc.get("cpt_codes","[]"), doc.get("icd10_codes","[]"),
            doc.get("hcpcs_codes","[]"), doc.get("specialties","[]"),
            doc.get("confidence_score", 0.85), doc.get("effective_date","2024-01-01"), h
        ))

    # Insert V28 seed codes
    for row in V28_CODES:
        conn.execute("""
            INSERT OR IGNORE INTO v28_hcc_codes
            (icd10_code, description, v28_hcc, v24_hcc, v28_pays, v24_pays, hcc_label, payment_tier)
            VALUES (?,?,?,?,?,?,?,?)
        """, row)

    # Insert expanded V28 codes (~237 additional high-revenue codes)
    try:
        from v28_hcc_expanded import V28_CODES_EXPANDED, get_change_note
        for row in V28_CODES_EXPANDED:
            conn.execute("""
                INSERT OR IGNORE INTO v28_hcc_codes
                (icd10_code, description, v28_hcc, v24_hcc, v28_pays, v24_pays, hcc_label, payment_tier)
                VALUES (?,?,?,?,?,?,?,?)
            """, row)
            note, rationale = get_change_note(row[0])
            if note or rationale:
                conn.execute("""
                    UPDATE v28_hcc_codes SET v28_change_note=?, clinical_rationale=?
                    WHERE icd10_code=?
                """, (note, rationale, row[0]))
    except ImportError:
        pass  # Expanded module optional

    # Seed V28 HCC category reference table
    try:
        from v28_hcc_categories import V28_HCC_CATEGORIES
        for hcc_num, cat in V28_HCC_CATEGORIES.items():
            conn.execute("""
                INSERT OR IGNORE INTO v28_hcc_categories
                (hcc_number, description, disease_family, severity, raf_weight, hierarchy_group)
                VALUES (?,?,?,?,?,?)
            """, (
                hcc_num,
                cat.get("desc", ""),
                cat.get("family", ""),
                cat.get("severity", "standard"),
                cat.get("raf_weight", 0.0),
                cat.get("hierarchy_group"),
            ))
    except ImportError:
        pass  # Optional — populated by cms_zip_ingest.py

    # Seed 2026 CMS model configuration (normalization factors, MA coding adjustment)
    CMS_2026_CONFIG = [
        # Normalization factors — applied to RAF before payment calculation
        (2026, "norm_factor_cms_hcc_v28_part_c",    "1.067",  "2024 CMS-HCC V28 Part C normalization factor", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_cms_hcc_v22_part_c",    "1.187",  "2017 CMS-HCC V22 Part C normalization factor (PACE blend)", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_esrd_dialysis_v24",      "1.062",  "2023 ESRD V24 dialysis normalization factor", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_esrd_dialysis_v21",      "1.129",  "2019 ESRD V21 dialysis normalization factor (PACE)", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_esrd_graft_v24",         "1.104",  "2023 ESRD V24 graft normalization factor", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_esrd_graft_v21",         "1.203",  "2019 ESRD V21 graft normalization factor (PACE)", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_rxhcc_ma_pd",            "1.194",  "RxHCC MA-PD 2022/2023 calibration normalization", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_rxhcc_pdp",              "0.887",  "RxHCC PDP 2022/2023 calibration normalization", "2026 CMS Final Rate Announcement"),
        (2026, "norm_factor_rxhcc_pace",             "1.202",  "RxHCC PACE 2018/2019 calibration normalization", "2026 CMS Final Rate Announcement"),
        # MA coding intensity adjustment
        (2026, "ma_coding_intensity_adjustment",     "0.059",  "5.90% statutory minimum coding intensity adjustment applied to all MA plans", "2026 CMS Final Rate Announcement"),
        # PACE blending
        (2026, "pace_v28_blend_pct",                 "0.10",   "PACE plans: 10% V28 (2024 CMS-HCC) weight in 2026", "2026 CMS Final Rate Announcement"),
        (2026, "pace_v22_blend_pct",                 "0.90",   "PACE plans: 90% V22 (2017 CMS-HCC) weight in 2026", "2026 CMS Final Rate Announcement"),
        # Non-PACE MA
        (2026, "non_pace_v28_blend_pct",             "1.00",   "Non-PACE MA: 100% V28 (full phase-in complete)", "2026 CMS Final Rate Announcement"),
        # Revenue impact
        (2026, "avg_risk_score_change_v28_vs_blend", "-0.0301", "-3.01% average risk score change vs 2025 V24/V28 blend", "2026 CMS Final Rate Announcement"),
        (2026, "ma_payment_increase_pct",            "0.0506",  "5.06% average MA payment increase for 2026", "2026 CMS Final Rate Announcement"),
        (2026, "effective_growth_rate",              "0.0904",  "9.04% effective growth rate (includes Q4 2024 FFS data)", "2026 CMS Final Rate Announcement"),
        # Data sources
        (2026, "data_source_non_pace",              "encounter_data_ffs_only", "Non-PACE: encounter data + FFS claims only; RAPS no longer accepted for new data", "2026 Implementation Memo"),
        (2026, "data_source_pace",                  "raps_encounter_ffs_blend", "PACE: RAPS + encounter + FFS blended", "2026 Implementation Memo"),
        # V28 model stats
        (2026, "v28_payment_hccs",                  "115",    "Number of payment HCC categories in V28 (vs 86 in V24)", "CMS V28 Model Documentation"),
        (2026, "v28_icd10_mapped_codes",             "7770",   "Approximate number of ICD-10-CM codes mapping to V28 payment HCCs (vs 9,797 in V24)", "CMS V28 Model Documentation"),
        (2026, "v28_icd10_removed_codes",            "2290",   "ICD-10-CM codes removed from HCC mapping in V28 vs V24 transition", "CMS V28 Model Documentation"),
        # MOR/MMR record types — Non-PACE MA (2026)
        (2026, "mor_record_type_non_pace_part_c",    "2024 CMS-HCC V28 M",  "Non-PACE Part C MOR/MMR record type identifier for 2026 payment year", "CMS MOR/MMR 2026 Spec"),
        (2026, "mor_record_type_non_pace_rxhcc",     "2026 RxHCC V08 6",    "Non-PACE Part D RxHCC MOR/MMR record type for 2026", "CMS MOR/MMR 2026 Spec"),
        (2026, "mor_record_type_non_pace_esrd",      "2023 ESRD V24 L",     "Non-PACE ESRD MOR/MMR record type for 2026", "CMS MOR/MMR 2026 Spec"),
        # MOR/MMR record types — PACE (2026, blended V28+V22)
        (2026, "mor_record_type_pace_part_c",        "2024 CMS-HCC V28 M",  "PACE Part C MOR/MMR record type — V28 portion (10% weight)", "CMS MOR/MMR 2026 Spec / PCUG Nov 2025"),
        (2026, "mor_record_type_pace_rxhcc",         "2026 RxHCC V08 6/7",  "PACE Part D RxHCC MOR/MMR record type — V08 records 6 and 7", "CMS MOR/MMR 2026 Spec / PCUG Nov 2025"),
        (2026, "mor_record_type_pace_v22",           "2017 CMS-HCC V22 K",  "PACE V22 legacy MOR/MMR record type — 90% weight in 2026 blend", "CMS MOR/MMR 2026 Spec / PCUG Nov 2025"),
        (2026, "mor_record_type_pace_esrd_v24",      "2023 ESRD V24 L",     "PACE ESRD V24 MOR/MMR record type", "CMS MOR/MMR 2026 Spec"),
        (2026, "mor_record_type_pace_esrd_v21",      "2019 ESRD V21 B",     "PACE ESRD V21 legacy MOR/MMR record type", "CMS MOR/MMR 2026 Spec"),
        # Frailty supplemental payment — FIDE-SNPs
        (2026, "norm_factor_frailty_fide_snps",      "full_2024_factors",   "Frailty supplemental payment uses full 2024 CMS frailty factors for FIDE-SNPs in 2026 — no phase-in reduction", "2026 CMS Final Rate Announcement"),
        # Encounter data filtering rules — what qualifies for risk adjustment
        (2026, "encounter_filter_face_to_face_required",   "true",  "Diagnoses must come from face-to-face visits with eligible CPT/HCPCS codes to qualify for risk adjustment", "2026 CMS Encounter Data Guidance"),
        (2026, "encounter_excluded_audio_only_telehealth",  "true",  "Audio-only telehealth visits do NOT qualify as face-to-face encounters for risk adjustment (video-enabled telehealth does qualify)", "2026 CMS Encounter Data Guidance"),
        (2026, "encounter_excluded_labs_radiology_alone",   "true",  "Laboratory, radiology, and pathology results alone (without face-to-face CPT/HCPCS) do not qualify diagnoses for risk adjustment", "2026 CMS Encounter Data Guidance"),
        (2026, "encounter_excluded_home_health_snf_no_f2f", "true",  "Home health agency and SNF claims without an accompanying face-to-face CPT/HCPCS encounter code do not qualify for risk adjustment", "2026 CMS Encounter Data Guidance"),
        (2026, "encounter_accepted_sources",         "physician_inpatient_outpatient_facility", "Qualifying face-to-face sources: physician office (E&M), inpatient hospital, outpatient hospital, FQHC/RHC — with eligible CPT/HCPCS", "2026 CMS Encounter Data Guidance"),
        # Medical education cost adjustment
        (2026, "medical_education_cost_adjustment",   "1.00",   "100% technical adjustment applied in 2026 — 3-year phase-in to remove medical education costs from growth rate calculation is complete", "2026 CMS Final Rate Announcement"),
        # CMS scale
        (2026, "cms_beneficiary_count",              "150000000", "CMS covers 150 million Americans across Medicare, Medicaid/CHIP, and Marketplace", "CMS Strategic Plan 2026"),
        # MIPS HIPAA Security attestation
        (2026, "mips_hipaa_security_attestation_required", "true", "CMS-1832-F: MIPS eligible clinicians must attest to HIPAA Security Rule compliance — formal risk analysis + risk management plan required", "CY2026 Physician Fee Schedule CMS-1832-F"),
        (2026, "mips_max_negative_adjustment",       "-0.09",  "Maximum MIPS negative payment adjustment for low performers in CY2026: −9%", "CY2026 PFS CMS-1832-F"),
        # Part D redesign
        (2026, "part_d_oop_cap_dollars",             "2000",   "Medicare Part D annual out-of-pocket cap: $2,000 (IRA; effective 2025, continuing 2026)", "Inflation Reduction Act / 2026 Part D Program Instructions"),
        (2026, "part_d_m3p_available",               "true",   "Medicare Prescription Payment Plan (M3P): beneficiaries can spread Part D OOP costs in monthly installments", "2026 Part D Program Instructions"),
        (2026, "part_d_rxhcc_non_pace_record",       "2026 RxHCC V08 6",  "Non-PACE MA-PD RxHCC MOR/MMR record type for 2026", "2026 Part D Redesign Program Instructions"),
        (2026, "part_d_rxhcc_pace_records",          "2026 RxHCC V08 6/7", "PACE RxHCC MOR/MMR record types (records 6 and 7) for 2026", "2026 Part D Redesign Program Instructions"),
        # CPT surgery coding guidelines
        (2026, "cabg_combined_series_start_cpt",     "33517",  "CABG combined arterial-venous series starts at 33517 — must use this series when both arterial and venous conduits are used", "AMA CPT 2026"),
        (2026, "cabg_radial_artery_harvest_cpt",     "35600",  "Upper extremity artery harvest (e.g., radial) for CABG: separately reportable as CPT 35600", "AMA CPT 2026"),
        (2026, "cabg_saphenous_harvest_bundled",     "true",   "Lower extremity (saphenous) vein harvest for CABG: BUNDLED — do not bill separately", "AMA CPT 2026 / NCCI Edits"),
        (2026, "pacemaker_upgrade_dual_cpt",         "33214",  "Upgrade single-chamber to dual-chamber pacemaker: CPT 33214 — includes removal, lead test, new lead + generator; do not unbundle", "AMA CPT 2026"),
        (2026, "colonoscopy_requires_cecum",         "true",   "Colonoscopy CPT codes (45378+) require documentation that scope reached the cecum; failure = recode as sigmoidoscopy (45330)", "AMA CPT 2026 / CMS Correct Coding"),
        (2026, "small_intestine_addon_cpt",          "44121",  "Multiple small intestine resections: 44120 once + 44121 (add-on) for each additional — never multiple units of 44120", "AMA CPT 2026"),
        (2026, "enterolysis_adhesions_cpt",          "44005",  "Extensive intestinal adhesion lysis: CPT 44005. Add Modifier 22 for unusually time-consuming cases with documented complexity", "AMA CPT 2026"),
        # V28 audit and hierarchy
        (2026, "v28_hierarchy_enforcement",          "automated", "V28 CMS payment engine automatically suppresses child HCCs when parent is present — code stacking is a RADV audit trigger", "CMS V28 Model Documentation"),
        (2026, "meat_evidence_required",             "true",   "Each coded HCC requires MEAT (Monitor/Evaluate/Assess/Treat) evidence in the provider note for the payment year", "CMS RADV Program Guidance PY2020+"),
        (2026, "radv_audit_scope",                   "annual_all_plans", "RADV audits: annual for ALL MA plans starting PY2020; invalid HCC triggers repayment of full HCC payment × enrollment count", "CMS RADV Guidance PY2020+"),
    ]
    for config_year, config_key, config_value, description, source in CMS_2026_CONFIG:
        conn.execute("""
            INSERT OR IGNORE INTO cms_model_config
            (config_year, config_key, config_value, description, source)
            VALUES (?,?,?,?,?)
        """, (config_year, config_key, config_value, description, source))

    # Seed a demo API key
    import secrets as s
    demo_key = "cmg_demo_key_replace_in_production"
    key_hash = hashlib.sha256(demo_key.encode()).hexdigest()
    conn.execute("""
        INSERT OR IGNORE INTO api_keys (key_hash, customer_name, tier, notes)
        VALUES (?, 'CodeMed Demo', 'demo', 'Built-in demo key for testing')
    """, (key_hash,))

    conn.commit()
    conn.close()

    conn2 = sqlite3.connect(DB_PATH)
    v28_total   = conn2.execute("SELECT COUNT(*) FROM v28_hcc_codes").fetchone()[0]
    v28_rejected = conn2.execute("SELECT COUNT(*) FROM v28_hcc_codes WHERE v28_pays=0 AND v24_pays=1").fetchone()[0]
    conn2.close()
    print(f"✅ nexusauth.db built at {DB_PATH}")
    print(f"   {len(DOCUMENTS)} LCD/NCD documents")
    print(f"   {v28_total} V28 HCC codes ({v28_rejected} rejected in V28)")
    print(f"   Demo API key: {demo_key}")

if __name__ == "__main__":
    build()
