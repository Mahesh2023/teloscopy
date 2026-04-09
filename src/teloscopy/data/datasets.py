"""
teloscopy.data.datasets — Dataset catalog and downloader for Teloscopy.

Curated catalog of **real, publicly available** datasets for benchmarking,
training, and validation.  Every entry carries a working URL, DOI (where
applicable), citation, and licensing metadata.

Catalogued datasets: Spotiflow FISH Benchmark, Annotated Fluorescence
Nuclear Segmentation, NHANES 1999-2002 Telomere Length, ClinVar Variant
Summary, GigaScience FM Training, IDR Telomere FISH Study, BBBC039.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import logging
import os
import struct
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DatasetInfo dataclass
# ---------------------------------------------------------------------------


@dataclass
class DatasetInfo:
    """Descriptor for a single catalogued dataset.

    Attributes
    ----------
    name : str          — unique catalog key (e.g. ``"spotiflow_fish"``).
    url : str           — primary download URL.
    doi : str           — DOI, or ``""`` when not applicable.
    description : str   — human-readable summary.
    license : str       — SPDX identifier (e.g. ``"CC-BY-4.0"``).
    size_mb : int       — approximate download size in MB.
    format_desc : str   — file format after extraction.
    citation : str      — full bibliographic citation.
    use_case : str      — primary pipeline use.
    extra_urls : list   — additional URLs for multi-file datasets.
    note : str          — access restrictions / API notes.
    downloaded : bool   — whether locally cached.
    local_path : str    — absolute disk path, or ``""``.
    """

    name: str
    url: str
    doi: str = ""
    description: str = ""
    license: str = ""
    size_mb: int = 0
    format_desc: str = ""
    citation: str = ""
    use_case: str = ""
    extra_urls: list[str] = field(default_factory=list)
    note: str = ""
    downloaded: bool = False
    local_path: str = ""


# ---------------------------------------------------------------------------
# DATASET_CATALOG
# ---------------------------------------------------------------------------

DATASET_CATALOG: dict[str, DatasetInfo] = {
    # (a) Spotiflow FISH Benchmark ------------------------------------------
    "spotiflow_fish": DatasetInfo(
        name="spotiflow_fish",
        url="https://zenodo.org/records/14514463/files/spotiflow_datasets.zip?download=1",
        doi="10.5281/zenodo.14514463",
        description=(
            "8 annotated FISH spot detection datasets (synthetic, FISH, "
            "live-cell) from Spotiflow paper (Dominguez Mantes et al. 2025, "
            "Nature Methods). 697 MB. BSD-3-Clause."
        ),
        license="BSD-3-Clause",
        size_mb=697,
        format_desc="zip containing TIFF images + CSV spot annotations",
        citation=(
            "Dominguez Mantes, A. et al. Spotiflow: accurate and efficient "
            "spot detection for fluorescence microscopy. Nature Methods "
            "(2025). DOI: 10.1038/s41592-025-02662-x"
        ),
        use_case="spot_detection_training",
    ),
    # (b) Annotated Fluorescence Nuclear Segmentation -----------------------
    "fluorescence_nuclear_seg": DatasetInfo(
        name="fluorescence_nuclear_seg",
        url="https://zenodo.org/records/3713518/files/dataset.zip?download=1",
        doi="10.5281/zenodo.3713518",
        description=(
            "Annotated fluorescence microscopy images for training nuclear "
            "segmentation methods. Includes DAPI/Hoechst stained nuclei with "
            "ground truth masks. From Kromp et al. 2020, Scientific Data."
        ),
        license="CC-BY-4.0",
        size_mb=480,
        format_desc="TIFF images + PNG masks",
        citation=(
            "Kromp, F. et al. An annotated fluorescence image dataset for "
            "training nuclear segmentation methods. Scientific Data 7, 262 "
            "(2020). DOI: 10.1038/s41597-020-00608-w"
        ),
        use_case="nuclear_segmentation",
    ),
    # (c) NHANES 1999-2002 Telomere Length ----------------------------------
    "nhanes_telomere": DatasetInfo(
        name="nhanes_telomere",
        url="https://wwwn.cdc.gov/Nchs/Nhanes/1999-2000/TELO_A.XPT",
        description=(
            "Leukocyte telomere length measurements (T/S ratio) from 7,839 "
            "US adults aged 20+. NHANES 1999-2002. Conversion formula: "
            "TL(kb) = (3274 + 2413 * T/S) / 1000. Public domain."
        ),
        license="Public Domain (US Government)",
        size_mb=2,
        format_desc="SAS XPORT (.XPT) files",
        citation="National Health and Nutrition Examination Survey, 1999-2002. CDC/NCHS.",
        use_case="telomere_population_reference",
        extra_urls=["https://wwwn.cdc.gov/Nchs/Nhanes/2001-2002/TELO_B.XPT"],
    ),
    # (d) ClinVar Variant Summary -------------------------------------------
    "clinvar_variants": DatasetInfo(
        name="clinvar_variants",
        url="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz",
        description=(
            "Complete ClinVar variant classifications. Contains "
            "pathogenic/benign/VUS annotations for all clinically reported "
            "genetic variants. Updated monthly."
        ),
        license="Public Domain (US Government)",
        size_mb=120,
        format_desc="gzipped TSV",
        citation=(
            "Landrum, M.J. et al. ClinVar: public archive of "
            "interpretations of clinically relevant variants. Nucleic Acids "
            "Research 44, D862-D868 (2016). DOI: 10.1093/nar/gkv1222"
        ),
        use_case="variant_validation",
    ),
    # (e) GigaScience Fluorescence Microscopy Training ----------------------
    "gigascience_fm": DatasetInfo(
        name="gigascience_fm",
        url="https://zenodo.org/records/4744853/files/FMDataset.zip?download=1",
        doi="10.5281/zenodo.4744853",
        description=(
            "Fluorescence microscopy datasets for training deep neural "
            "networks. Multiple imaging modalities. From Speiser et al. "
            "2021, GigaScience."
        ),
        license="CC0-1.0",
        size_mb=2400,
        format_desc="TIFF images",
        citation=(
            "Speiser, A. et al. Fluorescence microscopy datasets for "
            "training deep neural networks. GigaScience 10(5), giab032 "
            "(2021). DOI: 10.1093/gigascience/giab032"
        ),
        use_case="microscopy_denoising",
    ),
    # (f) IDR Telomere FISH Study -------------------------------------------
    "idr_telomere_fish": DatasetInfo(
        name="idr_telomere_fish",
        url="https://idr.openmicroscopy.org/webclient/?show=project-301",
        description=(
            "3D telomere FISH images from hTERT-immortalized fibroblasts. "
            "Includes wide-field microscopy z-stacks. From Adam et al. "
            "2019, Communications Biology."
        ),
        license="CC-BY-4.0",
        size_mb=5000,
        format_desc="OME-TIFF via OMERO API",
        citation=(
            "Adam, N. et al. Telomere analysis using 3D fluorescence "
            "microscopy suggests mammalian telomere clustering in "
            "hTERT-immortalized Hs68 fibroblasts. Communications Biology "
            "2, 451 (2019). DOI: 10.1038/s42003-019-0692-3"
        ),
        use_case="telomere_3d_analysis",
        note="Access via OMERO API; not direct download",
    ),
    # (g) Broad Bioimage Benchmark Collection BBBC039 -----------------------
    "bbbc039": DatasetInfo(
        name="bbbc039",
        url="https://bbbc.broadinstitute.org/BBBC039",
        description=(
            "BBBC039 — fluorescence microscopy images of U2OS cells with "
            "ground truth nuclei outlines. 200 images at 520x696 pixels."
        ),
        license="CC0-1.0",
        size_mb=400,
        format_desc="PNG images + ground truth masks",
        citation=(
            "Caicedo, J.C. et al. Nucleus segmentation across imaging "
            "experiments: the 2018 Data Science Bowl. Nature Methods 16, "
            "1247-1253 (2019). DOI: 10.1038/s41592-019-0612-7"
        ),
        use_case="nuclear_segmentation_benchmark",
    ),
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _download_file(url: str, dest: str, chunk_size: int = 8192) -> str:
    """Download *url* to *dest* with progress logging.

    Returns the absolute path *dest* on success.  Creates parent dirs as
    needed.  Raises ``urllib.error.URLError`` on network failures.
    """
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s -> %s", url, dest)

    req = urllib.request.Request(url, headers={"User-Agent": "Teloscopy/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = resp.headers.get("Content-Length")
        total_bytes = int(total) if total else None
        downloaded = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                fh.write(chunk)
                downloaded += len(chunk)
                if total_bytes and downloaded % (chunk_size * 128) < chunk_size:
                    logger.info("  %.1f%%", downloaded / total_bytes * 100)

    logger.info("Download complete: %s (%d bytes)", dest, downloaded)
    return dest


def _extract_zip(zip_path: str, dest_dir: str) -> str:
    """Extract ZIP archive to *dest_dir*, then delete the archive.

    Validates paths to prevent zip-slip attacks.
    """
    logger.info("Extracting %s -> %s", zip_path, dest_dir)
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    dest_resolved = str(Path(dest_dir).resolve())
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if not str(Path(dest_dir, member).resolve()).startswith(dest_resolved):
                raise ValueError(f"Zip member {member!r} escapes {dest_dir!r}")
        zf.extractall(dest_dir)
    os.remove(zip_path)
    logger.info("Extraction complete; removed %s", zip_path)
    return dest_dir


def _parse_xpt(path: str) -> list[dict[str, Any]]:
    """Parse a SAS XPORT v5 (.XPT) file into a list of dicts.

    Implements the TS-140 spec: reads NAMESTR variable descriptors and
    observation records, converting IBM System/360 floats to IEEE 754.
    Only the first member is read.  Missing values become ``None``.
    """

    def _ibm_to_ieee(ibm: bytes) -> float | None:
        """Convert 8-byte IBM hex float to Python float (or None for missing)."""
        if ibm == b"\x00" * 8:
            return 0.0
        first = ibm[0]
        # SAS missing sentinels: 0x2E (dot) or 0x41-0x5A with zero mantissa
        if first == 0x2E or (0x41 <= first <= 0x5A and ibm[1:] == b"\x00" * 7):
            return None
        raw = struct.unpack(">Q", ibm)[0]
        sign = (raw >> 63) & 1
        exp = ((raw >> 56) & 0x7F) - 64  # excess-64, base-16
        mant = raw & 0x00FFFFFFFFFFFFFF
        if mant == 0:
            return 0.0
        # Normalise so top bit of 56-bit mantissa is 1
        shift = 0
        tmp = mant
        while tmp and not (tmp & (1 << 55)):
            tmp <<= 1
            shift += 1
        mant <<= shift
        ieee_exp = 4 * exp - shift - 1 + 1023  # base-16 -> base-2
        if ieee_exp <= 0:
            return 0.0
        if ieee_exp >= 2047:
            return float("-inf") if sign else float("inf")
        ieee_mant = (mant & ((1 << 55) - 1)) >> 3  # drop implicit 1, keep 52 bits
        return struct.unpack(">d", struct.pack(">Q", (sign << 63) | (ieee_exp << 52) | ieee_mant))[
            0
        ]

    with open(path, "rb") as fh:
        data = fh.read()

    # Locate NAMESTR header
    ns_pos = data.find(b"HEADER RECORD*******NAMESTR")
    if ns_pos < 0:
        raise ValueError(f"No NAMESTR header in {path}")
    ns_header = data[ns_pos : ns_pos + 80]

    # Determine variable count
    obs_marker = b"HEADER RECORD*******OBS"
    obs_pos = data.find(obs_marker)
    if obs_pos < 0:
        raise ValueError(f"No OBS header in {path}")

    nvar_str = ns_header[54:58].strip()
    ns_data_start = ns_pos + 160
    try:
        nvar = int(nvar_str)
    except ValueError:
        nvar = (obs_pos - ns_data_start) // 140
        if nvar < 1:
            raise ValueError("Cannot determine variable count")

    # Read 140-byte NAMESTR entries
    variables: list[dict[str, Any]] = []
    for i in range(nvar):
        entry = data[ns_data_start + i * 140 : ns_data_start + (i + 1) * 140]
        if len(entry) < 140:
            break
        ntype = struct.unpack(">H", entry[0:2])[0]
        nlng = struct.unpack(">H", entry[4:6])[0]
        nname = entry[8:16].split(b"\x00")[0].strip().decode("ascii", errors="replace")
        variables.append(
            {
                "name": nname,
                "type": "numeric" if ntype == 1 else "character",
                "length": nlng,
            }
        )

    obs_len = sum(v["length"] for v in variables)
    remaining = data[obs_pos + 80 :]
    records: list[dict[str, Any]] = []
    offset = 0

    while offset + obs_len <= len(remaining):
        rec_data = remaining[offset : offset + obs_len]
        offset += obs_len
        row: dict[str, Any] = {}
        fld = 0
        for var in variables:
            raw = rec_data[fld : fld + var["length"]]
            fld += var["length"]
            if var["type"] == "numeric":
                row[var["name"]] = _ibm_to_ieee(raw[:8] if len(raw) >= 8 else raw.ljust(8, b"\x00"))
            else:
                row[var["name"]] = raw.decode("ascii", errors="replace").rstrip()
        if any(v is not None and v != "" for v in row.values()):
            records.append(row)

    return records


def _parse_tsv_gz(
    path: str,
    filters: dict[str, str] | None = None,
    max_rows: int | None = None,
) -> list[dict[str, str]]:
    """Parse a gzipped TSV file with optional column filters.

    *filters* maps column names to required substrings (case-insensitive).
    Streaming: only matching rows are kept in memory.
    """
    results: list[dict[str, str]] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            if filters:
                if not all(v.lower() in row.get(k, "").lower() for k, v in filters.items()):
                    continue
            results.append(dict(row))
            if max_rows is not None and len(results) >= max_rows:
                break
    return results


# ---------------------------------------------------------------------------
# DatasetManager
# ---------------------------------------------------------------------------


class DatasetManager:
    """High-level manager for catalogued Teloscopy datasets.

    Provides methods to browse the catalog, download datasets to a local
    cache, parse format-specific files, and generate citation strings.

    Parameters
    ----------
    data_dir : str
        Root directory for local storage (default ``~/.teloscopy/datasets``).
    """

    def __init__(self, data_dir: str = "~/.teloscopy/datasets") -> None:
        self._data_dir = Path(data_dir).expanduser().resolve()
        self._catalog: dict[str, DatasetInfo] = {
            k: DatasetInfo(
                name=v.name,
                url=v.url,
                doi=v.doi,
                description=v.description,
                license=v.license,
                size_mb=v.size_mb,
                format_desc=v.format_desc,
                citation=v.citation,
                use_case=v.use_case,
                extra_urls=list(v.extra_urls),
                note=v.note,
            )
            for k, v in DATASET_CATALOG.items()
        }
        self._refresh_local_state()

    def _refresh_local_state(self) -> None:
        """Scan local cache and update ``downloaded`` / ``local_path``."""
        for name, info in self._catalog.items():
            ds_dir = self._data_dir / name
            if ds_dir.exists() and any(ds_dir.iterdir()):
                info.downloaded = True
                info.local_path = str(ds_dir)
            else:
                info.downloaded = False
                info.local_path = ""

    # -- Listing -------------------------------------------------------------

    def list_available(self) -> list[DatasetInfo]:
        """Return every dataset in the catalog, sorted by name."""
        return sorted(self._catalog.values(), key=lambda d: d.name)

    def list_downloaded(self) -> list[DatasetInfo]:
        """Return only locally-cached datasets."""
        self._refresh_local_state()
        return [d for d in self.list_available() if d.downloaded]

    # -- Info & citation -----------------------------------------------------

    def dataset_info(self, name: str) -> DatasetInfo | None:
        """Look up a single dataset by catalog key."""
        return self._catalog.get(name)

    def cite(self, name: str) -> str:
        """Return the citation string for *name*, or ``""`` if unknown."""
        info = self._catalog.get(name)
        return info.citation if info else ""

    def cite_all_used(self) -> str:
        """Compile newline-separated citations for every downloaded dataset."""
        self._refresh_local_state()
        return "\n\n".join(f"[{ds.name}] {ds.citation}" for ds in self.list_downloaded())

    # -- Paths ---------------------------------------------------------------

    def get_path(self, name: str) -> str | None:
        """Return local path for a downloaded dataset, or ``None``."""
        self._refresh_local_state()
        info = self._catalog.get(name)
        if info and info.downloaded:
            return info.local_path
        return None

    # -- Download ------------------------------------------------------------

    def download(self, name: str, *, force: bool = False) -> str:
        """Download a single dataset by catalog name.

        Parameters
        ----------
        name : str
            Key in ``DATASET_CATALOG``.
        force : bool
            Re-download even when already cached.

        Returns
        -------
        str
            Absolute path to the local dataset directory.

        Raises
        ------
        KeyError
            If *name* is unknown.
        RuntimeError
            If the dataset requires API access (e.g. IDR/OMERO).
        """
        if name not in self._catalog:
            raise KeyError(
                f"Unknown dataset {name!r}. Available: {', '.join(sorted(self._catalog))}"
            )
        info = self._catalog[name]

        if info.note and "not direct download" in info.note.lower():
            raise RuntimeError(
                f"Dataset {name!r} requires specialised API access. Note: {info.note}"
            )

        ds_dir = self._data_dir / name
        if ds_dir.exists() and any(ds_dir.iterdir()) and not force:
            logger.info("Dataset %r already cached at %s", name, ds_dir)
            info.downloaded = True
            info.local_path = str(ds_dir)
            return str(ds_dir)

        ds_dir.mkdir(parents=True, exist_ok=True)
        for url in [info.url] + list(info.extra_urls):
            filename = url.split("/")[-1].split("?")[0]
            local_file = str(ds_dir / filename)
            _download_file(url, local_file)
            if filename.lower().endswith(".zip"):
                _extract_zip(local_file, str(ds_dir))

        # Provenance sidecar
        (ds_dir / ".teloscopy_meta.txt").write_text(
            f"name: {info.name}\nurl: {info.url}\ndoi: {info.doi}\n"
            f"license: {info.license}\n"
            f"downloaded: {datetime.now(tz=timezone.utc).isoformat()}\n"
            f"citation: {info.citation}\n",
            encoding="utf-8",
        )
        info.downloaded = True
        info.local_path = str(ds_dir)
        logger.info("Dataset %r ready at %s", name, ds_dir)
        return str(ds_dir)

    def download_all(self, use_cases: list[str] | None = None) -> dict[str, str]:
        """Download datasets, optionally filtered by use-case.

        Parameters
        ----------
        use_cases : list[str] | None
            Restrict to these use-cases; ``None`` downloads everything.

        Returns
        -------
        dict[str, str]
            ``{name: local_path}`` for each successfully downloaded dataset.
        """
        results: dict[str, str] = {}
        for name, info in self._catalog.items():
            if use_cases is not None and info.use_case not in use_cases:
                continue
            try:
                results[name] = self.download(name)
            except RuntimeError as exc:
                logger.warning("Skipping %s: %s", name, exc)
        return results

    # -- Checksum verification -----------------------------------------------

    def verify_checksum(self, name: str) -> bool:
        """Verify dataset integrity via SHA-256 manifest.

        On first call the checksum is *recorded*; subsequent calls compare
        against it.  Returns ``True`` when checksums match or on first run.

        Raises ``KeyError`` for unknown names and ``FileNotFoundError`` if
        the dataset has not been downloaded.
        """
        if name not in self._catalog:
            raise KeyError(f"Unknown dataset {name!r}")
        info = self._catalog[name]
        if not info.downloaded or not info.local_path:
            raise FileNotFoundError(f"Dataset {name!r} not downloaded.")

        ds_dir = Path(info.local_path)
        manifest = ds_dir / ".teloscopy_sha256"
        current = self._compute_dir_hash(ds_dir)

        if manifest.exists():
            stored = manifest.read_text(encoding="utf-8").strip()
            ok = stored == current
            if ok:
                logger.info("Checksum OK for %s", name)
            else:
                logger.warning("Checksum MISMATCH for %s", name)
            return ok

        manifest.write_text(current + "\n", encoding="utf-8")
        logger.info("Checksum recorded for %s: %s", name, current)
        return True

    @staticmethod
    def _compute_dir_hash(directory: Path) -> str:
        """SHA-256 over all non-hidden files (sorted by relative path)."""
        sha = hashlib.sha256()
        for fp in sorted(
            p for p in directory.rglob("*") if p.is_file() and not p.name.startswith(".")
        ):
            sha.update(str(fp.relative_to(directory)).encode())
            sha.update(fp.read_bytes())
        return sha.hexdigest()

    # -- NHANES telomere data ------------------------------------------------

    def get_nhanes_telomere_data(self) -> list[dict[str, Any]]:
        """Parse NHANES telomere XPT files into usable records.

        Downloads the dataset automatically if not cached.  Applies the
        standard CDC conversion::

            TL (kb) = (3274 + 2413 * T/S) / 1000

        Returns
        -------
        list[dict[str, Any]]
            Each dict contains ``SEQN``, the raw T/S ratio, and a
            computed ``telomere_kb`` key.  Both 1999-2000 (TELO_A) and
            2001-2002 (TELO_B) cycles are concatenated.
        """
        ds_path = self.get_path("nhanes_telomere") or self.download("nhanes_telomere")
        all_records: list[dict[str, Any]] = []

        for xpt_name in ("TELO_A.XPT", "TELO_B.XPT"):
            xpt_path = Path(ds_path) / xpt_name
            if not xpt_path.exists():
                logger.warning("Expected file not found: %s", xpt_path)
                continue
            for rec in _parse_xpt(str(xpt_path)):
                ts = rec.get("TELOMEAN") or rec.get("TELO_MEAN") or rec.get("MEAN_TS")
                if ts is not None:
                    try:
                        rec["telomere_kb"] = round((3274 + 2413 * float(ts)) / 1000, 3)
                    except (TypeError, ValueError):
                        rec["telomere_kb"] = None
                else:
                    rec["telomere_kb"] = None
                all_records.append(rec)

        logger.info("Loaded %d NHANES telomere records", len(all_records))
        return all_records

    # -- ClinVar variant query -----------------------------------------------

    def get_clinvar_variants(
        self,
        gene: str | None = None,
        significance: str | None = None,
        max_rows: int | None = None,
    ) -> list[dict[str, str]]:
        """Query ClinVar variant_summary with optional filters.

        Parameters
        ----------
        gene : str | None
            Restrict to variants in this gene (``GeneSymbol`` column,
            case-insensitive substring match).
        significance : str | None
            Restrict by ``ClinicalSignificance`` substring
            (e.g. ``"Pathogenic"``).
        max_rows : int | None
            Cap returned rows to avoid memory issues.

        Returns
        -------
        list[dict[str, str]]
            Column-header -> value for each matching variant.
        """
        ds_path = self.get_path("clinvar_variants") or self.download("clinvar_variants")
        gz_path = Path(ds_path) / "variant_summary.txt.gz"
        if not gz_path.exists():
            raise FileNotFoundError(f"Expected ClinVar file not found: {gz_path}")

        filters: dict[str, str] = {}
        if gene is not None:
            filters["GeneSymbol"] = gene
        if significance is not None:
            filters["ClinicalSignificance"] = significance

        results = _parse_tsv_gz(str(gz_path), filters=filters or None, max_rows=max_rows)
        logger.info(
            "ClinVar query: %d variants (gene=%s, sig=%s)", len(results), gene, significance
        )
        return results

    # -- Spotiflow dataset loader --------------------------------------------

    def get_spotiflow_dataset(self, subset: str = "all") -> dict[str, Any]:
        """Load Spotiflow FISH benchmark images and annotations.

        Parameters
        ----------
        subset : str
            Specific sub-dataset name (e.g. ``"synthetic"``) or ``"all"``.

        Returns
        -------
        dict[str, Any]
            ``"root"`` — dataset root path.
            ``"subsets"`` — ``{name: {"images": [...], "annotations": [...],
            "count": int}}``.

        Raises
        ------
        KeyError
            If *subset* does not match any unpacked sub-directory.
        """
        ds_path = self.get_path("spotiflow_fish") or self.download("spotiflow_fish")
        root = Path(ds_path)
        result: dict[str, Any] = {"root": str(root), "subsets": {}}

        subdirs = sorted(d for d in root.iterdir() if d.is_dir() and not d.name.startswith("."))
        # Handle a single wrapper directory produced by some zip layouts
        if not subdirs:
            for child in root.iterdir():
                if child.is_dir() and not child.name.startswith("."):
                    inner = sorted(
                        d for d in child.iterdir() if d.is_dir() and not d.name.startswith(".")
                    )
                    if inner:
                        root = child
                        result["root"] = str(root)
                        subdirs = inner
                        break

        for sd in subdirs:
            images = sorted(str(p) for p in sd.rglob("*") if p.suffix.lower() in (".tif", ".tiff"))
            annots = sorted(str(p) for p in sd.rglob("*") if p.suffix.lower() == ".csv")
            result["subsets"][sd.name] = {
                "images": images,
                "annotations": annots,
                "count": max(len(images), len(annots)),
            }

        if subset != "all":
            if subset not in result["subsets"]:
                raise KeyError(
                    f"Subset {subset!r} not found. "
                    f"Available: {', '.join(sorted(result['subsets']))}"
                )
            result["subsets"] = {subset: result["subsets"][subset]}

        logger.info("Spotiflow: %d subsets loaded from %s", len(result["subsets"]), root)
        return result
