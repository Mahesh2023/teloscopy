# Teloscopy

**The first comprehensive Python pipeline for telomere length analysis from qFISH microscopy images.**

Teloscopy automates the quantification of telomere fluorescence intensity from quantitative Fluorescence In Situ Hybridisation (qFISH) microscopy images, converting raw fluorescence photographs into per-chromosome telomere length estimates.

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Microscopy      │     │  Teloscopy       │     │  Results         │
│  Image (TIFF)    │────▶│  Pipeline        │────▶│  CSV + Plots     │
│                  │     │                  │     │                  │
│  DAPI + Cy3      │     │  Segment → Detect│     │  Per-telomere    │
│  channels        │     │  → Associate →   │     │  intensity &     │
│                  │     │  Quantify        │     │  length (bp)     │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

## Why Teloscopy?

| Problem | Existing Tools | Teloscopy |
|---------|---------------|-----------|
| qFISH analysis | ImageJ macros (manual, Windows-only) | Python (cross-platform, automated) |
| Batch processing | Click through each image | `teloscopy batch ./images/` |
| Reproducibility | Manual thresholds per image | Config YAML, deterministic |
| Extensibility | Locked in Java/Fiji | pip-installable, scriptable |
| Deep learning | Not available | Cellpose integration for segmentation |

## Quick Start

### Installation

```bash
pip install -e ".[dev]"

# With deep learning segmentation:
pip install -e ".[cellpose]"

# With sequencing support:
pip install -e ".[all]"
```

### Generate Test Data

```bash
teloscopy generate -n 5 -o data/sample_images/
```

### Analyze a Single Image

```bash
teloscopy analyze data/sample_images/synthetic_001.tif -o output/
```

### Batch Process

```bash
teloscopy batch data/sample_images/ -o output/ -p "*.tif"
```

### Python API

```python
from teloscopy.telomere.pipeline import analyze_image

results = analyze_image("metaphase_001.tif")

print(f"Found {len(results['chromosomes'])} chromosomes")
print(f"Detected {len(results['spots'])} telomere spots")
print(f"Mean intensity: {results['statistics']['mean_intensity']:.0f}")
```

## Pipeline Architecture

```
Input: Multi-channel fluorescence microscopy image (TIFF)
       Channel 0: DAPI (chromosome bodies, blue)
       Channel 1: Cy3/FITC (telomere signals, red/green)

Step 1: PREPROCESSING
  ├── Load multi-channel image (tifffile / OpenCV)
  ├── Background subtraction (rolling ball / top-hat / Gaussian)
  └── Gaussian denoising

Step 2: CHROMOSOME SEGMENTATION (DAPI channel)
  ├── Method A: Otsu threshold + watershed separation
  └── Method B: Cellpose deep learning (optional)
  Output: Labeled mask (each chromosome = unique integer)

Step 3: CHROMOSOME PROPERTY EXTRACTION
  ├── Region properties (area, centroid, orientation)
  └── Tip detection (two most distant points = p-arm, q-arm)

Step 4: TELOMERE SPOT DETECTION (Cy3 channel)
  ├── Laplacian of Gaussian (blob_log) — most accurate
  ├── Difference of Gaussian (blob_dog) — faster
  └── Determinant of Hessian (blob_doh) — fastest
  Output: List of (y, x, sigma) per detected spot

Step 5: SPOT-CHROMOSOME ASSOCIATION
  ├── Build KDTree from all chromosome tips
  ├── Query nearest tip for each spot
  └── Filter by max distance threshold
  Output: Each spot tagged with chromosome label + arm (p/q)

Step 6: INTENSITY QUANTIFICATION
  ├── Circular aperture photometry around each spot
  ├── Local background subtraction (annular region)
  └── Signal-to-noise ratio computation

Step 7: CALIBRATION (optional)
  ├── Linear regression: intensity → base pairs
  └── Using reference cells with known telomere length

Step 8: STATISTICAL OUTPUT
  ├── Per-cell: mean, median, std, percentiles
  ├── Per-chromosome: p-arm and q-arm lengths
  └── CSV export + visualization plots
```

## Project Structure

```
teloscopy/
├── pyproject.toml              # Package metadata & dependencies
├── requirements.txt            # Pinned dependencies
├── configs/
│   └── pipeline.yaml           # Default pipeline configuration
│
├── src/teloscopy/
│   ├── __init__.py
│   ├── cli.py                  # Click CLI entry point
│   │
│   ├── telomere/               # Core image analysis
│   │   ├── preprocessing.py    # Image loading, bg subtraction, denoising
│   │   ├── segmentation.py     # Chromosome segmentation (Otsu/Cellpose)
│   │   ├── spot_detection.py   # Telomere spot detection (LoG/DoG/DoH)
│   │   ├── association.py      # Spot-to-chromosome tip matching
│   │   ├── quantification.py   # Intensity measurement + calibration
│   │   ├── pipeline.py         # End-to-end orchestrator
│   │   └── synthetic.py        # Synthetic test image generator
│   │
│   ├── sequencing/             # Sequence-based telomere analysis
│   │   └── telomere_seq.py     # Telomere length from BAM/FASTQ
│   │
│   ├── analysis/               # Statistical analysis
│   │   └── statistics.py       # Per-cell, per-sample statistics
│   │
│   └── visualisation/          # Plotting & reports
│       └── plots.py            # Overlays, histograms, heatmaps
│
├── tests/
│   ├── test_synthetic.py       # Synthetic data generator tests
│   └── test_pipeline.py        # Integration tests (full pipeline)
│
├── data/
│   ├── sample_images/          # Test microscopy images
│   └── reference/              # Reference genome files
│
├── notebooks/                  # Jupyter notebooks for exploration
├── scripts/                    # Utility scripts
└── KNOWLEDGE_BASE.md           # Technical reference (1,200+ lines)
```

## Configuration

Pipeline behavior is controlled via `configs/pipeline.yaml`:

```yaml
pipeline:
  preprocessing:
    background_method: "rolling_ball"   # rolling_ball | tophat | gaussian
    background_radius: 50
    denoise_sigma: 1.0

  segmentation:
    method: "otsu_watershed"            # otsu_watershed | cellpose
    min_chromosome_area: 500
    watershed_min_distance: 20

  spot_detection:
    method: "blob_log"                  # blob_log | blob_dog | blob_doh
    min_sigma: 1.0
    max_sigma: 5.0
    threshold: 0.05

  association:
    max_distance: 15                    # pixels

  quantification:
    spot_radius: 5
    bg_inner_radius: 7
    bg_outer_radius: 12

calibration:
  enabled: false
  references:
    - intensity: 5000
      length_bp: 10000
    - intensity: 50000
      length_bp: 80000
```

## Supported Image Formats

| Format | Extension | Library |
|--------|-----------|---------|
| TIFF (16-bit) | `.tif`, `.tiff` | tifffile |
| PNG | `.png` | OpenCV |
| JPEG | `.jpg`, `.jpeg` | OpenCV |
| Zeiss CZI | `.czi` | aicsimageio (optional) |
| Nikon ND2 | `.nd2` | aicsimageio (optional) |

## Sequencing-Based Telomere Analysis

Teloscopy also supports telomere length estimation from whole genome sequencing data:

```python
from teloscopy.sequencing.telomere_seq import estimate_from_fastq

results = estimate_from_fastq("sample_R1.fastq.gz", max_reads=1_000_000)
print(f"Telomere fraction: {results['telomere_fraction']:.6f}")
print(f"Estimated mean length: {results['estimated_mean_length_bp']:.0f} bp")
```

## Dependencies

### Core (always required)
- numpy, scipy, pandas
- scikit-image (segmentation, blob detection)
- opencv-python-headless (image I/O)
- tifffile (microscopy TIFF)
- matplotlib, seaborn (plotting)
- click, rich (CLI)

### Optional
- **cellpose** — deep learning chromosome segmentation
- **biopython** — FASTA/FASTQ parsing
- **pysam** — BAM file reading
- **plotly** — interactive charts

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Generate synthetic test data
teloscopy generate -n 10 -o data/sample_images/
```

## Scientific Background

Telomeres are repetitive DNA sequences (TTAGGG in humans) at chromosome ends that shorten with each cell division. Quantitative FISH (qFISH) measures telomere length by:

1. Hybridizing fluorescent PNA probes (Cy3-labeled CCCTAA) to telomere repeats
2. Imaging under fluorescence microscopy (DAPI for chromosomes, Cy3 for telomeres)
3. Measuring fluorescence intensity at each chromosome end
4. Converting intensity to base pairs using calibration standards

Teloscopy automates steps 3-4, replacing manual ImageJ-based workflows.

## License

MIT

## References

- Lansdorp, P. M. et al. (1996). "Heterogeneity in telomere length of human chromosomes." *Human Molecular Genetics*, 5(5), 685-691.
- Stringer, C. et al. (2021). "Cellpose: a generalist algorithm for cellular segmentation." *Nature Methods*, 18, 100-106.
- van der Walt, S. et al. (2014). "scikit-image: image processing in Python." *PeerJ*, 2, e453.
