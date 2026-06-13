#!/usr/bin/env python3

from lxml import etree
import os
import re
import logging
import json

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

SOURCE_FILE = '../../dimev/data/PrintedBooks.xml'
NAMESPACE = '{http://www.w3.org/XML/1998/namespace}'
TEI = '{http://www.tei-c.org/ns/1.0}'
LOG_FILE = "../artefacts/update_printed_books.log"

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

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

def restructure_as_tei_biblstruct(root):
    print('Building a new tree...\n')
    new_root = etree.Element("listBibl")
    pi = etree.ProcessingInstruction("xml-model", "href='../schemas/printedbooks.xsd'")
    new_root.addprevious(pi)

    for current_item in root.findall("bibl"):

        # Create new parent elements
        new_item = etree.Element("biblStruct")
        level = etree.Element("monogr")

        # Apply xml:id
        id_ = current_item.get(NAMESPACE + "id")
        new_item.set(NAMESPACE + "id", id_)

        # Convert author data
        authorstmt = current_item.find("authorstmt")
        authors = authorstmt.findall("author")
        for author in authors:
            level.append(author)

        # Convert title data
        titlestmt = current_item.find("titlestmt")
        title = titlestmt.find("title")
        level.append(title)

        # Convert imprint data
        pubstmt = current_item.find("pubstmt")
        date_str = pubstmt.get("date")

        imprint = etree.Element("imprint")
        publisher = etree.Element("publisher")
        publisher.text = pubstmt.text
        imprint.append(publisher)

        date_el = etree.Element("date")
        date_el.text = date_str
        imprint.append(date_el)

        level.append(imprint)

        # Convert STC number
        stc_ref = current_item.get("n")
        pattern = r"STC (\d+([a-z])?(\.\d+)?)"
        match = re.fullmatch(pattern, stc_ref)
        if match:
            repertory = etree.Element("idno")
            repertory.set("type", "STC (2nd ed.)")
            repertory.text = match.group(1)
            level.append(repertory)
        else:
            log.info("No STC number found on item %s.", id_)

        # Package
        new_item.append(level)
        new_root.append(new_item)
        new_tree = etree.ElementTree(new_root)

    return new_tree

def overwrite_from_estc(root):
    print("Overwriting with ESTC data...\n")

    estc_download_dir = "../../estc/estc_output/"
    estc_file_list = [f for f in os.listdir(estc_download_dir) if os.path.isfile(os.path.join(estc_download_dir, f))]
    count = 0
    idno_count = 0
    date_count = 0

    for item in root.findall(TEI + "biblStruct"):
        id_ = item.get(NAMESPACE + "id")
        monogr = item.find(TEI + "monogr")
        refs = monogr.findall(TEI + "idno")
        count += 1
        if refs is not None:
            stc_number = get_idno(refs, "STC")
            if stc_number != "":
                filename_target = "STC_" + re.sub(r"\.", "_", stc_number) + ".json"
                if filename_target in estc_file_list:
                    path = os.path.join(estc_download_dir, filename_target)
                    with open(path) as f:
                        estc_data = json.load(f)
                    if estc_data["matching_records"] == 1:
                        estc_record = estc_data["records"][0]

                        # add ESTC number after the STC number (idno precedes
                        # imprint, per the TEI content model for monogr)
                        estc_el = None
                        for ref in refs:
                            if ref.get("type") == "ESTC":
                                estc_el = ref
                                break
                        if estc_el is None:
                            stc_el = monogr.find(TEI + "idno[@type='STC']")
                            estc_el = etree.Element(TEI + "idno")
                            estc_el.set("type", "ESTC")
                            stc_el.addnext(estc_el)
                        estc_el.text = estc_record["001"][0]
                        idno_count += 1

                        # NOTE: titles were replaced from MARC 130/240 in a
                        # previous run (see git history) and then manually
                        # curated; do not touch them again

                        # NOTE: publishers were replaced with names extracted
                        # from MARC 260 $b in a previous run (see git history)
                        # and then manually curated; do not touch them again

                        # replace date with the year(s) from MARC 008
                        # (positions 06-14), with uncertainty markers taken
                        # from the transcribed date statement (MARC 260 $c)
                        text, attrs, confident = extract_date(estc_record)
                        date_el = monogr.find(TEI + "imprint/" + TEI + "date")
                        old_text = date_el.text
                        for att in ("when", "notBefore", "notAfter", "cert"):
                            if att in date_el.attrib:
                                del date_el.attrib[att]
                        date_el.text = text
                        for att, value in attrs.items():
                            date_el.set(att, value)
                        date_count += 1
                        if not confident:
                            log.warning("Low-confidence date extraction for item %s: %r", id_, text)
                        elif old_text not in text:
                            log.info("Date changed for item %s: %r -> %r", id_, old_text, text)
                    else:
                        matching_records = estc_data["matching_records"]
                        log.warning("Found %d matching records for item %s. Skipping.", matching_records, id_)
                else:
                    log.warning("No ESTC data found for item %s. Skipping.", id_)
            else:
                log.info("No STC number found for item %s. Skipping.", id_)
        else:
            log.info("No element `idno` found on item %s. Skipping.", id_)
    log.info("Found %d items. Added or updated %d ESTC numbers. Replaced %d dates.", count, idno_count, date_count)
    return root

ADDRESS_WORDS = (
    r"(dwell\w*|strete|streate|street|sygne|signe|chirche|chyrche|churche|church"
    r"|yerde|yarde|yard|lane|gate|brigge|bridge|hous|house|shoppe|shop|buith"
    r"|market|abbay|abbey|cathedral|town|towne|cite|citie|city)"
)

def extract_publisher_name(statement):
    """Extract the publisher name(s) from a transcribed imprint statement
    (MARC 260 $b). Returns (text, confident). When extraction is not
    confident, text is the full statement, lightly normalized."""

    # Square brackets mark text supplied by the cataloguer; DIMEV does not
    # claim to give imprint statements as printed, so drop them everywhere
    s = re.sub(r"[\[\]]", "", statement)
    s = re.sub(r"\s+", " ", s).strip().strip(",.;: ")
    original = s

    # Drop a leading printing verb ("Enprynted", "Newlie Imprintit", ...)
    s = re.sub(
        r"^(newlie |newlye |fyrst )?(printed|prynted|imprinted|imprynted"
        r"|inprinted|inprynted|enprynted|enprinted|emprented|enprented"
        r"|emprynted|prentyd|imprintit|impressit)\b[,:;]?\s*",
        "", s, flags=re.I)

    # Drop a leading location clause through the first agent marker
    # ("In Fletestrete at the synge of the Sonne, by me ..."), else a bare
    # leading agent marker ("By ...", "Be ...", "per ...")
    m = re.search(r"^(at|in|on|vpon|within)\b.*?\b(by|be)\b\s+", s, flags=re.I)
    if m:
        s = s[m.end():]
    else:
        s = re.sub(r"^(by|be|per)\b\s+", "", s, flags=re.I)
    s = re.sub(r"^(me|my)\s+", "", s, flags=re.I)

    # An agent marker stranded mid-string by bracket removal
    # ("[I. Charlewood for] By Rycharde Ihones" -> "for By")
    s = re.sub(r"\b(for)\s+(by|be)\b\s*", r"\1 ", s, flags=re.I)

    # Cut trailing matter: retail clauses, offices, addresses. Locational
    # prepositions survive when they introduce an expense clause, which
    # names a second party ("at the expensis of Henrie Charteris")
    s = re.split(r"\s*[,:;]?\s*\band ar?e? to be (sa|so)u?lde?\b", s, flags=re.I)[0]
    s = re.split(r"\s*[,:;.]?\s*\b(prynter|printer|prentar|boke ?seller|bookseller|stationer)\b", s, flags=re.I)[0]
    s = re.split(r"\s*[,:;]?\s*\bdwell\w*\b", s, flags=re.I)[0]
    s = re.split(
        r"\s*[,:;.]?\s*\b(?:at|in|on|ouer|over|vpon|next|besyde|beside|by ?syde)\b"
        r"(?!\s+(?:the|ye|his|her)?\s*expen)",
        s, flags=re.I)[0]
    s = s.strip().strip(",.;: ")

    confident = bool(s) and len(s) <= 60 and not re.search(ADDRESS_WORDS, s, flags=re.I)
    if confident:
        return s, True
    return original, False

def extract_date(estc_record):
    """Build a TEI date from MARC 008 (machine-readable years) and 260 $c
    (uncertainty markers). Returns (text, attrs, confident); attrs holds
    att.datable.w3c attributes (@when or @notBefore/@notAfter) plus @cert.
    When extraction is not confident, text is the 260 $c statement, lightly
    normalized, with no attributes."""

    f008 = estc_record.get("008", [""])[0]
    date_type = f008[6:7]
    date1 = f008[7:11]
    date2 = f008[11:15].strip()

    statement = ""
    if "260" in estc_record:
        c_values = estc_record["260"][0]["subfields"].get("c")
        if c_values:
            statement = c_values[0]
    fallback = re.sub(r"[\[\]]", "", statement)
    fallback = re.sub(r"\s+", " ", fallback).strip().strip(",.;: ")

    # "ca." must precede a digit, lest "[et]⁻c.lxxxxvi" read as circa
    circa = bool(re.search(r"\bca?\.\s*\d|\bcirca\b|\bapproximately\b", statement, flags=re.I))
    uncertain = circa or "?" in statement

    if not re.fullmatch(r"\d{4}", date1):
        return fallback, {}, False

    # termini from the date statement ("after 2 July 1482", "not after
    # 1509"); MARC 008 records these as plain single dates. Anchored at the
    # start: "1481 (after 8 March)" is a single date, not a terminus
    if re.match(r"not after\b", fallback, flags=re.I):
        return "not after " + date1, {"notAfter": date1}, True
    if re.match(r"after\b", fallback, flags=re.I):
        return "after " + date1, {"notBefore": date1}, True

    # date type "e" gives a day-level date: Date2 is MMDD, not a year
    if date_type == "e":
        date2 = ""

    if date2 and not re.fullmatch(r"\d{4}", date2):
        return fallback, {}, False

    if date2 and date2 != date1:
        attrs = {"notBefore": date1, "notAfter": date2}
        if re.search(r"\bor\b", statement, flags=re.I):
            text = date1 + " or " + date2
        elif uncertain:
            text = date1 + "–" + date2 + "?"
            attrs["cert"] = "medium"
        else:
            text = date1 + "–" + date2
        return text, attrs, True

    attrs = {"when": date1}
    if circa:
        text = "ca. " + date1
        attrs["cert"] = "medium"
    elif uncertain:
        text = date1 + "?"
        attrs["cert"] = "medium"
    else:
        text = date1
    return text, attrs, True

def get_idno(refs, target_att_type):
    ref_number = ""
    for ref in refs:
        if ref.get("type") == target_att_type:
            ref_number = ref.text
            break
    return ref_number

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    tree = etree.parse(SOURCE_FILE)
    root = tree.getroot()

    # tree = restructure_as_tei_biblstruct(root)
    overwrite_from_estc(root)

    print('All transformations complete')
    etree.indent(tree, space="    ", level=0)
    tree.write(SOURCE_FILE, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print(f'Wrote the revised tree to {SOURCE_FILE}')

if __name__ == "__main__":
    main()
