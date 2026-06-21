#!/usr/bin/env python3

"""Rationalize DIMEV pointing markup toward TEI P5 Ch. 17 (dimev #65).

Background. DIMEV's referencing markup had grown ambiguous: `ref` was used for
several distinct pointing roles, with `@target` values following inconsistent
conventions (bare internal ids vs. absolute URIs). The most recent step (dimev
386c5c6 / sandbox 3e6ebcf) moved Middle English Compendium citations from
`bibl key="MECompendium"` to `ref target="https://...MED.../BIBxxx"`, leaving
internal record cross-references and external MED links sharing one element.

This script completes the "targeted cleanup" of #65. Every live `ref` is an
empty pointer (the only text-bearing `ref`s are dead, inside XML comments), and
TEI reserves `ptr` for empty pointers, so `ref` is retired in favour of `ptr`:

  Records.xml (no namespace)
    * freeMix cross-references   <ref target="record-4886"/>  -> <ptr target="#record-4886"/>
                                 <ref target="wit-13-1"/>     -> <ptr target="#wit-13-1"/>
    * repertory MED links        <ref target="https://...BIBxxx"/> -> <ptr .../> (target unchanged)

  Manuscripts.xml (TEI namespace)
    * catalogue/surrogate wrapper <bibl><ref target="https://..."/></bibl>
                                  -> <bibl><ptr target="https://..."/></bibl>  (outer bibl kept)

The internal/external split becomes syntactic: internal targets are "#"+xml:id
(record or witness), external targets are absolute URIs. validator.py resolves
the two by the leading "#", so its quod.lib.umich.edu special-case is dropped.

Targets are only changed for internal references (a leading "#" is added);
absolute URIs are left exactly as they are. The 11 dead `xml:target` references
inside `<!-- comment -->` blocks in Records.xml are not elements and are left
untouched (inert).

Usage:
    python3 rationalize_pointers.py           # dry run -> print summary
    python3 rationalize_pointers.py --write    # rewrite the data files
"""

import argparse
import sys
from pathlib import Path

from lxml import etree

TEI = "http://www.tei-c.org/ns/1.0"

DIMEV_RECORDS = Path("../../dimev/data/Records.xml")
DIMEV_MSS = Path("../../dimev/data/Manuscripts.xml")


def is_external(target):
    """An absolute URI (external resource) rather than an internal id reference."""
    return "://" in target


def retarget(target):
    """Internal id -> "#"+id; absolute URI left unchanged; already-"#" left as is."""
    if target.startswith("#") or is_external(target):
        return target
    return "#" + target


def rename_refs(root, ref_tag, ptr_tag):
    """Rename every `ref` element to `ptr`, fixing internal targets.

    Returns (internal, external) lists of (old_target, new_target) for reporting.
    """
    internal, external = [], []
    for el in root.iter(ref_tag):
        old = el.get("target")
        if old is None:
            continue
        new = retarget(old)
        el.tag = ptr_tag
        el.set("target", new)
        el.text = None  # ptr is empty; live refs already are
        (external if is_external(old) else internal).append((old, new))
    return internal, external


def write(tree, path):
    etree.indent(tree, space="    ", level=0)
    tree.write(str(path), pretty_print=True, xml_declaration=True, encoding="UTF-8")
    print(f"Wrote {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help="rewrite the data files (default: dry run)")
    args = ap.parse_args()

    # Records.xml -- unqualified element names.
    rec_tree = etree.parse(str(DIMEV_RECORDS))
    rec_internal, rec_external = rename_refs(rec_tree.getroot(), "ref", "ptr")

    # Manuscripts.xml -- TEI namespace; all `ref`s are catalogue/surrogate
    # wrappers carrying absolute URIs.
    mss_tree = etree.parse(str(DIMEV_MSS))
    mss_internal, mss_external = rename_refs(
        mss_tree.getroot(), f"{{{TEI}}}ref", f"{{{TEI}}}ptr")

    print("## Records.xml")
    print(f"  internal ref -> ptr (# added): {len(rec_internal)}")
    print(f"  external ref -> ptr (URI kept): {len(rec_external)}")
    for old, new in rec_internal[:3]:
        print(f"    {old}  ->  {new}")
    print("## Manuscripts.xml")
    print(f"  internal ref -> ptr (# added): {len(mss_internal)}")
    print(f"  external ref -> ptr (URI kept): {len(mss_external)}")

    if mss_internal:
        print("WARNING: unexpected internal ref target(s) in Manuscripts.xml:")
        for old, new in mss_internal:
            print(f"    {old}  ->  {new}")

    total = sum(map(len, (rec_internal, rec_external, mss_internal, mss_external)))
    print(f"\n{total} ref element(s) renamed to ptr.")

    if args.write:
        write(rec_tree, DIMEV_RECORDS)
        write(mss_tree, DIMEV_MSS)
    else:
        print("Dry run; pass --write to apply.")


if __name__ == "__main__":
    main()
