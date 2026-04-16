from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from typing import Dict, Iterable
from xml.etree import ElementTree as ET


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "docrel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def normalize_name(value: str | None) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def col_to_num(col: str) -> int:
    num = 0
    for ch in col:
        num = num * 26 + (ord(ch) - 64)
    return num


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in zf.namelist():
        return []

    root = ET.fromstring(zf.read(path))
    values: list[str] = []
    for si in root.findall("main:si", NS):
        values.append("".join((t.text or "") for t in si.findall(".//main:t", NS)))
    return values


def workbook_targets(zf: zipfile.ZipFile) -> dict[str, str]:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.get("Id"): rel.get("Target")
        for rel in rels.findall("pkgrel:Relationship", NS)
    }

    result: dict[str, str] = {}
    for sheet in wb.findall("main:sheets/main:sheet", NS):
        name = sheet.get("name")
        rid = sheet.get(f"{{{NS['docrel']}}}id")
        if not name or not rid:
            continue
        target = rid_to_target.get(rid)
        if target:
            result[name] = f"xl/{target}"
    return result


def iter_sheet_rows(
    zf: zipfile.ZipFile, sheet_path: str, shared: list[str]
) -> Iterable[dict[int, str]]:
    root = ET.fromstring(zf.read(sheet_path))
    for row in root.findall(".//main:sheetData/main:row", NS):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", NS):
            ref = cell.get("r", "")
            m = re.match(r"([A-Z]+)(\d+)", ref)
            if not m:
                continue
            col = col_to_num(m.group(1))
            ctype = cell.get("t")
            if ctype == "s":
                v = cell.find("main:v", NS)
                if v is not None and v.text is not None:
                    values[col] = shared[int(v.text)]
                else:
                    values[col] = ""
            elif ctype == "inlineStr":
                tnode = cell.find(".//main:t", NS)
                values[col] = (tnode.text or "") if tnode is not None else ""
            else:
                v = cell.find("main:v", NS)
                values[col] = v.text if v is not None and v.text is not None else ""
        yield values


def read_xlsx(xlsx_path: Path) -> dict[str, list[dict[int, str]]]:
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = read_shared_strings(zf)
        targets = workbook_targets(zf)
        sheets: dict[str, list[dict[int, str]]] = {}
        for sheet_name, path in targets.items():
            sheets[sheet_name] = list(iter_sheet_rows(zf, path, shared))
        return sheets


def build_crosswalks(base_dir: Path) -> list[dict[str, str]]:
    crosswalk_dir = base_dir / "flat_data" / "in" / "raw_data" / "crosswalks"

    school_to_system: dict[str, str] = {}
    for part in [
        "al_school_to_system_part_one.xlsx",
        "al_school_to_system_part_two.xlsx",
    ]:
        sheets = read_xlsx(crosswalk_dir / part)
        rows = sheets.get("Sheet1", [])
        for row in rows[1:]:
            school = (row.get(1, "") or "").strip()
            system = (row.get(2, "") or "").strip()
            if school and system:
                school_to_system[normalize_name(school)] = system

    alsde_to_system: dict[str, str] = {}
    alsde_book = read_xlsx(crosswalk_dir / "alsdeNameToSEDAToNcesshID.xlsx")
    for row in alsde_book.get("ALSDE", [])[1:]:
        alsde_school = (row.get(1, "") or "").strip()
        system = (row.get(2, "") or "").strip()
        if alsde_school and system:
            alsde_to_system[normalize_name(alsde_school)] = system

    out: list[dict[str, str]] = []

    # Highest priority: hand-match overrides from SEDA sheet.
    for row in alsde_book.get("SEDA", [])[1:]:
        ncessch = (row.get(2, "") or "").strip()
        alsde_school = (row.get(3, "") or "").strip()
        hand_match = (row.get(4, "") or "").strip()
        chosen_school = hand_match or alsde_school
        if not chosen_school or not ncessch:
            continue
        if not re.fullmatch(r"\d+", ncessch):
            continue
        system = alsde_to_system.get(normalize_name(chosen_school), "")
        out.append(
            {
                "school_name": chosen_school,
                "system_name": system,
                "ncessch": ncessch.zfill(12),
                "match_method": "HAND_MATCH",
                "priority": "100",
            }
        )

    # Direct SEDA->ALSDE->NCES map.
    for row in alsde_book.get("SEDA w ALSDE", [])[1:]:
        ncessch = (row.get(2, "") or "").strip()
        school = (row.get(3, "") or "").strip()
        if not school or not ncessch or not re.fullmatch(r"\d+", ncessch):
            continue
        system = alsde_to_system.get(normalize_name(school), "")
        out.append(
            {
                "school_name": school,
                "system_name": system,
                "ncessch": ncessch.zfill(12),
                "match_method": "SEDA_ALSDE_NCESSCH",
                "priority": "90",
            }
        )

    # ALSDE school -> NCES school id direct map.
    school_to_nces = read_xlsx(crosswalk_dir / "al_school_to_ncesshid.xlsx")
    for row in school_to_nces.get("Sheet1", [])[1:]:
        ncessch = (row.get(1, "") or "").strip()
        school = (row.get(2, "") or "").strip()
        if not school or not ncessch or not re.fullmatch(r"\d+", ncessch):
            continue
        system = school_to_system.get(normalize_name(school), "")
        out.append(
            {
                "school_name": school,
                "system_name": system,
                "ncessch": ncessch.zfill(12),
                "match_method": "ALSDE_TO_NCESSCH",
                "priority": "80",
            }
        )

    # System-name crosswalk, resolved with school->ncessch mapping if possible.
    ncessch_by_school = {
        normalize_name(rec["school_name"]): rec["ncessch"]
        for rec in out
        if rec["ncessch"]
    }

    for school_norm, system in school_to_system.items():
        ncessch = ncessch_by_school.get(school_norm, "")
        if not ncessch:
            continue
        out.append(
            {
                "school_name": school_norm,
                "system_name": system,
                "ncessch": ncessch,
                "match_method": "SYSTEM_MAP_RESOLVED",
                "priority": "70",
            }
        )

    # Deduplicate on exact payload for stability.
    seen: set[tuple[str, str, str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for row in out:
        key = (
            row["school_name"],
            row["system_name"],
            row["ncessch"],
            row["match_method"],
            row["priority"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    return deduped


def build_audit_rows(
    base_dir: Path, crosswalk_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    crosswalk_dir = base_dir / "flat_data" / "in" / "raw_data" / "crosswalks"

    # School-name roster coverage from al_school_names.xlsx.
    school_names_book = read_xlsx(crosswalk_dir / "al_school_names.xlsx")
    roster_rows = school_names_book.get("Sheet1", [])
    roster = {
        normalize_name((row.get(1, "") or "").strip())
        for row in roster_rows[1:]
        if (row.get(1, "") or "").strip()
    }

    mapped = {normalize_name(row["school_name"]) for row in crosswalk_rows}
    roster_matched = len(roster & mapped)

    # Basic codebook presence checks for outcome fields.
    codebook_book = read_xlsx(crosswalk_dir / "al_sch_v1_codebook.xlsx")
    codebook_rows = codebook_book.get("Sheet1", [])
    codebook_vars = {
        (row.get(1, "") or "").strip()
        for row in codebook_rows[1:]
        if (row.get(1, "") or "").strip()
    }
    expected_vars = ["AchAll", "GrwAll", "AbsAll", "COI", "ncessch", "countyid"]
    missing = [v for v in expected_vars if v not in codebook_vars]

    return [
        {
            "metric": "crosswalk_rows",
            "value": str(len(crosswalk_rows)),
            "detail": "Rows emitted to school_identity_crosswalk_prepared.csv",
        },
        {
            "metric": "al_school_names_total",
            "value": str(len(roster)),
            "detail": "Unique normalized school names in al_school_names.xlsx",
        },
        {
            "metric": "al_school_names_matched",
            "value": str(roster_matched),
            "detail": "Roster names present in emitted crosswalk rows",
        },
        {
            "metric": "codebook_missing_expected_vars",
            "value": str(len(missing)),
            "detail": ",".join(missing) if missing else "none",
        },
    ]


def build_al_sch24_selected(base_dir: Path) -> list[dict[str, str]]:
    src = base_dir / "flat_data" / "in" / "raw_data" / "al_sch24_v1.csv"
    wanted = [
        "Year",
        "System",
        "School",
        "ncessch",
        "countyid",
        "AchAll",
        "GrwAll",
        "AbsAll",
        "AchECD",
        "GrwECD",
        "AbsECD",
        "AchESL",
        "GrwESL",
        "AbsESL",
        "AchAsian",
        "GrwAsian",
        "AbsAsian",
        "AchBlack",
        "GrwBlack",
        "AbsBlack",
        "AchHsp",
        "GrwHsp",
        "AbsHsp",
        "AchWhite",
        "GrwWhite",
        "AbsWhite",
        "AchOther",
        "GrwOther",
        "AbsOther",
        "COI",
        "COI_Ed",
        "COI_HE",
        "COI_ST",
        "PPE",
    ]

    out: list[dict[str, str]] = []
    with src.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append({k: row.get(k, "") or "" for k in wanted})
    return out


def main() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    out_dir = repo_root / "flat_data" / "in" / "raw_data" / "crosswalks" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = build_crosswalks(repo_root)
    out_path = out_dir / "school_identity_crosswalk_prepared.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "school_name",
                "system_name",
                "ncessch",
                "match_method",
                "priority",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    audit_rows = build_audit_rows(repo_root, rows)
    audit_path = out_dir / "school_identity_crosswalk_audit.csv"
    with audit_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value", "detail"])
        writer.writeheader()
        writer.writerows(audit_rows)

    al_sch_rows = build_al_sch24_selected(repo_root)
    al_sch_out_path = out_dir / "al_sch24_selected.csv"
    with al_sch_out_path.open("w", newline="") as f:
        fieldnames = [
            "Year",
            "System",
            "School",
            "ncessch",
            "countyid",
            "AchAll",
            "GrwAll",
            "AbsAll",
            "AchECD",
            "GrwECD",
            "AbsECD",
            "AchESL",
            "GrwESL",
            "AbsESL",
            "AchAsian",
            "GrwAsian",
            "AbsAsian",
            "AchBlack",
            "GrwBlack",
            "AbsBlack",
            "AchHsp",
            "GrwHsp",
            "AbsHsp",
            "AchWhite",
            "GrwWhite",
            "AbsWhite",
            "AchOther",
            "GrwOther",
            "AbsOther",
            "COI",
            "COI_Ed",
            "COI_HE",
            "COI_ST",
            "PPE",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(al_sch_rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Wrote audit metrics to {audit_path}")
    print(f"Wrote {len(al_sch_rows)} rows to {al_sch_out_path}")


if __name__ == "__main__":
    main()
