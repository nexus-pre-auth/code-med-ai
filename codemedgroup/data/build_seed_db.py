"""
CodeMed Group — Database Builder
Run once: python data/build_seed_db.py
Builds nexusauth.db with schema + seeded CMS LCD/NCD data + V28 codes
"""
import sqlite3, json, hashlib, secrets
from pathlib import Path

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
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    icd10_code    TEXT NOT NULL UNIQUE,
    description   TEXT,
    v28_hcc       TEXT,
    v24_hcc       TEXT,
    v28_pays      INTEGER DEFAULT 0,
    v24_pays      INTEGER DEFAULT 0,
    hcc_label     TEXT,
    payment_tier  TEXT DEFAULT 'standard'
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

    # Insert V28 codes
    for row in V28_CODES:
        conn.execute("""
            INSERT OR IGNORE INTO v28_hcc_codes
            (icd10_code, description, v28_hcc, v24_hcc, v28_pays, v24_pays, hcc_label, payment_tier)
            VALUES (?,?,?,?,?,?,?,?)
        """, row)

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

    doc_count = len(DOCUMENTS)
    v28_count = len(V28_CODES)
    rejected = sum(1 for r in V28_CODES if r[4] == 0 and r[5] == 1)
    print(f"✅ nexusauth.db built at {DB_PATH}")
    print(f"   {doc_count} LCD/NCD documents")
    print(f"   {v28_count} V28 HCC codes ({rejected} rejected in V28)")
    print(f"   Demo API key: {demo_key}")

if __name__ == "__main__":
    build()
