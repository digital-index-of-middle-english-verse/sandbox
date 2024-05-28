This repository is a sandbox in which to prototype tools for cleanup, transformation, and validation of data curated by editors of *DIMEV: An Open Access, Digital Edition of the "Index of Middle English Verse"*.
Researchers interested in Middle English verse should consult [dimev.net](https://www.dimev.net/), not this repository, as the XML source files in this repository are a snapshot and will not be updated.
They are for testing only.
Commentary is welcome.

The repository also hosts source files for an experimental new *DIMEV* website, built with Jekyll and hosted by GitHub Pages.
All this is very much work in progress.
An inspiration is Andrew Dunning's [prototype](https://github.com/medievallibraries/latin-writers) for a digital edition of Richard Sharpe, *A Handlist of Latin Writers of Great Britain and Ireland Before 1540*.

# Assets
- `artefacts/`
  Warnings, reports, and csv artefacts of the scripts in `scripts/`.
  Transformed source data are written instead to `docs/` for use by the Jekyll website builder.
- `DIMEV_XML/`
  DIMEV source files as of May 2023.
- `docs/`
  Source files and templates for a website.
  The contents of `docs/_items/` are written by `scripts/transform-Records.py`.
- `schemas/`
  JSON schemas for validation of transformed source files.
- `scripts/`
  Python scripts for review and transformation of the files in `DIMEV_XML`.
  For details see comments at the head of each file.
