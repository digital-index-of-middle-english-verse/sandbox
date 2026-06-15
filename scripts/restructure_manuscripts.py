#!/usr/bin/env python3

"""Phase 1 of the Manuscripts.xml TEI restructure (see dimev issue #36).

Structural mapping ONLY. This script rebuilds the data file in the TEI
namespace, performing the safe, mechanical part of the conversion and
deferring all content disaggregation to later phases:

    list                  -> listBibl   (xmlns = TEI)
    item                  -> msDesc      (xml:id preserved verbatim)
    settlement, repos     -> msIdentifier/{settlement, repository}
    desc                  -> desc        (TRANSITIONAL, carried verbatim)
    lang                  -> lang        (TRANSITIONAL, carried verbatim)
    surrogates/ref        -> additional/surrogates/bibl/ref

What this script deliberately does NOT do:
    - disaggregate desc into idno/altIdentifier/msName/notes   (Phase 2)
    - add country / regularize settlement & repository names    (Phase 3)
    - touch the lang dialect-localization data                  (Phase 4)
    - rewrite legacy inline markup (<i>, <sup>) into TEI <hi>   (Phase 2)

Commented-out (legacy) blocks in the source are dropped: the output tree is
rebuilt from live <item> elements only, so XML comment nodes do not survive.

xml:id values are the join key referenced from Records.xml via <mss key="...">
and are copied through unchanged.

Output validates against the INTERIM schemas/manuscripts.xsd, not yet tei_all.

Usage:
    python3 restructure_manuscripts.py            # dry run -> ../artefacts/Manuscripts.phase1.xml
    python3 restructure_manuscripts.py --in-place # overwrite the real data file
"""

from lxml import etree
import argparse
import logging
import os

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SOURCE_FILE = "../../dimev/data/Manuscripts.xml"
PREVIEW_FILE = "../artefacts/Manuscripts.phase1.xml"
LOG_FILE = "../artefacts/restructure_manuscripts.log"

TEI = "http://www.tei-c.org/ns/1.0"
TEI_B = "{%s}" % TEI
XML_B = "{http://www.w3.org/XML/1998/namespace}"

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

def tei_copy(src, localname=None):
    """Deep-copy a legacy (no-namespace) element into the TEI namespace.

    Preserves mixed content (text and tails), attributes, and child order.
    Optionally renames the element via *localname*. Comment/PI nodes are
    skipped. Attributes are copied as-is, which keeps xml:id (and the
    unprefixed key/target/county/... attributes) intact.
    """
    name = localname or etree.QName(src.tag).localname
    new = etree.Element(TEI_B + name)
    for key, value in src.attrib.items():
        new.set(key, value)
    new.text = src.text
    for child in src:
        if not isinstance(child.tag, str):
            continue  # drop comments / processing instructions
        new_child = tei_copy(child)
        new_child.tail = child.tail
        new.append(new_child)
    return new


def build_msdesc(item, tally):
    """Map one legacy <item> to a TEI <msDesc>."""
    msdesc = etree.Element(TEI_B + "msDesc")

    xmlid = item.get(XML_B + "id")
    if not xmlid:
        log.error("SKIP: <item> without xml:id; cannot map (join key missing)")
        tally["skipped (no xml:id)"] += 1
        return None
    msdesc.set(XML_B + "id", xmlid)

    # --- msIdentifier: settlement, repository ------------------------------
    msid = etree.SubElement(msdesc, TEI_B + "msIdentifier")

    settlement = item.find("settlement")
    if settlement is None:
        log.warning("%s: no <settlement>; inserting an empty one", xmlid)
        etree.SubElement(msid, TEI_B + "settlement")
        tally["missing settlement"] += 1
    else:
        msid.append(tei_copy(settlement, "settlement"))
        if not (settlement.text or "").strip():
            tally["empty settlement"] += 1

    repos = item.find("repos")
    if repos is None:
        log.error("%s: no <repos>; inserting an empty <repository>", xmlid)
        etree.SubElement(msid, TEI_B + "repository")
        tally["missing repos"] += 1
    else:
        msid.append(tei_copy(repos, "repository"))

    # --- desc (TRANSITIONAL, verbatim) -------------------------------------
    desc = item.find("desc")
    if desc is None:
        log.error("%s: no <desc>; inserting an empty one", xmlid)
        etree.SubElement(msdesc, TEI_B + "desc")
        tally["missing desc"] += 1
    else:
        msdesc.append(tei_copy(desc, "desc"))

    # --- lang (TRANSITIONAL, verbatim) -------------------------------------
    lang = item.find("lang")
    if lang is not None:
        msdesc.append(tei_copy(lang, "lang"))
        tally["with lang"] += 1

    # --- surrogates -> additional/surrogates/bibl/ref ----------------------
    surrogates = item.find("surrogates")
    if surrogates is not None:
        additional = etree.SubElement(msdesc, TEI_B + "additional")
        new_surr = etree.SubElement(additional, TEI_B + "surrogates")
        for ref in surrogates.findall("ref"):
            bibl = etree.SubElement(new_surr, TEI_B + "bibl")
            new_ref = etree.SubElement(bibl, TEI_B + "ref")
            new_ref.set("target", ref.get("target"))
        tally["with surrogates"] += 1

    return msdesc


def restructure(root, tally):
    """Build a fresh TEI <listBibl> from the live <item> elements of <list>."""
    new_root = etree.Element(TEI_B + "listBibl", nsmap={None: TEI})
    pi = etree.ProcessingInstruction("xml-model", "href='../schemas/manuscripts.xsd'")
    new_root.addprevious(pi)

    for item in root.findall("item"):
        msdesc = build_msdesc(item, tally)
        if msdesc is not None:
            new_root.append(msdesc)
            tally["msDesc written"] += 1

    return etree.ElementTree(new_root)


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

    from collections import Counter
    tally = Counter()
    new_tree = restructure(root, tally)

    etree.indent(new_tree, space="    ")

    out = SOURCE_FILE if args.in_place else PREVIEW_FILE
    os.makedirs(os.path.dirname(out), exist_ok=True)
    new_tree.write(out, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    log.info("Tally: %s", dict(tally))
    log.info("Wrote %d msDesc to %s%s",
             tally["msDesc written"], out,
             "" if args.in_place else "  (preview; re-run with --in-place to apply)")


if __name__ == "__main__":
    main()
