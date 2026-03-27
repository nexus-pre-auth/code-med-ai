"""
CodeMed Group — CMS V28 ZIP Data Ingest
Downloads official 2026 CMS ICD-10 → HCC mapping files and loads them
into the nexusauth.db v28_hcc_codes table.

The CMS ZIP files contain tab-delimited files mapping ~7,770 ICD-10 codes
to V28 HCC categories. This script parses those files and upserts the data
into the database, enriching any existing records.

Usage:
  # Download ZIPs from CMS and import
  python data/cms_zip_ingest.py --download --db data/nexusauth.db

  # Parse a local ZIP already downloaded
  python data/cms_zip_ingest.py --file /path/to/2026-initial-icd-10-cm-mappings.zip

  # Preview what's in a ZIP without writing to DB
  python data/cms_zip_ingest.py --file /path/to/mappings.zip --preview

  # Import CPT/HCPCS eligible encounter codes
  python data/cms_zip_ingest.py --download --type cpt-eligible

Official 2026 CMS ZIP URLs:
  ICD-10 Initial:  https://www.cms.gov/files/zip/2026-initial-icd-10-cm-mappings.zip
  ICD-10 Final:    https://www.cms.gov/files/zip/2026-midyear-final-icd-10-mappings.zip
  Model Initial:   https://www.cms.gov/files/zip/2026-initial-model-software.zip
  Model Final:     https://www.cms.gov/files/zip/2026-midyear-final-model-software.zip
  CPT/HCPCS:       https://www.cms.gov/files/zip/2026-medicare-advantage-risk-adjustment-eligible-cpt-hcpcs-codes.zip
"""
import argparse, csv, io, json, logging, re, sqlite3, sys, time, zipfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("codemed.cms_zip_ingest")

DEFAULT_DB = Path(__file__).parent / "nexusauth.db"

# Official 2026 CMS ZIP URLs
CMS_ZIP_URLS = {
    "icd10_initial": "https://www.cms.gov/files/zip/2026-initial-icd-10-cm-mappings.zip",
    "icd10_final":   "https://www.cms.gov/files/zip/2026-midyear-final-icd-10-mappings.zip",
    "model_initial": "https://www.cms.gov/files/zip/2026-initial-model-software.zip",
    "model_final":   "https://www.cms.gov/files/zip/2026-midyear-final-model-software.zip",
    "cpt_eligible":  "https://www.cms.gov/files/zip/2026-medicare-advantage-risk-adjustment-eligible-cpt-hcpcs-codes.zip",
}

# ── Column detection patterns (handles all known CMS file variants) ───────────
ICD_COL_PATTERNS    = [r"icd.?10.?cm|icd.?code|diagnosis.?code|dx.?code", r"^code$"]
HCC_NUM_PATTERNS    = [r"cms.?hcc|hcc.?number|hcc.?num|hcc_number|payment.?hcc", r"^hcc$"]
HCC_LABEL_PATTERNS  = [r"hcc.?label|hcc.?desc|category.?label|model.?category"]
DESC_PATTERNS       = [r"description|icd.?desc|code.?desc"]
PAYMENT_FLAG_PATTERNS = [r"payment.?flag|is.?payment|pays"]

# Critical HCCs for automatic tier inference when importing raw CMS data
CRITICAL_HCCS = {1, 2, 6, 17, 18, 19, 35, 36, 62, 63, 66, 107, 125, 169, 180, 221, 222, 224, 253, 326, 327, 377, 378, 379}
HIGH_HCCS     = {20, 21, 22, 23, 37, 48, 54, 55, 57, 64, 65, 80, 81, 93, 126, 151, 223, 225, 226, 227, 238, 279, 280, 328, 329}


def detect_column(headers: list, patterns: list) -> int | None:
    """Return the index of the first header that matches any pattern, or None."""
    for pat in patterns:
        for i, h in enumerate(headers):
            if re.search(pat, h.strip(), re.IGNORECASE):
                return i
    return None


def normalize_icd10(code: str) -> str:
    """
    Normalize ICD-10-CM code: uppercase, strip whitespace, insert decimal if missing.
    CMS files sometimes omit the decimal (e.g. "E1121" instead of "E11.21").
    """
    code = code.strip().upper().replace(" ", "")
    if not code:
        return code
    if "." not in code and len(code) >= 4:
        code = code[:3] + "." + code[3:]
    return code


def parse_mapping_file(f, filename: str) -> list[dict]:
    """
    Parse a tab- or comma-delimited ICD-10 → HCC mapping file from a CMS ZIP.
    Returns list of dicts with keys: icd10_code, description, v28_hcc, hcc_label, v28_pays.
    """
    content = f.read()
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            content = content.decode("latin-1")

    # Detect delimiter from first non-empty line
    for line in content.split("\n"):
        if line.strip():
            delimiter = "\t" if line.count("\t") >= line.count(",") else ","
            break
    else:
        return []

    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = [r for r in reader if any(c.strip() for c in r)]

    if not rows:
        logger.warning(f"  Empty file: {filename}")
        return []

    # Find header row: first row containing ICD/HCC/code keywords
    header_idx = 0
    for i, row in enumerate(rows[:5]):
        if any(re.search(r"icd|code|hcc|desc", c, re.IGNORECASE) for c in row):
            header_idx = i
            break

    headers   = rows[header_idx]
    data_rows = rows[header_idx + 1:]

    logger.info(f"  {filename}: {len(headers)} cols, {len(data_rows)} data rows")
    logger.info(f"  Headers detected: {headers[:8]}")

    icd_col   = detect_column(headers, ICD_COL_PATTERNS)
    hcc_col   = detect_column(headers, HCC_NUM_PATTERNS)
    label_col = detect_column(headers, HCC_LABEL_PATTERNS)
    desc_col  = detect_column(headers, DESC_PATTERNS)
    pay_col   = detect_column(headers, PAYMENT_FLAG_PATTERNS)

    # Fallback: ICD code is usually column 0 in CMS files
    if icd_col is None:
        logger.warning(f"  Cannot detect ICD-10 column — defaulting to column 0")
        icd_col = 0
    if hcc_col is None and label_col is None:
        logger.warning(f"  Cannot detect HCC column — defaulting to column 3")
        hcc_col = 3

    logger.info(f"  Col map → ICD:{icd_col} HCC#:{hcc_col} Label:{label_col} Desc:{desc_col} PayFlag:{pay_col}")

    records = []
    for row in data_rows:
        if not row:
            continue

        code = row[icd_col].strip() if icd_col is not None and icd_col < len(row) else ""
        if not code or not re.match(r"^[A-Z]\d", code, re.IGNORECASE):
            continue  # skip non-ICD rows and blank lines

        code = normalize_icd10(code)

        desc      = row[desc_col].strip()   if desc_col  is not None and desc_col  < len(row) else ""
        hcc_num   = row[hcc_col].strip()    if hcc_col   is not None and hcc_col   < len(row) else ""
        hcc_label = row[label_col].strip()  if label_col is not None and label_col < len(row) else ""

        # Determine payment status
        v28_pays = 1
        if pay_col is not None and pay_col < len(row):
            flag = row[pay_col].strip()
            v28_pays = 1 if flag in ("1", "Y", "y", "Yes", "yes", "TRUE", "true") or (flag and flag not in ("0", "N", "n", "No", "no")) else 0

        # Non-mapped rows have blank or "0" HCC
        if not hcc_num or hcc_num in ("0", "N/A", "NA", "none", "None"):
            v28_pays = 0
            hcc_num  = None

        records.append({
            "icd10_code": code,
            "description": desc,
            "v28_hcc": hcc_num,
            "hcc_label": hcc_label,
            "v28_pays": v28_pays,
        })

    paying = sum(1 for r in records if r["v28_pays"])
    logger.info(f"  Parsed {len(records)} ICD-10 codes ({paying} with paying V28 HCC)")
    return records


def ingest_zip(zip_path: str, db_path: str, preview: bool = False) -> int:
    """
    Parse all CSV/TXT files in a CMS ZIP and upsert into v28_hcc_codes.
    Returns number of records processed.
    """
    all_records = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        logger.info(f"ZIP '{Path(zip_path).name}' contains {len(names)} files")

        target_exts = {".csv", ".txt", ".tsv"}
        mapping_files = [
            n for n in names
            if Path(n).suffix.lower() in target_exts
            and not Path(n).name.startswith(".")
            and "__MACOSX" not in n
        ]

        if not mapping_files:
            logger.error(f"No CSV/TXT files found in {zip_path}")
            logger.info(f"All files in ZIP: {names}")
            return 0

        for fname in mapping_files:
            logger.info(f"Parsing: {fname}")
            with zf.open(fname) as f:
                records = parse_mapping_file(f, fname)
                all_records.extend(records)

    if not all_records:
        logger.warning("No valid records parsed from ZIP")
        return 0

    if preview:
        print(f"\n{'='*70}")
        print(f"PREVIEW — {Path(zip_path).name}")
        print(f"{'='*70}")
        print(f"{'ICD-10':12} {'HCC':6} {'PAYS':6}  DESCRIPTION")
        print(f"{'-'*70}")
        for r in all_records[:30]:
            pays = "✓" if r["v28_pays"] else "✗"
            hcc  = r["v28_hcc"] or "—"
            print(f"  {r['icd10_code']:12} {hcc:6} {pays:6}  {r['description'][:50]}")
        if len(all_records) > 30:
            print(f"  ... and {len(all_records) - 30} more rows")
        paying = sum(1 for r in all_records if r["v28_pays"])
        print(f"\nTotal: {len(all_records):,} records | V28 Paying: {paying:,}")
        return len(all_records)

    return upsert_to_db(all_records, db_path)


def upsert_to_db(records: list[dict], db_path: str) -> int:
    """
    Upsert parsed ICD-10 → HCC records into v28_hcc_codes.
    Updates V28 fields for existing codes; inserts new codes.
    Preserves hand-curated fields: payment_tier, v28_change_note, clinical_rationale, v24_hcc.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    inserted = updated = 0
    for r in records:
        code = r["icd10_code"]
        existing = conn.execute(
            "SELECT id FROM v28_hcc_codes WHERE icd10_code=?", (code,)
        ).fetchone()

        tier = _infer_payment_tier(r.get("v28_hcc"))

        if existing:
            conn.execute("""
                UPDATE v28_hcc_codes SET
                    description = COALESCE(NULLIF(?, ''), description),
                    v28_hcc     = COALESCE(?, v28_hcc),
                    hcc_label   = COALESCE(NULLIF(?, ''), hcc_label),
                    v28_pays    = ?
                WHERE icd10_code = ?
            """, (r["description"], r["v28_hcc"], r["hcc_label"], r["v28_pays"], code))
            updated += 1
        else:
            conn.execute("""
                INSERT OR IGNORE INTO v28_hcc_codes
                    (icd10_code, description, v28_hcc, v24_hcc, v28_pays, v24_pays, hcc_label, payment_tier)
                VALUES (?, ?, ?, NULL, ?, 0, ?, ?)
            """, (code, r["description"], r["v28_hcc"], r["v28_pays"], r["hcc_label"], tier))
            inserted += 1

    conn.commit()
    conn.close()

    total = inserted + updated
    paying = sum(1 for r in records if r["v28_pays"])
    logger.info(f"Done: {inserted} inserted, {updated} updated | {paying:,} with paying V28 HCC")
    return total


def _infer_payment_tier(hcc: str | None) -> str:
    """Infer payment_tier from HCC number using known V28 payment weights."""
    if not hcc:
        return "standard"
    try:
        n = int(hcc)
    except (ValueError, TypeError):
        return "standard"
    if n in CRITICAL_HCCS: return "critical"
    if n in HIGH_HCCS:     return "high"
    return "standard"


def download_zip(url: str, dest: Path) -> bool:
    """Download a file with up to 3 retries and exponential backoff."""
    import urllib.request, urllib.error
    for attempt in range(1, 4):
        try:
            logger.info(f"Downloading (attempt {attempt}): {url}")
            req = urllib.request.Request(
                url, headers={"User-Agent": "CodeMedGroup/2.0 CMS-HCC-Ingest"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                while chunk := resp.read(65536):
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        print(f"\r  {pct:3}%  {downloaded:>10,} / {total:>10,} bytes", end="", flush=True)
            print()
            logger.info(f"Saved: {dest}  ({dest.stat().st_size:,} bytes)")
            return True
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP {e.code}: {e.reason} — {url}")
            return False
        except Exception as e:
            wait = 2 ** attempt
            logger.warning(f"Error: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="CodeMed Group — CMS V28 ZIP Data Ingest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download initial 2026 mappings from CMS and import
  python data/cms_zip_ingest.py --download --db data/nexusauth.db

  # Download both initial and midyear-final releases
  python data/cms_zip_ingest.py --download --which both

  # Parse a ZIP you already have locally
  python data/cms_zip_ingest.py --file ~/Downloads/2026-initial-icd-10-cm-mappings.zip

  # Preview contents without writing to DB
  python data/cms_zip_ingest.py --file ~/Downloads/mappings.zip --preview
""")
    parser.add_argument("--download",  action="store_true",  help="Download ZIPs from CMS")
    parser.add_argument("--file",      metavar="PATH",       help="Parse a local ZIP file")
    parser.add_argument("--which",     default="initial",
                        choices=["initial", "final", "both"],
                        help="Which CMS release to download (default: initial)")
    parser.add_argument("--type",      default="icd10",
                        choices=["icd10", "cpt-eligible"],
                        help="Data type to ingest (default: icd10)")
    parser.add_argument("--db",        default=str(DEFAULT_DB), metavar="DB",
                        help="Path to nexusauth.db (default: data/nexusauth.db)")
    parser.add_argument("--preview",   action="store_true",  help="Print rows, do not write to DB")
    parser.add_argument("--out-dir",   default=".",          help="Save downloaded ZIPs here")
    args = parser.parse_args()

    if args.download:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        to_fetch = []
        if args.type == "cpt-eligible":
            to_fetch.append(("cpt_eligible", CMS_ZIP_URLS["cpt_eligible"]))
        else:
            if args.which in ("initial", "both"):
                to_fetch.append(("icd10_initial", CMS_ZIP_URLS["icd10_initial"]))
            if args.which in ("final", "both"):
                to_fetch.append(("icd10_final", CMS_ZIP_URLS["icd10_final"]))

        total = 0
        for key, url in to_fetch:
            dest = out_dir / f"{key}.zip"
            if download_zip(url, dest):
                n = ingest_zip(str(dest), args.db, preview=args.preview)
                total += n
                logger.info(f"[{key}] processed {n:,} records")
            else:
                logger.error(f"[{key}] download failed — skipping")

        logger.info(f"\nTotal records processed: {total:,}")

    elif args.file:
        n = ingest_zip(args.file, args.db, preview=args.preview)
        logger.info(f"Done. Processed {n:,} records from {args.file}")

    else:
        parser.print_help()
        print("\nCMS 2026 ZIP URLs:")
        for k, v in CMS_ZIP_URLS.items():
            print(f"  {k:20} {v}")


if __name__ == "__main__":
    main()
