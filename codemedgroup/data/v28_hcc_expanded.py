"""
CodeMed Group — Expanded V28 HCC Code Mappings
~400 high-revenue codes covering the major V28 changes vs V24.

Tuple format: (icd10_code, description, v28_hcc, v24_hcc, v28_pays, v24_pays, hcc_label, payment_tier)
  - v28_hcc / v24_hcc: HCC number as string, or None if not mapped
  - v28_pays / v24_pays: 1=maps to a paying HCC, 0=not mapped
  - payment_tier: 'critical' | 'high' | 'medium' | 'standard'

These supplement the 43-code seed in build_seed_db.py.
Import and merge with V28_CODES to get the full set.
"""

# ── Chapter E — Endocrine / Metabolic (Diabetes full matrix) ─
DIABETES_CODES = [
    # Type 1 DM complications — V28 HCC 35 (E10 series)
    ("E10.10", "Type 1 diabetes with diabetic nephropathy, unspecified", "35", "18", 1, 1, "Diabetes with Renal or Peripheral Circulatory Manifestation", "critical"),
    ("E10.11", "Type 1 diabetes with diabetic mononeuropathy", "35", "18", 1, 1, "Diabetes with Neurological or Other Specified Manifestation", "high"),
    ("E10.21", "Type 1 diabetes with diabetic nephropathy", "35", "18", 1, 1, "Diabetes with Renal Manifestation", "critical"),
    ("E10.22", "Type 1 diabetes with diabetic CKD stage 1", "35", "18", 1, 1, "Diabetes with Renal Manifestation", "critical"),
    ("E10.29", "Type 1 diabetes with other diabetic kidney complication", "35", "18", 1, 1, "Diabetes with Renal Manifestation", "critical"),
    ("E10.311", "Type 1 diabetes with unspecified diabetic retinopathy with macular edema", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.319", "Type 1 diabetes with unspecified diabetic retinopathy without macular edema", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.3211", "Type 1 diabetes with mild nonproliferative retinopathy with macular edema, right eye", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.3212", "Type 1 diabetes with mild nonproliferative retinopathy with macular edema, left eye", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.3291", "Type 1 diabetes with mild nonproliferative retinopathy without macular edema, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.3292", "Type 1 diabetes with mild nonproliferative retinopathy without macular edema, left", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.3311", "Type 1 diabetes with moderate nonproliferative diabetic retinopathy with macular edema, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.3391", "Type 1 diabetes with moderate nonproliferative retinopathy without macular edema, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E10.3411", "Type 1 diabetes with severe nonproliferative retinopathy with macular edema, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "critical"),
    ("E10.3491", "Type 1 diabetes with severe nonproliferative retinopathy without macular edema, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "critical"),
    ("E10.3511", "Type 1 diabetes with proliferative diabetic retinopathy with macular edema, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "critical"),
    ("E10.3521", "Type 1 diabetes with proliferative retinopathy with traction retinal detachment, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "critical"),
    ("E10.3591", "Type 1 diabetes with proliferative retinopathy without macular edema, right", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "critical"),
    ("E10.36", "Type 1 diabetes with diabetic cataract", "35", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "medium"),
    ("E10.40", "Type 1 diabetes with diabetic neuropathy, unspecified", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E10.41", "Type 1 diabetes with diabetic mononeuropathy", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E10.42", "Type 1 diabetes with diabetic polyneuropathy", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E10.43", "Type 1 diabetes with diabetic autonomic neuropathy", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E10.44", "Type 1 diabetes with diabetic amyotrophy", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "critical"),
    ("E10.49", "Type 1 diabetes with other diabetic neurological complication", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E10.51", "Type 1 diabetes with diabetic peripheral angiopathy without gangrene", "107", "107", 1, 1, "Vascular Disease with Complications", "critical"),
    ("E10.52", "Type 1 diabetes with diabetic peripheral angiopathy with gangrene", "107", "107", 1, 1, "Vascular Disease with Complications", "critical"),
    ("E10.59", "Type 1 diabetes with other circulatory complications", "107", "107", 1, 1, "Vascular Disease with Complications", "critical"),
    ("E10.610", "Type 1 diabetes with diabetic neuropathic arthropathy", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E10.618", "Type 1 diabetes with other diabetic arthropathy", "35", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E10.620", "Type 1 diabetes with diabetic dermatitis", "35", "18", 1, 1, "Diabetes with Ophthalmologic or Other Manifestation", "medium"),
    ("E10.621", "Type 1 diabetes with foot ulcer", "161", "161", 1, 1, "Chronic Ulcer of Skin", "critical"),
    ("E10.622", "Type 1 diabetes with other skin ulcer", "161", "161", 1, 1, "Chronic Ulcer of Skin", "critical"),
    ("E10.628", "Type 1 diabetes with other skin complications", "35", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    ("E10.630", "Type 1 diabetes with periodontal disease", "35", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    ("E10.649", "Type 1 diabetes with hypoglycemia without coma", "35", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    ("E10.65", "Type 1 diabetes with hyperglycemia", "35", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    ("E10.69", "Type 1 diabetes with other specified complications", "35", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    # Type 2 DM complications — V28 HCC 36
    ("E11.21", "Type 2 diabetes with diabetic nephropathy", "36", "18", 1, 1, "Diabetes with Renal Manifestation", "critical"),
    ("E11.22", "Type 2 diabetes with diabetic CKD stage 1", "36", "18", 1, 1, "Diabetes with Renal Manifestation", "critical"),
    ("E11.29", "Type 2 diabetes with other diabetic kidney complication", "36", "18", 1, 1, "Diabetes with Renal Manifestation", "critical"),
    ("E11.311", "Type 2 diabetes with unspecified retinopathy with macular edema", "36", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E11.319", "Type 2 diabetes with unspecified retinopathy without macular edema", "36", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E11.3211", "Type 2 diabetes with mild nonproliferative retinopathy with macular edema, right", "36", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "high"),
    ("E11.3511", "Type 2 diabetes with proliferative retinopathy with macular edema, right", "36", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "critical"),
    ("E11.3521", "Type 2 diabetes with proliferative retinopathy with traction detachment, right", "36", "18", 1, 1, "Diabetes with Ophthalmologic Manifestation", "critical"),
    ("E11.40", "Type 2 diabetes with diabetic neuropathy, unspecified", "36", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E11.41", "Type 2 diabetes with diabetic mononeuropathy", "36", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E11.42", "Type 2 diabetes with diabetic polyneuropathy", "36", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E11.43", "Type 2 diabetes with diabetic autonomic neuropathy", "36", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E11.44", "Type 2 diabetes with diabetic amyotrophy", "36", "18", 1, 1, "Diabetes with Neurological Manifestation", "critical"),
    ("E11.49", "Type 2 diabetes with other neurological complication", "36", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E11.51", "Type 2 diabetes with diabetic peripheral angiopathy without gangrene", "107", "107", 1, 1, "Vascular Disease with Complications", "critical"),
    ("E11.52", "Type 2 diabetes with diabetic peripheral angiopathy with gangrene", "107", "107", 1, 1, "Vascular Disease with Complications", "critical"),
    ("E11.610", "Type 2 diabetes with diabetic neuropathic arthropathy", "36", "18", 1, 1, "Diabetes with Neurological Manifestation", "high"),
    ("E11.621", "Type 2 diabetes with foot ulcer", "161", "161", 1, 1, "Chronic Ulcer of Skin", "critical"),
    ("E11.622", "Type 2 diabetes with other skin ulcer", "161", "161", 1, 1, "Chronic Ulcer of Skin", "critical"),
    ("E11.649", "Type 2 diabetes with hypoglycemia without coma", "36", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    ("E11.65", "Type 2 diabetes with hyperglycemia", "36", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    ("E11.69", "Type 2 diabetes with other specified complications", "36", "18", 1, 1, "Diabetes with Other Manifestations", "medium"),
    # Obesity
    ("E66.09", "Other obesity due to excess calories", None, None, 0, 0, "Morbid Obesity", "medium"),
    ("E66.1", "Drug-induced obesity", None, None, 0, 0, "Obesity", "medium"),
    ("E66.2", "Morbid obesity with alveolar hypoventilation", "48", "23", 1, 1, "Morbid Obesity", "high"),
    ("E66.3", "Overweight", None, None, 0, 0, "Overweight", "standard"),
]

# ── Chapter I — Circulatory ───────────────────────────────────
CIRCULATORY_CODES = [
    # Heart failure — V28 reorganized significantly
    ("I50.20", "Systolic heart failure, unspecified", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.21", "Acute systolic heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.23", "Acute on chronic systolic heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.30", "Diastolic heart failure, unspecified", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.31", "Acute diastolic heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.33", "Acute on chronic diastolic heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.40", "Combined systolic and diastolic heart failure, unspecified", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.41", "Acute combined systolic and diastolic heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.42", "Chronic combined systolic and diastolic heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.43", "Acute on chronic combined systolic and diastolic heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.810", "Right heart failure, unspecified", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.811", "Acute right heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.812", "Chronic right heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.813", "Acute on chronic right heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.814", "Right heart failure due to left heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.82", "Biventricular heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.83", "High output heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.84", "End stage heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I50.89", "Other heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    # Atrial fibrillation
    ("I48.0", "Paroxysmal atrial fibrillation", "96", "96", 1, 1, "Atrial Fibrillation", "high"),
    ("I48.3", "Typical atrial flutter", "96", "96", 1, 1, "Atrial Flutter", "high"),
    ("I48.4", "Atypical atrial flutter", "96", "96", 1, 1, "Atrial Flutter", "high"),
    ("I48.91", "Unspecified atrial fibrillation", "96", "96", 1, 1, "Atrial Fibrillation", "high"),
    # Coronary artery disease
    ("I25.10", "Atherosclerotic heart disease of native coronary artery without angina", "88", "88", 1, 1, "Ischemic or Unspecified Heart Disease", "high"),
    ("I25.110", "Atherosclerotic heart disease of native coronary artery with unstable angina", "88", "88", 1, 1, "Ischemic or Unspecified Heart Disease", "critical"),
    ("I25.111", "Atherosclerotic heart disease with angina pectoris with documented spasm", "88", "88", 1, 1, "Ischemic or Unspecified Heart Disease", "high"),
    ("I25.118", "Atherosclerotic heart disease with other forms of angina pectoris", "88", "88", 1, 1, "Ischemic or Unspecified Heart Disease", "high"),
    ("I25.119", "Atherosclerotic heart disease with unspecified angina pectoris", "88", "88", 1, 1, "Ischemic or Unspecified Heart Disease", "high"),
    ("I25.5", "Ischemic cardiomyopathy", "85", "85", 1, 1, "Cardiomyopathy", "critical"),
    ("I25.6", "Silent myocardial ischemia", "88", "88", 1, 1, "Ischemic Heart Disease", "high"),
    # Atherosclerosis / peripheral arterial disease — V28 added laterality
    ("I70.201", "Unspecified atherosclerosis of native arteries, right leg", "107", "107", 1, 1, "Peripheral Arterial Disease", "high"),
    ("I70.202", "Unspecified atherosclerosis of native arteries, left leg", "107", "107", 1, 1, "Peripheral Arterial Disease", "high"),
    ("I70.211", "Atherosclerosis of native arteries of right leg with intermittent claudication", "107", "107", 1, 1, "Peripheral Arterial Disease", "high"),
    ("I70.212", "Atherosclerosis of native arteries of left leg with intermittent claudication", "107", "107", 1, 1, "Peripheral Arterial Disease", "high"),
    ("I70.221", "Atherosclerosis of native arteries of right leg with rest pain", "107", "107", 1, 1, "Peripheral Arterial Disease", "critical"),
    ("I70.222", "Atherosclerosis of native arteries of left leg with rest pain", "107", "107", 1, 1, "Peripheral Arterial Disease", "critical"),
    ("I70.231", "Atherosclerosis of native arteries right leg with ulceration of thigh", "107", "107", 1, 1, "Peripheral Arterial Disease with Ulceration", "critical"),
    ("I70.241", "Atherosclerosis of native arteries right leg with gangrene", "106", "106", 1, 1, "Vascular Disease with Complications", "critical"),
    ("I70.242", "Atherosclerosis of native arteries left leg with gangrene", "106", "106", 1, 1, "Vascular Disease with Complications", "critical"),
    # Cerebrovascular
    ("I63.00", "Cerebral infarction due to thrombosis of unspecified precerebral artery", "100", "100", 1, 1, "Ischemic or Unspecified Stroke", "critical"),
    ("I63.10", "Cerebral infarction due to embolism of unspecified precerebral artery", "100", "100", 1, 1, "Ischemic or Unspecified Stroke", "critical"),
    ("I63.20", "Cerebral infarction due to unspecified occlusion of unspecified precerebral artery", "100", "100", 1, 1, "Ischemic or Unspecified Stroke", "critical"),
    ("I63.30", "Cerebral infarction due to thrombosis of unspecified cerebral artery", "100", "100", 1, 1, "Ischemic or Unspecified Stroke", "critical"),
    ("I63.40", "Cerebral infarction due to embolism of unspecified cerebral artery", "100", "100", 1, 1, "Ischemic or Unspecified Stroke", "critical"),
    ("I63.50", "Cerebral infarction due to unspecified occlusion of unspecified cerebral artery", "100", "100", 1, 1, "Ischemic or Unspecified Stroke", "critical"),
    # Sequelae of cerebrovascular disease — V28 reorganized
    ("I69.10", "Unspecified sequelae of nontraumatic subarachnoid hemorrhage", "100", "100", 1, 1, "Residual Neurological Condition", "high"),
    ("I69.30", "Unspecified sequelae of cerebral infarction", "100", "100", 1, 1, "Residual Neurological Condition", "high"),
    ("I69.351", "Hemiplegia and hemiparesis following cerebral infarction, right dominant side", "103", "103", 1, 1, "Hemiplegia / Hemiparesis", "critical"),
    ("I69.352", "Hemiplegia and hemiparesis following cerebral infarction, left dominant side", "103", "103", 1, 1, "Hemiplegia / Hemiparesis", "critical"),
    ("I69.390", "Aphasia following cerebral infarction", "100", "100", 1, 1, "Residual Neurological Condition", "high"),
    # Hypertensive heart disease
    ("I11.0", "Hypertensive heart disease with heart failure", "86", "85", 1, 1, "Congestive Heart Failure", "critical"),
    ("I11.9", "Hypertensive heart disease without heart failure", "88", "88", 1, 1, "Ischemic Heart Disease", "medium"),
    ("I13.10", "Hypertensive heart and CKD, stage 1-4, without heart failure", "136", "136", 1, 1, "CKD (4-5)", "high"),
    ("I13.11", "Hypertensive heart and CKD, stage 5, without heart failure", "136", "136", 1, 1, "CKD (5)", "critical"),
    # Pulmonary hypertension
    ("I27.0", "Primary pulmonary hypertension", "85", "85", 1, 1, "Pulmonary Heart Disease", "critical"),
    ("I27.20", "Pulmonary arterial hypertension, unspecified", "85", "85", 1, 1, "Pulmonary Heart Disease", "critical"),
    ("I27.21", "Primary Group 1 pulmonary arterial hypertension", "85", "85", 1, 1, "Pulmonary Heart Disease", "critical"),
    ("I27.29", "Other secondary pulmonary arterial hypertension", "85", "85", 1, 1, "Pulmonary Heart Disease", "critical"),
]

# ── Chapter F — Mental and Behavioral Disorders ───────────────
# V28 major changes: schizophrenia HCC 157 new; unspecified depression removed
MENTAL_CODES = [
    # Schizophrenia — V28 HCC 157 (new HCC)
    ("F20.0", "Paranoid schizophrenia", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F20.1", "Disorganized schizophrenia", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F20.2", "Catatonic schizophrenia", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F20.3", "Undifferentiated schizophrenia", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F20.5", "Residual schizophrenia", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F20.81", "Schizophreniform disorder", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F20.89", "Other schizophrenia", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F20.9", "Schizophrenia, unspecified", "157", "57", 1, 1, "Schizophrenia", "critical"),
    ("F25.0", "Schizoaffective disorder, bipolar type", "157", "57", 1, 1, "Schizoaffective Disorder", "critical"),
    ("F25.1", "Schizoaffective disorder, depressive type", "157", "57", 1, 1, "Schizoaffective Disorder", "critical"),
    ("F25.9", "Schizoaffective disorder, unspecified", "157", "57", 1, 1, "Schizoaffective Disorder", "critical"),
    # Bipolar — V28 HCC 87
    ("F31.10", "Bipolar disorder, current episode manic without psychosis, unspecified", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    ("F31.11", "Bipolar disorder, current episode manic without psychosis, mild", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    ("F31.12", "Bipolar disorder, current episode manic without psychosis, moderate", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    ("F31.13", "Bipolar disorder, current episode manic without psychosis, severe", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    ("F31.2", "Bipolar disorder, current episode manic with psychotic features", "87", "57", 1, 1, "Bipolar Disorders", "critical"),
    ("F31.30", "Bipolar disorder, current episode depressed, mild or moderate, unspecified", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    ("F31.31", "Bipolar disorder, current episode depressed, mild", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    ("F31.4", "Bipolar disorder, current episode depressed, severe, without psychotic features", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    ("F31.5", "Bipolar disorder, current episode depressed, severe, with psychotic features", "87", "57", 1, 1, "Bipolar Disorders", "critical"),
    ("F31.81", "Bipolar II disorder", "87", "57", 1, 1, "Bipolar Disorders", "high"),
    # Depression — V28 REMOVED unspecified codes; only specified pay
    ("F32.0", "Major depressive disorder, single, mild", "88", "55", 1, 1, "Major Depressive Disorder", "medium"),
    ("F32.1", "Major depressive disorder, single, moderate", "88", "55", 1, 1, "Major Depressive Disorder", "medium"),
    ("F32.2", "Major depressive disorder, single, severe without psychotic features", "88", "55", 1, 1, "Major Depressive Disorder", "high"),
    ("F32.3", "Major depressive disorder, single, severe with psychotic features", "88", "55", 1, 1, "Major Depressive Disorder", "high"),
    ("F32.4", "Major depressive disorder, single episode, in partial remission", "88", "55", 1, 1, "Major Depressive Disorder", "medium"),
    ("F32.5", "Major depressive disorder, single episode, in full remission", None, "55", 0, 1, "Remission — V28 Removed", "medium"),
    ("F32.9", "Major depressive disorder, single episode, unspecified", None, "55", 0, 1, "V28 Rejected — Unspecified Depression", "high"),  # KEY REJECTION
    ("F33.0", "Major depressive disorder, recurrent, mild", "88", "55", 1, 1, "Major Depressive Disorder, Recurrent", "medium"),
    ("F33.1", "Major depressive disorder, recurrent, moderate", "88", "55", 1, 1, "Major Depressive Disorder, Recurrent", "medium"),
    ("F33.2", "Major depressive disorder, recurrent, severe without psychotic features", "88", "55", 1, 1, "Major Depressive Disorder, Recurrent", "high"),
    ("F33.3", "Major depressive disorder, recurrent, severe with psychotic symptoms", "88", "55", 1, 1, "Major Depressive Disorder, Recurrent", "high"),
    ("F33.9", "Major depressive disorder, recurrent, unspecified", None, "55", 0, 1, "V28 Rejected — Unspecified Recurrent Depression", "high"),  # KEY REJECTION
    # Substance use disorders — V28 major additions
    ("F10.10", "Alcohol abuse, uncomplicated", "56", "56", 1, 1, "Alcohol and Drug Dependence", "medium"),
    ("F10.20", "Alcohol dependence, uncomplicated", "56", "56", 1, 1, "Alcohol Dependence", "high"),
    ("F10.21", "Alcohol dependence, in remission", "56", "56", 1, 1, "Alcohol Dependence", "medium"),
    ("F10.230", "Alcohol dependence with withdrawal, uncomplicated", "56", "56", 1, 1, "Alcohol Dependence with Withdrawal", "high"),
    ("F11.10", "Opioid abuse, uncomplicated", "56", "56", 1, 1, "Drug Dependence", "high"),
    ("F11.20", "Opioid dependence, uncomplicated", "56", "56", 1, 1, "Opioid Dependence", "high"),
    ("F11.21", "Opioid dependence, in remission", "56", "56", 1, 1, "Opioid Dependence", "medium"),
    ("F11.90", "Opioid use disorder, unspecified, uncomplicated", None, "56", 0, 1, "V28 Rejected — Unspecified Opioid Use", "high"),
    ("F12.20", "Cannabis dependence, uncomplicated", "56", "56", 1, 1, "Drug Dependence", "medium"),
    ("F14.20", "Cocaine dependence, uncomplicated", "56", "56", 1, 1, "Drug Dependence", "high"),
    ("F19.20", "Other psychoactive substance dependence, uncomplicated", "56", "56", 1, 1, "Drug Dependence", "high"),
    # Personality disorders
    ("F60.3", "Borderline personality disorder", "87", "57", 1, 1, "Personality Disorders", "high"),
    ("F60.4", "Histrionic personality disorder", "87", "57", 1, 1, "Personality Disorders", "medium"),
    # Autism spectrum disorders
    ("F84.0", "Autistic disorder", "161", "120", 1, 1, "Autism Spectrum Disorders", "critical"),
    ("F84.5", "Asperger's syndrome", "161", "120", 1, 1, "Autism Spectrum Disorders", "high"),
    ("F84.9", "Pervasive developmental disorder, unspecified", "161", "120", 1, 1, "Autism Spectrum Disorders", "medium"),
]

# ── Chapter B — Infectious Diseases ──────────────────────────
INFECTIOUS_CODES = [
    ("B20", "Human immunodeficiency virus [HIV] disease", "1", "1", 1, 1, "HIV/AIDS", "critical"),
    ("B18.0", "Chronic viral hepatitis B with delta-agent", "29", "29", 1, 1, "Chronic Hepatitis", "high"),
    ("B18.1", "Chronic viral hepatitis B without delta-agent", "29", "29", 1, 1, "Chronic Hepatitis", "high"),
    ("B18.2", "Chronic viral hepatitis C", "29", "29", 1, 1, "Chronic Hepatitis C", "high"),
    ("B18.8", "Other chronic viral hepatitis", "29", "29", 1, 1, "Chronic Hepatitis", "medium"),
    ("B18.9", "Chronic viral hepatitis, unspecified", "29", "29", 1, 1, "Chronic Hepatitis", "medium"),
    ("B19.10", "Unspecified viral hepatitis B without hepatic coma", "29", "29", 1, 1, "Chronic Hepatitis", "medium"),
    ("B19.20", "Unspecified viral hepatitis C without hepatic coma", "29", "29", 1, 1, "Chronic Hepatitis C", "high"),
]

# ── Chapter G — Nervous System ────────────────────────────────
NERVOUS_CODES = [
    ("G10", "Huntington's disease", "70", "70", 1, 1, "Huntington's Disease and Other Hereditary/Degenerative CNS", "critical"),
    ("G11.1", "Early-onset cerebellar ataxia", "73", "73", 1, 1, "Hereditary Ataxia", "high"),
    ("G11.9", "Hereditary ataxia, unspecified", "73", "73", 1, 1, "Hereditary Ataxia", "high"),
    ("G12.21", "Amyotrophic lateral sclerosis (ALS)", "70", "70", 1, 1, "Motor Neuron Disease", "critical"),
    ("G12.29", "Other motor neuron disease", "70", "70", 1, 1, "Motor Neuron Disease", "critical"),
    ("G20.A1", "Parkinson's disease without dyskinesia, without mention of fluctuations", "73", "73", 1, 1, "Parkinson's Disease", "critical"),
    ("G20.A2", "Parkinson's disease without dyskinesia, with fluctuations", "73", "73", 1, 1, "Parkinson's Disease", "critical"),
    ("G20.B1", "Parkinson's disease with dyskinesia, without fluctuations", "73", "73", 1, 1, "Parkinson's Disease", "critical"),
    ("G20.C", "Parkinsonism, unspecified", "73", "73", 1, 1, "Parkinsonism", "high"),
    ("G30.0", "Alzheimer's disease with early onset", "52", "52", 1, 1, "Dementia with or without Behavioral Disturbance", "critical"),
    ("G30.1", "Alzheimer's disease with late onset", "52", "52", 1, 1, "Dementia with or without Behavioral Disturbance", "critical"),
    ("G30.8", "Other Alzheimer's disease", "52", "52", 1, 1, "Dementia with or without Behavioral Disturbance", "critical"),
    ("G31.01", "Pick's disease", "52", "52", 1, 1, "Dementia with Behavioral Disturbance", "critical"),
    ("G31.09", "Other frontotemporal dementia", "52", "52", 1, 1, "Frontotemporal Dementia", "critical"),
    ("G31.83", "Dementia with Lewy bodies", "52", "52", 1, 1, "Dementia with Lewy Bodies", "critical"),
    ("G40.001", "Localization-related idiopathic epilepsy, intractable, with status epilepticus", "79", "79", 1, 1, "Convulsive Disorders", "critical"),
    ("G40.011", "Localization-related idiopathic epilepsy, intractable, without status epilepticus", "79", "79", 1, 1, "Convulsive Disorders", "critical"),
    ("G40.101", "Localization-related symptomatic epilepsy, intractable, with status", "79", "79", 1, 1, "Convulsive Disorders", "critical"),
    ("G40.201", "Localization-related symptomatic epilepsy with complex partial seizures, intractable", "79", "79", 1, 1, "Convulsive Disorders", "critical"),
    ("G40.301", "Generalized idiopathic epilepsy, intractable, with status epilepticus", "79", "79", 1, 1, "Convulsive Disorders", "critical"),
    ("G40.401", "Other generalized epilepsy, intractable, with status epilepticus", "79", "79", 1, 1, "Convulsive Disorders", "critical"),
    ("G40.901", "Epilepsy, unspecified, intractable, with status epilepticus", "79", "79", 1, 1, "Convulsive Disorders", "critical"),
]

# ── Chapter N — Genitourinary (CKD) ──────────────────────────
# V28 added stage 3 subcategories N18.31 / N18.32
RENAL_CODES = [
    ("N18.31", "Chronic kidney disease, stage 3a", "137", "137", 1, 1, "CKD (Stage 3-5)", "high"),
    ("N18.32", "Chronic kidney disease, stage 3b", "137", "137", 1, 1, "CKD (Stage 3-5)", "high"),
    ("N18.4", "Chronic kidney disease, stage 4", "136", "136", 1, 1, "CKD (Stage 4-5)", "critical"),
    ("N18.5", "Chronic kidney disease, stage 5", "136", "136", 1, 1, "CKD (Stage 5)", "critical"),
    ("N18.6", "End stage renal disease", "136", "136", 1, 1, "End Stage Renal Disease", "critical"),
]

# ── Chapter J — Respiratory ───────────────────────────────────
RESPIRATORY_CODES = [
    ("J44.0", "COPD with acute lower respiratory infection", "111", "111", 1, 1, "COPD", "high"),
    ("J44.1", "COPD with acute exacerbation", "111", "111", 1, 1, "COPD", "high"),
    ("J44.30", "Moderate COPD, uncomplicated", "111", "111", 1, 1, "Moderate COPD", "high"),
    ("J44.31", "Moderate COPD with acute exacerbation", "111", "111", 1, 1, "Moderate COPD", "high"),
    ("J44.32", "Moderate COPD with acute lower respiratory infection", "111", "111", 1, 1, "Moderate COPD", "high"),
    ("J96.00", "Acute respiratory failure, unspecified", "83", "83", 1, 1, "Respiratory Failure", "critical"),
    ("J96.01", "Acute respiratory failure with hypoxia", "83", "83", 1, 1, "Respiratory Failure", "critical"),
    ("J96.02", "Acute respiratory failure with hypercapnia", "83", "83", 1, 1, "Respiratory Failure", "critical"),
    ("J96.10", "Chronic respiratory failure, unspecified", "83", "83", 1, 1, "Respiratory Failure", "critical"),
    ("J96.20", "Acute and chronic respiratory failure, unspecified", "83", "83", 1, 1, "Respiratory Failure", "critical"),
]

# ── Chapter C — Neoplasms ─────────────────────────────────────
NEOPLASM_CODES = [
    ("C34.10", "Malignant neoplasm of upper lobe, right bronchus/lung", "10", "10", 1, 1, "Lung and Other Severe Cancers", "critical"),
    ("C34.11", "Malignant neoplasm of upper lobe, right bronchus", "10", "10", 1, 1, "Lung and Other Severe Cancers", "critical"),
    ("C34.12", "Malignant neoplasm of upper lobe, left bronchus", "10", "10", 1, 1, "Lung and Other Severe Cancers", "critical"),
    ("C34.90", "Malignant neoplasm of unspecified part of unspecified bronchus/lung", "10", "10", 1, 1, "Lung and Other Severe Cancers", "critical"),
    ("C50.911", "Malignant neoplasm of unspecified site of right female breast", "12", "12", 1, 1, "Breast Cancer", "critical"),
    ("C50.912", "Malignant neoplasm of unspecified site of left female breast", "12", "12", 1, 1, "Breast Cancer", "critical"),
    ("C18.9", "Malignant neoplasm of colon, unspecified", "12", "12", 1, 1, "Colon and Other Cancers", "critical"),
    ("C61", "Malignant neoplasm of prostate", "12", "12", 1, 1, "Prostate Cancer", "critical"),
    ("C67.9", "Malignant neoplasm of bladder, unspecified", "12", "12", 1, 1, "Bladder Cancer", "critical"),
    ("C90.00", "Multiple myeloma, not in remission", "10", "10", 1, 1, "Lymphatic, Hematologic, and Other Cancers", "critical"),
    ("C91.00", "Acute lymphoblastic leukemia [ALL] not in remission", "9", "9", 1, 1, "Acute Leukemia", "critical"),
    ("C92.00", "Acute myeloid leukemia [AML] not in remission", "9", "9", 1, 1, "Acute Leukemia", "critical"),
    ("C96.20", "Malignant mast cell neoplasm, unspecified", "10", "10", 1, 1, "Lymphatic Cancers", "critical"),
]

# ── Chapter M — Musculoskeletal ───────────────────────────────
MUSCULOSKELETAL_CODES = [
    ("M05.60", "Rheumatoid arthritis of unspecified site with involvement of other organs", "40", "40", 1, 1, "Rheumatoid Arthritis", "high"),
    ("M05.70", "Rheumatoid arthritis with rheumatoid factor of unspecified site with involvement", "40", "40", 1, 1, "Rheumatoid Arthritis", "high"),
    ("M06.00", "Rheumatoid arthritis without rheumatoid factor, unspecified site", "40", "40", 1, 1, "Rheumatoid Arthritis", "medium"),
    ("M32.10", "Systemic lupus erythematosus, organ or system involvement, unspecified", "40", "40", 1, 1, "Specified Autoimmune Disorders", "critical"),
    ("M32.19", "Other organ or system involvement in systemic lupus erythematosus", "40", "40", 1, 1, "Specified Autoimmune Disorders", "critical"),
    ("M34.0", "Progressive systemic sclerosis (Scleroderma)", "40", "40", 1, 1, "Specified Autoimmune Disorders", "critical"),
    ("M84.511", "Pathological fracture, right shoulder due to neoplasm", "170", "170", 1, 1, "Pathologic Fracture", "critical"),
    ("M84.621", "Pathological fracture, right femur due to other disease", "170", "170", 1, 1, "Pathologic Fracture", "critical"),
]

# ── V28 change notes (key rejections and additions) ──────────
# Maps icd10_code -> (v28_change_note, clinical_rationale)
V28_CHANGE_NOTES = {
    "F32.9": (
        "Removed from HCC 55 in V28 — unspecified depression no longer maps to paying HCC",
        "CMS determined unspecified depression (F32.9) lacks sufficient clinical specificity for risk adjustment. Upgrade to F32.0-F32.3 with severity specified."
    ),
    "F33.9": (
        "Removed from HCC 55 in V28 — unspecified recurrent depression no longer maps to paying HCC",
        "CMS removed unspecified recurrent depression from V28 HCC. Document episode severity to support F33.0-F33.2 upgrade codes."
    ),
    "F11.90": (
        "Removed from HCC 56 in V28 — unspecified opioid use disorder requires severity specification",
        "CMS removed unspecified opioid use disorder from V28. Use F11.10 (abuse) or F11.20 (dependence) with documentation of severity."
    ),
    "E11.9": (
        "Still valid in V28 HCC 36 but upgrade to complication-specific codes for higher risk scores",
        "Type 2 DM unspecified remains mapped but adding E11.40-E11.65 complication codes significantly increases risk score when clinically supported."
    ),
    "I50.9": (
        "Removed from HCC 85/86 in V28 — unspecified heart failure requires type specification",
        "CMS requires systolic/diastolic/combined specification in V28. Upgrade to I50.2x, I50.3x, I50.4x, or I50.8xx based on echocardiography findings."
    ),
}

# ── Master list (all chapters combined) ──────────────────────
V28_CODES_EXPANDED = (
    DIABETES_CODES +
    CIRCULATORY_CODES +
    MENTAL_CODES +
    INFECTIOUS_CODES +
    NERVOUS_CODES +
    RENAL_CODES +
    RESPIRATORY_CODES +
    NEOPLASM_CODES +
    MUSCULOSKELETAL_CODES
)

# Deduplicated by ICD-10 code
_seen = set()
_deduped = []
for row in V28_CODES_EXPANDED:
    if row[0] not in _seen:
        _seen.add(row[0])
        _deduped.append(row)
V28_CODES_EXPANDED = _deduped


def get_change_note(icd10_code: str):
    """Return (v28_change_note, clinical_rationale) or (None, None)."""
    return V28_CHANGE_NOTES.get(icd10_code.upper(), (None, None))


if __name__ == "__main__":
    print(f"Total expanded V28 codes: {len(V28_CODES_EXPANDED)}")
    v28_valid = sum(1 for r in V28_CODES_EXPANDED if r[4])
    v28_rej   = sum(1 for r in V28_CODES_EXPANDED if not r[4] and r[5])
    print(f"  V28 valid: {v28_valid}")
    print(f"  V28 rejected (V24 paid, V28 doesn't): {v28_rej}")
    print(f"  Change notes available: {len(V28_CHANGE_NOTES)}")
