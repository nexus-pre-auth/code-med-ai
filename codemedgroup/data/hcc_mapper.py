"""
hcc_mapper.py — ComboCodeEnforcer for V28 HCC Risk Adjustment
Detects fragmented coding patterns and recommends combination codes.

Usage:
    from data.hcc_mapper import ComboCodeEnforcer
    enforcer = ComboCodeEnforcer()
    result = enforcer.check(["I10", "N18.32", "E11.65"])
    # result.combo_warnings: list of ComboWarning objects
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import re

# ---------------------------------------------------------------------------
# Combination code rules
# Each rule defines a fragmented pattern (trigger codes) and the correct
# combination code that should replace them. Codes are matched by prefix.
# ---------------------------------------------------------------------------

@dataclass
class ComboRule:
    rule_id: str
    description: str
    trigger_prefixes: list[str]        # e.g. ["I10", "N18"]
    trigger_exact: list[str]           # exact codes that all must be present
    combo_code: str                    # recommended combination code
    combo_description: str
    combo_hcc: Optional[str]           # V28 HCC for the combo code
    combo_payment_tier: str            # critical | high | medium | standard
    cms_note: str
    revenue_impact: str                # HIGH | MEDIUM | LOW


# Top 20 fragmented coding patterns based on CMS RADV findings and Module 2 training data
COMBO_RULES: list[ComboRule] = [
    # ── Hypertension + CKD combinations ──────────────────────────────────
    ComboRule(
        rule_id="HTN_CKD_3A",
        description="Hypertension + CKD Stage 3a → Hypertensive CKD Stage 3",
        trigger_prefixes=["I10"],
        trigger_exact=["N18.31"],
        combo_code="I12.9",
        combo_description="Hypertensive chronic kidney disease with stage 1-4 or unspecified CKD",
        combo_hcc="329",
        combo_payment_tier="high",
        cms_note="ICD-10 convention requires combination code when HTN and CKD coexist (I.C.9.a.2)",
        revenue_impact="HIGH",
    ),
    ComboRule(
        rule_id="HTN_CKD_3B",
        description="Hypertension + CKD Stage 3b → Hypertensive CKD Stage 3",
        trigger_prefixes=["I10"],
        trigger_exact=["N18.32"],
        combo_code="I12.9",
        combo_description="Hypertensive chronic kidney disease with stage 1-4 or unspecified CKD",
        combo_hcc="329",
        combo_payment_tier="high",
        cms_note="ICD-10 convention requires combination code when HTN and CKD coexist (I.C.9.a.2)",
        revenue_impact="HIGH",
    ),
    ComboRule(
        rule_id="HTN_CKD_4",
        description="Hypertension + CKD Stage 4 → Hypertensive CKD Stage 4",
        trigger_prefixes=["I10"],
        trigger_exact=["N18.4"],
        combo_code="I12.9",
        combo_description="Hypertensive chronic kidney disease with stage 1-4 or unspecified CKD",
        combo_hcc="329",
        combo_payment_tier="high",
        cms_note="ICD-10 convention requires combination code when HTN and CKD coexist (I.C.9.a.2)",
        revenue_impact="HIGH",
    ),
    ComboRule(
        rule_id="HTN_CKD_5",
        description="Hypertension + CKD Stage 5 → Hypertensive CKD Stage 5/ESRD",
        trigger_prefixes=["I10"],
        trigger_exact=["N18.5"],
        combo_code="I12.10",
        combo_description="Hypertensive CKD with stage 5 CKD, not requiring dialysis",
        combo_hcc="329",
        combo_payment_tier="critical",
        cms_note="Stage 5 non-dialysis has distinct combo code I12.10 per FY2023 ICD-10 update",
        revenue_impact="HIGH",
    ),
    ComboRule(
        rule_id="HTN_CKD_ESRD",
        description="Hypertension + ESRD → Hypertensive ESRD",
        trigger_prefixes=["I10"],
        trigger_exact=["N18.6"],
        combo_code="I12.11",
        combo_description="Hypertensive CKD with stage 5 CKD requiring chronic dialysis",
        combo_hcc="329",
        combo_payment_tier="critical",
        cms_note="ESRD dialysis requires I12.11; code Z99.2 as additional code for dialysis status",
        revenue_impact="HIGH",
    ),
    # ── Hypertension + Heart Failure ──────────────────────────────────────
    ComboRule(
        rule_id="HTN_HF_UNSPEC",
        description="Hypertension + Heart Failure (unspecified) → Hypertensive Heart Disease",
        trigger_prefixes=["I10"],
        trigger_exact=["I50.9"],
        combo_code="I11.0",
        combo_description="Hypertensive heart disease with heart failure",
        combo_hcc="85",
        combo_payment_tier="high",
        cms_note="ICD-10-CM requires I11.0 when hypertension and HF coexist; I50.9 becomes additional code",
        revenue_impact="HIGH",
    ),
    ComboRule(
        rule_id="HTN_HF_SYSTOLIC",
        description="Hypertension + Systolic Heart Failure → Hypertensive Heart Disease",
        trigger_prefixes=["I10"],
        trigger_exact=["I50.20"],
        combo_code="I11.0",
        combo_description="Hypertensive heart disease with heart failure",
        combo_hcc="85",
        combo_payment_tier="high",
        cms_note="Use I11.0 as principal; add I50.20 for specificity of HF type",
        revenue_impact="HIGH",
    ),
    ComboRule(
        rule_id="HTN_HF_DIASTOLIC",
        description="Hypertension + Diastolic Heart Failure → Hypertensive Heart Disease",
        trigger_prefixes=["I10"],
        trigger_exact=["I50.30"],
        combo_code="I11.0",
        combo_description="Hypertensive heart disease with heart failure",
        combo_hcc="85",
        combo_payment_tier="high",
        cms_note="Use I11.0 as principal; add I50.30 for specificity of HF type",
        revenue_impact="HIGH",
    ),
    # ── Hypertension + CKD + Heart Failure (triple) ──────────────────────
    ComboRule(
        rule_id="HTN_CKD_HF_TRIPLE",
        description="Hypertension + CKD + Heart Failure → Hypertensive Heart and CKD",
        trigger_prefixes=["I10"],
        trigger_exact=["N18.32", "I50.9"],
        combo_code="I13.10",
        combo_description="Hypertensive heart and chronic kidney disease without heart failure, stage 1-4",
        combo_hcc="329",
        combo_payment_tier="critical",
        cms_note="I13.x family required when all three coexist; most common RADV fragmentation finding",
        revenue_impact="HIGH",
    ),
    # ── Diabetes combinations ────────────────────────────────────────────
    ComboRule(
        rule_id="DM2_NEPH_UNSPEC",
        description="T2DM + Diabetic Nephropathy unspecified → use combination code",
        trigger_prefixes=["E11.9", "E11.6"],
        trigger_exact=["N08"],
        combo_code="E11.21",
        combo_description="Type 2 diabetes mellitus with diabetic nephropathy",
        combo_hcc="36",
        combo_payment_tier="high",
        cms_note="N08 is 'glomerular disorders in DM' — use E11.21 instead when T2DM is primary",
        revenue_impact="MEDIUM",
    ),
    ComboRule(
        rule_id="DM2_CKD_COMBO",
        description="T2DM + CKD → T2DM with diabetic CKD combination code",
        trigger_prefixes=["E11"],
        trigger_exact=["N18.3"],
        combo_code="E11.65",
        combo_description="Type 2 diabetes mellitus with hyperglycemia",
        combo_hcc="36",
        combo_payment_tier="high",
        cms_note="When DM causes CKD, use E11.65 + N18.x; distinguish from hypertensive CKD cause",
        revenue_impact="MEDIUM",
    ),
    ComboRule(
        rule_id="DM2_RETINOPATHY_UNSPEC",
        description="T2DM + Unspecified diabetic retinopathy → specify laterality",
        trigger_prefixes=["E11.9"],
        trigger_exact=["H36.0"],
        combo_code="E11.319",
        combo_description="Type 2 diabetes with unspecified diabetic retinopathy without macular edema",
        combo_hcc="36",
        combo_payment_tier="high",
        cms_note="H36.0 is manifestation code — use E11.3x as principal with laterality when known",
        revenue_impact="MEDIUM",
    ),
    # ── COPD / Respiratory combinations ─────────────────────────────────
    ComboRule(
        rule_id="COPD_ACUTE_EXAC",
        description="COPD + Acute Exacerbation coded separately → use combination code",
        trigger_prefixes=["J44.1"],
        trigger_exact=["J22"],
        combo_code="J44.1",
        combo_description="Chronic obstructive pulmonary disease with acute exacerbation",
        combo_hcc="112",
        combo_payment_tier="high",
        cms_note="J44.1 already captures exacerbation; do not double-code J22 with J44.1",
        revenue_impact="LOW",
    ),
    # ── Atherosclerosis combinations ──────────────────────────────────────
    ComboRule(
        rule_id="CAD_ANGINA",
        description="CAD (unspecified) + Angina → use combination code",
        trigger_prefixes=["I25.10"],
        trigger_exact=["I20.9"],
        combo_code="I25.110",
        combo_description="Atherosclerotic heart disease of native coronary artery with unstable angina",
        combo_hcc="87",
        combo_payment_tier="high",
        cms_note="ICD-10 convention: when CAD and angina coexist, a combination code from I25.1x must be used",
        revenue_impact="HIGH",
    ),
    # ── CHF specificity upgrades ──────────────────────────────────────────
    ComboRule(
        rule_id="HF_UNSPEC_TO_DIASTOLIC",
        description="Heart Failure unspecified → document systolic vs diastolic type",
        trigger_prefixes=["I50.9"],
        trigger_exact=[],
        combo_code="I50.30",
        combo_description="Unspecified diastolic heart failure (or I50.20 for systolic)",
        combo_hcc="85",
        combo_payment_tier="high",
        cms_note="I50.9 maps to HCC 85 but specificity to systolic/diastolic is expected for RADV",
        revenue_impact="MEDIUM",
    ),
    # ── CKD specificity ───────────────────────────────────────────────────
    ComboRule(
        rule_id="CKD_UNSPEC_TO_STAGED",
        description="CKD unspecified (N18.9) → document and code specific stage",
        trigger_prefixes=["N18.9"],
        trigger_exact=[],
        combo_code="N18.32",
        combo_description="Chronic kidney disease, stage 3b (or appropriate stage per labs)",
        combo_hcc="329",
        combo_payment_tier="high",
        cms_note="N18.9 does not map to an HCC; N18.3+ required for HCC 329 in V28",
        revenue_impact="HIGH",
    ),
    # ── Morbid obesity combinations ────────────────────────────────────────
    ComboRule(
        rule_id="OBESITY_HYPOVENT",
        description="Morbid obesity + Hypoventilation → Obesity Hypoventilation Syndrome",
        trigger_prefixes=["E66.01"],
        trigger_exact=["R06.89"],
        combo_code="E66.2",
        combo_description="Morbid obesity with alveolar hypoventilation (Obesity Hypoventilation Syndrome)",
        combo_hcc="48",
        combo_payment_tier="high",
        cms_note="OHS (E66.2) is separate from morbid obesity (E66.01) and maps to distinct HCC",
        revenue_impact="HIGH",
    ),
    # ── Sepsis combinations ────────────────────────────────────────────────
    ComboRule(
        rule_id="SEPSIS_ORGAN_DYSFUNCTION",
        description="Sepsis + Organ dysfunction coded separately → Sepsis with Severe Sepsis",
        trigger_prefixes=["A41.9"],
        trigger_exact=["N17.9"],
        combo_code="A41.9",
        combo_description="Sepsis unspecified; add R65.20 for severe sepsis without organ failure",
        combo_hcc="2",
        combo_payment_tier="critical",
        cms_note="When sepsis causes organ dysfunction, R65.20/R65.21 (severe sepsis) must be added",
        revenue_impact="HIGH",
    ),
    # ── Stroke sequelae ──────────────────────────────────────────────────
    ComboRule(
        rule_id="HISTORY_STROKE_VS_SEQUELAE",
        description="Z86.73 (personal history of TIA/stroke) alone → use sequela code if deficits present",
        trigger_prefixes=["Z86.73"],
        trigger_exact=[],
        combo_code="I69.398",
        combo_description="Other sequelae of cerebral infarction (cognitive, motor, communication deficits)",
        combo_hcc="100",
        combo_payment_tier="high",
        cms_note="Z86.73 captures history only; if patient has ongoing neurological deficits, I69.x applies",
        revenue_impact="HIGH",
    ),
    # ── Alcohol-related liver disease ──────────────────────────────────────
    ComboRule(
        rule_id="ALD_CIRRHOSIS",
        description="Alcoholic liver disease + Cirrhosis coded separately → use combination code",
        trigger_prefixes=["K70.30"],
        trigger_exact=["K74.60"],
        combo_code="K70.30",
        combo_description="Alcoholic cirrhosis of liver without ascites (K70.30 already implies cirrhosis)",
        combo_hcc="27",
        combo_payment_tier="high",
        cms_note="K70.30 already captures cirrhosis; do not additionally code K74.60 — it is redundant",
        revenue_impact="LOW",
    ),
]


# ---------------------------------------------------------------------------
# Acute-only conditions — should not persist on chronic problem list post-discharge
# ---------------------------------------------------------------------------
ACUTE_ONLY_CODES: dict[str, str] = {
    "J18.9": "Pneumonia unspecified — resolve after treatment",
    "J06.9": "Acute upper respiratory infection — acute only",
    "N39.0": "UTI — acute episode only",
    "K92.1": "Melena — acute episode; investigate cause",
    "I26.99": "Pulmonary embolism — acute episode",
    "K35.80": "Acute appendicitis — surgical, not chronic",
    "S72.001A": "Femoral neck fracture — acute only",
    "A09":    "Infectious gastroenteritis — acute only",
    "J96.00": "Acute respiratory failure — acute only",
    "R57.9":  "Shock — acute episode; use underlying cause for chronic",
}

# Prefixes for "History of" codes that indicate resolved conditions
HISTORY_PREFIXES = ["Z85.", "Z86.", "Z87.", "Z80.", "Z81.", "Z82.", "Z83.", "Z84.", "Z89.", "Z90.", "Z96."]

# High-risk HCCs for RADV (commonly audited and denied)
HIGH_RADV_RISK_HCCS = {2, 8, 9, 10, 17, 18, 19, 21, 22, 27, 35, 36, 37, 38, 46, 47, 48,
                        82, 83, 84, 85, 86, 87, 100, 112, 114, 134, 135, 161, 329}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ComboWarning:
    rule_id: str
    description: str
    fragmented_codes: list[str]        # the codes that triggered this rule
    recommended_code: str
    recommended_description: str
    combo_hcc: Optional[str]
    combo_payment_tier: str
    cms_note: str
    revenue_impact: str                # HIGH | MEDIUM | LOW
    severity: str                      # ERROR (must fix) | WARNING (should review)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "fragmented_codes": self.fragmented_codes,
            "recommended_code": self.recommended_code,
            "recommended_description": self.recommended_description,
            "combo_hcc": self.combo_hcc,
            "combo_payment_tier": self.combo_payment_tier,
            "cms_note": self.cms_note,
            "revenue_impact": self.revenue_impact,
            "severity": self.severity,
        }


@dataclass
class AcuteOnlyFlag:
    code: str
    reason: str

    def to_dict(self) -> dict:
        return {"code": self.code, "reason": self.reason}


@dataclass
class HistoryOnlyFlag:
    code: str
    note: str

    def to_dict(self) -> dict:
        return {"code": self.code, "note": self.note}


@dataclass
class EnforcerResult:
    codes_checked: list[str]
    combo_warnings: list[ComboWarning] = field(default_factory=list)
    acute_only_flags: list[AcuteOnlyFlag] = field(default_factory=list)
    history_only_flags: list[HistoryOnlyFlag] = field(default_factory=list)
    has_errors: bool = False
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "codes_checked": self.codes_checked,
            "combo_warnings": [w.to_dict() for w in self.combo_warnings],
            "acute_only_flags": [f.to_dict() for f in self.acute_only_flags],
            "history_only_flags": [f.to_dict() for f in self.history_only_flags],
            "has_errors": self.has_errors,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# ComboCodeEnforcer
# ---------------------------------------------------------------------------

class ComboCodeEnforcer:
    """
    Detects fragmented coding patterns in a list of ICD-10 codes and returns
    warnings with recommended combination codes.

    Example:
        enforcer = ComboCodeEnforcer()
        result = enforcer.check(["I10", "N18.32", "I50.9"])
        # → combo_warnings: [HTN_CKD_3B (I12.9), HTN_HF_UNSPEC (I11.0), HTN_CKD_HF_TRIPLE (I13.10)]
    """

    def __init__(self) -> None:
        self.rules = COMBO_RULES

    def _normalize(self, code: str) -> str:
        """Normalize ICD-10 code to uppercase, strip whitespace."""
        return code.strip().upper()

    def _matches_prefix(self, code: str, prefix: str) -> bool:
        """Return True if the code starts with the given prefix."""
        return code.startswith(prefix.upper())

    def _code_set_matches_rule(self, code_set: set[str], rule: ComboRule) -> tuple[bool, list[str]]:
        """
        Return (matched: bool, triggering_codes: list).
        A rule matches if:
          1. For each trigger_prefix: at least one code in code_set starts with it
          2. For each trigger_exact code: it is present in code_set
        """
        triggering: list[str] = []

        # Check prefix requirements
        for prefix in rule.trigger_prefixes:
            matches = [c for c in code_set if self._matches_prefix(c, prefix)]
            if not matches:
                return False, []
            triggering.extend(matches)

        # Check exact requirements
        for exact in rule.trigger_exact:
            exact_upper = exact.upper()
            if exact_upper not in code_set:
                return False, []
            triggering.append(exact_upper)

        # Rule must have at least one requirement
        if not rule.trigger_prefixes and not rule.trigger_exact:
            return False, []

        return True, list(set(triggering))

    def check(self, codes: list[str]) -> EnforcerResult:
        """
        Check a list of ICD-10 codes for fragmented coding patterns.

        Args:
            codes: List of ICD-10 codes (any format, will be normalized)

        Returns:
            EnforcerResult with combo_warnings, acute_only_flags, history_only_flags
        """
        normalized = [self._normalize(c) for c in codes if c]
        code_set = set(normalized)
        result = EnforcerResult(codes_checked=normalized)

        # Check combination code rules
        for rule in self.rules:
            matched, triggering = self._code_set_matches_rule(code_set, rule)
            if matched:
                # Skip if the recommended combo code is already in the code set
                if rule.combo_code.upper() in code_set:
                    continue
                severity = "ERROR" if rule.revenue_impact == "HIGH" else "WARNING"
                result.combo_warnings.append(ComboWarning(
                    rule_id=rule.rule_id,
                    description=rule.description,
                    fragmented_codes=triggering,
                    recommended_code=rule.combo_code,
                    recommended_description=rule.combo_description,
                    combo_hcc=rule.combo_hcc,
                    combo_payment_tier=rule.combo_payment_tier,
                    cms_note=rule.cms_note,
                    revenue_impact=rule.revenue_impact,
                    severity=severity,
                ))

        # Check for acute-only conditions
        for code in normalized:
            if code in ACUTE_ONLY_CODES:
                result.acute_only_flags.append(AcuteOnlyFlag(
                    code=code,
                    reason=ACUTE_ONLY_CODES[code],
                ))

        # Check for history-only codes (Z85/Z86/Z87 etc.)
        for code in normalized:
            for prefix in HISTORY_PREFIXES:
                if code.startswith(prefix):
                    result.history_only_flags.append(HistoryOnlyFlag(
                        code=code,
                        note=(
                            f"{code} is a 'history of' or 'status' code. "
                            "If the condition is active and being managed, code the current condition. "
                            "History-only codes do not map to HCCs in V28."
                        ),
                    ))
                    break

        # Set has_errors flag
        result.has_errors = any(w.severity == "ERROR" for w in result.combo_warnings)

        # Build summary
        parts = []
        if result.combo_warnings:
            n_err = sum(1 for w in result.combo_warnings if w.severity == "ERROR")
            n_warn = len(result.combo_warnings) - n_err
            if n_err:
                parts.append(f"{n_err} fragmented coding error(s) requiring combination code")
            if n_warn:
                parts.append(f"{n_warn} coding warning(s) to review")
        if result.acute_only_flags:
            parts.append(f"{len(result.acute_only_flags)} acute-only condition(s) flagged")
        if result.history_only_flags:
            parts.append(f"{len(result.history_only_flags)} history/status code(s) flagged")
        result.summary = "; ".join(parts) if parts else "No fragmented coding issues detected."

        return result


# ---------------------------------------------------------------------------
# RADV risk classifier
# ---------------------------------------------------------------------------

def classify_radv_risk(
    icd10_code: str,
    hcc_number: Optional[str],
    v28_status: str,
    is_history_code: bool = False,
    is_acute_only: bool = False,
    has_upgrade_available: bool = False,
) -> str:
    """
    Classify RADV audit risk for a single code/HCC pair.

    Returns: "HIGH" | "MEDIUM" | "LOW"
    """
    if is_history_code:
        return "HIGH"

    if is_acute_only:
        return "HIGH"

    if v28_status == "REJECTED":
        return "HIGH"

    if hcc_number and int(hcc_number) in HIGH_RADV_RISK_HCCS:
        if has_upgrade_available:
            return "HIGH"
        return "MEDIUM"

    if v28_status == "NOT_MAPPED":
        return "MEDIUM"

    if has_upgrade_available:
        return "MEDIUM"

    return "LOW"


# ---------------------------------------------------------------------------
# Convenience function for API integration
# ---------------------------------------------------------------------------

_enforcer: Optional[ComboCodeEnforcer] = None

def get_enforcer() -> ComboCodeEnforcer:
    """Return a module-level singleton ComboCodeEnforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = ComboCodeEnforcer()
    return _enforcer


def check_combo_codes(codes: list[str]) -> dict:
    """
    Thin wrapper for app.py — returns serializable dict.

    Usage in app.py:
        from data.hcc_mapper import check_combo_codes
        combo_result = check_combo_codes(icd10_codes)
        # combo_result["combo_warnings"] → list of warning dicts
    """
    return get_enforcer().check(codes).to_dict()
