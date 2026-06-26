# Automated Wafer Numbering System (ver. 1.9.0)

An layout post-processing pipeline designed to inject unique serialized IDs into designs on integrated wafers. Powered entirely by the KLayout (pya) C++ geometry engine to eliminate legacy gdspy parsing bugs, this architecture utilizes Layer 100 geometries as spatial localization and identification anchors to trace, track, and execute a localized purge of legacy indicator marks with domain-level accuracy 
The system features multi-mode geometric serialization, sorting dense arrays via traditional Cartesian binning or a radial 12 o'clock clockwise spiral mapping. 
These computed coordinates undergo dynamic font translation, mapping serial IDs into 7-segment path polygons that scale automatically to localized cell dimensions.
---

## 🚀 Quick Start: Run Instantly on Google Colab (Recommended)

You can run the entire wafer layout processing stream directly in the cloud without configuring a local Python or EDA environment. 

### 1. Launch the Pipeline
Click the link below or load the script inside your Jupyter workspace:
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JiaHaoNCKU/Automated-Numbering-System/blob/main/ANS.ipynb)

### 2. Runtime Execution Flow
1. Configure Parameters : Modify target_cell_name or CHOSEN_SORT_MODE in the __main__ block if your design requires custom settings.

2. Run : Run the first cell to initialize the virtual machine and install the native klayout engine.

3. Upload GDS : Choose and upload your raw GDSII file (e.g., Probes_test.GDS) when the interactive prompt appears.

4. Auto-Process & Download : The pipeline clears legacy indicators, generates new serialized polygons, and automatically triggers a browser download for WAFER_numbered.gds.

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

## 🛠️ Monolithic Process Flow Architecture

The pipeline decouples raw geometric matrix computation from serialization mapping by bridging an intermediate hierarchical JSON layer:

[Master GDSII File]
│
▼ (Phase 1)
┌────────────────────────────────────────────────────────┐

│  CORE MODULE 1: Pure KLayout Extraction                

│  - Parses absolute vectors (inst.na/nb/a/b)            

│  - Dissolves 10,000µm array staggering limitations     

└────────────────────────────────────────────────────────┘

│

▼ [WAFER.json]

┌────────────────────────────────────────────────────────┐

│  CORE MODULE 2: Hybrid Cascaded Numbering Engine       

│  - Traces deep structural accumulative transforms      

│  - Multi-mode Sort: CARTESIAN (Binning) or RADIAL      

│  - Generates exact tilt/height-aligned 7-segment paths 

└────────────────────────────────────────────────────────┘

│

▼ [WAFER_numbered.json]

┌────────────────────────────────────────────────────────┐

│  CORE MODULE 3: GDSII Native Compilation               

│  - Spawns unique vector instances per probe index      

│  - Maps serial text strictly to Layer 100 Datatype 0   

│  - Executes native complex transforms (pya.DCplxTrans) 

└────────────────────────────────────────────────────────┘

│

▼ (Phase 4)
[WAFER_numbered.gds]


---

## 🔬 Target Production Mapping Specification
* **Text / Serial Insertion Boundary:** Routed strictly to **Layer 100, Datatype 0 (100/0)**.
* **Localized Purge:** Automatically scans for and erases old Layer 100 indicator rectangles (`O` marker cells) from individual probe cells without mutating other base fabrication arrays.
* **Dynamic Font Scaling:** Font heights are bound algorithmically to the target probe's bounding dimensions.
