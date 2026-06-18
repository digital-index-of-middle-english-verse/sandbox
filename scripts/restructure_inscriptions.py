#!/usr/bin/env python3

"""Structural restructure of Inscriptions.xml (see dimev issue #63).

Migrates the legacy list/item structure to the restricted TEI listBibl/msDesc
profile already adopted for Manuscripts.xml:

    list                  -> listBibl    (xmlns = TEI)
    item                  -> msDesc       (xml:id preserved verbatim; @type added)
    settlement            -> msIdentifier/settlement   (verbatim)
    repos                 -> msIdentifier/repository    (verbatim)
    desc                  -> desc         (TRANSITIONAL, carried verbatim)

Every record is a non-manuscript inscribed object, so msDesc/@type is REQUIRED
by the interim schema (schemas/inscriptions.xsd). This script assigns a
best-guess @type from a keyword classification of the legacy <desc> text, drawn
from the controlled vocabulary:

    monument | glazing | wallPainting | graffito | architectural | object

The assignment is HEURISTIC. Every record is dumped to a review artefact
(inscriptions-types.csv: id, type, keyword, confidence, settlement, desc) for
manual verification. Where automatic confidence is "low" (no keyword matched)
the value is a placeholder requiring human eyes.

A manual override file may be supplied (see OVERRIDE_FILE). If present, it is a
CSV of `id,type` rows; any id listed there takes the given type verbatim,
overriding the heuristic. This is the human-in-the-loop correction path: run
once, edit the corrections file, re-run.

What this script deliberately does NOT do (deferred to a later enrichment pass):
    - decompose desc into head / availability / custEvent (extant status) / idno
    - extract accession numbers (in repos/desc) into idno
    - rehome olim settlements/owners into altIdentifier type="former"
    - add country; split county out of settlement; regularize place names

xml:id values are the join key referenced from Records.xml via <source key="...">
and are copied through unchanged.

Output validates against the INTERIM schemas/inscriptions.xsd, not yet tei_all.

Usage:
    python3 restructure_inscriptions.py            # dry run -> ../artefacts/Inscriptions.phase1.xml
    python3 restructure_inscriptions.py --in-place # overwrite the real data file
"""

from lxml import etree
import argparse
import csv
import logging
import os
import re

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SOURCE_FILE = "../../dimev/data/Inscriptions.xml"
PREVIEW_FILE = "../artefacts/Inscriptions.phase1.xml"
REVIEW_FILE = "../artefacts/inscriptions-types.csv"
OVERRIDE_FILE = "../artefacts/inscriptions-types.corrections.csv"
LOG_FILE = "../artefacts/restructure_inscriptions.log"

TEI = "http://www.tei-c.org/ns/1.0"
TEI_B = "{%s}" % TEI
XML_B = "{http://www.w3.org/XML/1998/namespace}"

VOCAB = ("monument", "glazing", "wallPainting", "graffito", "architectural", "object")
FALLBACK_TYPE = "object"  # placeholder when no keyword matches; flagged low-confidence

# Ordered (first match wins). Order resolves overlap: a "brass tomb" is a
# monument, not (via "brass") an object; a "stained glass window" is glazing;
# "wall painting" is wallPainting but "wall inscription" falls through to
# architectural. Patterns are matched case-insensitively as whole words where
# that matters (\b) to avoid e.g. "tile" matching inside another word.
CLASSIFIER = [
    ("graffito",      r"graffit"),
    ("monument",      r"\btomb|\bbrass|epitaph|\bslab\b|memorial|effig|chrysom|palimpsest|incised|monument"),
    ("glazing",       r"window|glass|roundel|glazed"),
    ("wallPainting",  r"mural|wall painting|wall paintings|\bpainted\b|\bpainting\b"),
    ("object",        r"\bring\b|\bhoop\b|\bjug\b|\bewer\b|\bcup\b|mazer|\bslate\b|\btile\b|\bbell\b|\bsword\b|triptych|picture|\bcards\b|\bplate\b|copper|fortune"),
    ("architectural", r"\bdoor\b|porch|pillar|\bpier\b|arcade|gateway|\bfont\b|lectern|carved|\bwood\b|running around|tower|cloister|inscription|\bwall\b|\bpew\b"),
]


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

def load_overrides():
    """Read the optional manual `id,type` corrections file (if present)."""
    overrides = {}
    if not os.path.exists(OVERRIDE_FILE):
        return overrides
    with open(OVERRIDE_FILE, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            xmlid = (row.get("id") or "").strip()
            typ = (row.get("type") or "").strip()
            if not xmlid:
                continue
            if typ not in VOCAB:
                log.error("override for %s has invalid type %r; ignored", xmlid, typ)
                continue
            overrides[xmlid] = typ
    if overrides:
        log.info("loaded %d manual type override(s) from %s", len(overrides), OVERRIDE_FILE)
    return overrides


def classify(desc_text):
    """Return (type, matched_keyword, confidence) for a legacy desc string."""
    text = (desc_text or "").strip()
    if text:
        for typ, pattern in CLASSIFIER:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return typ, m.group(0), "high"
    return FALLBACK_TYPE, "", "low"


def tei_copy(src, localname=None):
    """Deep-copy a legacy (no-namespace) element into the TEI namespace.

    Preserves mixed content, attributes, and child order; skips comment/PI
    nodes. (Inscriptions desc/settlement/repos are text-only in practice, but
    this keeps the migration robust to stray inline markup.)
    """
    name = localname or etree.QName(src.tag).localname
    new = etree.Element(TEI_B + name)
    for key, value in src.attrib.items():
        new.set(key, value)
    new.text = src.text
    for child in src:
        if not isinstance(child.tag, str):
            continue
        new_child = tei_copy(child)
        new_child.tail = child.tail
        new.append(new_child)
    return new


def build_msdesc(item, overrides, tally, review_rows):
    """Map one legacy <item> to a TEI <msDesc>."""
    xmlid = item.get(XML_B + "id")
    if not xmlid:
        log.error("SKIP: <item> without xml:id; cannot map (join key missing)")
        tally["skipped (no xml:id)"] += 1
        return None

    msdesc = etree.Element(TEI_B + "msDesc")
    msdesc.set(XML_B + "id", xmlid)

    desc = item.find("desc")
    desc_text = desc.text if desc is not None else ""

    # --- @type: manual override beats heuristic ----------------------------
    if xmlid in overrides:
        typ, keyword, confidence = overrides[xmlid], "(override)", "manual"
    else:
        typ, keyword, confidence = classify(desc_text)
    msdesc.set("type", typ)
    tally["type:" + typ] += 1
    if confidence == "low":
        tally["LOW-CONFIDENCE (review)"] += 1
        log.warning("%s: no keyword matched; defaulted type=%s | desc=%r",
                    xmlid, typ, (desc_text or "").strip())

    settlement = item.find("settlement")
    repos = item.find("repos")
    review_rows.append({
        "id": xmlid,
        "type": typ,
        "keyword": keyword,
        "confidence": confidence,
        "settlement": (settlement.text or "").strip() if settlement is not None else "",
        "repository": (repos.text or "").strip() if repos is not None else "",
        "desc": (desc_text or "").strip(),
    })

    # --- msIdentifier: settlement, repository (verbatim) -------------------
    msid = etree.SubElement(msdesc, TEI_B + "msIdentifier")

    if settlement is None:
        log.warning("%s: no <settlement>; inserting an empty one", xmlid)
        etree.SubElement(msid, TEI_B + "settlement")
        tally["missing settlement"] += 1
    else:
        msid.append(tei_copy(settlement, "settlement"))

    if repos is None:
        log.error("%s: no <repos>; inserting an empty <repository>", xmlid)
        etree.SubElement(msid, TEI_B + "repository")
        tally["missing repos"] += 1
    else:
        msid.append(tei_copy(repos, "repository"))
        if not (repos.text or "").strip():
            tally["empty repository"] += 1

    # --- desc (TRANSITIONAL, verbatim) -------------------------------------
    if desc is None:
        log.warning("%s: no <desc>", xmlid)
        tally["missing desc"] += 1
    else:
        msdesc.append(tei_copy(desc, "desc"))

    return msdesc


def restructure(root, overrides, tally, review_rows):
    """Build a fresh TEI <listBibl> from the live <item> elements of <list>."""
    new_root = etree.Element(TEI_B + "listBibl", nsmap={None: TEI})
    pi = etree.ProcessingInstruction("xml-model", "href='../schemas/inscriptions.xsd'")
    new_root.addprevious(pi)

    for item in root.findall("item"):
        msdesc = build_msdesc(item, overrides, tally, review_rows)
        if msdesc is not None:
            new_root.append(msdesc)
            tally["msDesc written"] += 1

    return etree.ElementTree(new_root)


def write_review(review_rows):
    os.makedirs(os.path.dirname(REVIEW_FILE), exist_ok=True)
    fields = ["id", "type", "keyword", "confidence", "settlement", "repository", "desc"]
    with open(REVIEW_FILE, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(review_rows)
    log.info("Wrote type-review artefact (%d rows) to %s", len(review_rows), REVIEW_FILE)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="overwrite %s instead of writing the preview file" % SOURCE_FILE,
    )
    args = parser.parse_args()

    parser_obj = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(SOURCE_FILE, parser_obj)
    root = tree.getroot()

    source_items = len(root.findall("item"))
    source_comments = sum(1 for n in root if not isinstance(n.tag, str))
    log.info("Source <list>: %d live <item>, %d comment node(s) (dropped)",
             source_items, source_comments)

    overrides = load_overrides()

    from collections import Counter
    tally = Counter()
    review_rows = []
    new_tree = restructure(root, overrides, tally, review_rows)

    etree.indent(new_tree, space="    ")

    out = SOURCE_FILE if args.in_place else PREVIEW_FILE
    os.makedirs(os.path.dirname(out), exist_ok=True)
    new_tree.write(out, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    write_review(review_rows)

    log.info("Tally: %s", dict(sorted(tally.items())))
    log.info("Wrote %d msDesc to %s%s",
             tally["msDesc written"], out,
             "" if args.in_place else "  (preview; re-run with --in-place to apply)")


if __name__ == "__main__":
    main()
