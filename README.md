This repository is a sandbox in which to prototype tools for cleanup, transformation, and validation of data curated by editors of the *Digital Index of Middle English Verse* (*DIMEV*).
Files are for testing only: researchers interested in Middle English verse should consult [dimev.net](https://www.dimev.net/).
Commentary is welcome.

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

Source files for an experimental website, built with Jekyll and hosted by GitHub Pages.
An inspiration is Andrew Dunning's [prototype](https://github.com/medievallibraries/latin-writers) for a digital edition of Richard Sharpe, *A Handlist of Latin Writers of Great Britain and Ireland Before 1540*.
The contents of `docs/_items/` are written by `scripts/transform-Records.py`.
This experiment has been abandoned.

## schemas

JSON schemas for validation of transformed source files.

## scripts

Python scripts for review and transformation of the files in the `dimev` repository.
For details see comments at the head of each file.
Scripts presume that the `dimev` repository has been cloned to a directory sibling to this one.

# Technical direction

Plans for DIMEV are described in the [issues board](https://github.com/digital-index-of-middle-english-verse/dimev/issues)
and [Technical Introduction](https://github.com/digital-index-of-middle-english-verse/dimev/releases/latest/download/documentation.pdf).
The issues board is the most current.
