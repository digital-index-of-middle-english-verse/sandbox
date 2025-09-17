This repository is a sandbox in which to prototype tools for cleanup, transformation, and validation of data curated by editors of the *Digital Index of Middle English Verse* (*DIMEV*).
Files are for testing only: researchers interested in Middle English verse should consult [dimev.net](https://www.dimev.net/).
Commentary is welcome.

The repository also hosts source files for an experimental new *DIMEV* website, built with Jekyll and hosted by GitHub Pages.
All this is very much work in progress.
An inspiration is Andrew Dunning's [prototype](https://github.com/medievallibraries/latin-writers) for a digital edition of Richard Sharpe, *A Handlist of Latin Writers of Great Britain and Ireland Before 1540*.

# Repository contents

Directories are as follows.

## artefacts

Warnings, reports, and csv artefacts of the scripts in `scripts/`.
This directory also contains transitional files, to be used in cleaning and enrichment of certain data fields.

The file `bibliography.json` is created by `transform-Bibl.py`.
The file `bibliography.bib` was created from `bibliography.json` by pandoc.
For comment see this [Zotero forum post](https://forums.zotero.org/discussion/126264/csl-citation-key-zotero-citationkey).

The file `subjects.csv` was created by `inspect-Records.py`, supplying a list of subject terms currently used by DIMEV.
The output of the script is then edited manually to create a cross-walk from current subject terms to revised ones (WIP).

The file `subject-categories.csv` was created by `update-subjects.py`, supplying a list of revised subject terms.
The output of the script is edited manually to assign subject-terms to categories.
The Python script `update-subjects.py` reads this file and keeps it up to date, adding and deleting subject terms as specified in `subjects.csv`.

## docs

Source files and templates for a website.
The contents of `docs/_items/` are written by `scripts/transform-Records.py`.

## schemas

JSON schemas for validation of transformed source files.

## scripts

Python scripts for review and transformation of the files in the `dimev` repository.
For details see comments at the head of each file.
Scripts presume that the `dimev` repository has been cloned to a directory sibling to this one.

# Technical direction

The following is a summary of plans for DIMEV data.
A fuller treatment is provided in the [Technical Introduction](https://github.com/digital-index-of-middle-english-verse/dimev/releases/latest/download/documentation.pdf).

- `Records.xml` will be atomized (one file per `<record>`) to make effective use of `git` distributed version control.
  Data will be parsed to identify irregularities, remediated (manually where necessary), and written to a new consistent structure.
  For instance, any field that may be an array must be an array (even if an array of one).
  After migration, subsequent updates to any file must validate against a schema.
  Early prototypes of data files are in `docs_items`.
  An early prototype of the schema is `schemas/records.json`.
  Cross references (i.e., those `<record>` items without an `@xml:id`) will be handled differently, tbd.
- `Manuscripts.xml` and `MSSIndex.xml` will be de-duplicated.
  Data will be atomized (one file per `<item>`), parsed, remediated, and written to a new consistent structure.
  For an early partial prototype, see the output of `scripts/transform-Manuscripts.py`.
  `Inscriptions.xml` and `PrintedBooks.xml` will be handled similarly.
  After migration, subsequent updates to any file must validate against a schema.
- `Bibliography.xml`.
  Data will be parsed and remediated (as above), written to a standard bibliographic data format and imported to Zotero for distribution and curation on that platform.
  For a prototype of this conversion, see `artefacts/bibliography.yaml`; the schema is `schemas/csl-data.json`.
  To import tags we must target a format other than CSL JSON, per [this discussion](https://forums.zotero.org/discussion/115214/importing-tags-from-bibliographic-data-formats).
  Tags will be used to link bibliographic items to their objects, as in the Bodleian Library's [bibliographical references for Western manuscripts](https://www.zotero.org/bodleianwmss/library).
  Links to on-line facsimiles of manuscripts will be handled differently, probably as a field within the data structure for manuscripts.
- `Glossary.xml` tbd.
