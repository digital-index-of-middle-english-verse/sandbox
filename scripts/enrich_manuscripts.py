#!/usr/bin/env python3

"""Phase 2/3 of the Manuscripts.xml TEI restructure (see dimev issue #36).

CONTENT DISAGGREGATION + NORMALIZATION, driven by
``../artefacts/manuscripts-enrichment-wip.csv`` (the editor's first-pass tool).

This dissolves the transitional <desc> placeholder left by Phase 1
(restructure_manuscripts.py) and folds in the CSV enrichment:

    Phase 2 (disaggregation)            CSV column -> TEI destination
    ------------------------            -----------------------------
    shelfmark                           idno            -> msIdentifier/idno
    SC / catalogue numbers              altIdentifier 1 -> msIdentifier/altIdentifier/idno
    former ("olim") shelfmarks          altIdentifier 2 -> msIdentifier/altIdentifier[@type=former]/idno
    manuscript sobriquet                name            -> msIdentifier/msName
    descriptive heading / title         head            -> msDesc/head
    sale / provenance                   history         -> msDesc/history/provenance
    custodial / status note             adminInfo       -> additional/adminInfo/note
    editorial note                      note            -> additional/adminInfo/note[@type=editorial]

    Phase 3 (normalization)
    ------------------------
    country                             country         -> msIdentifier/country   (NEW)
    regularized holding place           settlement      -> msIdentifier/settlement (REPLACES Phase 1 value)
    regularized institution             repository      -> msIdentifier/repository (REPLACES Phase 1 value)

    Links
    ------------------------
    on-line surrogate (reproduction)    surrogate       -> additional/surrogates/bibl/ref   (MERGED with existing)
    on-line catalogue record            catalog link    -> additional/listBibl[@type=catalogue]/bibl/ref

Deliberately NOT touched here:
    - lang (LALME/LAEME dialect data)   -> carried verbatim, deferred to Phase 4.

Join: CSV column A (xml:id) joins to <msDesc xml:id>. The match is imperfect
(a few items were added to / removed from Manuscripts.xml after the CSV tool
was built). Unmatched msDesc keep their Phase 1 structure (settlement,
repository, transitional <desc>, lang) untouched; CSV rows with no msDesc are
reported and skipped. Nothing is deleted on the basis of an absent counterpart.

Safety nets:
    - Surrogates are MERGED: every existing additional/surrogates ref is kept;
      the CSV surrogate is added only if its URL is not already present.
    - Where the legacy <desc> holds text the CSV columns do not capture
      ("residual"), the full original <desc> is preserved as
      additional/adminInfo/note[@type=legacy-desc] (inline <i>/<sup> -> <hi>,
      <bibl>/<mss> kept) and the row is listed in the review report, so the
      editor can reconcile it later. No <desc> content is silently dropped.

Output validates against the INTERIM schemas/manuscripts.xsd (still not tei_all:
lang remains transitional until Phase 4).

Usage:
    python3 enrich_manuscripts.py            # dry run -> ../artefacts/Manuscripts.phase2.xml
    python3 enrich_manuscripts.py --in-place # overwrite the real data file
"""

from lxml import etree
import argparse
import copy
import csv
import logging
import os
import re
from collections import Counter, OrderedDict

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SOURCE_FILE = "../../dimev/data/Manuscripts.xml"
CSV_FILE = "../artefacts/manuscripts-enrichment-wip.csv"
PREVIEW_FILE = "../artefacts/Manuscripts.phase2.xml"
REPORT_FILE = "../artefacts/manuscripts-enrichment-report.md"
LOG_FILE = "../artefacts/enrich_manuscripts.log"

TEI = "http://www.tei-c.org/ns/1.0"
B = "{%s}" % TEI
XML_B = "{http://www.w3.org/XML/1998/namespace}"

OLIM_RE = re.compile(r"^olim\s+", re.IGNORECASE)

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

# legacy inline tags (as occasionally typed into CSV cells) -> TEI equivalents
INLINE_TAGMAP = {
    "i": ("hi", {"rend": "italic"}),
    "sup": ("hi", {"rend": "superscript"}),
    "biblio": ("bibl", {}),
    "bibl": ("bibl", {}),
    "mss": ("mss", {}),
}


def set_markup_text(node, value):
    """Set element content, parsing any inline markup the CSV cell may carry.

    Most cells are plain text (a bare '&' is fine -- lxml escapes it). A few
    hold legacy inline tags (<i>, <biblio .../>); those are parsed and mapped
    to their TEI equivalents rather than escaped into literal angle brackets.
    """
    if "<" not in value:
        node.text = value
        return
    try:
        frag = etree.fromstring(f"<x>{value}</x>")
    except etree.XMLSyntaxError:
        log.warning("could not parse inline markup, kept as text: %r", value)
        node.text = value
        return
    node.text = frag.text
    for child in frag:
        name, extra = INLINE_TAGMAP.get(child.tag, (child.tag, {}))
        new = etree.SubElement(node, B + name)
        for key, val in child.attrib.items():
            new.set(key, val)
        for key, val in extra.items():
            new.set(key, val)
        new.text = child.text
        new.tail = child.tail


def el(parent, name, text=None, **attrs):
    """Create and append a TEI child element, returning it."""
    node = etree.SubElement(parent, B + name)
    if text is not None:
        set_markup_text(node, text)
    for key, value in attrs.items():
        node.set(key, value)
    return node


def clean(value):
    """Trim a CSV cell; return '' for None."""
    return (value or "").strip()


def text_of(node):
    """Whitespace-normalized text content of an element (tags stripped)."""
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip()


def existing_surrogate_targets(msdesc):
    """Ordered list of surrogate ref URLs already on this msDesc."""
    out = OrderedDict()
    for ref in msdesc.findall(
        f"{B}additional/{B}surrogates/{B}bibl/{B}ref"
    ):
        target = ref.get("target")
        if target:
            out[target] = None
    return list(out)


def desc_to_note(desc):
    """Copy the legacy <desc> into a note[@type=legacy-desc].

    Inline <i>/<sup> become <hi rend="italic|superscript">; <bibl>/<mss>
    cross-references are preserved verbatim. Used only for 'residual' rows
    whose desc holds matter the CSV columns did not capture.
    """
    note = etree.Element(B + "note")
    note.set("type", "legacy-desc")
    note.text = desc.text
    for child in desc:
        if not isinstance(child.tag, str):
            continue
        localname = etree.QName(child).localname
        if localname in ("i", "sup"):
            hi = etree.SubElement(note, B + "hi")
            hi.set("rend", "italic" if localname == "i" else "superscript")
            hi.text = child.text
            for grandchild in child:
                hi.append(copy.deepcopy(grandchild))
        else:  # bibl, mss
            note.append(copy.deepcopy(child))
        note[-1].tail = child.tail
    return note


def residual_text(desc, row):
    """Desc text remaining after removing every value the CSV captured.

    Returns '' when the CSV fully accounts for the desc. A non-empty result
    flags content the disaggregation would otherwise drop.
    """
    rest = text_of(desc)
    for col in (
        "idno", "altIdentifier 1", "altIdentifier 2",
        "name", "head", "history", "adminInfo", "note",
    ):
        value = clean(row[col])
        if value:
            rest = rest.replace(value, " ")
            rest = rest.replace(OLIM_RE.sub("", value), " ")
    # drop scaffolding tokens that carry no independent information
    rest = re.sub(r"\b(olim|SC|sic|MS)\b", " ", rest)
    rest = re.sub(r"[()\[\].,;:’'\"=?/]", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip()
    return rest if re.search(r"[A-Za-z0-9]{2,}", rest) else ""


# ---------------------------------------------------------------------------
# msIdentifier construction
# ---------------------------------------------------------------------------

def add_alt_identifier(msid, value):
    """Append <altIdentifier>[<idno>value</idno>], flagging 'olim' as former."""
    attrs = {}
    if OLIM_RE.match(value):
        attrs["type"] = "former"
        value = OLIM_RE.sub("", value)
    alt = el(msid, "altIdentifier", **attrs)
    el(alt, "idno", value)


def build_msidentifier(row):
    """Build a fresh TEI <msIdentifier> from the CSV row."""
    msid = etree.Element(B + "msIdentifier")
    el(msid, "country", clean(row["country"]))
    el(msid, "settlement", clean(row["settlement"]))
    el(msid, "repository", clean(row["repository"]))
    if clean(row["idno"]):
        el(msid, "idno", clean(row["idno"]))
    if clean(row["name"]):
        el(msid, "msName", clean(row["name"]))
    for col in ("altIdentifier 1", "altIdentifier 2"):
        if clean(row[col]):
            add_alt_identifier(msid, clean(row[col]))
    return msid


# ---------------------------------------------------------------------------
# msDesc rebuild
# ---------------------------------------------------------------------------

def enrich_msdesc(msdesc, row, tally, report):
    """Rewrite a matched <msDesc> in place from its CSV row."""
    xmlid = msdesc.get(XML_B + "id")

    # capture data carried over from the existing element before we rebuild
    surrogate_targets = existing_surrogate_targets(msdesc)
    lang = msdesc.find(B + "lang")
    desc = msdesc.find(B + "desc")

    # legacy-desc safety net: keep the whole desc if it has residual matter
    legacy_note = None
    if desc is not None:
        residual = residual_text(desc, row)
        if residual:
            legacy_note = desc_to_note(desc)
            report["residual"].append((xmlid, residual))
            tally["legacy-desc preserved"] += 1

    # --- msIdentifier (replaces Phase 1 settlement/repository) -------------
    new_msid = build_msidentifier(row)

    # --- additional/adminInfo notes ---------------------------------------
    admin_notes = []
    if clean(row["adminInfo"]):
        n = etree.Element(B + "note")
        set_markup_text(n, clean(row["adminInfo"]))
        admin_notes.append(n)
    if clean(row["note"]):
        n = etree.Element(B + "note")
        n.set("type", "editorial")
        set_markup_text(n, clean(row["note"]))
        admin_notes.append(n)
    if legacy_note is not None:
        admin_notes.append(legacy_note)

    # --- merged surrogate URLs --------------------------------------------
    csv_surrogate = clean(row["surrogate"])
    if csv_surrogate and csv_surrogate not in surrogate_targets:
        if surrogate_targets:
            tally["surrogate added to existing"] += 1
            log.info(
                "%s: surrogate added alongside %d existing -> %s",
                xmlid, len(surrogate_targets), csv_surrogate,
            )
        surrogate_targets.append(csv_surrogate)
    elif surrogate_targets and not csv_surrogate:
        tally["surrogate kept (none in CSV)"] += 1
        # the CSV cell is empty but the data file has surrogate(s): the URL
        # may have been dropped from the CSV tool as a broken link -- worth a look
        log.info(
            "%s: %d existing surrogate(s) kept, none in CSV -> %s",
            xmlid, len(surrogate_targets), ", ".join(surrogate_targets),
        )

    # --- catalogue record links -------------------------------------------
    catalogue = clean(row["catalog link"])

    # --- rebuild the msDesc children in document order --------------------
    # (xml:id stays on the element; we only swap its children)
    for child in list(msdesc):
        msdesc.remove(child)
    msdesc.text = None

    msdesc.append(new_msid)

    if clean(row["head"]):
        el(msdesc, "head", clean(row["head"]))

    if clean(row["history"]):
        history = el(msdesc, "history")
        el(history, "provenance", clean(row["history"]))

    if lang is not None:
        msdesc.append(lang)
        tally["with lang"] += 1

    if admin_notes or surrogate_targets or catalogue:
        additional = el(msdesc, "additional")
        if admin_notes:
            admin = el(additional, "adminInfo")
            for n in admin_notes:
                admin.append(n)
        if surrogate_targets:
            surr = el(additional, "surrogates")
            for target in surrogate_targets:
                bibl = el(surr, "bibl")
                el(bibl, "ref", target=target)
            tally["with surrogates"] += 1
        if catalogue:
            listbibl = el(additional, "listBibl", type="catalogue")
            bibl = el(listbibl, "bibl")
            el(bibl, "ref", target=catalogue)
            tally["with catalogue"] += 1

    tally["enriched"] += 1


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def load_csv():
    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_id = OrderedDict((clean(r["xml:id"]), r) for r in rows if clean(r["xml:id"]))
    return by_id


def write_report(report, tally, xml_only, csv_only):
    lines = []
    lines.append("# Manuscripts.xml enrichment report (Phase 2/3)\n")
    lines.append("Generated by `enrich_manuscripts.py`.\n")
    lines.append("## Tally\n")
    for key, value in sorted(tally.items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append(f"## msDesc present in XML but absent from CSV ({len(xml_only)}) — left untouched\n")
    lines.append(", ".join(xml_only) if xml_only else "_none_")
    lines.append("")
    lines.append(f"## CSV rows with no msDesc ({len(csv_only)}) — skipped\n")
    lines.append(", ".join(csv_only) if csv_only else "_none_")
    lines.append("")
    lines.append(
        f"## Residual <desc> matter preserved as note[@type=legacy-desc] "
        f"({len(report['residual'])}) — for editorial review\n"
    )
    lines.append("These rows had <desc> text the CSV columns did not capture; "
                 "the full original <desc> was kept as a legacy-desc note.\n")
    lines.append("| xml:id | uncaptured residual |")
    lines.append("| --- | --- |")
    for xmlid, residual in report["residual"]:
        lines.append(f"| {xmlid} | {residual} |")
    lines.append("")
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log.info("Wrote review report -> %s", REPORT_FILE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="overwrite %s instead of writing the preview file" % SOURCE_FILE,
    )
    args = parser.parse_args()

    by_id = load_csv()
    log.info("Loaded %d CSV rows", len(by_id))

    parser_obj = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(SOURCE_FILE, parser_obj)
    root = tree.getroot()

    tally = Counter()
    report = {"residual": []}
    xml_ids = []
    seen_in_csv = set()

    for msdesc in root.findall(B + "msDesc"):
        xmlid = msdesc.get(XML_B + "id")
        xml_ids.append(xmlid)
        row = by_id.get(xmlid)
        if row is None:
            tally["unmatched (kept as-is)"] += 1
            continue
        seen_in_csv.add(xmlid)
        enrich_msdesc(msdesc, row, tally, report)

    xml_only = [x for x in xml_ids if x not in by_id]
    csv_only = [x for x in by_id if x not in seen_in_csv]

    etree.indent(tree, space="    ")

    out = SOURCE_FILE if args.in_place else PREVIEW_FILE
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tree.write(out, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    write_report(report, tally, xml_only, csv_only)

    log.info("Tally: %s", dict(tally))
    log.info(
        "Wrote %d msDesc (%d enriched, %d untouched) to %s%s",
        len(xml_ids), tally["enriched"], tally["unmatched (kept as-is)"], out,
        "" if args.in_place else "  (preview; re-run with --in-place to apply)",
    )


if __name__ == "__main__":
    main()
