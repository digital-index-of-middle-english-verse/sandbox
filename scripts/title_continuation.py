#!/usr/bin/env python3
"""Trim DIMEV <title> values that run past MARC 245 $a into the $b
continuation (subtitle), for records with NO uniform title (no 130/240).

Where the DIMEV title absorbs the $b continuation, $a alone is the sufficient
short title. This writes a report, then overwrites each flagged <title> with
MARC 245 $a (final punctuation stripped). Four records have a $a that is itself
long or cut mid-clause; they are trimmed too, but flagged with a log warning
for manual attention.
"""

from lxml import etree
import os
import re
import json
import logging
import difflib

SOURCE_FILE = '../../dimev/data/PrintedBooks.xml'
ESTC_DIR = '../../estc/estc_output/'
REPORT_FILE = '../artefacts/title_continuation.txt'
LOG_FILE = '../artefacts/title_continuation.log'
TEI = '{http://www.tei-c.org/ns/1.0}'

# $a is long or cut mid-clause; trim but flag for manual attention
REVIEW_TITLES = {"22607", "9983", "9983.3", "20722"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
log = logging.getLogger(__name__)


def get_idno(monogr, type_):
    for ref in monogr.findall(TEI + "idno"):
        if ref.get("type") == type_:
            return ref.text or ""
    return ""


def norm(s):
    s = s.lower()
    s = s.replace("…", " ")
    s = re.sub(r"\.\.\.", " ", s)
    s = re.sub(r"\[and\]|\[et\]|&", " and ", s)
    s = re.sub(r"[\[\]]", "", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def propose_title(a):
    """The MARC 245 $a, whitespace-normalized and stripped of trailing
    punctuation (DIMEV titles carry none)."""
    s = re.sub(r"\s+", " ", a).strip()
    s = re.sub(r"[\s.,;:/]+$", "", s)
    return s


def coverage(needle, haystack):
    """Fraction of `needle` (normalized) that appears, in order, inside
    `haystack` (normalized), via difflib matching blocks."""
    if not needle:
        return 0.0
    sm = difflib.SequenceMatcher(None, needle, haystack)
    matched = sum(size for _, _, size in sm.get_matching_blocks())
    return matched / len(needle)


def main():
    files = set(os.listdir(ESTC_DIR))
    tree = etree.parse(SOURCE_FILE)
    root = tree.getroot()

    rows = []
    for item in root.findall(TEI + "biblStruct"):
        monogr = item.find(TEI + "monogr")
        stc = get_idno(monogr, "STC")
        if not stc:
            continue
        fn = "STC_" + re.sub(r"\.", "_", stc) + ".json"
        if fn not in files:
            continue
        data = json.load(open(os.path.join(ESTC_DIR, fn)))
        if data["matching_records"] != 1:
            continue
        rec = data["records"][0]
        if "130" in rec or "240" in rec or "245" not in rec:
            continue
        sf = rec["245"][0]["subfields"]
        a = " ".join(sf.get("a", [])).strip()
        b = " ".join(sf.get("b", [])).strip()
        if not b:                                # no continuation to absorb
            continue

        title_el = monogr.find(TEI + "title")
        dimev = re.sub(r"\s+", " ", title_el.text or "").strip()
        dn, an, bn = norm(dimev), norm(a), norm(b)

        a_cover = coverage(an, dn)               # is $a present in DIMEV?
        b_cover = coverage(bn, dn)               # how much of $b is in DIMEV?
        rows.append({
            "stc": stc, "a_cover": a_cover, "b_cover": b_cover,
            "dimev": dimev, "a": a, "b": b,
            "title_el": title_el, "proposed": propose_title(a),
        })

    # only the records that carry $a and meaningfully absorb $b
    hits = [r for r in rows if r["a_cover"] >= 0.80 and r["b_cover"] >= 0.30]
    hits.sort(key=lambda r: -r["b_cover"])

    lines = []
    lines.append("DIMEV <title> absorbing MARC 245 $b (no uniform title)")
    lines.append("=" * 70)
    lines.append("%d records have a $b continuation; %d carry $b into the title."
                 % (len(rows), len(hits)))
    lines.append("Proposed = MARC 245 $a alone. b_cover = fraction of $b in DIMEV.")
    lines.append("")
    for r in hits:
        full = "ALL of $b" if r["b_cover"] >= 0.85 else "part of $b"
        flag = "  [REVIEW]" if r["stc"] in REVIEW_TITLES else ""
        lines.append("")
        lines.append("STC %s  (carries %s; b_cover=%.2f)%s"
                     % (r["stc"], full, r["b_cover"], flag))
        lines.append("  DIMEV now : " + r["dimev"])
        lines.append("  Trimmed to: " + r["proposed"])
        lines.append("  ($b tail) : " + r["b"])

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote %s" % REPORT_FILE)

    # apply the trims: overwrite each flagged <title> with MARC 245 $a
    for r in hits:
        r["title_el"].text = r["proposed"]
        if r["stc"] in REVIEW_TITLES:
            log.warning("REVIEW  STC%s: $a long or cut mid-clause; trimmed to %r",
                        r["stc"], r["proposed"])
        else:
            log.info("TRIM    STC%s: -> %r", r["stc"], r["proposed"])

    etree.indent(tree, space="    ", level=0)
    tree.write(SOURCE_FILE, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    log.info("Trimmed %d titles to MARC 245 $a (%d flagged for review).",
             len(hits), len(REVIEW_TITLES))
    print("Wrote %s" % SOURCE_FILE)


if __name__ == "__main__":
    main()
