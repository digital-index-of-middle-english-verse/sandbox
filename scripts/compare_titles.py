#!/usr/bin/env python3
"""Compare DIMEV <title> transcriptions against ESTC's transcribed title
(MARC 245 $a + $b) for records that have NO uniform title (no MARC 130/240).

This is a read-only diagnostic: it writes a report, never the XML. Its purpose
is to surface typographic and other input errors in DIMEV title
transcriptions. Records whose DIMEV title is an editorial short title (e.g.
"Canterbury Tales") differ wholesale from the transcription and are segregated;
the signal is in the NEAR bucket, where DIMEV closely tracks MARC but diverges.
"""

from lxml import etree
import os
import re
import json
import difflib

SOURCE_FILE = '../../dimev/data/PrintedBooks.xml'
ESTC_DIR = '../../estc/estc_output/'
REPORT_FILE = '../artefacts/title_comparison.txt'
NAMESPACE = '{http://www.w3.org/XML/1998/namespace}'
TEI = '{http://www.tei-c.org/ns/1.0}'


def get_idno(monogr, type_):
    for ref in monogr.findall(TEI + "idno"):
        if ref.get("type") == type_:
            return ref.text or ""
    return ""


def norm(s):
    """Fold the incidental differences (case, ampersand/[and], brackets,
    truncation marks, punctuation, whitespace) so the comparison ranks on
    substantive divergence, not transcription conventions."""
    s = s.lower()
    s = s.replace("…", " ")
    s = re.sub(r"\.\.\.", " ", s)
    s = re.sub(r"\[and\]|\[et\]|&", " and ", s)
    s = re.sub(r"[\[\]]", "", s)          # drop brackets, keep the content
    s = re.sub(r"[^\w\s]", " ", s)        # drop punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


def marc_245(rec):
    sf = rec["245"][0]["subfields"]
    a = " ".join(sf.get("a", []))
    b = " ".join(sf.get("b", []))
    return (a + " " + b).strip() if b else a.strip()


def char_diff(a, b):
    """Compact inline diff of two normalized strings, marking DIMEV-only text
    with {-...-} and MARC-only text with {+...+}."""
    sm = difflib.SequenceMatcher(None, a, b)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(a[i1:i2])
        elif tag == "delete":
            out.append("{-" + a[i1:i2] + "-}")
        elif tag == "insert":
            out.append("{+" + b[j1:j2] + "+}")
        elif tag == "replace":
            out.append("{-" + a[i1:i2] + "-}{+" + b[j1:j2] + "+}")
    return "".join(out)


def main():
    files = set(os.listdir(ESTC_DIR))
    root = etree.parse(SOURCE_FILE).getroot()

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
        if "130" in rec or "240" in rec:        # has a uniform title; skip
            continue
        if "245" not in rec:
            continue

        dimev_raw = (monogr.find(TEI + "title").text or "")
        dimev_raw = re.sub(r"\s+", " ", dimev_raw).strip()
        marc_raw = marc_245(rec)

        d, m = norm(dimev_raw), norm(marc_raw)
        # compare over the overlapping prefix: either side may be truncated
        L = min(len(d), len(m))
        ratio = difflib.SequenceMatcher(None, d[:L], m[:L]).ratio() if L else 0.0
        rows.append({
            "stc": stc, "ratio": ratio, "len": L,
            "dimev": dimev_raw, "marc": marc_raw, "dn": d, "mn": m,
        })

    # bucket by prefix similarity
    buckets = {"EXACT": [], "NEAR": [], "PARTIAL": [], "DISTINCT": []}
    for r in rows:
        if r["ratio"] >= 0.995:
            buckets["EXACT"].append(r)
        elif r["ratio"] >= 0.90:
            buckets["NEAR"].append(r)
        elif r["ratio"] >= 0.60:
            buckets["PARTIAL"].append(r)
        else:
            buckets["DISTINCT"].append(r)
    for b in buckets.values():
        b.sort(key=lambda r: -r["ratio"])

    lines = []
    lines.append("Title comparison: DIMEV <title> vs MARC 245 (no uniform title)")
    lines.append("=" * 70)
    lines.append("%d records compared (no MARC 130/240)." % len(rows))
    lines.append("EXACT %d  NEAR %d  PARTIAL %d  DISTINCT %d"
                 % tuple(len(buckets[k]) for k in
                         ("EXACT", "NEAR", "PARTIAL", "DISTINCT")))
    lines.append("Diff marks: {-DIMEV only-} {+MARC only+}; compared over the")
    lines.append("overlapping prefix (either side may be truncated).")
    lines.append("")

    explain = {
        "NEAR": "NEAR  (0.90<=r<0.995): close transcriptions; inspect for typos",
        "PARTIAL": "PARTIAL  (0.60<=r<0.90): divergent; typo, heavy spelling, or short title",
        "EXACT": "EXACT  (r>=0.995): match over the overlap; no action",
        "DISTINCT": "DISTINCT  (r<0.60): editorial short title, not a transcription",
    }
    for key in ("NEAR", "PARTIAL", "EXACT", "DISTINCT"):
        lines.append("")
        lines.append("#" * 70)
        lines.append("# " + explain[key])
        lines.append("#" * 70)
        for r in buckets[key]:
            lines.append("")
            lines.append("STC %s  (r=%.3f, overlap=%d)" % (r["stc"], r["ratio"], r["len"]))
            lines.append("  DIMEV: " + r["dimev"])
            lines.append("  MARC : " + r["marc"])
            if key in ("NEAR", "PARTIAL"):
                lines.append("  DIFF : " + char_diff(r["dn"], r["mn"]))

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote %s" % REPORT_FILE)
    print("EXACT %d  NEAR %d  PARTIAL %d  DISTINCT %d"
          % tuple(len(buckets[k]) for k in
                  ("EXACT", "NEAR", "PARTIAL", "DISTINCT")))


if __name__ == "__main__":
    main()
