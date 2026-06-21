#!/usr/bin/env python3

"""Regularize DIMEV Bodleian shelfmarks to the holding institution's form (#64).

bodleian_links.py flags 209 DIMEV Bodleian entries as matching a Bodleian record
only after abbreviation folding (DIMEV "Addit. A.106" vs Bodleian
"MS. Add. A. 106"): a convention difference, not a different manuscript. This
script conforms DIMEV <idno> shelfmarks to the Bodleian spelling so DIMEV agrees
with the holding institution -- the stated point of the exercise.

Target form (editorial decision): the Bodleian shelfmark, i.e. drop the "MS. "
prefix, abbreviate the collection name to the Bodleian's convention, and space
the enumeration ("A.106" -> "A. 106"). Trailing parentheticals are kept.

Scope (per instruction): every Bodleian *manuscript* msDesc, not just the matched
ones, so an unmatched "e Musaeo 180" is conformed to "e Mus. 180" alongside the
matched "e Musaeo 1". Two independent transforms run on each idno:

  * abbreviation folds  -- only the collections that differ from the Bodleian by
    convention (the maps below); everything else is left spelled as it is.
  * enumeration spacing -- a space after any single-letter designator's period,
    a format the Bodleian uses across all shelfmarks; applied to every idno.

Only the <idno> text changes; the msDesc xml:id is a stable identifier
(Records.xml key-joins) and is never touched. Folds are cross-checked against the
authoritative Bodleian shelfmark of every matched "abbrev" row in the matches CSV
before anything is written.

Usage:
    python3 regularize_bodleian_shelfmarks.py          # dry run -> print changes
    python3 regularize_bodleian_shelfmarks.py --write   # rewrite Manuscripts.xml
"""

import argparse
import csv
import re
import sys
from pathlib import Path

from lxml import etree

TEI = "http://www.tei-c.org/ns/1.0"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"t": TEI}

DIMEV_MSS = Path("../../dimev/data/Manuscripts.xml")
MATCHES_CSV = Path("../artefacts/bodleian-links-matches.csv")

# Multi-token folds, applied before tokenizing. "Bodl. Lat. liturg." drops the
# redundant library prefix the Bodleian omits; "Ashmole Rolls" is its own series.
PHRASE_FOLDS = {
    "Bodl. Lat. liturg.": "Lat. liturg.",
    "Ashmole Rolls": "Ash. Rolls",
}

# Whole-token folds: DIMEV collection spelling -> Bodleian spelling. Conservative:
# only collections the Bodleian actually abbreviates differently from DIMEV.
TOKEN_FOLDS = {
    "Addit.": "Add.",
    "Bodley": "Bodl.",
    "Rawlinson": "Rawl.",
    "Musaeo": "Mus.",   # "e Musaeo" -> "e Mus."
    "theol.": "th.",    # "Eng./Lat. theol." -> "... th."
    "Donati": "donat.",  # "Hatton Donati" -> "Hatton donat."
}

# A single letter + "." immediately followed by alphanumeric -> add a space.
# Lookbehind keeps it to standalone designators ("A.11", "Q.b.4"), never the tail
# of a multi-letter abbreviation ("Eng.", "theol.", "Misc.").
_SPACE_RE = re.compile(r"(?<![A-Za-z])([A-Za-z])\.(?=[A-Za-z0-9])")


def fold(idno):
    """Apply the abbreviation folds only (no spacing)."""
    s = idno
    for src, dst in PHRASE_FOLDS.items():
        s = s.replace(src, dst)
    s = " ".join(TOKEN_FOLDS.get(t, t) for t in s.split())
    return s


def space(idno):
    """Apply enumeration spacing only (no folds)."""
    return re.sub(r"\s{2,}", " ", _SPACE_RE.sub(r"\1. ", idno)).strip()


def transform(idno):
    """Full regularization: abbreviation folds, then enumeration spacing."""
    return space(fold(idno.strip()))


def crosscheck():
    """Validate the fold rules against the authoritative Bodleian shelfmarks.

    For every matched "abbrev" row, fold(dimev) must equal the Bodleian shelfmark
    minus its "MS. " prefix, compared with parentheticals ignored (DIMEV omits the
    Bodleian's "(R)" disambiguators, which we do not invent). Returns a list of
    genuine discrepancies; an empty list means the rules reproduce the catalogue.
    """
    def strip_ms(s):
        return re.sub(r"^MSS?\.\s+", "", s.strip())

    def bare(s):
        return re.sub(r"\s*\([^)]*\)", "", s).strip()

    bad = []
    with MATCHES_CSV.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["match_kind"] != "abbrev":
                continue
            got = space(fold(row["dimev_idno"]))
            want = space(strip_ms(row["bodleian_shelfmark"]))
            if bare(got) != bare(want):
                bad.append((row["xml_id"], row["dimev_idno"], got, want))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help="rewrite Manuscripts.xml (default: dry run)")
    args = ap.parse_args()

    bad = crosscheck()
    if bad:
        print("FOLD CROSS-CHECK FAILED -- fold rules disagree with the catalogue:")
        for xml_id, dimev, got, want in bad:
            print(f"  {xml_id}: {dimev!r} -> fold {got!r} != catalogue {want!r}")
        print("Refusing to write; fix the fold maps.")
        sys.exit(1)
    print("Fold cross-check: OK (rules reproduce every matched Bodleian shelfmark).")

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(DIMEV_MSS), parser)
    root = tree.getroot()

    folds, spaces = [], []  # (xml_id, old, new)
    for msd in root.findall(".//t:msDesc", NS):
        repo = msd.findtext("t:msIdentifier/t:repository", default="", namespaces=NS)
        if repo.strip() != "Bodleian Library" or msd.get("type") != "manuscript":
            continue
        idno = msd.find("t:msIdentifier/t:idno", NS)
        if idno is None or not (idno.text or "").strip():
            continue
        old = idno.text.strip()
        new = transform(old)
        if new == old:
            continue
        xml_id = msd.get(f"{{{XML}}}id")
        (folds if fold(old) != old else spaces).append((xml_id, old, new))
        if args.write:
            idno.text = new

    def dump(title, rows):
        print(f"\n## {title} ({len(rows)})")
        w = max((len(o) for _, o, _ in rows), default=0)
        for xml_id, old, new in sorted(rows, key=lambda r: r[1]):
            print(f"  {xml_id:18} {old:<{w}}  ->  {new}")

    dump("Abbreviation folds", folds)
    dump("Spacing only", spaces)
    print(f"\n{len(folds) + len(spaces)} idno(s) to change "
          f"({len(folds)} folded, {len(spaces)} spaced).")

    if args.write:
        etree.indent(tree, space=4 * " ", level=0)
        tree.write(str(DIMEV_MSS), pretty_print=True,
                   xml_declaration=True, encoding="UTF-8")
        print(f"Wrote {DIMEV_MSS}")
    else:
        print("Dry run; pass --write to apply.")


if __name__ == "__main__":
    main()
