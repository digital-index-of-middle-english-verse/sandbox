This repository contains scripts and other tools for cleanup and transformation of data for the *Digital Index of Middle English Verse* (*DIMEV*).

# Repository contents

## artefacts

Warnings, reports, and other artefacts of the scripts in `scripts/`.
This directory also contains transitional files, to be used in cleaning and enrichment of certain data fields.

The file `subjects.csv` was created by `inspect-Records.py`, supplying a list of subject terms currently used by DIMEV.
The file `subject-categories.csv` was created by `update-subjects.py`, supplying a list of revised subject terms.
The output of the script is edited manually to assign subject-terms to categories.
The Python script `update-subjects.py` reads this file and keeps it up to date, adding and deleting subject terms as specified in `subjects.csv`.

## docs

Source files for an experimental website, built with Jekyll and hosted by GitHub Pages.
This experiment has been abandoned.

## schemas

JSON schemas for validation of transformed source files.

## scripts

Python scripts for review and transformation of the files in the `dimev` repository.
For details see comments at the head of each file.
Scripts presume that the `dimev` repository has been cloned to a directory sibling to this one.

# Technical direction

Plans for DIMEV are described in the [issues board](https://github.com/digital-index-of-middle-english-verse/dimev/issues)
