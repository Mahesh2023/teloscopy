"""Benchmark validation suite for Teloscopy analysis modules.

Validates core components against real, publicly available datasets:

* **Spot detection** — Spotiflow FISH benchmark [1]_.  CNN vs LoG.
* **Disease-risk prediction** — ClinVar pathogenic/benign annotations [2]_.
* **Telomere population stats** — NHANES 1999–2002 survey [3]_.
* **Nuclear segmentation** — BBBC039 fluorescence nuclei [4]_.

.. [1] Grünwald *et al.* *Nature Methods* (2024).
.. [2] Landrum *et al.* *NAR* 48 (2020): D835–D844.
.. [3] Needham *et al.* *Soc. Sci. Med.* 85 (2013): 1–8.
.. [4] Ljosa *et al.* *Nature Methods* 9.7 (2012): 637.
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from teloscopy.genomics.disease_risk import (
    BUILTIN_VARIANT_DB,
    DiseasePredictor,
    GeneticVariant,
)
from teloscopy.ml.cnn_spot_detector import CNNSpotDetector
from teloscopy.telomere.segmentation import segment
from teloscopy.telomere.spot_detection import detect_spots
from teloscopy.tracking.longitudinal import (
    _POPULATION_REFERENCE,
    _population_stats_for_age,
)

logger = logging.getLogger(__name__)
_EPS = 1e-12  # guard against division by zero

# ---------------------------------------------------------------------------
# Metric helpers — real implementations, not mocked
# ---------------------------------------------------------------------------


def _precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Compute precision, recall, and F1 from raw counts."""
    prec = tp / (tp + fp + _EPS)
    rec = tp / (tp + fn + _EPS)
    f1 = 2.0 * prec * rec / (prec + rec + _EPS)
    return prec, rec, f1


def _compute_iou(mask_pred: np.ndarray, mask_gt: np.ndarray) -> float:
    """Intersection-over-Union for two binary masks."""
    p, g = mask_pred.astype(bool), mask_gt.astype(bool)
    inter = np.logical_and(p, g).sum()
    union = np.logical_or(p, g).sum()
    return 1.0 if union == 0 else float(inter / union)


def _compute_dice(mask_pred: np.ndarray, mask_gt: np.ndarray) -> float:
    """Sørensen–Dice coefficient for two binary masks."""
    p, g = mask_pred.astype(bool), mask_gt.astype(bool)
    inter = np.logical_and(p, g).sum()
    total = p.sum() + g.sum()
    return 1.0 if total == 0 else float(2.0 * inter / total)


def _instance_metric(
    labels_pred: np.ndarray,
    labels_gt: np.ndarray,
    metric_fn: Any,
) -> float:
    """Mean instance-level metric across all ground-truth objects.

    For every GT label, finds the predicted label with highest overlap
    and computes *metric_fn* on the pair.
    """
    gt_ids = np.unique(labels_gt)
    gt_ids = gt_ids[gt_ids != 0]
    if len(gt_ids) == 0:
        return 1.0
    scores: list[float] = []
    for gid in gt_ids:
        gt_mask = labels_gt == gid
        overlapping = np.unique(labels_pred[gt_mask])
        overlapping = overlapping[overlapping != 0]
        if len(overlapping) == 0:
            scores.append(0.0)
            continue
        best = max(metric_fn(labels_pred == pid, gt_mask) for pid in overlapping)
        scores.append(best)
    return float(np.mean(scores))


def _match_spots(
    pred: np.ndarray,
    gt: np.ndarray,
    tolerance: float,
) -> tuple[int, int, int, float]:
    """Greedy spot matching.  Returns ``(tp, fp, fn, mean_dist_error)``."""
    if len(gt) == 0 and len(pred) == 0:
        return 0, 0, 0, 0.0
    if len(gt) == 0:
        return 0, len(pred), 0, 0.0
    if len(pred) == 0:
        return 0, 0, len(gt), 0.0
    diff = pred[:, np.newaxis, :] - gt[np.newaxis, :, :]
    dists = np.sqrt((diff**2).sum(axis=2))
    matched_gt: set[int] = set()
    matched_pred: set[int] = set()
    errors: list[float] = []
    n_gt = dists.shape[1]
    for flat_idx in np.argsort(dists, axis=None):
        pi, gi = int(flat_idx // n_gt), int(flat_idx % n_gt)
        if pi in matched_pred or gi in matched_gt:
            continue
        d = dists[pi, gi]
        if d > tolerance:
            break
        matched_pred.add(pi)
        matched_gt.add(gi)
        errors.append(float(d))
    tp = len(matched_gt)
    return tp, len(pred) - tp, len(gt) - tp, (float(np.mean(errors)) if errors else 0.0)


def _r_squared(obs: np.ndarray, pred: np.ndarray) -> float:
    """Coefficient of determination (R²)."""
    ss_res = np.sum((obs - pred) ** 2)
    ss_tot = np.sum((obs - np.mean(obs)) ** 2)
    if ss_tot < _EPS:
        return 1.0 if ss_res < _EPS else 0.0
    return float(1.0 - ss_res / ss_tot)


def _rmse(obs: np.ndarray, pred: np.ndarray) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(np.mean((obs - pred) ** 2)))


def _bland_altman(a: np.ndarray, b: np.ndarray) -> tuple[float, tuple[float, float]]:
    """Bland–Altman: ``(mean_diff, (lower_limit, upper_limit))``."""
    diff = a - b
    md = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1)) if len(diff) > 1 else 0.0
    return md, (md - 1.96 * sd, md + 1.96 * sd)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SpotDetectionResult:
    """Spot detection benchmark results (Spotiflow FISH)."""

    dataset_name: str = ""
    n_images: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    mean_distance_error: float = 0.0
    thresholds_tested: list[float] = field(default_factory=list)
    per_threshold_f1: dict[str, float] = field(default_factory=dict)
    comparison_vs_log: dict[str, float] = field(default_factory=dict)


@dataclass
class DiseaseRiskResult:
    """Disease-risk prediction benchmark results (ClinVar)."""

    dataset_name: str = ""
    n_variants_tested: int = 0
    sensitivity: float = 0.0
    specificity: float = 0.0
    ppv: float = 0.0
    npv: float = 0.0
    genes_tested: list[str] = field(default_factory=list)
    per_gene_accuracy: dict[str, float] = field(default_factory=dict)


@dataclass
class TelomerePopResult:
    """Telomere population stats benchmark results (NHANES)."""

    dataset_name: str = ""
    n_subjects: int = 0
    r_squared: float = 0.0
    rmse: float = 0.0
    bland_altman_mean_diff: float = 0.0
    bland_altman_limits: tuple[float, float] = (0.0, 0.0)
    age_groups_tested: list[str] = field(default_factory=list)
    per_age_group_correlation: dict[str, float] = field(default_factory=dict)


@dataclass
class SegmentationResult:
    """Nuclear segmentation benchmark results (BBBC039)."""

    dataset_name: str = ""
    n_images: int = 0
    mean_iou: float = 0.0
    mean_dice: float = 0.0
    per_image_iou: dict[str, float] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Aggregate report from :meth:`BenchmarkSuite.run_all`."""

    timestamp: str = ""
    results: list[Any] = field(default_factory=list)
    overall_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Dataset loading helpers
# ---------------------------------------------------------------------------


def _resolve_dir(data_dir: str, name: str) -> Path:
    return Path(os.path.expanduser(data_dir)) / name


def _try_imread():
    """Return ``skimage.io.imread`` or ``None``."""
    try:
        from skimage.io import imread  # type: ignore[import-untyped]

        return imread
    except ImportError:
        logger.warning("scikit-image not installed; cannot load images.")
        return None


def _load_images_and_labels(ds: Path) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Load paired ``images/`` and ``labels/`` directories."""
    imread = _try_imread()
    if imread is None or not (ds / "images").is_dir() or not (ds / "labels").is_dir():
        return []
    pairs: list[tuple[str, np.ndarray, np.ndarray]] = []
    for p in sorted((ds / "images").glob("*.tif")):
        lp = ds / "labels" / p.name
        if lp.exists():
            pairs.append((p.name, imread(str(p)), imread(str(lp))))
    return pairs


def _load_spot_annotations(ds: Path) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Load ``images/*.tif`` + ``annotations/*.csv`` (y, x columns)."""
    imread = _try_imread()
    if imread is None or not (ds / "images").is_dir() or not (ds / "annotations").is_dir():
        return []
    out: list[tuple[str, np.ndarray, np.ndarray]] = []
    for p in sorted((ds / "images").glob("*.tif")):
        cp = ds / "annotations" / p.with_suffix(".csv").name
        if not cp.exists():
            continue
        coords = np.loadtxt(str(cp), delimiter=",", skiprows=1)
        if coords.ndim == 1 and coords.size >= 2:
            coords = coords.reshape(1, -1)
        if coords.ndim == 2 and coords.shape[1] >= 2:
            out.append((p.name, imread(str(p)), coords[:, :2]))
    return out


def _load_clinvar_tsv(ds: Path) -> list[dict[str, str]]:
    """Load ClinVar variant_summary TSV (plain or gzipped)."""
    for name in ("variant_summary.txt.gz", "variant_summary.txt"):
        path = ds / name
        if not path.exists():
            continue
        opener = gzip.open if name.endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8") as fh:  # type: ignore[arg-type]
            reader = csv.DictReader(fh, delimiter="\t")
            rows: list[dict[str, str]] = []
            for row in reader:
                rs = row.get("RS# (dbSNP)", row.get("rs", "")).strip()
                gene = row.get("GeneSymbol", row.get("gene", "")).strip()
                sig = row.get("ClinicalSignificance", row.get("clinical_significance", "")).strip()
                if rs and gene and sig:
                    rows.append(
                        {
                            "rsid": f"rs{rs}" if not rs.startswith("rs") else rs,
                            "gene": gene,
                            "significance": sig,
                        }
                    )
            return rows
    return []


def _load_nhanes(ds: Path) -> list[dict[str, float]]:
    """Load NHANES telomere data (CSV or SAS XPORT)."""
    csv_path = ds / "nhanes_telomere.csv"
    if csv_path.exists():
        with open(csv_path, encoding="utf-8") as fh:
            rows: list[dict[str, float]] = []
            for row in csv.DictReader(fh):
                try:
                    age = float(row.get("RIDAGEYR", row.get("age", "")))
                    tl = float(row.get("TELOMEAN", row.get("mean_tl_kb", "")))
                    rows.append({"age": age, "mean_tl_kb": tl})
                except (ValueError, TypeError):
                    continue
            return rows
    # SAS XPORT fallback (NHANES distributes .XPT files)
    for xpt in sorted(ds.glob("*.XPT")) + sorted(ds.glob("*.xpt")):
        try:
            import pandas as pd  # type: ignore[import-untyped]

            df = pd.read_sas(str(xpt), format="xport")
            if "RIDAGEYR" in df.columns and "TELOMEAN" in df.columns:
                sub = df.dropna(subset=["RIDAGEYR", "TELOMEAN"])
                return [
                    {"age": float(r["RIDAGEYR"]), "mean_tl_kb": float(r["TELOMEAN"])}
                    for _, r in sub.iterrows()
                ]
        except Exception:  # noqa: BLE001
            continue
    return []


# ---------------------------------------------------------------------------
# BenchmarkSuite
# ---------------------------------------------------------------------------


class BenchmarkSuite:
    """Run validation benchmarks against public reference datasets.

    Parameters
    ----------
    data_dir : str
        Root directory for benchmark datasets (``~`` expanded).
    output_dir : str
        Directory for reports and exported JSON.

    Examples
    --------
    >>> suite = BenchmarkSuite()
    >>> report = suite.run_all()
    >>> print(suite.generate_report(report))
    """

    def __init__(
        self, data_dir: str = "~/.teloscopy/datasets", output_dir: str = "./benchmark_results"
    ) -> None:
        self.data_dir = os.path.expanduser(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # run_all
    # ------------------------------------------------------------------

    def run_all(self) -> BenchmarkReport:
        """Execute every benchmark and return an aggregate :class:`BenchmarkReport`."""
        ts = datetime.now(tz=timezone.utc).isoformat()
        logger.info("Starting full benchmark run at %s", ts)
        spot = self.benchmark_spot_detection()
        disease = self.benchmark_disease_prediction()
        pop = self.benchmark_telomere_population()
        seg = self.benchmark_nuclear_segmentation()
        # Weighted harmonic mean (clinical accuracy weighted higher)
        pairs = [
            (spot.f1, 1.0),
            (disease.sensitivity, 1.5),
            (max(pop.r_squared, 0.0), 1.0),
            (seg.mean_iou, 1.0),
        ]
        w_sum = sum(w for _, w in pairs)
        denom = sum(w / (s + _EPS) for s, w in pairs)
        import platform, sys  # noqa: E401,I001

        report = BenchmarkReport(
            timestamp=ts,
            results=[spot, disease, pop, seg],
            overall_score=w_sum / denom if denom > _EPS else 0.0,
            metadata={"python": sys.version, "platform": platform.platform()},
        )
        logger.info("Benchmark complete — score %.3f", report.overall_score)
        return report

    # ------------------------------------------------------------------
    # Spot detection benchmark
    # ------------------------------------------------------------------

    def benchmark_spot_detection(self, dataset_name: str = "spotiflow_fish") -> SpotDetectionResult:
        """Evaluate CNN spot detector on Spotiflow FISH benchmark data.

        Compares :class:`~teloscopy.ml.cnn_spot_detector.CNNSpotDetector`
        against a classical LoG baseline.  Reports F1, precision, recall
        at different confidence thresholds.
        """
        ds = _resolve_dir(self.data_dir, dataset_name)
        data = _load_spot_annotations(ds)
        if not data:
            logger.warning("Dataset '%s' not found at %s — skipping.", dataset_name, ds)
            return SpotDetectionResult(dataset_name=dataset_name)

        logger.info("Spot detection benchmark: %d images", len(data))
        tol = 5.0
        thresholds = [0.15, 0.25, 0.35, 0.50, 0.65, 0.80]

        def _eval(detect_fn):  # type: ignore[no-untyped-def]
            """Run *detect_fn(img) -> list[dict]* over all images."""
            at, af, an = 0, 0, 0
            ds_: list[float] = []
            for _, image, gt in data:
                img = image if image.ndim == 2 else image[:, :, 0]
                spots = detect_fn(img)
                pc = np.array([[s["y"], s["x"]] for s in spots]) if spots else np.empty((0, 2))
                tp, fp, fn_, me = _match_spots(pc, gt, tol)
                at += tp
                af += fp
                an += fn_  # noqa: E702
                if me > 0:
                    ds_.append(me)
            p, r, f = _precision_recall_f1(at, af, an)
            return p, r, f, (float(np.mean(ds_)) if ds_ else 0.0)

        # CNN at multiple thresholds
        per_thresh: dict[str, float] = {}
        headline: dict[str, float] = {}
        for th in thresholds:
            det = CNNSpotDetector(confidence_threshold=th)
            p, r, f, me = _eval(det.detect)
            per_thresh[str(th)] = f
            if th == 0.35:
                headline = {"precision": p, "recall": r, "f1": f, "mean_distance_error": me}
        if not headline:
            headline = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "mean_distance_error": 0.0}
        # LoG baseline comparison
        lp, lr, lf, ld = _eval(lambda img: detect_spots(img, method="blob_log"))
        return SpotDetectionResult(
            dataset_name=dataset_name,
            n_images=len(data),
            precision=headline["precision"],
            recall=headline["recall"],
            f1=headline["f1"],
            mean_distance_error=headline["mean_distance_error"],
            thresholds_tested=thresholds,
            per_threshold_f1=per_thresh,
            comparison_vs_log={"precision": lp, "recall": lr, "f1": lf, "mean_distance_error": ld},
        )

    # ------------------------------------------------------------------
    # Disease prediction benchmark
    # ------------------------------------------------------------------

    def benchmark_disease_prediction(
        self, dataset_name: str = "clinvar_variants"
    ) -> DiseaseRiskResult:
        """Validate disease risk predictions against ClinVar-annotated variants.

        Cross-references ClinVar pathogenic/benign annotations against
        :data:`~teloscopy.genomics.disease_risk.BUILTIN_VARIANT_DB`.
        Reports sensitivity/specificity for known pathogenic variants.
        """
        ds = _resolve_dir(self.data_dir, dataset_name)
        clinvar = _load_clinvar_tsv(ds)
        builtin = {v.rsid: v for v in BUILTIN_VARIANT_DB}
        if not clinvar:
            logger.warning("ClinVar not found at %s — internal validation.", ds)
            return self._disease_internal(dataset_name, builtin)
        logger.info("Disease benchmark: %d ClinVar rows vs %d built-in", len(clinvar), len(builtin))
        tp, tn, fp, fn = 0, 0, 0, 0
        gene_ok: dict[str, list[bool]] = {}
        for row in clinvar:
            if row["rsid"] not in builtin:
                continue
            sig = row["significance"].lower()
            is_path = "pathogenic" in sig and "benign" not in sig
            is_ben = "benign" in sig and "pathogenic" not in sig
            if not is_path and not is_ben:
                continue
            pred_path = builtin[row["rsid"]].effect_size > 0
            gene_ok.setdefault(row["gene"], []).append(pred_path == is_path)
            if is_path and pred_path:
                tp += 1  # noqa: E701
            elif is_ben and not pred_path:
                tn += 1  # noqa: E701
            elif is_ben and pred_path:
                fp += 1  # noqa: E701
            elif is_path and not pred_path:
                fn += 1  # noqa: E701
        return self._disease_result(dataset_name, tp, tn, fp, fn, gene_ok)

    def _disease_internal(
        self, dataset_name: str, by_rsid: dict[str, GeneticVariant]
    ) -> DiseaseRiskResult:
        """Internal consistency check using BUILTIN_VARIANT_DB only."""
        predictor = DiseasePredictor()
        tp, tn, fp, fn = 0, 0, 0, 0
        gene_ok: dict[str, list[bool]] = {}
        for v in BUILTIN_VARIANT_DB:
            profile = predictor.predict_from_variants({v.rsid: v.risk_allele}, age=50, sex="female")
            has_risk = any(r.lifetime_risk_pct > 0 for r in profile.risks)
            is_risk = v.effect_size > 0
            gene_ok.setdefault(v.gene, []).append(has_risk == is_risk)
            if is_risk and has_risk:
                tp += 1  # noqa: E701
            elif not is_risk and not has_risk:
                tn += 1  # noqa: E701
            elif not is_risk and has_risk:
                fp += 1  # noqa: E701
            else:
                fn += 1  # noqa: E701
        return self._disease_result(f"{dataset_name} (internal)", tp, tn, fp, fn, gene_ok)

    @staticmethod
    def _disease_result(
        name: str, tp: int, tn: int, fp: int, fn: int, gene_ok: dict[str, list[bool]]
    ) -> DiseaseRiskResult:
        """Construct a :class:`DiseaseRiskResult` from raw confusion-matrix counts."""
        return DiseaseRiskResult(
            dataset_name=name,
            n_variants_tested=tp + tn + fp + fn,
            sensitivity=tp / (tp + fn + _EPS),
            specificity=tn / (tn + fp + _EPS),
            ppv=tp / (tp + fp + _EPS),
            npv=tn / (tn + fn + _EPS),
            genes_tested=sorted(gene_ok),
            per_gene_accuracy={g: float(np.mean(v)) for g, v in sorted(gene_ok.items())},
        )

    # ------------------------------------------------------------------
    # Telomere population benchmark
    # ------------------------------------------------------------------

    def benchmark_telomere_population(
        self, dataset_name: str = "nhanes_telomere"
    ) -> TelomerePopResult:
        """Validate population reference data against NHANES.

        Compares predicted vs actual age-stratified telomere length
        distributions.  Reports R², RMSE, Bland–Altman metrics.
        """
        ds = _resolve_dir(self.data_dir, dataset_name)
        nhanes = _load_nhanes(ds)
        if not nhanes:
            logger.warning("NHANES not found at %s — synthetic validation.", ds)
            return self._telomere_pop_synthetic(dataset_name)
        logger.info("Telomere pop benchmark: %d NHANES subjects", len(nhanes))
        # Bin by age groups matching _POPULATION_REFERENCE
        bins: dict[str, list[float]] = {}
        for rec in nhanes:
            for lo, hi in _POPULATION_REFERENCE:
                if lo <= int(rec["age"]) <= hi:
                    bins.setdefault(f"{lo}-{hi}", []).append(rec["mean_tl_kb"])
                    break
        obs, pred, labels = [], [], []  # type: ignore[var-annotated]
        per_grp: dict[str, float] = {}
        for (lo, hi), (ref_mean, _) in sorted(_POPULATION_REFERENCE.items()):
            lbl = f"{lo}-{hi}"
            if lbl not in bins or len(bins[lbl]) < 2:
                continue
            om = float(np.mean(bins[lbl]))
            obs.append(om)
            pred.append(ref_mean)
            labels.append(lbl)  # noqa: E702
            per_grp[lbl] = max(0.0, 1.0 - abs(ref_mean - om) / (om + _EPS))
        if len(obs) < 2:
            return TelomerePopResult(dataset_name=dataset_name, n_subjects=len(nhanes))
        return self._pop_result(dataset_name, len(nhanes), obs, pred, labels, per_grp)

    def _telomere_pop_synthetic(self, dataset_name: str) -> TelomerePopResult:
        """Self-consistency check with synthetic samples from built-in stats."""
        rng = np.random.default_rng(42)
        n_per, total = 200, 0
        obs, pred, labels = [], [], []  # type: ignore[var-annotated]
        per_grp: dict[str, float] = {}
        for (lo, hi), (rm, sd) in sorted(_POPULATION_REFERENCE.items()):
            lbl = f"{lo}-{hi}"
            om = float(np.mean(np.clip(rng.normal(rm, sd, n_per), 0.5, 20.0)))
            pm, _ = _population_stats_for_age((lo + hi) // 2)
            obs.append(om)
            pred.append(pm)
            labels.append(lbl)  # noqa: E702
            per_grp[lbl] = max(0.0, 1.0 - abs(pm - om) / (om + _EPS))
            total += n_per
        return self._pop_result(f"{dataset_name} (synthetic)", total, obs, pred, labels, per_grp)

    @staticmethod
    def _pop_result(
        name: str,
        n: int,
        obs: list[float],
        pred: list[float],
        labels: list[str],
        pg: dict[str, float],
    ) -> TelomerePopResult:
        """Construct a :class:`TelomerePopResult` from observed/predicted arrays."""
        oa, pa = np.array(obs), np.array(pred)
        ba_m, ba_l = _bland_altman(pa, oa)
        return TelomerePopResult(
            dataset_name=name,
            n_subjects=n,
            r_squared=_r_squared(oa, pa),
            rmse=_rmse(oa, pa),
            bland_altman_mean_diff=ba_m,
            bland_altman_limits=ba_l,
            age_groups_tested=labels,
            per_age_group_correlation=pg,
        )

    # ------------------------------------------------------------------
    # Nuclear segmentation benchmark
    # ------------------------------------------------------------------

    def benchmark_nuclear_segmentation(self, dataset_name: str = "bbbc039") -> SegmentationResult:
        """Evaluate segmentation against BBBC039 ground truth.

        Uses :func:`~teloscopy.telomere.segmentation.segment` with
        ``otsu_watershed``.  Reports IoU and Dice coefficient.
        """
        ds = _resolve_dir(self.data_dir, dataset_name)
        pairs = _load_images_and_labels(ds)
        if not pairs:
            logger.warning("BBBC039 not found at %s — skipping.", ds)
            return SegmentationResult(dataset_name=dataset_name)
        logger.info("Segmentation benchmark: %d images", len(pairs))
        per_img: dict[str, float] = {}
        ious: list[float] = []
        dices: list[float] = []
        for fname, image, gt_labels in pairs:
            img = image if image.ndim == 2 else image[:, :, 0]
            pred_labels = segment(img, method="otsu_watershed")
            iou = _instance_metric(pred_labels, gt_labels, _compute_iou)
            dice = _instance_metric(pred_labels, gt_labels, _compute_dice)
            per_img[fname] = iou
            ious.append(iou)
            dices.append(dice)
        return SegmentationResult(
            dataset_name=dataset_name,
            n_images=len(pairs),
            mean_iou=float(np.mean(ious)),
            mean_dice=float(np.mean(dices)),
            per_image_iou=per_img,
        )

    # ------------------------------------------------------------------
    # Report generation & export
    # ------------------------------------------------------------------

    def generate_report(self, results: BenchmarkReport) -> str:
        """Generate a human-readable Markdown report from benchmark results."""
        lines = [
            "# Teloscopy Benchmark Report",
            "",
            f"**Timestamp:** {results.timestamp}  ",
            f"**Overall score:** {results.overall_score:.3f}  ",
            "",
        ]
        if results.metadata:
            lines += ["## Environment", ""]
            lines += [f"- **{k}:** {v}" for k, v in results.metadata.items()]
            lines += [""]
        for res in results.results:
            lines.extend(self._fmt(res))
        lines += ["---", "*Generated by `teloscopy.data.benchmarks.BenchmarkSuite`*"]
        return "\n".join(lines)

    def export_results(self, results: BenchmarkReport, path: str) -> None:
        """Export benchmark results to JSON."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(asdict(results), fh, indent=2, default=str)
        logger.info("Exported results to %s", out)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt(result: Any) -> list[str]:
        """Format one result dataclass as Markdown lines."""
        if isinstance(result, SpotDetectionResult):
            lines = [
                "## Spot Detection",
                "",
                f"- **Dataset:** {result.dataset_name}  |  **Images:** {result.n_images}",
                f"- **P / R / F1:** {result.precision:.4f} / {result.recall:.4f} / {result.f1:.4f}",
                f"- **Mean dist error:** {result.mean_distance_error:.2f} px",
            ]
            if result.per_threshold_f1:
                lines += ["", "| Threshold | F1 |", "|-----------|------|"]
                lines += [f"| {t} | {f:.4f} |" for t, f in result.per_threshold_f1.items()]
            if result.comparison_vs_log:
                cv = result.comparison_vs_log
                lines += [
                    "",
                    f"**LoG baseline:** P={cv.get('precision', 0):.4f}  "
                    f"R={cv.get('recall', 0):.4f}  F1={cv.get('f1', 0):.4f}",
                ]
            return lines + [""]
        if isinstance(result, DiseaseRiskResult):
            return [
                "## Disease Risk Prediction",
                "",
                f"- **Dataset:** {result.dataset_name}  |  **Variants:** {result.n_variants_tested}",
                f"- **Sens / Spec:** {result.sensitivity:.4f} / {result.specificity:.4f}",
                f"- **PPV / NPV:** {result.ppv:.4f} / {result.npv:.4f}",
                f"- **Genes tested:** {len(result.genes_tested)}",
                "",
            ]
        if isinstance(result, TelomerePopResult):
            lo, hi = result.bland_altman_limits
            return [
                "## Telomere Population Statistics",
                "",
                f"- **Dataset:** {result.dataset_name}  |  **Subjects:** {result.n_subjects}",
                f"- **R² / RMSE:** {result.r_squared:.4f} / {result.rmse:.4f} kb",
                f"- **Bland–Altman:** mean={result.bland_altman_mean_diff:.4f}, "
                f"LoA=[{lo:.4f}, {hi:.4f}] kb",
                "",
            ]
        if isinstance(result, SegmentationResult):
            return [
                "## Nuclear Segmentation",
                "",
                f"- **Dataset:** {result.dataset_name}  |  **Images:** {result.n_images}",
                f"- **Mean IoU / Dice:** {result.mean_iou:.4f} / {result.mean_dice:.4f}",
                "",
            ]
        return []
