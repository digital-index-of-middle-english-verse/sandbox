#!/usr/bin/env python3
from rdflib import Graph, Literal
from rdflib.namespace import DC, DCTERMS
import re
import sys
from pathlib import Path

NUMBER_LINE = re.compile(r'(?mi)^\s*Number:\s*(\d+(-\d+)?(,\s+\d+(-\d+)?)*)\s*$')   # capture lines like "Number: 10-11, 13, 200-2"

def extract_numbers_and_clean(text: str):
    """
    Returns (numbers:list[str], cleaned_text:str)
    - removes any full lines matching 'Number: N'
    - preserves other content & original line endings
    """
    numbers = []
    kept_lines = []
    for line in text.splitlines(keepends=True):
        m = NUMBER_LINE.match(line)
        if m:
            numbers.append(m.group(1))
            print(m.group(1))
        else:
            kept_lines.append(line)
    cleaned = "".join(kept_lines).strip()
    return numbers, cleaned

def main(infile: str, outfile: str, in_format: str = None, out_format: str = "xml"):
    g = Graph()
    g.parse(infile, format=in_format)  # let rdflib sniff format if None

    total_descs = 0
    total_numbers = 0
    books_touched = 0

    # Iterate over all dc:description triples
    # (We don't require a particular rdf:type; the example shows bib:Book, but pattern-based is safer.)
    for s, p, o in list(g.triples((None, DC.description, None))):
        if not isinstance(o, Literal):
            continue
        text = str(o)

        numbers, cleaned = extract_numbers_and_clean(text)
        if not numbers:
            continue  # nothing to do

        total_descs += 1
        total_numbers += len(numbers)

        # Update description: remove old literal, add cleaned (if non-empty)
        g.remove((s, p, o))
        if cleaned:
            g.add((s, p, Literal(cleaned, lang=o.language, datatype=o.datatype)))

        # Attach each number as dc:identifier to the Series node(s) in dcterms:isPartOf
        # If there are multiple isPartOf targets, annotate all of them (common for series/collections).
        series_nodes = list(g.objects(s, DCTERMS.isPartOf))
        if series_nodes:
            for n in numbers:
                for series in series_nodes:
                    g.add((series, DC.identifier, Literal(n)))
            books_touched += 1
        else:
            # If no isPartOf is present, we simply keep the description cleaned.
            # (Alternatively: create a new blank node for the series and link it—but that’s a modeling decision.)
            pass

    g.serialize(destination=outfile, format=out_format)
    print(f"Descriptions cleaned: {total_descs}")
    print(f"Numbers extracted:   {total_numbers}")
    print(f"Resources annotated (had isPartOf): {books_touched}")
    print(f"Wrote: {outfile} ({out_format})")

if __name__ == "__main__":
    # Usage:
    #   python move_number_to_series_identifier.py data/Bibliography.rdf out.rdf
    inpath = sys.argv[1] if len(sys.argv) > 1 else "../../dimev/data/Bibliography.rdf"
    outpath = sys.argv[2] if len(sys.argv) > 2 else str(Path(inpath).with_suffix(".out.rdf"))
    # You can force formats via env or by editing defaults above; otherwise rdflib guesses input; output defaults to RDF/XML.
    main(inpath, outpath)
