Automated Wafer Numbering System (ver. 2.0.5)
An layout pipeline designed to inject unique serialized IDs into designs on integrated wafers.
Powered entirely by the KLayout (pya) C++ geometry engine, this architecture utilizes Layer 100 geometries as spatial localization and identification anchors to trace, track, and execute a localized purge of legacy indicator marks with domain-level accuracy. The system features multi-mode geometric serialization, sorting dense arrays via Cartesian binning or radial 12 o'clock clockwise spiral mapping.
From version 2.0.5, computed coordinates undergo dynamic native vector font translation with an integrated zero-width cutline algorithm to preserve topological integrity (rendering perfect holes in characters like '0' or 'B'). Furthermore, it introduces complete string format customization via a dynamic Lambda function directly from the main block.
🚀 Quick Start: Run Instantly on Google Colab (Recommended)
You can run the entire wafer layout processing stream directly in the cloud without configuring a local Python or EDA environment.
1. Launch the Pipeline
Click the link below or load the script inside your Jupyter workspace:

2. Runtime Execution Flow
Configure Parameters: Modify CHOSEN_SORT_MODE or define your custom string format in NUMBERING_FORMAT_LAMBDA inside the __main__ block.
Initialize Environment: Run the initialization cell to mount the virtual machine environment and install the native klayout engine.
Upload GDS: Choose and upload your raw GDSII file (e.g., Probes_test.GDS) when the interactive prompt appears.
Auto-Process & Download: The pipeline clears legacy indicators, generates new serialized native vector polygons, and automatically triggers a browser download for WAFER_numbered.gds.
🎛️ Control Panel Configurations
Global variables can be modified directly within the execution module block to match your specific cleanroom requirements:
Parameter
Type
Default Value
Description
target_cell_name
String
"WAFER"
The root top-level cell identifier inside the GDS file.
CHOSEN_SORT_MODE
String
"RADIAL"
Sequencing logic: "CARTESIAN" (Top-to-Bottom, Left-to-Right) or "RADIAL" (12 o'clock clockwise spiral).
WAFER_CENTER_COORDS
Tuple
(0.0, 0.0)
Global origin reference point utilized during Polar/Radial mapping calculations.
NUMBERING_FORMAT_LAMBDA
Lambda
lambda sn: f"B-{sn:03d}"
[New in v2.0.5] Dynamic callback function allowing complete formatting customization (e.g., B001, A_001, 1).
allowed_layers
List
[(81,0), (100,0)]
Active lithography masks passed into memory during the data minimization phase.

🛠️ Monolithic Process Flow Architecture
The pipeline decouples raw geometric matrix computation from serialization mapping by bridging an intermediate hierarchical JSON layer:



[Master GDSII File]
│
▼ (Phase 1)
┌────────────────────────────────────────────────────────┐
│  CORE MODULE 1: Pure KLayout Extraction                │
│  - Parses absolute vectors (inst.na/nb/a/b)            │
│  - Extracts precise Layer 81 & Layer 100 coordinates   │
│  - Native Zero-width cutline logic preserves topology  │
└────────────────────────────────────────────────────────┘
│
▼ [WAFER.json]
┌────────────────────────────────────────────────────────┐
│  CORE MODULE 2: Hybrid Cascaded Numbering Engine       │
│  - Bottom-up validation ensures absolute stability     │
│  - Custom Lambda string format evaluation (v2.0.5)     │
│  - Decoupled Native KLayout Vector Font Generator      │
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


🔬 Target Production Mapping Specification
Text / Serial Insertion Boundary: Routed strictly to Layer 100, Datatype 0 (100/0).
Localized Purge: Automatically scans for and erases old Layer 100 indicator rectangles (O or 0 marker cells) from individual probe cells without mutating other base fabrication arrays.
Dynamic Font Scaling & Topology: Font heights are bound algorithmically to the target probe's bounding dimensions using KLayout's native vector engine supported by a zero-width cutline cascade algorithm for geometric integrity.
