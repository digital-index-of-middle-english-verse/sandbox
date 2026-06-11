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

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    tree = etree.parse(SOURCE_FILE)
    root = tree.getroot()

    tree = restructure_as_tei_biblstruct(root)

    print('All transformations complete')
    etree.indent(tree, space="    ", level=0)
    tree.write(SOURCE_FILE, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print(f'Wrote the revised tree to {SOURCE_FILE}')

if __name__ == "__main__":
    main()
