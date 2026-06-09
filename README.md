# Wafer-Level Probe Automated Hybrid Numbering System

This system is an automated layout processing toolchain designed for integrated circuits and high-density neural probe wafer layouts. Utilizing a **Hybrid Positioning Method**, the toolchain recursively scans deep into the nested subcell hierarchy to automatically classify probe types using Layer 81 contours. It then targets Layer 100 "O" character placeholders, inversely solves their nested transformation matrices, and directly writes 100% height-matched and angle-aligned physical polygon serial numbers into the top-level `WAFER` cell.

Optimized with "Layer Whitelist Filtering" and a "Big Matrix" data structure encapsulation, this toolchain completely eliminates `MemoryError` when handling massive wafer-level layouts and reduces processing times to seconds.

---

## 🔄 Architecture & Workflow

The automated pipeline consists of three Python scripts working sequentially:

[ Step 1 ]                    [ Step 2 ]                    [ Step 3 ]
┌──────────────┐   WAFER.json  ┌────────────────────────┐  WAFER_numbered.json ┌──────────────┐
│ Original GDS │ ───────────► │  Hybrid Numbering Core │ ───────────────────► │ JSON to GDS  │ ──► Numbered GDS
└──────────────┘               └────────────────────────┘                      └──────────────┘
gds_to_json.py                 probe_hybrid_numbering.py                       json_to_gds.py
(ver. 1.1.4)                   (ver. 1.0.9)                                    (ver. 1.3.2)


1. **`gds_to_json.py`**: Translates binary GDSII data into a structured, highly compatible JSON hierarchical tree dictionary.
2. **`probe_hybrid_numbering.py`**: The geometric solver core. It extracts deep nested layers, resolves orientation/scale matrices, flushes out old placeholders globally, and injects unique serial numbers into the `WAFER` cell.
3. **`json_to_gds.py`**: Reconstructs the modified JSON structure back into a standard physical GDSII file using the KLayout C++ core (`pya`).

---

## 📦 Script Detailed Specifications

### 1. GDS to JSON Converter: `gds_to_json.py` (ver. 1.1.4)
* **Core Responsibility**: Layout format translation and structural serialization.
* **Key Optimizations**:
  * **Layer Whitelist Filtering (Allowed Layers)**: Directly filters out unrelated geometric layers (such as dense interconnects and dummy fills that constitute 90%+ of the GDS size) at the source stage, drastically minimizing memory footprint.
  * **Big Matrix Optimization**: Bypasses the old approach of fragmenting each polygon into millions of independent subcell dictionaries. It aggregates all vertices of a single layer into a single `self_shapes` matrix list, avoiding Python dictionary object allocation overhead and preventing `MemoryError`.
  * **Unique Namespace Prefixes**: Automatically prefixes merged polygon primitive names with their respective parent `{cell.name}`. This guarantees unique names globally and prevents KLayout from cross-contaminating subcells due to Name Collisions during layout reconstruction.

### 2. Hybrid Numbering Solver Core: `probe_hybrid_numbering.py` (ver. 1.0.9)
* **Core Responsibility**: Intelligent classification, geometric matrix composition, global placeholder purging, and top-level serial text generation.
* **Key Optimizations**:
  * **Depth Recursive Sweep**: Resolves deep multi-level subcell branching. No matter how deeply Layer 81 and Layer 100 are nested within grandchildren subcells (e.g., inside `17ch_ZIF`), they are caught successfully.
  * **Nested Transformation Matrix Composition**: Accumulates multi-layer grid array (AREF/CellArray) transformations along the recursive path. It uses inverse matrix operations to capture the true upright design height of the "O" placeholder and computes the combined global matrix (`final_rot`, `final_mirror`, `final_mag`). This ensures new numbers match the original custom tilt of the "O" placeholders precisely.
  * **Global Flush Mechanism**: Erases old Layer 100 shapes globally, regardless of whether a cell qualifies as a probe or fails matching. This cuts off KLayout's C++ internal geometry caching mechanism, neutralizing Cache Pollution and ensuring no old characters are stubbornly preserved.
  * **Model-Independent Serial Numbering**: Automatically extracts the direct subcell variant name (e.g., `_v2`, `_v3`) as an independent group, assigning separated 1, 2, 3... sequential serial numbers sorted from top-to-bottom and left-to-right.

### 3. JSON to GDS Layout Reconstructor: `json_to_gds.py` (ver. 1.3.2)
* **Core Responsibility**: Geometric instantiation, high-precision transformation matrix mapping, and binary GDSII export.
* **Key Optimizations**:
  * **Dual-Format Compatibility**: Fully backward-compatible with both the legacy singular `self_shape` format and the new ver. 1.1.3+ plural `self_shapes` big matrix optimization array list.
  * **Complex Coordinate Transformation**: Fully supports multi-parameter `pya.DCplxTrans` tracking, seamlessly executing mirror, rotation angle, and magnification adjustments.

---

## 🛠️ Data Structure Schema Changes

To achieve extreme performance leaps, the internal geometric polygon storage schema was upgraded. If you write custom extensions to parse the exported JSON files, please map fields according to the following specification:

* **Legacy Format (Segmented Subcells)**:
  ```json
  "poly_81_0_0_instance": {
    "definition": { "name": "poly_81_0_0", "self_shape": [[x1, y1], [x2, y2], ...] },
    "instances": [{"origin": [0.0, 0.0], "rotation": 0.0}]
  }
Optimized Big Matrix Format (ver. 1.1.3+):

JSON
"CellName_merged_polys_81_0_instance": {
  "definition": {
    "name": "CellName_merged_polys_81_0",
    "self_shapes": [
      [[x1, y1], [x2, y2], ...],  // Polygon 1
      [[x5, y5], [x6, y6], ...]   // Polygon 2 (Stored inside a flat layer array)
    ]
  },
  "instances": [{"origin": [0.0, 0.0], "rotation": 0.0, "mirror": false, "magnification": 1.0}]
}
🚀 Execution & Operational Steps
1. Prerequisites
Ensure your Python environment has the following libraries installed:

gdspy

klayout (Python module pya)

numpy

matplotlib

2. Running the Pipeline
Open your IDE (e.g., Spyder) or a terminal, and execute the scripts in the following exact order:

Bash
# Step 1: Export and screen layout data into custom JSON with a layer whitelist
runfile('gds_to_json.py')

# Step 2: Parse JSON, clear out old placeholders globally, solve tilt, and generate top-level serial numbers
runfile('probe_hybrid_numbering.py')

# Step 3: Rebuild the processed JSON structure back into standard GDSII
runfile('json_to_gds.py')
3. Layer Configuration Maps
The system default layer whitelist is configured inside the gds_to_json.py main block:
allowed_layers = [(11, 0), (92, 0), (81, 0), (99, 0), (4, 0), (100, 0)]

Layer 81: Probe physical contour/boundary layer (used for height analysis and model classification).

Layer 100: Pre-tilted letter "O" placeholder layer.

New physical alphanumeric polygon numbers generated by the toolchain will be written back to Layer 100:0, directly replacing the old placeholders in the output file.
