#!/usr/bin/env python3

"""Rehome administrative/editorial notes from additional/adminInfo into
TEI-conformant homes (dimev issue #36, comment 4730645468).

Phase 2 parked a mixed bag of notes under additional/adminInfo/note as a
safety net. This pass gives the clearly classifiable ones a real home and
leaves the rest in place:

    printed-book flag        -> msDesc/@type="printed"  (note deleted)
    deposit / on-loan        -> adminInfo/custodialHist/custEvent[@type="deposit"]
    destroyed by fire        -> adminInfo/custodialHist/custEvent[@type="destroyed"] (+@when)
    missing/untraced/unknown -> adminInfo/availability[@status="unknown"]/p
    everything else          -> stays as adminInfo/note  (residue)

This is a live-tree transform (not a text rewrite): note content is MOVED
node-by-node so inline <bibl key=.../> citations (Fenn, Dod, Tiverton,
Stephens) survive as markup. After rehoming, children are re-emitted in
schema order (availability, custodialHist, note); adminInfo/additional left
empty are dropped.

Output validates against the (extended) INTERIM schemas/manuscripts.xsd.

Usage:
    python3 rehome_admin_notes.py            # dry run -> ../artefacts/Manuscripts.rehomed.xml
    python3 rehome_admin_notes.py --in-place # overwrite the real data file
"""

from lxml import etree
from collections import Counter
import argparse
import logging
import os
import re

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SOURCE_FILE = "../../dimev/data/Manuscripts.xml"
PREVIEW_FILE = "../artefacts/Manuscripts.rehomed.xml"
LOG_FILE = "../artefacts/rehome_admin_notes.log"

TEI = "http://www.tei-c.org/ns/1.0"
TEI_B = "{%s}" % TEI
XML_B = "{http://www.w3.org/XML/1998/namespace}"

# Per-record overrides, applied before keyword classification.
#   keep    -> editorial prose with no clean home; leave as note
#   missing -> availability[@status="unknown"] despite no matching keyword
OVERRIDE = {
    "HelminghamHall": "keep",   # long identification argument, not a status
    "Stephens": "missing",      # second-hand "reports as destroyed", cited
}

# Destruction years stated explicitly in the note (others get no @when;
# e.g. BLCottOthoAXVIII's 1721 is a transcription date, not the fire).
DESTROYED_WHEN = {
    "DublinChrCh": "1922",
    "Sharp": "1879",
}

PRINTED_PREFIX = re.compile(r"^printed book\b[;,.\s]*", re.IGNORECASE)

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

def note_text(note):
    """Flattened text of a note, for classification only."""
    return " ".join("".join(note.itertext()).split())


def move_content(src, dst):
    """Move src's text and child elements (with tails) into dst.

    Elements are re-parented (lxml append detaches from src), so inline
    markup is preserved exactly. dst must start empty.
    """
    dst.text = src.text
    for child in list(src):
        dst.append(child)  # moves child out of src, keeping its tail


def classify(msid, note):
    """Return one of: printed, deposit, destroyed, missing, keep."""
    if msid in OVERRIDE:
        return OVERRIDE[msid]
    text = note_text(note)
    low = text.lower()
    if low.startswith("printed book"):
        return "printed"
    if "deposit" in low:
        return "deposit"
    if "destroyed by fire" in low:
        return "destroyed"
    if any(w in low for w in
           ("missing", "untraced", "present location unknown", "unidentified")):
        return "missing"
    return "keep"


def rehome_admininfo(msdesc, admininfo, tally):
    """Rebuild one adminInfo, rehoming classifiable notes. Returns nothing;
    mutates the tree (sets msDesc/@type, replaces adminInfo children, and
    prunes adminInfo/additional if left empty)."""
    msid = msdesc.get(XML_B + "id")

    availability = None          # at most one
    custodial_events = []        # list of custEvent elements
    kept_notes = []              # notes left in place (residue)

    for note in admininfo.findall(TEI_B + "note"):
        kind = classify(msid, note)

        if kind == "printed":
            msdesc.set("type", "printed")
            tally["printed -> @type"] += 1
            # Retain any remainder beyond the bare flag (e.g. BodDoufrD48
            # "?Copland, c. 1500"). Bare flags leave nothing -> deleted.
            leftover = PRINTED_PREFIX.sub("", note_text(note)).strip()
            if leftover or len(note):
                resid = etree.SubElement(admininfo, TEI_B + "note")
                resid.text = leftover or None
                for child in list(note):
                    resid.append(child)
                kept_notes.append(resid)
                tally["printed residual note kept"] += 1

        elif kind in ("deposit", "destroyed"):
            ev = etree.Element(TEI_B + "custEvent")
            ev.set("type", kind)
            if kind == "destroyed" and msid in DESTROYED_WHEN:
                ev.set("when", DESTROYED_WHEN[msid])
            move_content(note, ev)
            custodial_events.append(ev)
            tally["%s -> custEvent" % kind] += 1

        elif kind == "missing":
            if availability is None:
                availability = etree.Element(TEI_B + "availability")
                availability.set("status", "unknown")
            p = etree.SubElement(availability, TEI_B + "p")
            move_content(note, p)
            tally["missing -> availability"] += 1

        else:  # keep
            kept_notes.append(note)
            tally["note kept (residue)"] += 1

    # Reassemble children in schema order: availability, custodialHist, note*.
    for child in list(admininfo):
        admininfo.remove(child)

    if availability is not None:
        admininfo.append(availability)
    if custodial_events:
        hist = etree.SubElement(admininfo, TEI_B + "custodialHist")
        for ev in custodial_events:
            hist.append(ev)
    for note in kept_notes:
        admininfo.append(note)

    # Prune emptied containers.
    if len(admininfo) == 0:
        additional = admininfo.getparent()
        additional.remove(admininfo)
        tally["empty adminInfo dropped"] += 1
        if len(additional) == 0:
            additional.getparent().remove(additional)
            tally["empty additional dropped"] += 1


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

    tally = Counter()
    blocks = root.findall(".//%sadditional/%sadminInfo" % (TEI_B, TEI_B))
    log.info("adminInfo blocks found: %d", len(blocks))
    for admininfo in blocks:
        msdesc = admininfo.getparent().getparent()  # adminInfo < additional < msDesc
        rehome_admininfo(msdesc, admininfo, tally)

    etree.indent(tree, space="    ")
    out = SOURCE_FILE if args.in_place else PREVIEW_FILE
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tree.write(out, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    log.info("Tally: %s", dict(tally))
    log.info("Wrote %s%s", out,
             "" if args.in_place else "  (preview; re-run with --in-place to apply)")


if __name__ == "__main__":
    main()
