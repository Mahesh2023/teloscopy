# Gene Sequencing & DNA Telomere Analysis by Photo
## Complete Technical Knowledge Base

---

## Table of Contents

1. [What Is Gene Sequencing](#1-what-is-gene-sequencing)
2. [DNA Structure Fundamentals](#2-dna-structure-fundamentals)
3. [Sequencing Technologies](#3-sequencing-technologies)
4. [Sequencing Data Formats](#4-sequencing-data-formats)
5. [Sequencing Pipeline (End to End)](#5-sequencing-pipeline-end-to-end)
6. [What Are Telomeres](#6-what-are-telomeres)
7. [Telomere Length Measurement Methods](#7-telomere-length-measurement-methods)
8. [Telomere Analysis by Photo (Q-FISH / Microscopy)](#8-telomere-analysis-by-photo-q-fish--microscopy)
9. [Image Processing Pipeline for Telomere Photos](#9-image-processing-pipeline-for-telomere-photos)
10. [Computational Telomere Length from Sequencing Data](#10-computational-telomere-length-from-sequencing-data)
11. [Python Libraries & Tools](#11-python-libraries--tools)
12. [Project Architecture (Proposed)](#12-project-architecture-proposed)
13. [Key Algorithms](#13-key-algorithms)
14. [Glossary](#14-glossary)
15. [Internet Research Findings (April 2026)](#15-internet-research-findings-april-2026)

---

## 1. What Is Gene Sequencing

Gene sequencing is the process of determining the **exact order of
nucleotide bases** (A, T, G, C) in a DNA molecule. A human genome
contains ~3.2 billion base pairs across 23 chromosome pairs.

### Why it matters

| Application | What sequencing reveals |
|-------------|----------------------|
| **Disease diagnosis** | Mutations causing cancer, genetic disorders |
| **Pharmacogenomics** | Which drugs work for a patient's genotype |
| **Ancestry/forensics** | Lineage, identity matching |
| **Aging research** | Telomere shortening rate |
| **Cancer genomics** | Tumor mutations, treatment targets |
| **Pathogen identification** | Viral/bacterial strain identification |

### Levels of sequencing

```
Whole Genome Sequencing (WGS)
  └── Sequences ALL 3.2 billion bases
  └── Most comprehensive, most expensive
  └── Output: ~100-300 GB per sample

Whole Exome Sequencing (WES)
  └── Sequences only coding regions (~1.5% of genome)
  └── ~22,000 genes
  └── Output: ~5-10 GB per sample

Targeted Panel Sequencing
  └── Sequences specific genes (e.g., BRCA1, TP53)
  └── Cheapest, fastest
  └── Output: ~1-2 GB per sample

RNA Sequencing (RNA-Seq)
  └── Sequences transcribed RNA (gene expression)
  └── Shows which genes are "turned on"
  └── Output: ~5-20 GB per sample
```

---

## 2. DNA Structure Fundamentals

### The Double Helix

```
         5' end                              3' end
         ┌─────────────────────────────────────┐
Strand 1 │ A─T  G─C  T─A  C─G  A─T  G─C ... │  →  "sense strand"
         │ │    │    │    │    │    │         │
Strand 2 │ T─A  C─G  A─T  G─C  T─A  C─G ... │  →  "antisense strand"
         └─────────────────────────────────────┘
         3' end                              5' end

Base pairing rules:
  A (Adenine)  ←→  T (Thymine)     [2 hydrogen bonds]
  G (Guanine)  ←→  C (Cytosine)    [3 hydrogen bonds]
```

### Chromosome Structure

```
                    Telomere (TTAGGG repeats)
                    ↓
    ════════════════╤══════════════════════════╤════════════════
    TTAGGGTTAGGG... │   p-arm (short arm)     │                
                    │                          │ Centromere     
                    │   q-arm (long arm)       │                
    ...TTAGGGTTAGGG │                          │                
    ════════════════╧══════════════════════════╧════════════════
                                                ↑
                                                Telomere (TTAGGG repeats)

Humans have 23 pairs of chromosomes (46 total).
Each chromosome has telomeres at both ends.
That's 92 telomeres per cell.
```

### Gene → Protein Flow

```
DNA  →(transcription)→  mRNA  →(translation)→  Protein
         in nucleus          in ribosome

Codons (3 bases = 1 amino acid):
  ATG → Methionine (START codon)
  TAA, TAG, TGA → STOP codons
  GCT → Alanine
  ... (64 codons total, 20 amino acids)
```

---

## 3. Sequencing Technologies

### 3.1 Sanger Sequencing (1st Generation)

```
Method: Chain termination with fluorescent ddNTPs
Read length: 700-1000 bp
Throughput: 1 read at a time
Cost: ~$500 per megabase
Use: Validation, small targets
```

### 3.2 Illumina / Short-Read (2nd Generation, NGS)

```
Method: Sequencing by synthesis (SBS)
  1. Fragment DNA into ~300-600 bp pieces
  2. Attach adapters to both ends
  3. Bind to flow cell, amplify into clusters
  4. Add fluorescent nucleotides one at a time
  5. Camera captures which base was added (A=green, C=blue, G=yellow, T=red)
  6. Millions of fragments sequenced in parallel

Read length: 75-300 bp (paired-end: 2×150 bp is standard)
Throughput: 100 million - 10 billion reads per run
Error rate: ~0.1% (substitution errors)
Cost: ~$0.01 per megabase
Platforms: NovaSeq 6000, NextSeq 2000, MiSeq
Output: FASTQ files (compressed: .fastq.gz)
```

### 3.3 PacBio / Long-Read (3rd Generation)

```
Method: Single Molecule Real-Time (SMRT) sequencing
  1. Single DNA molecule in a nanoscale well (ZMW)
  2. Polymerase synthesizes complementary strand
  3. Fluorescent nucleotides detected as they're incorporated

Read length: 10,000-100,000 bp (average ~15,000 bp)
Throughput: 4 million reads per SMRT cell
Error rate: ~1% (random insertion/deletion errors)
  → Correctable with HiFi mode (circular consensus): <0.1% error
Platforms: Sequel IIe, Revio
Use: Structural variants, telomere-to-telomere assembly, repeat regions
```

### 3.4 Oxford Nanopore / Ultra-Long Read (3rd Generation)

```
Method: Measures electrical current changes as DNA passes through a nanopore
  1. DNA strand fed through a protein pore
  2. Each base causes a different current disruption
  3. Real-time basecalling from the current signal

Read length: 1,000-4,000,000 bp (record: >4 Mb!)
Throughput: Variable (MinION: 50 Gb, PromethION: 7 Tb)
Error rate: ~3-5% (systematic errors in homopolymers)
  → Improving rapidly with new basecallers (Dorado)
Platforms: MinION (portable, USB), GridION, PromethION
Use: Field sequencing, real-time pathogen ID, telomere assembly
```

### Comparison Table

| Feature | Illumina | PacBio HiFi | Nanopore |
|---------|----------|-------------|----------|
| Read length | 150-300 bp | 15,000 bp | 1,000-4,000,000 bp |
| Error rate | 0.1% | 0.1% (HiFi) | 3-5% |
| Error type | Substitution | Indel | Indel + homopolymer |
| Throughput | Highest | Medium | Medium-High |
| Cost/Gb | $5-10 | $20-30 | $10-20 |
| Time to result | 1-3 days | 1 day | Minutes to hours |
| Telomere sequencing | Poor (too short) | Good | Best |

---

## 4. Sequencing Data Formats

### 4.1 FASTA — Reference Sequences

```
>chr1 Human chromosome 1
ATCGATCGATCGATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA
>chr2 Human chromosome 2
TTAAGCCGGTTAAGCCGGTTAAGCCGGTTAAG
```

- Header line starts with `>`
- Sequence on subsequent lines (usually 80 chars/line)
- Used for: reference genomes, protein sequences
- File extensions: `.fasta`, `.fa`, `.fna`

### 4.2 FASTQ — Raw Sequencing Reads

```
@SEQ_ID_001 instrument:run:flowcell:lane:tile:x:y
ATCGATCGATCGATCGATCGATCGATCGATCG
+
FFFFFFFF:FFFFF:F:FFFFFFFFFFF:FFF
```

- Line 1: `@` + read identifier
- Line 2: DNA sequence
- Line 3: `+` (separator)
- Line 4: Quality scores (Phred+33 ASCII encoding)
  - `F` = Phred 37 = 99.98% accuracy
  - `!` = Phred 0 = 0% confidence
- File extensions: `.fastq`, `.fq`, `.fastq.gz`
- **Paired-end**: Two files per sample (`_R1.fastq.gz` + `_R2.fastq.gz`)

### 4.3 SAM/BAM — Aligned Reads

```
@HD VN:1.6 SO:coordinate
@SQ SN:chr1 LN:248956422
read001  99  chr1  10000  60  150M  =  10300  450  ATCG...  FFFF...
read001  147 chr1  10300  60  150M  =  10000  -450 GCTA...  FFFF...
```

- SAM = text format; BAM = compressed binary (preferred)
- Contains: read name, flags, chromosome, position, mapping quality,
  CIGAR string (alignment), mate position, sequence, quality
- CIGAR: `150M` = 150 bases matched; `50M2I98M` = 50 match, 2 insertion, 98 match
- Created by aligners: BWA-MEM2, minimap2, STAR
- File extensions: `.sam`, `.bam`, `.cram`

### 4.4 VCF — Variant Calls

```
##fileformat=VCFv4.3
#CHROM  POS    ID        REF  ALT  QUAL  FILTER  INFO
chr1    10177  rs12345   A    C    50    PASS    DP=30;AF=0.5
chr1    10352  .         T    TA   40    PASS    DP=25;AF=0.3
```

- Lists every position where the sample differs from the reference
- REF = reference base, ALT = sample's variant
- Types: SNP (single nucleotide), Indel (insertion/deletion), SV (structural)
- File extensions: `.vcf`, `.vcf.gz` (+ `.tbi` index)

### 4.5 BED — Genomic Regions

```
chr1    10000   20000   telomere_region
chr1    50000   51000   gene_TP53_exon1
```

- Tab-separated: chromosome, start (0-based), end, optional name
- Used for: target regions, telomere coordinates, gene annotations

---

## 5. Sequencing Pipeline (End to End)

```
┌─────────────────────────────────────────────────────────────┐
│ WET LAB                                                     │
│                                                             │
│  Blood/tissue sample                                        │
│       ↓ DNA extraction                                      │
│  Pure DNA (~1-10 μg)                                        │
│       ↓ Library preparation (fragmentation + adapters)      │
│  Sequencing library                                         │
│       ↓ Load onto sequencer                                 │
│  Raw signal data (BCL files / FAST5 files)                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓ basecalling
┌──────────────────────────────────────────────────────────────┐
│ BIOINFORMATICS PIPELINE                                      │
│                                                              │
│  Step 1: Quality Control                                     │
│    Input:  sample_R1.fastq.gz, sample_R2.fastq.gz           │
│    Tool:   FastQC → quality report (HTML)                    │
│    Tool:   fastp / Trimmomatic → trim adapters + low-quality │
│    Output: sample_trimmed_R1.fastq.gz                        │
│                                                              │
│  Step 2: Alignment / Mapping                                 │
│    Input:  trimmed FASTQ + reference genome (GRCh38.fa)      │
│    Tool:   BWA-MEM2 (short reads) / minimap2 (long reads)    │
│    Output: sample.bam (sorted, indexed)                      │
│                                                              │
│  Step 3: Post-Alignment Processing                           │
│    Tool:   samtools sort + index                             │
│    Tool:   GATK MarkDuplicates → remove PCR duplicates       │
│    Tool:   GATK BaseRecalibrator → recalibrate quality scores│
│    Output: sample.dedup.recal.bam                            │
│                                                              │
│  Step 4: Variant Calling                                     │
│    Tool:   GATK HaplotypeCaller (germline)                   │
│            or Mutect2 (somatic / cancer)                     │
│    Output: variants.vcf.gz                                   │
│                                                              │
│  Step 5: Variant Annotation                                  │
│    Tool:   VEP (Ensembl), ANNOVAR, snpEff                   │
│    Output: annotated_variants.vcf.gz                         │
│            (gene name, consequence, population frequency,    │
│             clinical significance)                           │
│                                                              │
│  Step 6: Filtering & Interpretation                          │
│    Filter: PASS quality, allele frequency <1%, damaging      │
│    Output: clinically relevant variants list                 │
│                                                              │
│  Optional — Telomere Analysis:                               │
│    Tool:   TelomereHunter / Telomerecat / computel           │
│    Input:  sample.bam                                        │
│    Output: telomere length estimates per chromosome arm      │
└──────────────────────────────────────────────────────────────┘
```

### Compute Requirements

| Step | CPU | RAM | Storage | GPU |
|------|-----|-----|---------|-----|
| FastQC | 1-4 cores | 2 GB | — | No |
| Alignment (BWA-MEM2) | 16-32 cores | 32 GB | — | No (but GPU versions exist) |
| GATK processing | 4-8 cores | 16 GB | — | No |
| Variant calling | 4-16 cores | 16-64 GB | — | Optional (DeepVariant uses GPU) |
| Telomere analysis | 2-8 cores | 8-16 GB | — | No |
| **Total per WGS sample** | **~16 core-hours** | **32 GB peak** | **~500 GB** | Optional |

---

## 6. What Are Telomeres

Telomeres are **repetitive DNA sequences** at the ends of chromosomes
that protect genetic data from degradation.

### Structure

```
Chromosome end:
  ═══════════════════╤═══════════════════════════
  ...coding DNA...   │  TTAGGG TTAGGG TTAGGG TTAGGG TTAGGG TTAGGG →
                     │  ←── 5,000 to 15,000 base pairs ──→
                     │  (shortened by ~50-200 bp per cell division)
                     │
                     │  Plus single-stranded 3' overhang (150-200 nt)
                     │  that loops back to form a "T-loop"
  ═══════════════════╧═══════════════════════════

Human telomere repeat unit: TTAGGG (6 bases)
  - Hexameric repeat, conserved across vertebrates
  - Double-stranded region: 5-15 kb
  - 3' single-stranded overhang: 150-200 nt
  - Forms T-loop + D-loop secondary structure
```

### Why Telomeres Matter

```
Birth:       ~15,000 bp telomere length
             ████████████████████████████████████████

Age 30:      ~10,000 bp
             ██████████████████████████████

Age 60:      ~7,000 bp
             ████████████████████

Age 90:      ~5,000 bp
             ██████████████

Cancer:      ~4,000 bp (or abnormally long via telomerase reactivation)
             ████████████

Hayflick limit (~50-70 divisions):
             ~3,000 bp → cell senescence or apoptosis
             ████████
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **End replication problem** | DNA polymerase can't fully copy chromosome ends; ~50-200 bp lost per division |
| **Telomerase** | Enzyme (hTERT + hTERC) that adds TTAGGG repeats; active in stem cells, germ cells, ~85% of cancers |
| **Shelterin complex** | 6-protein complex (TRF1, TRF2, POT1, TIN2, TPP1, RAP1) that protects telomere ends |
| **T-loop** | Telomere folds back on itself, hiding the free end from DNA repair machinery |
| **Hayflick limit** | Maximum number of cell divisions (~50-70) before telomeres become critically short |
| **Crisis** | When telomeres are too short → chromosome fusions → genomic instability → cancer or cell death |

### Telomere Length as a Biomarker

| Condition | Telomere Length |
|-----------|----------------|
| Normal aging | Gradually shorter |
| Chronic stress | Shorter than expected |
| Obesity | Shorter |
| Exercise | Protective (longer) |
| Cancer | Usually shorter; BUT telomerase reactivation makes them longer in tumor cells |
| Dyskeratosis congenita | Very short (genetic telomere disorder) |
| Idiopathic pulmonary fibrosis | Short |
| Aplastic anemia | Short |

---

## 7. Telomere Length Measurement Methods

### 7.1 Terminal Restriction Fragment (TRF) — Southern Blot

```
Method:
  1. Extract genomic DNA
  2. Digest with restriction enzymes (cuts non-telomeric DNA)
  3. Gel electrophoresis (separates fragments by size)
  4. Southern blot with telomere-specific probe
  5. Measure smear distribution → mean TRF length

Resolution: ~1 kb
Throughput: Low (days per batch)
Input: 1-3 μg DNA
Output: Mean telomere length for entire cell population
Limitation: Includes subtelomeric DNA (overestimates by ~2-4 kb)
```

### 7.2 Quantitative PCR (qPCR)

```
Method:
  1. Design primers for telomere repeats (T) and single-copy gene (S)
  2. Run qPCR for both
  3. T/S ratio = relative telomere length

Resolution: Relative (not absolute)
Throughput: High (96-384 samples per run)
Input: 10-50 ng DNA
Output: T/S ratio (compared to reference sample)
Limitation: Cannot measure individual chromosomes
```

### 7.3 Q-FISH (Quantitative Fluorescence In Situ Hybridisation) ← THIS IS "TELOMERE BY PHOTO"

```
Method:
  1. Prepare metaphase chromosome spreads on glass slides
  2. Denature DNA (heat + formamide)
  3. Hybridise with fluorescent PNA probe: Cy3-(CCCTAA)₃
     (complementary to TTAGGG repeat)
  4. Wash off unbound probe
  5. Counterstain chromosomes with DAPI (blue)
  6. Image under fluorescence microscope
  7. SOFTWARE ANALYSIS:
     - Segment individual chromosomes from DAPI channel
     - Measure telomere fluorescence intensity at each chromosome end
     - Convert intensity → telomere length (using calibration curve)

Resolution: Individual chromosome arms (all 92 telomeres per cell)
Throughput: Medium (10-50 cells per sample)
Input: Cells (lymphocytes, fibroblasts)
Output: Telomere length per chromosome arm per cell
```

**This is what "DNA telomere by photo" means** — analysing fluorescence
microscopy images to quantify telomere length at each chromosome end.

### 7.4 Flow-FISH

```
Method:
  Same principle as Q-FISH but on single cells in suspension
  Measured by flow cytometer instead of microscope

Resolution: Per-cell (not per-chromosome)
Throughput: High (thousands of cells per sample)
Input: Cells in suspension
Output: Mean telomere fluorescence per cell
```

### 7.5 Computational (from WGS/WES data)

```
Method:
  Count TTAGGG repeat-containing reads in BAM/FASTQ
  Normalise by genome coverage
  Estimate total telomeric DNA content

Tools: TelomereHunter, Telomerecat, computel, TelSeq
Resolution: Whole-genome average
Throughput: Depends on sequencing
Input: BAM or FASTQ files
Output: Estimated telomere length in bp
```

---

## 8. Telomere Analysis by Photo (Q-FISH / Microscopy)

### The Image

A typical Q-FISH microscopy image has:

```
┌──────────────────────────────────────────────────┐
│                                                  │
│  Blue channel (DAPI):                            │
│    Shows chromosome bodies as blue shapes         │
│    46 chromosomes per metaphase spread            │
│                                                  │
│  Red/Green channel (Cy3 or FITC):                │
│    Shows telomere signals as bright dots           │
│    at the ends of each chromosome                 │
│    92 telomere spots per cell                     │
│    Brighter = longer telomere                     │
│                                                  │
│        ┌───┐         ┌───┐                       │
│        │   │ •     • │   │    • = telomere spot   │
│        │   │         │   │    █ = chromosome body  │
│        │   │ •     • │   │                        │
│        └───┘         └───┘                        │
│                                                  │
│  Merge: Blue chromosomes with red telomere dots   │
└──────────────────────────────────────────────────┘
```

### Image Specifications

| Parameter | Typical Value |
|-----------|---------------|
| Format | TIFF (16-bit), CZI (Zeiss), ND2 (Nikon), LIF (Leica) |
| Channels | 2-3 (DAPI, Cy3/FITC, optional brightfield) |
| Resolution | 1024×1024 to 2048×2048 pixels |
| Pixel size | 0.065-0.13 μm/pixel (63× or 100× objective) |
| Bit depth | 16-bit (0-65535 intensity range) |
| Z-stacks | Optional (3-10 focal planes, 0.2-0.5 μm spacing) |
| File size | 10-100 MB per image |
| Samples per study | 10-50 cells per patient, 20-100 patients |

### What the Analysis Software Must Do

```
Input: Multi-channel fluorescence microscopy image

Step 1: CHROMOSOME SEGMENTATION (from DAPI channel)
  - Threshold or ML-based segmentation of blue channel
  - Separate touching chromosomes (watershed algorithm)
  - Identify individual chromosomes (46 per cell)
  - Optionally: karyotype (classify chromosome 1-22, X, Y)

Step 2: TELOMERE SPOT DETECTION (from Cy3/FITC channel)
  - Detect bright spots (telomere signals) in red/green channel
  - Methods: Laplacian of Gaussian, local maxima, template matching
  - Typically 50-200 spots per cell (including noise)
  - Filter by size, circularity, and minimum intensity

Step 3: TELOMERE-CHROMOSOME ASSOCIATION
  - Assign each telomere spot to a chromosome
  - Must be at the END of a chromosome (within ~5 pixels)
  - Each chromosome should have 2 telomere spots (p-arm and q-arm)
  - Handle: missing spots, extra spots (noise), overlapping chromosomes

Step 4: INTENSITY QUANTIFICATION
  - For each telomere spot, measure integrated fluorescence intensity
  - Methods:
    a. Sum of pixel intensities in a circular ROI around spot center
    b. Gaussian fit to the spot → amplitude × area
    c. Total intensity above local background
  - Subtract local background (annular region around spot)
  - Correct for photobleaching (if time-series)

Step 5: CALIBRATION (intensity → base pairs)
  - Use reference cells with known telomere length
  - Or use fluorescent beads with known intensity
  - Linear regression: length_bp = a × intensity + b
  - Typical range: 2,000-20,000 bp

Step 6: STATISTICAL OUTPUT
  - Per cell: mean, median, min, max telomere length
  - Per chromosome arm (if karyotyped): individual telomere lengths
  - Per sample: distribution, percentiles, short telomere percentage
  - Visualisation: scatter plots, histograms, heatmaps
```

---

## 9. Image Processing Pipeline for Telomere Photos

### 9.1 Preprocessing

```python
# Load multi-channel image
import tifffile
img = tifffile.imread("metaphase_001.tif")  # shape: (channels, Y, X) or (Z, C, Y, X)
dapi = img[0]    # Blue channel (chromosomes)
cy3  = img[1]    # Red channel (telomeres)

# Background subtraction
from skimage.morphology import white_tophat, disk
dapi_clean = white_tophat(dapi, disk(50))

# Gaussian blur for denoising
from skimage.filters import gaussian
dapi_smooth = gaussian(dapi_clean, sigma=1.0)
cy3_smooth  = gaussian(cy3, sigma=0.8)
```

### 9.2 Chromosome Segmentation

```python
from skimage.filters import threshold_otsu
from skimage.morphology import remove_small_objects, binary_fill_holes
from skimage.segmentation import watershed
from skimage.measure import label, regionprops
from scipy.ndimage import distance_transform_edt

# Otsu threshold
thresh = threshold_otsu(dapi_smooth)
binary = dapi_smooth > thresh
binary = binary_fill_holes(binary)
binary = remove_small_objects(binary, min_size=500)

# Watershed to separate touching chromosomes
distance = distance_transform_edt(binary)
from skimage.feature import peak_local_max
local_max = peak_local_max(distance, min_distance=20, labels=binary)
markers = label(local_max)  # simplified
labels = watershed(-distance, markers, mask=binary)

# Get chromosome regions
chromosomes = regionprops(labels, intensity_image=dapi)
# Each region has: centroid, area, bbox, major_axis_length, orientation
```

### 9.3 Telomere Spot Detection

```python
from skimage.feature import blob_log
import numpy as np

# Laplacian of Gaussian blob detection
blobs = blob_log(
    cy3_smooth,
    min_sigma=1,
    max_sigma=5,
    num_sigma=10,
    threshold=0.05,
)
# blobs: array of (y, x, sigma) — one row per detected spot

# Filter by intensity
telomere_spots = []
for y, x, sigma in blobs:
    r = int(np.ceil(sigma * np.sqrt(2)))
    patch = cy3[max(0,int(y)-r):int(y)+r+1, max(0,int(x)-r):int(x)+r+1]
    intensity = patch.sum()
    if intensity > min_intensity_threshold:
        telomere_spots.append({
            "y": y, "x": x, "sigma": sigma,
            "intensity": intensity,
        })
```

### 9.4 Telomere-Chromosome Association

```python
from scipy.spatial import cKDTree

# Get chromosome endpoints (tips of each chromosome)
chromosome_tips = []
for region in chromosomes:
    # Find the two endpoints of each elongated chromosome
    # Using skeleton or major axis endpoints
    coords = region.coords  # (N, 2) array of pixel coordinates
    # Find the two most distant points (chromosome ends)
    from scipy.spatial.distance import pdist, squareform
    D = squareform(pdist(coords))
    i, j = np.unravel_index(D.argmax(), D.shape)
    tip1 = coords[i]
    tip2 = coords[j]
    chromosome_tips.append({
        "label": region.label,
        "tip_p": tip1,   # p-arm telomere location
        "tip_q": tip2,   # q-arm telomere location
    })

# Match telomere spots to nearest chromosome tip
tip_coords = []
tip_labels = []
for ct in chromosome_tips:
    tip_coords.append(ct["tip_p"])
    tip_labels.append((ct["label"], "p"))
    tip_coords.append(ct["tip_q"])
    tip_labels.append((ct["label"], "q"))

tree = cKDTree(tip_coords)
for spot in telomere_spots:
    dist, idx = tree.query([spot["y"], spot["x"]])
    if dist < max_association_distance:  # e.g., 10 pixels
        spot["chromosome"] = tip_labels[idx][0]
        spot["arm"] = tip_labels[idx][1]
```

### 9.5 Intensity Quantification

```python
def measure_telomere_intensity(image, y, x, radius=5, bg_inner=7, bg_outer=12):
    """Measure telomere fluorescence with local background subtraction."""
    Y, X = np.ogrid[-bg_outer:bg_outer+1, -bg_outer:bg_outer+1]
    dist = np.sqrt(Y**2 + X**2)

    # Signal mask (circle of given radius)
    signal_mask = dist <= radius

    # Background mask (annulus)
    bg_mask = (dist >= bg_inner) & (dist <= bg_outer)

    yi, xi = int(round(y)), int(round(x))
    patch = image[yi-bg_outer:yi+bg_outer+1, xi-bg_outer:xi+bg_outer+1].astype(float)

    if patch.shape != signal_mask.shape:
        return None  # Edge of image

    signal = patch[signal_mask].sum()
    bg_per_pixel = patch[bg_mask].mean()
    bg_total = bg_per_pixel * signal_mask.sum()

    return max(signal - bg_total, 0)
```

### 9.6 Calibration

```python
# Known reference: L5178Y-S cells (mouse lymphoma) have ~80 kb telomeres
# Known reference: L5178Y-R cells have ~10 kb telomeres
# Fluorescent beads: Invitrogen MESF beads

def calibrate(reference_intensities, reference_lengths_bp):
    """Fit linear calibration: length = slope * intensity + intercept."""
    from numpy.polynomial import polynomial as P
    coeffs = P.polyfit(reference_intensities, reference_lengths_bp, deg=1)
    # coeffs[0] = intercept, coeffs[1] = slope
    return lambda intensity: coeffs[0] + coeffs[1] * intensity

# Example:
calibration = calibrate(
    reference_intensities=[5000, 50000],   # arbitrary fluorescence units
    reference_lengths_bp=[10000, 80000],    # known lengths
)

for spot in telomere_spots:
    spot["length_bp"] = calibration(spot["intensity"])
```

---

## 10. Computational Telomere Length from Sequencing Data

### 10.1 From FASTQ/BAM (Whole Genome Sequencing)

```python
# Count reads containing telomere repeats
import pysam
import re

TELOMERE_PATTERN = re.compile(r"(TTAGGG){3,}|(CCCTAA){3,}")

def count_telomere_reads(bam_path):
    """Count reads with ≥3 consecutive TTAGGG or CCCTAA repeats."""
    total_reads = 0
    telomere_reads = 0

    with pysam.AlignmentFile(bam_path, "rb") as bam:
        for read in bam.fetch():
            total_reads += 1
            if read.query_sequence and TELOMERE_PATTERN.search(read.query_sequence):
                telomere_reads += 1

    # Normalise by total reads to get telomere content
    telomere_fraction = telomere_reads / total_reads if total_reads else 0

    # Estimate length: fraction × genome_size / (92 telomeres × 2 strands)
    genome_size = 3.2e9  # bp
    estimated_total_telomeric_bp = telomere_fraction * genome_size
    mean_telomere_length = estimated_total_telomeric_bp / 184  # 92 telomeres × 2 ends

    return {
        "total_reads": total_reads,
        "telomere_reads": telomere_reads,
        "telomere_fraction": telomere_fraction,
        "estimated_mean_length_bp": mean_telomere_length,
    }
```

### 10.2 Existing Tools

| Tool | Input | Method | Output |
|------|-------|--------|--------|
| **TelomereHunter** | BAM | Counts TTAGGG reads, GC-correction | Per-arm estimates |
| **Telomerecat** | BAM | Read pair analysis | Length distribution |
| **computel** | BAM/FASTQ | K-mer counting | Mean length |
| **TelSeq** | BAM | Read proportion method | Mean length |
| **Telomere-to-Telomere (T2T)** | Long reads | Full assembly of telomeres | Exact sequence |

---

## 11. Python Libraries & Tools

### Bioinformatics Core

| Library | Purpose | Install |
|---------|---------|---------|
| **Biopython** | FASTA/FASTQ/GenBank parsing, sequence analysis | `pip install biopython` |
| **pysam** | BAM/SAM/VCF reading (wraps htslib) | `pip install pysam` |
| **pybedtools** | BED file operations | `pip install pybedtools` |
| **pyvcf3** | VCF parsing | `pip install pyvcf3` |
| **HTSeq** | High-throughput sequencing analysis | `pip install HTSeq` |

### Image Analysis (for telomere photos)

| Library | Purpose | Install |
|---------|---------|---------|
| **scikit-image** | Image segmentation, blob detection, filters | `pip install scikit-image` |
| **OpenCV** | Image I/O, contours, watershedding | `pip install opencv-python` |
| **tifffile** | Read multi-channel TIFF microscopy images | `pip install tifffile` |
| **aicsimageio** | Read CZI, ND2, LIF microscopy formats | `pip install aicsimageio` |
| **cellpose** | Deep learning cell/nucleus segmentation | `pip install cellpose` |
| **stardist** | Star-convex polygon nucleus detection | `pip install stardist` |
| **napari** | Interactive image viewer (3D, multi-channel) | `pip install napari` |

### Machine Learning / Deep Learning

| Library | Purpose | Install |
|---------|---------|---------|
| **PyTorch** | CNN for chromosome segmentation | `pip install torch` |
| **TensorFlow** | Alternative DL framework | `pip install tensorflow` |
| **segmentation-models-pytorch** | U-Net, FPN for image segmentation | `pip install segmentation-models-pytorch` |
| **albumentations** | Image augmentation for training | `pip install albumentations` |

### Data Analysis & Visualisation

| Library | Purpose | Install |
|---------|---------|---------|
| **pandas** | Tabular data manipulation | `pip install pandas` |
| **numpy** | Numerical computing | `pip install numpy` |
| **matplotlib** | Plotting | `pip install matplotlib` |
| **seaborn** | Statistical visualisations | `pip install seaborn` |
| **plotly** | Interactive charts | `pip install plotly` |
| **scipy** | Statistics, spatial analysis | `pip install scipy` |

### Existing Telomere Software (non-Python)

| Tool | Language | Method |
|------|----------|--------|
| **TFL-TeloV2** | ImageJ/Fiji macro | Q-FISH telomere quantification |
| **Telometer** | Java | Automated telomere measurement |
| **DART** | MATLAB | Digital Analysis of Telomere length |
| **TeloView** | Java | 3D telomere analysis |

---

## 12. Project Architecture (Proposed)

```
gene_sequencing/
├── README.md
├── pyproject.toml
├── requirements.txt
│
├── data/                          # Sample data & references
│   ├── reference/                 # Reference genome files
│   │   └── telomere_regions.bed   # Known telomere coordinates
│   ├── sample_images/             # Q-FISH microscopy test images
│   └── sample_sequences/          # FASTQ/BAM test files
│
├── src/
│   ├── __init__.py
│   │
│   ├── sequencing/                # Gene sequencing pipeline
│   │   ├── __init__.py
│   │   ├── qc.py                  # FastQC wrapper, adapter trimming
│   │   ├── alignment.py           # BWA-MEM2 / minimap2 alignment
│   │   ├── variant_calling.py     # GATK HaplotypeCaller wrapper
│   │   ├── annotation.py          # VEP / snpEff annotation
│   │   └── parsers.py             # FASTA/FASTQ/VCF/BAM parsers
│   │
│   ├── telomere/                  # Telomere analysis
│   │   ├── __init__.py
│   │   ├── from_sequencing.py     # Telomere length from BAM/FASTQ
│   │   ├── from_image.py          # Telomere length from Q-FISH photos
│   │   ├── segmentation.py        # Chromosome segmentation (DAPI)
│   │   ├── spot_detection.py      # Telomere spot detection (Cy3)
│   │   ├── quantification.py      # Intensity measurement + calibration
│   │   ├── association.py         # Map spots to chromosome tips
│   │   └── models/                # ML models for segmentation
│   │       ├── chromosome_unet.py
│   │       └── telomere_detector.py
│   │
│   ├── analysis/                  # Statistical analysis
│   │   ├── __init__.py
│   │   ├── statistics.py          # Telomere length statistics
│   │   ├── aging.py               # Age-telomere correlation
│   │   └── comparison.py          # Case vs control comparisons
│   │
│   └── visualisation/             # Plotting & reports
│       ├── __init__.py
│       ├── plots.py               # Histograms, scatter, heatmaps
│       ├── karyogram.py           # Chromosome ideogram with telomere lengths
│       └── report.py              # HTML/PDF report generation
│
├── notebooks/                     # Jupyter notebooks for exploration
│   ├── 01_data_exploration.ipynb
│   ├── 02_image_segmentation.ipynb
│   ├── 03_telomere_quantification.ipynb
│   └── 04_sequencing_pipeline.ipynb
│
├── tests/
│   ├── test_segmentation.py
│   ├── test_spot_detection.py
│   ├── test_quantification.py
│   └── test_parsers.py
│
├── configs/
│   ├── pipeline.yaml              # Pipeline configuration
│   └── calibration.yaml           # Telomere intensity calibration
│
└── scripts/
    ├── run_pipeline.py            # CLI entry point
    ├── process_images.py          # Batch process Q-FISH images
    └── estimate_telomere.py       # Estimate from BAM files
```

---

## 13. Key Algorithms

### 13.1 Otsu Thresholding (Chromosome Segmentation)

Automatically finds the intensity threshold that minimises within-class
variance between foreground (chromosomes) and background.

```
Histogram of DAPI intensities:

Count
  │  ████
  │  ██████
  │  ████████       ████
  │  ██████████   ██████
  │  ████████████████████
  └──────────────────────── Intensity
     background    ↑    chromosomes
                 Otsu
                threshold
```

### 13.2 Watershed (Separating Touching Chromosomes)

```
Distance transform of binary mask:
  ┌─────────────┐
  │ 1 2 3 2 1 0 │  ← distance from edge
  │ 1 2 3 3 2 1 │
  │ 0 1 2 2 1 0 │  ← valley between two touching chromosomes
  │ 1 2 3 3 2 1 │
  │ 1 2 3 2 1 0 │
  └─────────────┘

Watershed treats this as a topographic surface and "floods" from the peaks
(chromosome centers) to separate at the valley (contact point).
```

### 13.3 Laplacian of Gaussian (Telomere Spot Detection)

```
Detects bright spots of a specific size (sigma) in an image.
At the correct sigma, the LoG response is maximised.

LoG(x,y) = -(1/(πσ⁴)) × [1 - (x²+y²)/(2σ²)] × e^(-(x²+y²)/(2σ²))

Process:
  1. Convolve image with LoG kernels at multiple scales (sigma values)
  2. Find local maxima in scale-space (x, y, sigma)
  3. Each maximum = one detected spot
  4. sigma indicates spot size
```

### 13.4 T/S Ratio (qPCR Telomere Length)

```
T/S = 2^(-ΔCt)

where ΔCt = Ct_telomere - Ct_single_copy_gene

Ct = cycle threshold (PCR cycle where fluorescence crosses threshold)
T = telomere primers (TTAGGG repeats)
S = single-copy gene primers (e.g., 36B4, albumin)

Interpretation:
  T/S = 1.0 → same telomere content as reference
  T/S = 1.5 → 50% more telomeric DNA
  T/S = 0.5 → 50% less telomeric DNA
```

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **Base pair (bp)** | A pair of complementary bases (A-T or G-C) in double-stranded DNA |
| **Read** | A single sequenced DNA fragment (75-4,000,000 bp depending on technology) |
| **Coverage / Depth** | Average number of reads covering each base position (30× WGS = standard) |
| **Phred quality score** | Q = -10 × log₁₀(P_error); Q30 = 1 in 1000 error rate |
| **Alignment** | Mapping a read to its position in the reference genome |
| **Variant** | Any position where the sample differs from the reference |
| **SNP** | Single Nucleotide Polymorphism (one base change) |
| **Indel** | Insertion or deletion of 1+ bases |
| **Structural variant** | Large genomic rearrangement (>50 bp) |
| **Allele frequency** | Proportion of chromosomes carrying a variant |
| **Heterozygous** | Two different alleles at a locus (e.g., A/G) |
| **Homozygous** | Two identical alleles at a locus (e.g., A/A) |
| **Exon** | Coding region of a gene (translated to protein) |
| **Intron** | Non-coding region between exons (spliced out of mRNA) |
| **Metaphase spread** | Chromosomes arrested at metaphase, spread on a glass slide for imaging |
| **DAPI** | 4',6-diamidino-2-phenylindole — blue fluorescent DNA stain |
| **Cy3** | Cyanine 3 — orange/red fluorescent dye used for telomere probes |
| **FITC** | Fluorescein isothiocyanate — green fluorescent dye |
| **PNA probe** | Peptide nucleic acid probe (binds telomere repeats with high affinity) |
| **Q-FISH** | Quantitative Fluorescence In Situ Hybridisation |
| **FISH** | Fluorescence In Situ Hybridisation (general technique) |
| **Karyotype** | Classification of chromosomes by size, shape, and banding pattern |
| **T-loop** | Lasso-like structure at telomere ends (3' overhang tucks into double-stranded region) |
| **Shelterin** | Six-protein complex that protects and regulates telomeres |
| **hTERT** | Human telomerase reverse transcriptase (catalytic subunit) |
| **Hayflick limit** | Maximum number of cell divisions before senescence (~50-70) |
| **Senescence** | Permanent cell cycle arrest triggered by short telomeres or DNA damage |

---

## 15. Internet Research Findings (April 2026)

### 15.1 Existing Open-Source Telomere Repositories on GitHub

The landscape for telomere-by-photo (qFISH) Python tools is **extremely sparse**.
Only ~8 public repos exist on GitHub with the `telomere-length` topic.
There is **no comprehensive Python-based qFISH analysis tool** — this is an
open niche.

| Repository | Stars | Language | What It Does |
|-----------|-------|----------|--------------|
| **[Adamtaranto/teloclip](https://github.com/Adamtaranto/teloclip)** | 50 | Python | Recovers unassembled telomeres from soft-clipped read alignments in BAM files. Sequence-based, not image-based. |
| **[jaeyoungchoilab/Topsicle](https://github.com/jaeyoungchoilab/Topsicle)** | 20 | Python | Estimates telomere length from long reads (Nanopore/PacBio) using k-mer abundance of telomere pattern. |
| **[vgl-hub/teloscope](https://github.com/vgl-hub/teloscope)** | 13 | C++ | Comprehensive telomere annotation for genome assemblies and graphs. |
| **[NicolasH2/TeloScope](https://github.com/NicolasH2/TeloScope)** | 0 | ImageJ Macro | **qFISH telomere length from microscopy images** — closest to our goal, but it's an ImageJ/Fiji macro, NOT Python. Requires BioVoxxel plugin. Windows 10 only. |
| **[acayuelalopez/3DTelomereRoiAnalysis](https://github.com/acayuelalopez/3DTelomereRoiAnalysis)** | 0 | Groovy | 3D confocal microscopy telomere quantification in liver tissue. Uses Cellpose for segmentation + Fiji Groovy scripts for quantification. |
| **[romanlupashin-source/DNA-Telomere-Length-Simulation](https://github.com/romanlupashin-source/DNA-Telomere-Length-Simulation)** | 0 | Python | Simple simulation — generates synthetic DNA with TTAGGG repeats and estimates biological age. Educational, not real analysis. |

**Key insight**: No Python-native qFISH telomere analysis tool exists.
The only image-based tools are ImageJ macros (TeloScope) or Groovy/Java
scripts (3DTelomereRoiAnalysis). Our project would be **the first
comprehensive Python pipeline for telomere-by-photo analysis**.

### 15.2 TeloScope (ImageJ Macro) — Closest Prior Art

The NicolasH2/TeloScope macro is the closest existing tool to what we want
to build. Key details from its documentation:

```
Workflow:
  1. User opens Fiji (ImageJ) and drags TeloScope.ijm into it
  2. Selects a folder of microscopy images
  3. For first 5 images, user manually sets:
     - Which channel = telomere foci, which = background (nucleus)
     - How big the foci are (draws a circle over a telomere)
     - Background threshold
     - Telomere sensitivity level
  4. For each image, user draws a background correction area
  5. Output: one CSV per image with per-telomere measurements

Output columns:
  - Label: image name + cell ID
  - Area: telomere area (should be consistent; outliers = artifacts)
  - IntDen: integrated density = intensity measurement for that telomere
  - RawIntDen: raw integrated density (before correction)

Requires: Fiji + BioVoxxel plugin
Only tested on: Windows 10
```

**What we can improve over TeloScope**:
- Pure Python (cross-platform, scriptable, automatable)
- No manual interaction required (fully automated pipeline)
- Deep learning segmentation (Cellpose) instead of manual thresholding
- Batch processing without user intervention
- Statistical analysis and reporting built-in
- Calibration system for intensity → base pairs conversion

### 15.3 3DTelomereRoiAnalysis — Cellpose for Telomere Segmentation

The acayuelalopez/3DTelomereRoiAnalysis project validates our approach:

```
Pipeline (Groovy/Fiji):
  1. Preprocessing: apply manually curated ROIs to z-stacks,
     remove background outside crypt regions
  2. Segmentation: Cellpose 3D models to segment:
     - Nuclei from DAPI channel
     - Telomeres (TRF1 stained) from telomere channel
  3. Quantification per nucleus:
     - Number of telomeres
     - Mean/sum intensity
     - Foci stratified by intensity percentiles
  4. Quantification per telomere object:
     - Intensity, volume, spatial association with nuclei

Key libraries used: Fiji, MCIB3D, Cellpose, Java 8+
```

**Confirms**: Cellpose works well for both nucleus AND telomere segmentation
in fluorescence microscopy. We should use it.

### 15.4 Cellpose — Deep Learning Segmentation (2.1k Stars)

**Cellpose** (MouseLand/cellpose) is the leading tool for cell/nucleus
segmentation in microscopy images.

```
Key facts:
  - 2,100+ stars, 599 forks on GitHub
  - Latest: Cellpose-SAM (April 2025) — "superhuman generalization
    for cellular segmentation"
  - Pre-trained models: cyto, cyto2, cyto3, nuclei
  - Works on: fluorescence, brightfield, phase contrast
  - Install: pip install cellpose
  - GPU support: optional (CUDA)
  - GUI available: cellpose --gui
  - API: from cellpose import models; model = models.Cellpose(model_type='nuclei')

Usage for our project:
  - model_type='nuclei' → segment DAPI-stained chromosomes/nuclei
  - Can fine-tune on chromosome metaphase spreads if needed
  - Returns: masks (labeled image), flows, styles
```

### 15.5 scikit-image Blob Detection — Key for Telomere Spots

Three blob detection algorithms available in `skimage.feature`:

```python
from skimage.feature import blob_log, blob_dog, blob_doh

# Laplacian of Gaussian (LoG) — BEST for telomere spots
#   Most accurate, slowest
#   Computes LoG at multiple sigma values, finds local maxima in scale-space
blobs_log = blob_log(image, min_sigma=1, max_sigma=5, threshold=0.05)

# Difference of Gaussian (DoG) — FAST approximation of LoG
#   Faster, nearly as accurate
blobs_dog = blob_dog(image, min_sigma=1, max_sigma=5, threshold=0.05)

# Determinant of Hessian (DoH) — FASTEST
#   Uses box filters, independent of blob size
#   BUT: inaccurate for small blobs (<3 pixels)
blobs_doh = blob_doh(image, min_sigma=1, max_sigma=5, threshold=0.01)

# All return: array of (y, x, sigma)
# sigma * sqrt(2) = approximate radius in pixels
```

**Recommendation**: Use `blob_log` for accuracy, fall back to `blob_dog`
for large images where speed matters. Telomere spots are typically
2-8 pixels in diameter.

### 15.6 scikit-image Version & Compatibility

```
Current version: scikit-image 0.26.0 (released Dec 20, 2025)
Requires: Python >= 3.11
License: BSD
Key modules for our project:
  - skimage.feature: blob_log, blob_dog, blob_doh, peak_local_max
  - skimage.filters: threshold_otsu, gaussian
  - skimage.segmentation: watershed
  - skimage.morphology: remove_small_objects, binary_fill_holes, disk
  - skimage.measure: label, regionprops
  - skimage.color: rgb2gray
```

### 15.7 Gap Analysis — What's Missing in the Ecosystem

```
EXISTING (available):
  ✓ Cellpose — nucleus/cell segmentation (Python, pip install)
  ✓ scikit-image — blob detection, watershed, thresholding (Python)
  ✓ tifffile — read microscopy TIFF images (Python)
  ✓ TeloScope — qFISH analysis (ImageJ macro, manual, Windows only)
  ✓ teloclip / Topsicle — sequence-based telomere analysis (Python)

MISSING (our opportunity):
  ✗ Python-native automated qFISH pipeline (end-to-end)
  ✗ Deep learning telomere spot detector (trained on qFISH data)
  ✗ Automated chromosome tip finding + telomere association
  ✗ Intensity-to-bp calibration system in Python
  ✗ Batch processing of hundreds of images without user interaction
  ✗ Statistical analysis + HTML report generation
  ✗ Synthetic test data generator (for testing without real microscopy images)
  ✗ Web UI for uploading and analysing images
```

### 15.8 Recommended Technology Stack (Updated)

Based on internet research, here's the refined technology stack:

```
Core Image Analysis:
  - cellpose >= 3.0       (nucleus/chromosome segmentation)
  - scikit-image >= 0.26  (blob detection, morphology, filters)
  - opencv-python >= 4.8  (image I/O, contours, drawing)
  - tifffile >= 2024.1    (microscopy TIFF I/O)
  - scipy >= 1.11         (spatial analysis, KDTree, statistics)

Sequence Analysis (optional module):
  - biopython >= 1.83     (FASTA/FASTQ parsing)
  - pysam >= 0.22         (BAM/SAM reading)

Data & Visualization:
  - numpy >= 1.26
  - pandas >= 2.1
  - matplotlib >= 3.8
  - seaborn >= 0.13
  - plotly >= 5.18        (interactive charts)

Testing:
  - pytest >= 8.0
  - pytest-cov

CLI:
  - click >= 8.1          (command-line interface)
  - rich >= 13.0          (pretty terminal output)
```

---

*This document provides the foundational knowledge for building a gene
sequencing and telomere analysis platform. Internet research confirms
there is NO existing Python-native qFISH telomere analysis tool — our
project fills a genuine gap in the open-source ecosystem.*
