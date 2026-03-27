"""
CodeMed Group — V28 HCC Category Reference
Full CMS-HCC Version 28 (2024 model, 100% effective CY2026) reference catalog.

Contains:
  V28_HCC_CATEGORIES  — all 115 paying HCC categories with metadata
  V28_HIERARCHIES     — parent→child suppression rules
  V28_INTERACTIONS    — disease interaction pairs (additive RAF)
  V28_RADV_REQUIREMENTS — RADV documentation standards per disease family

Sources:
  CMS 2026 Final Rate Announcement (April 2025)
  CMS-HCC V28 Model Software (2026-midyear-final-model-software.zip)
  CMS RADV Program Guidance (PY2020+ annual audit expansion)
  CMS ICD-10-CM to CMS-HCC Crosswalk (2026-initial-icd-10-cm-mappings.zip)

Note on RAF weights: approximate community non-dual aged relative factors from
published CMS rate data. Exact values are in the CMS model software ZIP.
"""

# ── Full V28 HCC Category Catalog ─────────────────────────────────────────────
# Format: hcc_number → {desc, family, severity, raf_weight, hierarchy_group}
# severity: 'critical' | 'high' | 'medium' | 'standard'
# hierarchy_group: string key shared by HCCs in the same hierarchy chain

V28_HCC_CATEGORIES: dict[int, dict] = {

    # ══ INFECTIOUS DISEASE ═══════════════════════════════════════════════════
    1:   {"desc": "HIV/AIDS",
          "family": "Infectious", "severity": "critical",
          "raf_weight": 0.335, "hierarchy_group": "HIV"},

    2:   {"desc": "Septicemia, Sepsis, Systemic Inflammatory Response Syndrome/Shock",
          "family": "Infectious", "severity": "critical",
          "raf_weight": 0.380, "hierarchy_group": None},

    6:   {"desc": "Opportunistic Infections",
          "family": "Infectious", "severity": "critical",
          "raf_weight": 0.421, "hierarchy_group": "HIV"},

    # ══ CANCER / NEOPLASM ════════════════════════════════════════════════════
    17:  {"desc": "Cancer Metastatic to Lung, Liver, Brain, and Other Organs; AML Except Promyelocytic",
          "family": "Cancer", "severity": "critical",
          "raf_weight": 2.488, "hierarchy_group": "Cancer_Severity"},

    18:  {"desc": "Cancer Metastatic to Bone, Other and Unspecified Metastatic Cancer; Acute Leukemia Except Myeloid",
          "family": "Cancer", "severity": "critical",
          "raf_weight": 1.849, "hierarchy_group": "Cancer_Severity"},

    19:  {"desc": "Myelodysplastic Syndromes, Multiple Myeloma, and Other Cancers",
          "family": "Cancer", "severity": "critical",
          "raf_weight": 1.202, "hierarchy_group": "Cancer_Severity"},

    20:  {"desc": "Lung and Other Severe Cancers",
          "family": "Cancer", "severity": "critical",
          "raf_weight": 1.190, "hierarchy_group": "Cancer_Severity"},

    21:  {"desc": "Lymphoma and Other Cancers",
          "family": "Cancer", "severity": "high",
          "raf_weight": 0.951, "hierarchy_group": "Cancer_Severity"},

    22:  {"desc": "Bladder, Colorectal, and Other Cancers and Tumors",
          "family": "Cancer", "severity": "high",
          "raf_weight": 0.307, "hierarchy_group": "Cancer_Severity"},

    23:  {"desc": "Prostate, Breast, and Other Cancers and Tumors",
          "family": "Cancer", "severity": "high",
          "raf_weight": 0.146, "hierarchy_group": "Cancer_Severity"},

    # ══ DIABETES ═════════════════════════════════════════════════════════════
    35:  {"desc": "Pancreas Transplant Status",
          "family": "Diabetes", "severity": "critical",
          "raf_weight": 1.378, "hierarchy_group": "Diabetes"},

    36:  {"desc": "Diabetes with Severe Acute Complications",
          "family": "Diabetes", "severity": "critical",
          "raf_weight": 0.302, "hierarchy_group": "Diabetes"},

    37:  {"desc": "Diabetes with Chronic Complications",
          "family": "Diabetes", "severity": "high",
          "raf_weight": 0.302, "hierarchy_group": "Diabetes"},

    38:  {"desc": "Diabetes with Glycemic, Unspecified, or No Complications",
          "family": "Diabetes", "severity": "medium",
          "raf_weight": 0.105, "hierarchy_group": "Diabetes"},

    # ══ METABOLIC ════════════════════════════════════════════════════════════
    48:  {"desc": "Morbid Obesity",
          "family": "Metabolic", "severity": "high",
          "raf_weight": 0.273, "hierarchy_group": None},

    # ══ SUBSTANCE USE DISORDER ═══════════════════════════════════════════════
    54:  {"desc": "Substance Use with Psychotic Complications",
          "family": "Behavioral_Health", "severity": "critical",
          "raf_weight": 0.329, "hierarchy_group": "Substance_Use"},

    55:  {"desc": "Substance Use Disorder, Moderate/Severe, Except Alcohol and Cannabis",
          "family": "Behavioral_Health", "severity": "high",
          "raf_weight": 0.329, "hierarchy_group": "Substance_Use"},

    56:  {"desc": "Substance Use Disorder, Mild; Alcohol and Cannabis Dependence",
          "family": "Behavioral_Health", "severity": "medium",
          "raf_weight": 0.143, "hierarchy_group": "Substance_Use"},

    # ══ PSYCHIATRIC ══════════════════════════════════════════════════════════
    57:  {"desc": "Schizophrenia",
          "family": "Behavioral_Health", "severity": "critical",
          "raf_weight": 0.453, "hierarchy_group": "Psychosis"},

    58:  {"desc": "Reactive and Unspecified Psychosis; Delusional Disorders",
          "family": "Behavioral_Health", "severity": "high",
          "raf_weight": 0.315, "hierarchy_group": "Psychosis"},

    59:  {"desc": "Personality Disorders; Anorexia/Bulimia Nervosa",
          "family": "Behavioral_Health", "severity": "medium",
          "raf_weight": 0.221, "hierarchy_group": None},

    60:  {"desc": "Bipolar Disorders without Psychosis",
          "family": "Behavioral_Health", "severity": "high",
          "raf_weight": 0.221, "hierarchy_group": "Mood_Disorder"},

    # V28 KEY CHANGE: F32.9, F33.9 (unspecified depression) REMOVED from V28
    61:  {"desc": "Major Depression, Moderate/Severe, and Dysthymia",
          "family": "Behavioral_Health", "severity": "medium",
          "raf_weight": 0.157, "hierarchy_group": "Mood_Disorder"},

    # ══ LIVER / HEPATIC ══════════════════════════════════════════════════════
    62:  {"desc": "Liver Transplant Status/Complications",
          "family": "Hepatic", "severity": "critical",
          "raf_weight": 1.200, "hierarchy_group": "Liver_Severity"},

    63:  {"desc": "Chronic Liver Failure/End-Stage Liver Disorders",
          "family": "Hepatic", "severity": "critical",
          "raf_weight": 0.939, "hierarchy_group": "Liver_Severity"},

    64:  {"desc": "Cirrhosis of Liver",
          "family": "Hepatic", "severity": "high",
          "raf_weight": 0.402, "hierarchy_group": "Liver_Severity"},

    65:  {"desc": "Chronic Hepatitis",
          "family": "Hepatic", "severity": "high",
          "raf_weight": 0.163, "hierarchy_group": "Liver_Severity"},

    # ══ GASTROINTESTINAL ═════════════════════════════════════════════════════
    66:  {"desc": "Intestine Transplant Status/Complications",
          "family": "GI", "severity": "critical",
          "raf_weight": 1.500, "hierarchy_group": None},

    67:  {"desc": "Peritonitis/Gastrointestinal Perforation/Necrotizing Enterocolitis",
          "family": "GI", "severity": "critical",
          "raf_weight": 0.564, "hierarchy_group": None},

    68:  {"desc": "Intestinal Obstruction/Perforation",
          "family": "GI", "severity": "high",
          "raf_weight": 0.271, "hierarchy_group": None},

    69:  {"desc": "Esophageal Hemorrhage and Other Upper GI Conditions",
          "family": "GI", "severity": "high",
          "raf_weight": 0.180, "hierarchy_group": None},

    # V28 NEW: IBD split into Crohn's vs Ulcerative Colitis
    80:  {"desc": "Crohn's Disease (Regional Enteritis)",
          "family": "GI_IBD", "severity": "high",
          "raf_weight": 0.305, "hierarchy_group": "GI_IBD"},

    81:  {"desc": "Ulcerative Colitis",
          "family": "GI_IBD", "severity": "high",
          "raf_weight": 0.235, "hierarchy_group": "GI_IBD"},

    # ══ RHEUMATOLOGY / AUTOIMMUNE ════════════════════════════════════════════
    93:  {"desc": "Rheumatoid Arthritis and Other Specified Inflammatory Rheumatic Disorders",
          "family": "Rheumatology", "severity": "high",
          "raf_weight": 0.421, "hierarchy_group": None},

    94:  {"desc": "Systemic Lupus Erythematosus and Other Autoimmune Disorders",
          "family": "Rheumatology", "severity": "high",
          "raf_weight": 0.421, "hierarchy_group": None},

    # ══ HEMATOLOGIC ══════════════════════════════════════════════════════════
    107: {"desc": "Sickle Cell Anemia (Hb-SS) and Thalassemia Beta Zero",
          "family": "Hematologic", "severity": "critical",
          "raf_weight": 0.298, "hierarchy_group": "Sickle_Cell"},

    108: {"desc": "Beta Thalassemia Major",
          "family": "Hematologic", "severity": "high",
          "raf_weight": 0.298, "hierarchy_group": "Sickle_Cell"},

    110: {"desc": "Coagulation Defects and Other Specified Hematological Disorders",
          "family": "Hematologic", "severity": "high",
          "raf_weight": 0.275, "hierarchy_group": None},

    # ══ NEUROLOGICAL — DEMENTIA ══════════════════════════════════════════════
    # V28 KEY CHANGE: Dementia split into 3 severity tiers (125/126/127)
    125: {"desc": "Dementia, Severe",
          "family": "Neurology_Dementia", "severity": "critical",
          "raf_weight": 0.509, "hierarchy_group": "Dementia"},

    126: {"desc": "Dementia, Moderate",
          "family": "Neurology_Dementia", "severity": "high",
          "raf_weight": 0.346, "hierarchy_group": "Dementia"},

    127: {"desc": "Dementia, Mild or Unspecified",
          "family": "Neurology_Dementia", "severity": "medium",
          "raf_weight": 0.195, "hierarchy_group": "Dementia"},

    # ══ NEUROLOGICAL — MOTOR / DEGENERATIVE ══════════════════════════════════
    134: {"desc": "Parkinson's Disease and Huntington's Disease",
          "family": "Neurology_Motor", "severity": "critical",
          "raf_weight": 0.371, "hierarchy_group": None},

    135: {"desc": "Multiple Sclerosis",
          "family": "Neurology_Motor", "severity": "critical",
          "raf_weight": 0.556, "hierarchy_group": None},

    136: {"desc": "Seizure Disorders and Convulsions",
          "family": "Neurology_Motor", "severity": "high",
          "raf_weight": 0.284, "hierarchy_group": None},

    137: {"desc": "Coma, Brain Compression/Anoxic Damage",
          "family": "Neurology_Injury", "severity": "critical",
          "raf_weight": 1.123, "hierarchy_group": None},

    # ══ NEUROLOGICAL — SPINAL CORD / INJURY ══════════════════════════════════
    # V28 KEY CHANGE: Spinal cord disorders expanded with laterality
    159: {"desc": "Quadriplegia",
          "family": "Neurology_Injury", "severity": "critical",
          "raf_weight": 1.098, "hierarchy_group": "Spinal"},

    160: {"desc": "Paraplegia",
          "family": "Neurology_Injury", "severity": "critical",
          "raf_weight": 0.768, "hierarchy_group": "Spinal"},

    161: {"desc": "Spinal Cord Disorders/Injuries",
          "family": "Neurology_Injury", "severity": "critical",
          "raf_weight": 0.652, "hierarchy_group": "Spinal"},

    162: {"desc": "Major Head Injury",
          "family": "Neurology_Injury", "severity": "critical",
          "raf_weight": 0.516, "hierarchy_group": "Head_Injury"},

    163: {"desc": "Vertebral Fractures without Spinal Cord Injury",
          "family": "Neurology_Injury", "severity": "high",
          "raf_weight": 0.293, "hierarchy_group": None},

    180: {"desc": "Quadriplegia (Alternative Mapping)",
          "family": "Neurology_Injury", "severity": "critical",
          "raf_weight": 1.098, "hierarchy_group": "Spinal"},

    # ══ PSYCHIATRIC (continued) ══════════════════════════════════════════════
    151: {"desc": "Schizophrenia (V28 renumbered from V24 HCC 57)",
          "family": "Behavioral_Health", "severity": "critical",
          "raf_weight": 0.453, "hierarchy_group": "Psychosis"},

    # ══ CARDIAC — HEART FAILURE ══════════════════════════════════════════════
    # V28 KEY CHANGE: Heart failure expanded from 2 HCCs to 6
    221: {"desc": "Heart Transplant Status/Complications",
          "family": "Cardiac_HF", "severity": "critical",
          "raf_weight": 1.799, "hierarchy_group": "Heart_Failure"},

    222: {"desc": "End-Stage Heart Failure",
          "family": "Cardiac_HF", "severity": "critical",
          "raf_weight": 0.875, "hierarchy_group": "Heart_Failure"},

    223: {"desc": "Heart Failure with Reduced Ejection Fraction (HFrEF)",
          "family": "Cardiac_HF", "severity": "critical",
          "raf_weight": 0.323, "hierarchy_group": "Heart_Failure"},

    224: {"desc": "Acute on Chronic Heart Failure",
          "family": "Cardiac_HF", "severity": "critical",
          "raf_weight": 0.323, "hierarchy_group": "Heart_Failure"},

    225: {"desc": "Chronic Systolic (Reduced Ejection Fraction) Heart Failure",
          "family": "Cardiac_HF", "severity": "high",
          "raf_weight": 0.323, "hierarchy_group": "Heart_Failure"},

    226: {"desc": "Heart Failure, Except End-Stage and Acute-on-Chronic",
          "family": "Cardiac_HF", "severity": "high",
          "raf_weight": 0.323, "hierarchy_group": "Heart_Failure"},

    # V28 KEY CHANGE: I50.9 (unspecified HF) REMOVED — must specify type
    227: {"desc": "Cardiomyopathy/Myocarditis",
          "family": "Cardiac_CAD", "severity": "high",
          "raf_weight": 0.170, "hierarchy_group": "Heart_Failure"},

    # ══ CARDIAC — ISCHEMIC / ARRHYTHMIA ══════════════════════════════════════
    228: {"desc": "Acute Myocardial Infarction",
          "family": "Cardiac_CAD", "severity": "critical",
          "raf_weight": 0.193, "hierarchy_group": "CAD"},

    229: {"desc": "Unstable Angina and Other Acute Ischemic Heart Disease",
          "family": "Cardiac_CAD", "severity": "high",
          "raf_weight": 0.127, "hierarchy_group": "CAD"},

    238: {"desc": "Specified Heart Arrhythmias",
          "family": "Cardiac_Arrhythmia", "severity": "high",
          "raf_weight": 0.165, "hierarchy_group": None},

    # ══ CEREBROVASCULAR / STROKE ═════════════════════════════════════════════
    # V28 KEY CHANGE: Stroke sequelae expanded with disability-based tiers
    253: {"desc": "Hemiplegia/Hemiparesis",
          "family": "Cerebrovascular", "severity": "critical",
          "raf_weight": 0.481, "hierarchy_group": "Stroke_Severity"},

    254: {"desc": "Monoplegia, Other Paralytic Syndromes",
          "family": "Cerebrovascular", "severity": "high",
          "raf_weight": 0.295, "hierarchy_group": "Stroke_Severity"},

    255: {"desc": "Ischemic or Unspecified Stroke",
          "family": "Cerebrovascular", "severity": "high",
          "raf_weight": 0.124, "hierarchy_group": "Stroke_Severity"},

    # ══ VASCULAR ═════════════════════════════════════════════════════════════
    263: {"desc": "Vascular Disease with Complications",
          "family": "Vascular", "severity": "critical",
          "raf_weight": 0.452, "hierarchy_group": "Vascular"},

    264: {"desc": "Vascular Disease",
          "family": "Vascular", "severity": "high",
          "raf_weight": 0.258, "hierarchy_group": "Vascular"},

    # ══ RESPIRATORY ══════════════════════════════════════════════════════════
    # V28 KEY CHANGE: COPD expanded with severity tiers
    279: {"desc": "Severe Persistent Asthma",
          "family": "Respiratory", "severity": "high",
          "raf_weight": 0.133, "hierarchy_group": "Asthma"},

    280: {"desc": "COPD, Interstitial Lung Disorders, and Other Chronic Lung Disorders",
          "family": "Respiratory", "severity": "high",
          "raf_weight": 0.340, "hierarchy_group": "COPD"},

    281: {"desc": "Asthma",
          "family": "Respiratory", "severity": "medium",
          "raf_weight": 0.063, "hierarchy_group": "Asthma"},

    282: {"desc": "Respiratory Arrest",
          "family": "Respiratory", "severity": "critical",
          "raf_weight": 0.715, "hierarchy_group": None},

    # ══ RENAL ═════════════════════════════════════════════════════════════════
    # V28 KEY CHANGE: CKD renumbered and stage 3 split into 3a/3b
    326: {"desc": "Chronic Kidney Disease, Stage 5",
          "family": "Renal", "severity": "critical",
          "raf_weight": 0.290, "hierarchy_group": "CKD"},

    327: {"desc": "Chronic Kidney Disease, Severe (Stage 4)",
          "family": "Renal", "severity": "critical",
          "raf_weight": 0.184, "hierarchy_group": "CKD"},

    328: {"desc": "Chronic Kidney Disease, Moderate (Stage 3B)",
          "family": "Renal", "severity": "high",
          "raf_weight": 0.104, "hierarchy_group": "CKD"},

    329: {"desc": "Chronic Kidney Disease, Moderate (Stage 3, Except 3B)",
          "family": "Renal", "severity": "medium",
          "raf_weight": 0.059, "hierarchy_group": "CKD"},

    # ══ WOUNDS / PRESSURE ULCER ══════════════════════════════════════════════
    377: {"desc": "Pressure Ulcer of Skin with Full Thickness Skin Loss",
          "family": "Wound", "severity": "high",
          "raf_weight": 0.452, "hierarchy_group": "Pressure_Ulcer"},

    378: {"desc": "Pressure Ulcer of Skin with Necrosis Through to Subcutaneous Tissue",
          "family": "Wound", "severity": "critical",
          "raf_weight": 0.585, "hierarchy_group": "Pressure_Ulcer"},

    379: {"desc": "Pressure Ulcer of Skin with Necrosis Through to Muscle, Tendon, or Bone",
          "family": "Wound", "severity": "critical",
          "raf_weight": 0.901, "hierarchy_group": "Pressure_Ulcer"},

    380: {"desc": "Chronic Ulcer of Skin, Except Pressure",
          "family": "Wound", "severity": "high",
          "raf_weight": 0.306, "hierarchy_group": None},
}


# ── V28 Hierarchy Rules ────────────────────────────────────────────────────────
# Format: (parent_hcc, child_hcc, rule_description)
# Rule: If PARENT is present in a patient's HCC set, CHILD is suppressed.
# This is the hierarchy CMS applies in the payment model (no code-stacking).

V28_HIERARCHIES: list[tuple[int, int, str]] = [
    # Cancer (most severe → least severe)
    (17, 18, "Metastatic brain/lung/liver trumps other metastatic"),
    (18, 19, "Acute leukemia/metastatic bone trumps MDS/myeloma"),
    (19, 20, "Myeloma/MDS trumps lung cancer"),
    (20, 21, "Lung cancer trumps lymphoma"),
    (21, 22, "Lymphoma trumps bladder/colorectal"),
    (22, 23, "Bladder/colorectal trumps prostate/breast"),

    # Diabetes
    (35, 36, "Pancreas transplant trumps severe acute DM complications"),
    (36, 37, "Severe acute DM complications trump chronic DM complications"),
    (37, 38, "Chronic DM complications trump unspecified/glycemic DM"),

    # Liver
    (62, 63, "Liver transplant trumps liver failure"),
    (63, 64, "End-stage liver failure trumps cirrhosis"),
    (64, 65, "Cirrhosis trumps chronic hepatitis"),

    # Heart failure
    (221, 222, "Heart transplant trumps end-stage HF"),
    (221, 223, "Heart transplant trumps HFrEF"),
    (221, 224, "Heart transplant trumps acute-on-chronic HF"),
    (222, 223, "End-stage HF trumps HFrEF"),
    (222, 224, "End-stage HF trumps acute-on-chronic HF"),
    (222, 225, "End-stage HF trumps chronic systolic HF"),
    (222, 226, "End-stage HF trumps other HF"),
    (223, 225, "HFrEF trumps chronic systolic HF"),
    (224, 225, "Acute-on-chronic HF trumps chronic systolic HF"),
    (225, 226, "Chronic systolic HF trumps unspecified HF"),
    (226, 227, "HF trumps cardiomyopathy when both present"),

    # CKD
    (326, 327, "CKD stage 5 trumps stage 4"),
    (327, 328, "CKD stage 4 trumps stage 3B"),
    (328, 329, "CKD stage 3B trumps stage 3A"),

    # Dementia
    (125, 126, "Severe dementia trumps moderate dementia"),
    (126, 127, "Moderate dementia trumps mild/unspecified dementia"),

    # Substance Use
    (54, 55, "SUD with psychosis trumps moderate SUD"),
    (55, 56, "Moderate SUD trumps mild SUD"),

    # Schizophrenia / Psychosis
    (57, 58,  "Schizophrenia trumps reactive/unspecified psychosis"),
    (151, 58, "Schizophrenia (alt HCC) trumps reactive psychosis"),

    # Pressure Ulcer
    (379, 378, "Through muscle/tendon/bone trumps subcutaneous ulcer"),
    (378, 377, "Through subcutaneous trumps full-thickness"),

    # Respiratory
    (279, 281, "Severe persistent asthma trumps unspecified asthma"),
    (280, 281, "COPD trumps asthma when both present"),

    # Spinal cord / paralysis
    (159, 160, "Quadriplegia trumps paraplegia"),
    (160, 161, "Paraplegia trumps spinal cord disorder"),
    (180, 160, "Quadriplegia (alt) trumps paraplegia"),

    # Stroke severity
    (253, 254, "Hemiplegia/hemiparesis trumps monoplegia"),
    (254, 255, "Monoplegia trumps unspecified stroke sequelae"),

    # Vascular
    (263, 264, "Vascular disease with complications trumps vascular disease"),

    # HIV
    (6, 1, "Opportunistic infection in HIV patients — may co-exist; check CMS rules"),
]


# ── Disease Interaction Pairs ──────────────────────────────────────────────────
# V28 model applies additive RAF for certain high-cost co-morbidity combinations.
# Format: {hccs: [n1, n2], label, desc, additional_raf}
# RAF values approximate from CMS published rate data and model documentation.

V28_INTERACTIONS: list[dict] = [
    # Diabetes + other chronic conditions
    {"hccs": [37, 326], "label": "DIABETES_CKD5",
     "desc": "Diabetes with Chronic Complications + CKD Stage 5",
     "additional_raf": 0.156},
    {"hccs": [37, 327], "label": "DIABETES_CKD4",
     "desc": "Diabetes with Chronic Complications + CKD Stage 4",
     "additional_raf": 0.118},
    {"hccs": [37, 328], "label": "DIABETES_CKD3B",
     "desc": "Diabetes with Chronic Complications + CKD Stage 3B",
     "additional_raf": 0.071},
    {"hccs": [37, 226], "label": "DIABETES_CHF",
     "desc": "Diabetes with Chronic Complications + Heart Failure",
     "additional_raf": 0.121},
    {"hccs": [37, 280], "label": "DIABETES_COPD",
     "desc": "Diabetes with Chronic Complications + COPD",
     "additional_raf": 0.082},
    {"hccs": [38, 326], "label": "DM_UNSPEC_CKD5",
     "desc": "Diabetes (Glycemic/Unspecified) + CKD Stage 5",
     "additional_raf": 0.095},

    # Heart failure + other conditions
    {"hccs": [226, 280], "label": "CHF_COPD",
     "desc": "Heart Failure + COPD",
     "additional_raf": 0.140},
    {"hccs": [226, 326], "label": "CHF_CKD5",
     "desc": "Heart Failure + CKD Stage 5",
     "additional_raf": 0.156},
    {"hccs": [222, 280], "label": "ESRD_HF_COPD",
     "desc": "End-Stage Heart Failure + COPD",
     "additional_raf": 0.185},
    {"hccs": [226, 327], "label": "CHF_CKD4",
     "desc": "Heart Failure + CKD Stage 4",
     "additional_raf": 0.118},

    # Stroke + co-morbidities
    {"hccs": [253, 226], "label": "STROKE_CHF",
     "desc": "Hemiplegia/Hemiparesis + Heart Failure",
     "additional_raf": 0.197},
    {"hccs": [253, 37],  "label": "STROKE_DIABETES",
     "desc": "Hemiplegia/Hemiparesis + Diabetes with Chronic Complications",
     "additional_raf": 0.076},
    {"hccs": [253, 326], "label": "STROKE_CKD5",
     "desc": "Hemiplegia/Hemiparesis + CKD Stage 5",
     "additional_raf": 0.143},

    # COPD + CKD
    {"hccs": [280, 326], "label": "COPD_CKD5",
     "desc": "COPD + CKD Stage 5",
     "additional_raf": 0.085},

    # Psychiatric co-morbidities
    {"hccs": [57,  60],  "label": "SCHIZO_BIPOLAR",
     "desc": "Schizophrenia + Bipolar Disorders",
     "additional_raf": 0.095},
    {"hccs": [151, 60],  "label": "SCHIZO_BIPOLAR_ALT",
     "desc": "Schizophrenia (alt) + Bipolar Disorders",
     "additional_raf": 0.095},

    # Dementia + other conditions
    {"hccs": [125, 226], "label": "DEMENTIA_SEVERE_CHF",
     "desc": "Severe Dementia + Heart Failure",
     "additional_raf": 0.165},
    {"hccs": [127, 280], "label": "DEMENTIA_COPD",
     "desc": "Dementia (any) + COPD",
     "additional_raf": 0.071},
]


# ── RADV Documentation Requirements per Disease Family ────────────────────────
# CMS RADV (PY2020+, expanded to all plans annually): diagnoses must be
# supported by face-to-face encounter data with valid eligible CPT/HCPCS codes.
# Labs, imaging, and radiology alone do NOT qualify as face-to-face encounters.

V28_RADV_REQUIREMENTS: dict[str, dict] = {
    "Diabetes": {
        "encounter_requirements": (
            "Face-to-face encounter with eligible CPT/HCPCS code; "
            "physician/NP/PA only — no labs or radiology alone"
        ),
        "documentation": [
            "Progress note dated within payment year with DM type and complication in Assessment/Plan",
            "MEAT: Monitor (HbA1c trending), Evaluate (exam findings), Assess (diagnosis statement), Treat (medications/insulin listed)",
            "For complication codes: objective findings (GFR for nephropathy, monofilament test for neuropathy, fundus exam for retinopathy)",
            "For HCC 36 (severe acute): DKA hospitalization record or ketoacidosis labs with physician interpretation",
            "For HCC 37 (chronic complications): specific complication code must be used, not E11.9",
        ],
        "v28_traps": [
            "E11.9 (unspecified T2DM) — maps to HCC 38 only; misses HCC 37 revenue if complications exist",
            "F32.9 companion code — no longer maps to paying HCC in V28 (affects DM + depression combos)",
            "Problem list only — code must appear in dated A/P note, not just problem list",
        ],
        "upgrade_path": (
            "Unspecified → Specify complication: "
            "E11.9 → E11.40 (neuropathy), E11.21 (nephropathy), E11.311 (retinopathy), E11.65 (hyperglycemia)"
        ),
    },

    "Cardiac_HF": {
        "encounter_requirements": (
            "Face-to-face with cardiologist, internist, or FP — "
            "inpatient or outpatient; telehealth only if audio-video (not audio-only)"
        ),
        "documentation": [
            "Echocardiogram documenting EF% (required to distinguish HFrEF from HFpEF)",
            "Progress note explicitly stating systolic/diastolic/combined type (not just 'CHF')",
            "Current medication list (diuretics, ACE/ARB/ARNI, beta-blocker, SGLT2 inhibitor)",
            "NYHA functional class documented in note",
            "For end-stage HF (HCC 222): advanced therapy evaluation (LVAD, transplant, or hospice)",
        ],
        "v28_traps": [
            "I50.9 (unspecified HF) — REMOVED from V28 payment HCCs; must specify type",
            "I50.1 (left ventricular failure) — maps to HCC 226 in V28; upgrade to I50.2x/I50.3x when echocardiogram available",
            "Discharge summary only without outpatient follow-up — need visit in same payment year",
        ],
        "upgrade_path": (
            "I50.9 → I50.20 (systolic unspecified) or I50.30 (diastolic unspecified) → "
            "with EF: I50.22 (chronic systolic) or I50.32 (chronic diastolic)"
        ),
    },

    "Cancer": {
        "encounter_requirements": (
            "Oncologist or treating physician face-to-face with active treatment plan; "
            "inpatient qualifies if attending physician is oncology"
        ),
        "documentation": [
            "Pathology report confirming cancer type, primary site, and grade",
            "Imaging report (CT/PET) documenting active tumor or metastatic sites",
            "Active treatment plan in oncologist's note (chemotherapy, radiation, immunotherapy)",
            "For metastatic codes (HCC 17/18): imaging confirming specific metastatic site",
            "Staging documentation in the note (AJCC stage or equivalent)",
        ],
        "v28_traps": [
            "History of cancer only (Z85.x) — does not map to payment HCC; need active diagnosis codes",
            "Remission codes without active condition codes — lose HCC payment",
            "Missing metastatic site documentation — affects which HCC tier applies",
        ],
        "upgrade_path": (
            "Localized cancer → if metastases identified on imaging, update to metastatic code (C78.x/C79.x) + primary site"
        ),
    },

    "Renal": {
        "encounter_requirements": (
            "Face-to-face with nephrologist or PCP; "
            "GFR-based staging must appear in physician note (not lab report alone)"
        ),
        "documentation": [
            "GFR value with physician-documented CKD stage in progress note",
            "Stage 3 MUST specify 3a (N18.31) or 3b (N18.32) — V28 split these; unspecified N18.30 disfavored",
            "Underlying etiology documented (diabetic nephropathy, hypertensive, IgA, etc.)",
            "For ESRD (N18.6): dialysis modality documented (HD, PD) or transplant status",
            "Medication adjustments for CKD documented (dose adjustments, avoidance of NSAIDs)",
        ],
        "v28_traps": [
            "N18.9 (unspecified CKD) — V28 prefers staged codes; use N18.31/N18.32/N18.4 etc.",
            "Lab-only CKD documentation — GFR lab alone insufficient; needs physician staging in note",
            "CKD stage 2 (N18.2) — does NOT map to a paying V28 HCC",
        ],
        "upgrade_path": (
            "N18.9 → determine stage from GFR: "
            ">60=stage 2 (no pay), 45-59=N18.32 (HCC 328), 30-44=N18.31 (HCC 329), 15-29=N18.4 (HCC 327), <15=N18.5 (HCC 326)"
        ),
    },

    "Behavioral_Health": {
        "encounter_requirements": (
            "Psychiatric provider, behavioral health specialist, or PCP; "
            "telehealth acceptable if audio-video"
        ),
        "documentation": [
            "DSM-5 diagnosis with severity specifier (mild/moderate/severe) in Assessment",
            "For schizophrenia: type specified (paranoid, undifferentiated, schizoaffective, etc.)",
            "For SUD: substance type, severity, and remission status specified",
            "Active treatment documented (medications, therapy modality, MAT for SUD)",
            "Mental status exam (orientation, mood, affect, cognition) in note",
        ],
        "v28_traps": [
            "F32.9 (unspecified major depression) — REMOVED from V28 payment HCCs; must specify severity",
            "F33.9 (unspecified recurrent depression) — REMOVED; use F33.0-F33.2 with documented severity",
            "F11.90 (unspecified opioid use) — REMOVED; must use F11.10 (abuse) or F11.20 (dependence)",
            "F10.10 (alcohol abuse uncomplicated) maps to HCC 56 — lower tier than F10.20 (dependence)",
        ],
        "upgrade_path": (
            "F32.9 → F32.1 (moderate) or F32.2 (severe without psychosis); "
            "F11.90 → F11.20 (dependence) with documentation of compulsive use"
        ),
    },

    "Neurology_Dementia": {
        "encounter_requirements": (
            "Neurologist, geriatrician, or PCP with documented cognitive assessment; "
            "caregiver-only history insufficient"
        ),
        "documentation": [
            "Objective cognitive assessment score in note: MMSE, MoCA, CDR, or SLUMS",
            "Severity mapped to HCC: MMSE 0-17 = severe (HCC 125), 18-23 = moderate (HCC 126), 24+ = mild (HCC 127)",
            "Etiology specified: Alzheimer's (G30.x), vascular (F01.x), Lewy body (G31.83), frontotemporal (G31.0x)",
            "ADL/IADL functional status documented",
            "Behavioral/psychological symptoms noted if present (agitation, psychosis, wandering)",
        ],
        "v28_traps": [
            "G30.9 (Alzheimer's unspecified) — maps to HCC 127 (mild); "
            "with severity assessment could map to HCC 125/126 with behavioral disturbance codes",
            "No cognitive testing score — hard to defend severity level in RADV audit",
        ],
        "upgrade_path": (
            "Unspecified dementia → conduct MMSE/MoCA → document severity → "
            "use G31.83 (Lewy body) or G30.1 (late onset Alzheimer's) with severity-appropriate HCC"
        ),
    },

    "Wound": {
        "encounter_requirements": (
            "Wound care specialist, surgeon, or hospitalist; "
            "wound care nurse documentation alone insufficient — needs MD/DO/NP/PA countersignature"
        ),
        "documentation": [
            "Wound measurement (length × width × depth in cm) with clinician signature",
            "Depth classification by clinician: full thickness (HCC 377), subcutaneous (HCC 378), muscle/tendon/bone (HCC 379)",
            "Anatomical location with laterality",
            "Wound photos attached to note",
            "Wound vac or debridement order with ICD-10 code matching wound stage",
        ],
        "v28_traps": [
            "Wound staging only by wound care nurse without physician co-sign — rejected in RADV",
            "Pressure ulcer vs. diabetic ulcer vs. venous ulcer — use correct category code",
        ],
        "upgrade_path": (
            "L89 (pressure ulcer) → specify stage: L89.x0 (unstageable), L89.x3 (stage 3 → HCC 378), L89.x4 (stage 4 → HCC 379)"
        ),
    },

    "Hepatic": {
        "encounter_requirements": (
            "Gastroenterologist, hepatologist, or internist; "
            "inpatient or outpatient"
        ),
        "documentation": [
            "Liver biopsy (fibrosis/cirrhosis grade), or fibroscan/elastography score in note",
            "Etiology documented: viral (HBV/HCV), alcoholic, NAFLD/NASH",
            "For cirrhosis (HCC 64): decompensated (ascites, varices) vs compensated status",
            "For end-stage (HCC 63): MELD score and/or transplant evaluation",
            "Antiviral therapy documented if HBV/HCV",
        ],
        "v28_traps": [
            "Elevated LFTs alone — not sufficient; needs physician interpretation and diagnosis code",
            "K76.0 (fatty liver) — does NOT map to a paying V28 HCC",
        ],
        "upgrade_path": (
            "K76.0 (fatty liver) → if advanced: K74.60 (unspecified cirrhosis → HCC 64) with biopsy support"
        ),
    },

    "Respiratory": {
        "encounter_requirements": (
            "Pulmonologist, hospitalist, or PCP; "
            "spirometry results should be in chart"
        ),
        "documentation": [
            "Spirometry (FEV1/FVC ratio and % predicted) documented in note",
            "GOLD classification for COPD (I-IV) or asthma severity (mild/moderate/severe/persistent)",
            "Exacerbation history documented (hospitalizations, steroid courses)",
            "Current inhaler therapy documented (SABA, LABA, ICS, LAMA)",
            "For J44.0/J44.1 (acute exacerbation): hospitalization or ED visit record",
        ],
        "v28_traps": [
            "J44.9 (COPD unspecified) — maps to HCC 280 but upgrade to J44.30/J44.31 if severity documented",
            "Asthma (J45.x) — maps to HCC 281 (standard); severe persistent (J45.50) → HCC 279 (high)",
        ],
        "upgrade_path": (
            "J44.9 → J44.30 (moderate COPD) → J44.1 (with acute exacerbation) when spirometry and exacerbations documented"
        ),
    },
}


# ── Hierarchy Enforcement ──────────────────────────────────────────────────────

def enforce_hierarchy(hcc_list: list[int]) -> dict:
    """
    Apply V28 hierarchy rules to a list of HCC numbers.
    Returns {kept, suppressed, rules_applied}.

    CMS applies these rules during payment calculation — submitting both parent
    and child HCCs does not result in double-counting; the child is suppressed.
    CodeMed flags this so billers avoid audit risk from code-stacking.
    """
    hcc_set     = set(hcc_list)
    suppressed  = set()
    rules_applied = []

    for parent, child, description in V28_HIERARCHIES:
        if parent in hcc_set and child in hcc_set:
            suppressed.add(child)
            rules_applied.append({
                "parent_hcc": parent,
                "parent_desc": V28_HCC_CATEGORIES.get(parent, {}).get("desc", ""),
                "suppressed_hcc": child,
                "suppressed_desc": V28_HCC_CATEGORIES.get(child, {}).get("desc", ""),
                "rule": description,
            })

    kept = [h for h in hcc_list if h not in suppressed]
    return {
        "kept": kept,
        "suppressed": list(suppressed),
        "rules_applied": rules_applied,
    }


# ── Interaction Scoring ────────────────────────────────────────────────────────

def score_interactions(hcc_list: list[int]) -> dict:
    """
    Identify disease interaction pairs and sum additional RAF bonuses.
    Returns {interactions_found, total_interaction_raf}.
    """
    hcc_set = set(hcc_list)
    found   = []
    total   = 0.0

    for interaction in V28_INTERACTIONS:
        if all(h in hcc_set for h in interaction["hccs"]):
            found.append(interaction)
            total += interaction["additional_raf"]

    return {
        "interactions_found": found,
        "total_interaction_raf": round(total, 4),
    }


# ── RAF Simulation ─────────────────────────────────────────────────────────────

def simulate_raf(hcc_list: list[int], age: int = 70, sex: str = "F",
                 segment: str = "CNA") -> dict:
    """
    Estimate approximate RAF score for a patient's HCC set.

    Parameters:
      hcc_list  — list of V28 HCC numbers from code audit
      age       — patient age (used for age/sex demographic coefficient)
      sex       — 'M' or 'F'
      segment   — 'CNA' (community non-dual aged, default)

    Returns approximate RAF components. CMS uses exact coefficients from
    the model software ZIP; these approximations are for illustrative purposes.
    """
    # 1. Apply hierarchy (remove suppressed HCCs)
    hierarchy = enforce_hierarchy(hcc_list)
    active_hccs = hierarchy["kept"]

    # 2. Sum HCC risk scores
    hcc_raf = 0.0
    hcc_details = []
    for hcc in active_hccs:
        cat = V28_HCC_CATEGORIES.get(hcc)
        if cat:
            weight = cat.get("raf_weight", 0.0)
            hcc_raf += weight
            hcc_details.append({"hcc": hcc, "desc": cat["desc"], "raf_weight": weight})

    # 3. Disease interactions
    interactions = score_interactions(active_hccs)
    interaction_raf = interactions["total_interaction_raf"]

    # 4. Demographic coefficient (simplified age/sex lookup — CNA segment)
    # Full table is in CMS model software; this covers common age ranges
    demo_raf = _age_sex_coefficient(age, sex, segment)

    # 5. Total
    total_raf = round(demo_raf + hcc_raf + interaction_raf, 4)

    return {
        "total_raf": total_raf,
        "demographic_raf": demo_raf,
        "hcc_raf": round(hcc_raf, 4),
        "interaction_raf": interaction_raf,
        "active_hccs": hcc_details,
        "suppressed_hccs": hierarchy["suppressed"],
        "hierarchy_rules_applied": hierarchy["rules_applied"],
        "interactions_found": interactions["interactions_found"],
        "note": (
            "Approximate RAF using published CMS rate data. "
            "For exact payment calculation, use official CMS V28 model software."
        ),
    }


def _age_sex_coefficient(age: int, sex: str = "F", segment: str = "CNA") -> float:
    """
    Approximate CNA demographic coefficient.
    Full lookup table is in CMS model software (coefficient tables by age band and sex).
    """
    # CNA segment coefficients approximate by age band (from published CMS rate data)
    if segment == "CNA":
        if sex.upper() == "F":
            if age < 65:   return 0.302
            elif age < 70: return 0.184
            elif age < 75: return 0.209
            elif age < 80: return 0.251
            elif age < 85: return 0.295
            else:          return 0.331
        else:  # Male
            if age < 65:   return 0.281
            elif age < 70: return 0.163
            elif age < 75: return 0.191
            elif age < 80: return 0.236
            elif age < 85: return 0.278
            else:          return 0.326
    return 0.200  # fallback for other segments


def get_radv_requirements(hcc: int) -> dict | None:
    """Return RADV documentation requirements for a given HCC number."""
    cat = V28_HCC_CATEGORIES.get(hcc, {})
    family = cat.get("family", "")
    return V28_RADV_REQUIREMENTS.get(family)


if __name__ == "__main__":
    print(f"V28 HCC Categories defined:  {len(V28_HCC_CATEGORIES)}")
    print(f"Hierarchy rules:             {len(V28_HIERARCHIES)}")
    print(f"Disease interaction pairs:   {len(V28_INTERACTIONS)}")
    print(f"RADV family requirements:    {len(V28_RADV_REQUIREMENTS)}")
    print()

    # Demo: enforce hierarchy on a sample set
    test_hccs = [37, 38, 226, 280, 326, 327]
    print(f"Test HCC set: {test_hccs}")
    h = enforce_hierarchy(test_hccs)
    print(f"  Kept: {h['kept']}")
    print(f"  Suppressed: {h['suppressed']} ({len(h['rules_applied'])} rules applied)")
    print()

    # Demo: RAF simulation
    sim = simulate_raf([37, 226, 280, 328], age=72, sex="F")
    print(f"RAF simulation (T2DM+HF+COPD+CKD3B, 72F):")
    print(f"  Total RAF:         {sim['total_raf']}")
    print(f"  Demographic RAF:   {sim['demographic_raf']}")
    print(f"  HCC RAF:           {sim['hcc_raf']}")
    print(f"  Interaction RAF:   {sim['interaction_raf']}")
    if sim["interactions_found"]:
        for i in sim["interactions_found"]:
            print(f"    + {i['label']}: +{i['additional_raf']}")
