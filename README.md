# Automated Wafer Numbering System (ver. 1.9.0)

An industrial-grade semiconductor layout post-processing pipeline designed to inject unique serialized IDs into multi-channel 3D neural probes on integrated wafers. Powered entirely by the **KLayout (`pya`) C++ geometry engine**, this architecture completely eliminates older `gdspy` parsing bugs, providing absolute precision for complex, staggered, or non-orthogonal micro-electromechanical systems (MEMS) arrays.

---

## 🚀 Quick Start: Run Instantly on Google Colab (Recommended)

You can run the entire wafer layout processing stream directly in the cloud without configuring a local Python or EDA environment. 

### 1. Launch the Pipeline
Click the link below or load the script inside your Jupyter workspace:
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com)

### 2. Runtime Execution Flow
1. **Initialize Environment:** Run **Step 0** to provision the cloud virtual machine and pull the native `klayout` package.
2. **Upload GDSII Layout:** The system will dynamically prompt an upload interface. Select your master raw wafer layout (e.g., `Circle_nubering_tet.GDS` or `Probes_test.GDS`).
3. **Automated Run:** The pipeline parses geometry boundaries, removes legacy indicators, calculates structural cascade orientations, and generates layout-aligned serial polygons.
4. **Dynamic Output Stream:** Once processing completes, your browser will automatically trigger a browser download for the compiled physical stream-out file: `WAFER_numbered.gds`.

---

## 🛠️ Monolithic Process Flow Architecture

The pipeline decouples raw geometric matrix computation from serialization mapping by bridging an intermediate hierarchical JSON layer:

[Master GDSII File]
│
▼ (Phase 1)
┌────────────────────────────────────────────────────────┐
│  CORE MODULE 1: Pure KLayout Extraction                │
│  - Parses absolute vectors (inst.na/nb/a/b)            │
│  - Dissolves 10,000µm array staggering limitations     │
└────────────────────────────────────────────────────────┘
│
▼ [WAFER.json]
┌────────────────────────────────────────────────────────┐
│  CORE MODULE 2: Hybrid Cascaded Numbering Engine       │
│  - Traces deep structural accumulative transforms      │
│  - Multi-mode Sort: CARTESIAN (Binning) or RADIAL     │
│  - Generates exact tilt/height-aligned 7-segment paths │
└────────────────────────────────────────────────────────┘
│
▼ [WAFER_numbered.json]
┌────────────────────────────────────────────────────────┐
│  CORE MODULE 3: GDSII Native Compilation               │
│  - Spawns unique vector instances per probe index      │
│  - Maps serial text strictly to Layer 100 Datatype 0   │
│  - Executes native complex transforms (pya.DCplxTrans) │
└────────────────────────────────────────────────────────┘
│
▼ (Phase 4)
[WAFER_numbered.gds]


---

## 💎 Key Upgrades over Legacy Frameworks

* **Pure KLayout Database Engine Integration:** Replaced the legacy `gdspy` parsing infrastructure. Complex array step vectors—such as the asymmetric $10,000\,\mu\text{m}$ Y-axis stagger found in advanced cable routings—are resolved natively with zero data loss or cell overlapping.
* **Database Unit (DBU) Domain Precision:** Coordinates are processed within KLayout's native integer DBU domain ($1\,\text{DBU} = 1\,\text{nm}$). This eliminates floating-point summation truncations, entirely preventing layout skips or chaotic row misalignments during Cartesian serialization.
* **Perfect Multi-Level Transformation Algebra:** Leverages native `pya.DCplxTrans` matrix multiplication for deep traversal parsing. This ensures that spatial orientations, scaling factors, and multi-level nested mirror states match the CAD layout identically, preventing inverted text or misplaced geometries.

---

## 🎛️ Control Panel Configurations

Global variables can be modified directly within the execution module block to match your specific cleanroom requirements:

| Parameter | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `target_cell_name` | String | `"WAFER"` | The root top-level cell identifier inside the GDS file. |
| `CHOSEN_SORT_MODE` | String | `"CARTESIAN"` | Sequencing logic: `"CARTESIAN"` (Top-to-Bottom, Left-to-Right) or `"RADIAL"` (12 o'clock clockwise spiral). |
| `WAFER_CENTER_COORDS`| Tuple | `(0.0, 0.0)` | Global origin reference point utilized during Polar/Radial mapping calculations. |
| `allowed_layers` | List | `[(11,0), (92,0), (81,0)...]`| Active lithography masks passed into memory during the data minimization phase. |

---

## 🔬 Target Production Mapping Specification
* **Text / Serial Insertion Boundary:** Routed strictly to **Layer 100, Datatype 0 (100/0)**.
* **Localized Purge:** Automatically scans for and erases old Layer 100 indicator rectangles (`O` marker cells) from individual probe cells without mutating other base fabrication arrays.
* **Dynamic Font Scaling:** Font heights are bound algorithmically to the target probe's bounding dimensions.

---
*For technical inquiries or pipeline adjustments, please review the latest ver. 1.9.0 architect
