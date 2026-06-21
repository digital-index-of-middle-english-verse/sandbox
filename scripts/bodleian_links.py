#!/usr/bin/env python3

"""Match DIMEV Bodleian manuscripts to bodleian/medieval-mss (see dimev issue #64).

Goal: supply links to on-line catalogue records and digital facsimiles for
Oxford, Bodleian Library manuscripts by reading them from a local clone of
``bodleian/medieval-mss`` rather than transcribing by hand.

This module does the *lookup*, which is the hard part. Rather than constructing
a Bodleian filename from a DIMEV shelfmark (brittle: DIMEV "Addit. A.11" ->
Bodleian "MS. Add. A. 11" -> file MS_Add_A_11.xml, so the construction misses
on the "Addit"/"Add" convention), it INVERTS the lookup:

  1. Parse every collections/*/*.xml in the clone once, building an index keyed
     on a normalized shelfmark -> {catalogue xml:id, facsimile URLs, file}.
     Each file already records its own msID and collection, so we never guess
     filenames or maintain a subdir gazetteer.
  2. Normalize each DIMEV <idno> the same way and look it up.
  3. A second pass folds known abbreviation differences (addit->add etc.) so
     that mere convention variants MATCH instead of failing; those are reported
     separately so the editor can regularize DIMEV's spelling if desired.
  4. Whatever is still unmatched is a genuine shelfmark discrepancy -> review.

Per the issue, retrieving the links doubles as a test that DIMEV's shelfmarks
agree with the holding institution's.

For the catalogue URL, base + root TEI/@xml:id (an opaque "manuscript_NNNN").
For facsimiles, surrogates/bibl[@type="digital-facsimile"]//ref/@target.

Usage:
    python3 bodleian_links.py        # dry run -> ../artefacts/bodleian-links-report.md
                                     #         -> ../artefacts/bodleian-links-matches.csv
    python3 bodleian_links.py --write  # also apply the matched links to Manuscripts.xml

The --write pass edits ../../dimev/data/Manuscripts.xml in place, adding to each
matched msDesc a listBibl[@type="catalogue"] for the catalogue record and, where
the Bodleian record carries them, a surrogates block of digital-facsimile refs.
It only touches the *matched* set (exact + abbreviation-folded); ambiguous, near
miss, and absent entries are never written. A link is skipped when the msDesc
already carries one of that kind, so the pass is idempotent. The file is written
through the same lxml indent pipeline as scripts/formatter.py, so the diff
contains only the inserted elements.
"""

import argparse
import csv
import difflib
import re
from collections import defaultdict
from pathlib import Path

from lxml import etree

TEI = "http://www.tei-c.org/ns/1.0"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"t": TEI}

BODLEIAN_CLONE = Path("../../external-resources/oxford-medieval-mss/collections")
DIMEV_MSS = Path("../../dimev/data/Manuscripts.xml")
CATALOG_BASE = "https://medieval.bodleian.ox.ac.uk/catalog/"

REPORT_FILE = Path("../artefacts/bodleian-links-report.md")
MATCHES_CSV = Path("../artefacts/bodleian-links-matches.csv")

# Token-level abbreviation folding: DIMEV spelling -> Bodleian spelling.
# Applied only in the second ("folded") matching pass, so the report can show
# which DIMEV shelfmarks differ from the Bodleian's only by convention.
# Kept conservative: only mechanical, unambiguous conventions go here. Anything
# subtler is left to the fuzzy pass, which surfaces it as a review suggestion
# rather than silently rewriting the shelfmark.
ABBREV = {
    "addit": "add",        # DIMEV "Addit. A.11"     vs Bodleian "MS. Add. A. 11"
    "musaeo": "mus",       # the issue's own example: "e Mus." not "e Musaeo"
    "bodley": "bodl",      # DIMEV "Bodley 100"      vs Bodleian "MS. Bodl. 100"
    "rawlinson": "rawl",   # DIMEV "Rawlinson C.22"  vs Bodleian "MS. Rawl. C. 22"
    "theol": "th",         # DIMEV "Eng. theol. e.1" vs Bodleian "MS. Eng. th. e. 1"
    "donati": "donat",     # DIMEV "Hatton Donati 1" vs Bodleian "MS. Hatton donat. 1"
}

# Phrase-level folds, applied before tokenizing in the folded pass. Used where a
# token fold would over-reach: "Ashmole" alone must stay, but the DIMEV "Ashmole
# Rolls" series is the Bodleian "Ash. Rolls".
PHRASE = {
    "ashmole rolls": "ash rolls",
}

# Fuzzy threshold for classifying an otherwise-unmatched DIMEV shelfmark as a
# probable spelling discrepancy (a near match exists in the clone) rather than
# absent from medieval-mss altogether. In a shelfmark the enumeration is the
# identity: the numbers AND the single-letter designators ("Eng. poet. b.5" is
# not "Eng. poet. d.5"; "Add. A." is not "Add. B."). So the fuzzy pass requires
# the identity signature (digits + single letters, in order) to be identical and
# only lets multi-letter collection names vary in spelling; the ratio on those
# guards against cross-collection collisions ("Ashmole 176" vs "Douce 176").
FUZZY_CUTOFF = 0.5


def idsig(tokens):
    """Identity-bearing tokens: digits and single letters, in order."""
    return tuple(t for t in tokens if t.isdigit() or len(t) == 1)


def collsig(tokens):
    """Collection-name tokens (multi-letter), whose spelling may vary."""
    return " ".join(t for t in tokens if t.isalpha() and len(t) > 1)


def normalize(raw, fold=False):
    """Reduce a shelfmark string to a comparison key.

    Lowercase; drop a trailing ", Part(s) ..." qualifier (DIMEV records parts
    the Bodleian keeps in one file); collapse punctuation to single spaces; drop
    a leading MS/MSS token. With fold=True, also apply the ABBREV map.
    """
    s = raw.lower().strip()
    s = re.sub(r",\s*parts?\b.*$", "", s)        # "ashmole 1378, parts ii, iii" -> "ashmole 1378"
    s = re.sub(r"\(.*?\)", " ", s)               # drop Bodleian annotations e.g. "(R)"
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"^mss?\b\s*", "", s)             # drop leading "ms"/"mss"
    if fold:
        for src, dst in PHRASE.items():
            s = s.replace(src, dst)
    tokens = s.split()
    if fold:
        tokens = [ABBREV.get(t, t) for t in tokens]
        # Drop a redundant leading "bodl" library prefix when it is followed by
        # a sub-collection name (alphabetic), e.g. DIMEV "Bodl. Lat. liturg. e.10"
        # vs Bodleian "MS. Lat. liturg. e. 10". Keep it for the Bodley collection
        # itself ("Bodl. 100" -> "bodl 100"), where the next token is numeric.
        if len(tokens) >= 3 and tokens[0] == "bodl" and not tokens[1].isdigit():
            tokens = tokens[1:]
    return " ".join(tokens)


def build_index():
    """Index the Bodleian clone: normalized shelfmark -> list of records."""
    base = defaultdict(list)
    folded = defaultdict(list)
    n_files = n_shelfmarks = 0
    for path in sorted(BODLEIAN_CLONE.glob("*/*.xml")):
        try:
            root = etree.parse(str(path)).getroot()
        except etree.XMLSyntaxError:
            continue
        if not root.tag.endswith("}TEI"):
            continue
        n_files += 1
        cat_id = root.get(f"{{{XML}}}id")
        facs = [
            ref.get("target")
            for ref in root.findall(
                './/t:surrogates/t:bibl[@type="digital-facsimile"]//t:ref', NS
            )
            if ref.get("target")
        ]
        for idno in root.findall('.//t:msIdentifier/t:idno[@type="shelfmark"]', NS):
            shelf = (idno.text or "").strip()
            if not shelf:
                continue
            n_shelfmarks += 1
            rec = {
                "shelfmark": shelf,
                "cat_id": cat_id,
                "cat_url": CATALOG_BASE + cat_id if cat_id else "",
                "facsimiles": facs,
                "file": path.relative_to(BODLEIAN_CLONE.parent).as_posix(),
            }
            base[normalize(shelf)].append(rec)
            folded[normalize(shelf, fold=True)].append(rec)
    return base, folded, n_files, n_shelfmarks


def load_dimev_bodleian():
    """DIMEV msDesc entries whose repository is the Bodleian Library.

    Returns every Bodleian entry with its @type. The caller links only
    type="manuscript": the Bodleian catalogue records manuscripts, so a
    type="printed" entry has no legitimate record to match and any apparent hit
    is a shelfmark-string collision (e.g. printed "Bodley 88" vs MS. Bodl. 88*).
    """
    root = etree.parse(str(DIMEV_MSS)).getroot()
    entries = []
    for msd in root.findall(".//t:msDesc", NS):
        repo = msd.findtext("t:msIdentifier/t:repository", default="", namespaces=NS)
        if repo.strip() != "Bodleian Library":
            continue
        idno = msd.findtext("t:msIdentifier/t:idno", default="", namespaces=NS).strip()
        has_surr = msd.find("t:additional/t:surrogates", NS) is not None
        has_cat = (
            msd.find('t:additional/t:listBibl[@type="catalogue"]', NS) is not None
        )
        entries.append(
            {
                "xml_id": msd.get(f"{{{XML}}}id"),
                "idno": idno,
                "type": msd.get("type"),
                "has_surrogates": has_surr,
                "has_catalogue": has_cat,
            }
        )
    return entries


def classify(entries, base, folded, by_sig):
    """Bucket entries against the Bodleian index: exact/abbrev/ambiguous/
    nearmiss/absent. Returns the five lists."""
    exact, abbrev, ambiguous, nearmiss, absent = [], [], [], [], []
    for e in entries:
        nb = normalize(e["idno"])
        nf = normalize(e["idno"], fold=True)
        if nb in base:
            hits = base[nb]
            (ambiguous if len(hits) > 1 else exact).append((e, hits))
        elif nf in folded:
            hits = folded[nf]
            (ambiguous if len(hits) > 1 else abbrev).append((e, hits))
        else:
            # Still no match. Among Bodleian keys sharing the exact enumeration,
            # is one a close collection-name variant (probable discrepancy)?
            # Otherwise treat as absent from medieval-mss.
            toks = nf.split()
            cands = by_sig.get(idsig(toks), [])
            target = collsig(toks)
            scored = sorted(
                ((difflib.SequenceMatcher(None, target, collsig(c.split())).ratio(), c)
                 for c in cands),
                reverse=True,
            )
            if scored and scored[0][0] >= FUZZY_CUTOFF:
                nearmiss.append((e, base[scored[0][1]]))
            else:
                absent.append(e)
    return exact, abbrev, ambiguous, nearmiss, absent


# Child order within <additional>, per manuscripts.xsd: adminInfo, surrogates,
# listBibl. New elements are appended then the children re-sorted to this order.
ADDITIONAL_ORDER = {"adminInfo": 0, "surrogates": 1, "listBibl": 2}


def apply_links(matched):
    """Write the matched catalogue/surrogate links into Manuscripts.xml in place.

    Idempotent: a link is added only when the msDesc lacks one of that kind, so
    re-running (or running after manual pre-emption) is a no-op for already-linked
    entries. Returns (n_cat, n_surr, n_new_additional, skipped_cat, skipped_surr).
    """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(DIMEV_MSS), parser)
    root = tree.getroot()
    by_id = {m.get(f"{{{XML}}}id"): m for m in root.findall(".//t:msDesc", NS)}

    n_cat = n_surr = n_new_add = skipped_cat = skipped_surr = 0
    for e, hits in matched:
        rec = hits[0]
        msd = by_id.get(e["xml_id"])
        if msd is None:
            continue
        additional = msd.find("t:additional", NS)
        has_surr = additional is not None and additional.find("t:surrogates", NS) is not None
        has_cat = (
            additional is not None
            and additional.find('t:listBibl[@type="catalogue"]', NS) is not None
        )
        want_surr = bool(rec["facsimiles"]) and not has_surr
        want_cat = bool(rec["cat_url"]) and not has_cat
        if rec["facsimiles"] and has_surr:
            skipped_surr += 1
        if rec["cat_url"] and has_cat:
            skipped_cat += 1
        if not (want_surr or want_cat):
            continue

        if additional is None:
            additional = etree.SubElement(msd, f"{{{TEI}}}additional")
            n_new_add += 1
        if want_surr:
            surr = etree.SubElement(additional, f"{{{TEI}}}surrogates")
            for url in rec["facsimiles"]:
                ref = etree.SubElement(
                    etree.SubElement(surr, f"{{{TEI}}}bibl"), f"{{{TEI}}}ref"
                )
                ref.set("target", url)
            n_surr += 1
        if want_cat:
            lb = etree.SubElement(additional, f"{{{TEI}}}listBibl")
            lb.set("type", "catalogue")
            ref = etree.SubElement(
                etree.SubElement(lb, f"{{{TEI}}}bibl"), f"{{{TEI}}}ref"
            )
            ref.set("target", rec["cat_url"])
            n_cat += 1

        for child in sorted(
            additional, key=lambda c: ADDITIONAL_ORDER.get(etree.QName(c).localname, 99)
        ):
            additional.append(child)  # move into schema order

    etree.indent(tree, space=4 * " ", level=0)
    tree.write(str(DIMEV_MSS), pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return n_cat, n_surr, n_new_add, skipped_cat, skipped_surr


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--write",
        action="store_true",
        help="apply the matched links to Manuscripts.xml (default: dry run only)",
    )
    args = ap.parse_args()

    base, folded, n_files, n_shelf = build_index()
    all_entries = load_dimev_bodleian()

    # For the fuzzy pass: bucket Bodleian keys by identity signature so a
    # candidate must share the exact enumeration (numbers + single letters).
    by_sig = defaultdict(list)
    for k in base:
        by_sig[idsig(k.split())].append(k)

    # The Bodleian catalogue holds manuscripts only; link those. Printed-book
    # entries are tabulated separately as a footprint check, never linked.
    entries = [e for e in all_entries if e["type"] == "manuscript"]
    printed = [e for e in all_entries if e["type"] == "printed"]

    exact, abbrev, ambiguous, nearmiss, absent = classify(entries, base, folded, by_sig)
    p_exact, p_abbrev, p_ambig, p_near, p_absent = classify(printed, base, folded, by_sig)

    matched = exact + abbrev
    with_facs = sum(1 for e, h in matched if h[0]["facsimiles"])
    already_cat = sum(1 for e in entries if e["has_catalogue"])
    already_surr = sum(1 for e in entries if e["has_surrogates"])

    # ---- matches CSV (one row per matched DIMEV entry) ----
    MATCHES_CSV.parent.mkdir(exist_ok=True)
    with MATCHES_CSV.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["xml_id", "dimev_idno", "match_kind", "bodleian_shelfmark",
             "cat_id", "cat_url", "n_facsimiles", "facsimile_urls", "file"]
        )
        for kind, group in (("exact", exact), ("abbrev", abbrev)):
            for e, hits in group:
                r = hits[0]
                w.writerow([
                    e["xml_id"], e["idno"], kind, r["shelfmark"], r["cat_id"],
                    r["cat_url"], len(r["facsimiles"]), " ".join(r["facsimiles"]),
                    r["file"],
                ])

    # ---- markdown report ----
    L = []
    L.append("# Bodleian links — dry-run match report (issue #64)\n")
    L.append(f"- Bodleian clone indexed: **{n_files}** TEI files, "
             f"**{n_shelf}** shelfmark idnos.")
    L.append(f"- DIMEV Bodleian Library entries: **{len(all_entries)}** "
             f"({len(entries)} type=manuscript [linked], "
             f"{len(printed)} type=printed [excluded — see footprint]).")
    L.append(f"- Matched: **{len(matched)}** "
             f"({len(exact)} exact, {len(abbrev)} after abbreviation folding).")
    L.append(f"- Ambiguous (normalized to >1 Bodleian record): **{len(ambiguous)}**.")
    L.append(f"- Near miss (close Bodleian record exists — likely a shelfmark "
             f"discrepancy to reconcile): **{len(nearmiss)}**.")
    L.append(f"- Absent (no close record in medieval-mss — uncatalogued there, "
             f"lost, or DIMEV-only): **{len(absent)}**.")
    L.append(f"- Of matched, **{with_facs}** have at least one digital facsimile.")
    L.append(f"- Already carry links in DIMEV (skip on write): "
             f"{already_cat} catalogue, {already_surr} surrogates.\n")

    L.append("## Printed-book footprint (type=\"printed\", excluded from linking)\n")
    L.append(f"{len(printed)} Bodleian entries are copies of printed books. The "
             "Bodleian catalogue records manuscripts only, so these are not "
             "linked. Any apparent hit below is a shelfmark-string collision "
             "with an unrelated manuscript, not a real match.\n")
    L.append(f"- Would-be exact/abbrev hits (spurious): "
             f"**{len(p_exact) + len(p_abbrev)}**")
    L.append(f"- Would-be ambiguous: **{len(p_ambig)}**")
    L.append(f"- Would-be near miss: **{len(p_near)}**")
    L.append(f"- No Bodleian record at all: **{len(p_absent)}**\n")
    spurious = [(e, h) for e, h in (p_exact + p_abbrev + p_ambig)]
    if spurious:
        L.append("Spurious would-be matches (excluded because type=printed):\n")
        L.append("| DIMEV xml:id | DIMEV idno | Collided with |")
        L.append("|---|---|---|")
        for e, hits in sorted(spurious, key=lambda x: x[0]["idno"]):
            L.append(f"| {e['xml_id']} | {e['idno']} | {hits[0]['shelfmark']} |")
        L.append("")

    if abbrev:
        L.append("## Matched only after abbreviation folding\n")
        L.append("DIMEV's spelling differs from the Bodleian's by convention "
                 "only. Consider regularizing the DIMEV shelfmark.\n")
        L.append("| DIMEV xml:id | DIMEV idno | Bodleian shelfmark |")
        L.append("|---|---|---|")
        for e, hits in sorted(abbrev, key=lambda x: x[0]["idno"]):
            L.append(f"| {e['xml_id']} | {e['idno']} | {hits[0]['shelfmark']} |")
        L.append("")

    if ambiguous:
        L.append("## Ambiguous — normalized to more than one Bodleian record\n")
        L.append("| DIMEV xml:id | DIMEV idno | Bodleian shelfmarks |")
        L.append("|---|---|---|")
        for e, hits in sorted(ambiguous, key=lambda x: x[0]["idno"]):
            shelves = "; ".join(h["shelfmark"] for h in hits)
            L.append(f"| {e['xml_id']} | {e['idno']} | {shelves} |")
        L.append("")

    if nearmiss:
        L.append("## Near miss — probable shelfmark discrepancy to reconcile\n")
        L.append("A close Bodleian record exists, so this is most likely a "
                 "spelling difference rather than an absent manuscript. Verify "
                 "before linking; fix the DIMEV shelfmark if it is wrong.\n")
        L.append("| DIMEV xml:id | DIMEV idno | Closest Bodleian shelfmark |")
        L.append("|---|---|---|")
        for e, hits in sorted(nearmiss, key=lambda x: x[0]["idno"]):
            L.append(f"| {e['xml_id']} | {e['idno']} | {hits[0]['shelfmark']} |")
        L.append("")

    if absent:
        L.append("## Absent — no close record in medieval-mss\n")
        L.append("Nothing comparable in the clone. The Bodleian's coverage is "
                 "partial (e.g. only some Ashmole MSS), so most of these are "
                 "simply not catalogued there; some may be lost, composite, or "
                 "DIMEV-only. No link to supply; no action unless the shelfmark "
                 "itself looks wrong.\n")
        L.append("| DIMEV xml:id | DIMEV idno |")
        L.append("|---|---|")
        for e in sorted(absent, key=lambda x: x["idno"]):
            L.append(f"| {e['xml_id']} | {e['idno']} |")
        L.append("")

    REPORT_FILE.write_text("\n".join(L))
    print(f"Indexed {n_files} Bodleian files ({n_shelf} shelfmarks).")
    print(f"DIMEV Bodleian entries: {len(all_entries)} "
          f"({len(entries)} manuscript, {len(printed)} printed [excluded])")
    print(f"  exact match     : {len(exact)}")
    print(f"  abbrev-folded   : {len(abbrev)}")
    print(f"  ambiguous       : {len(ambiguous)}")
    print(f"  near miss       : {len(nearmiss)}  (probable discrepancy)")
    print(f"  absent          : {len(absent)}  (not in medieval-mss)")
    print(f"  with facsimile  : {with_facs} of {len(matched)} matched")
    print(f"printed footprint : {len(p_exact)+len(p_abbrev)+len(p_ambig)} spurious "
          f"hits, {len(p_near)} near, {len(p_absent)} absent")
    print(f"Report  -> {REPORT_FILE}")
    print(f"Matches -> {MATCHES_CSV}")

    if args.write:
        n_cat, n_surr, n_new_add, sk_cat, sk_surr = apply_links(matched)
        print(f"\nWrote links into {DIMEV_MSS}:")
        print(f"  catalogue listBibl added : {n_cat}  (skipped {sk_cat} already present)")
        print(f"  surrogates blocks added  : {n_surr}  (skipped {sk_surr} already present)")
        print(f"  new <additional> created : {n_new_add}")


if __name__ == "__main__":
    main()
