"""
teloscopy.data — Data management modules for Teloscopy.

This subpackage provides tools for acquiring, cataloging, and managing
public benchmark and reference datasets used throughout the Teloscopy
pipeline.  Key capabilities include:

* **Dataset catalog** — a curated registry of real, publicly available
  datasets (microscopy images, telomere-length population references,
  variant databases) with DOIs, citations, and licensing metadata.
* **Automated downloading** — stream-based fetchers with progress
  reporting, checksum verification, and archive extraction.
* **Format-specific parsers** — lightweight readers for SAS XPORT
  (.XPT), gzipped TSV, TIFF + CSV annotation bundles, and other
  formats encountered in the catalogued resources.
* **Citation management** — helpers that collect and format the
  bibliographic references for every dataset a user has downloaded,
  simplifying reproducibility reporting.

Modules
-------
datasets
    Dataset catalog definitions, the ``DatasetManager`` class, and all
    download / parsing utilities.
"""
