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
    title_count = 0

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

                        # replace title
                        title = monogr.find(TEI + "title")
                        marc_fields = ["130", "240"]
                        # MARC 130 is Main Entry Uniform Title; MARC 240 is Title: Uniform Title
                        for field in marc_fields:
                            if field in estc_record.keys():
                                estc_title = estc_record[field][0]["subfields"]["a"][0]
                                title.text = estc_title.strip(".")
                                title_count += 1
                                break
                    else:
                        matching_records = estc_data["matching_records"]
                        log.warning("Found %d matching records for item %s. Skipping.", matching_records, id_)
                else:
                    log.warning("No ESTC data found for item %s. Skipping.", id_)
            else:
                log.info("No STC number found for item %s. Skipping.", id_)
        else:
            log.info("No element `idno` found on item %s. Skipping.", id_)
    log.info("Found %d items. Added or updated %d ESTC numbers. Replaced %d titles.", count, idno_count, title_count)
    return root

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
