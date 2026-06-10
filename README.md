# Wafer-Level Probe Automated Hybrid Numbering System

An automated toolchain for processing and serial-numbering wafer layouts. It uses **Layer 81** for probe type classification and replaces **Layer 100** placeholders with auto-scaled, angle-aligned physical polygon serial numbers directly inside the top-level `WAFER` cell.

---

## 🔄 Architecture & Workflow

The automated pipeline consists of three Python scripts working sequentially:

[-Step-1-]---------------------[-Step-2-]-------------------------------------[-Step-3-]

┌──────────────┐-WAFER.json-┌────────────────────────┐-WAFER_numbered.json-┌──────────────┐

│-Original-GDS-│-─────────►-│--Hybrid-Numbering-Core-│-──────────────────►-│-JSON-to-GDS--│-──►-Numbered-GDS
-
└──────────────┘------------└────────────────────────┘---------------------└──────────────┘
gds_to_json.py---------------probe_hybrid_numbering.py--------------------json_to_gds.py
(ver.-1.1.4)-----------------(ver.-1.0.9)---------------------------------(ver.1.3.2)


1. **`gds_to_json.py`**: Translates binary GDSII data into a structured, highly compatible JSON hierarchical tree dictionary.
2. **`probe_hybrid_numbering.py`**: The geometric solver core. It extracts deep nested layers, resolves orientation/scale matrices, flushes out old placeholders globally, and injects unique serial numbers into the `WAFER` cell.
3. **`json_to_gds.py`**: Reconstructs the modified JSON structure back into a standard physical GDSII file using the KLayout C++ core (`pya`).

---

## 📦 Script Detailed Specifications

### 1. `gds_to_json.py` (ver. 1.1.4)
* **Layer Whitelist**: Filters out >90% of layout data (dense routing, dummy fills) at source.
* **Big Matrix**: Aggregates all vertices of a layer into a single flat array, bypassing dictionary overhead to prevent `MemoryError`.
* **Namespace Prefix**: Automatically prefixes merged shapes with `{cell.name}` to eliminate cell name collisions during GDS reconstruction.

### 2. `probe_hybrid_numbering.py` (ver. 1.0.9)
* **Depth Recursive Sweep**: Traverses multi-level subcell branching to capture Layer 81 & 100 regardless of nesting depth.
* **Matrix Composition**: Accumulates grid array (AREF) transformations and original custom placeholder tilts, ensuring 100% accurate angle alignment and sizing.
* **Global Flush**: Erases Layer 100 shapes globally across all subcells to eliminate KLayout C++ cache pollution and stale artifacts.
* **Independent Numbering**: Groups probes by direct subcell variant name (e.g., `_v2`, `_v3`) and indexes them (1, 2, 3...) sorted top-to-bottom, left-to-right.

### 3. `json_to_gds.py` (ver. 1.3.2)
* **Dual-Format Support**: Handles both legacy singular `self_shape` and optimized `self_shapes` big matrix array lists.
* **Complex Transformations**: Maps orientation and scaling parameters seamlessly into KLayout `pya.DCplxTrans`.

---

## 🛠️ Data Structure Schema Changes

* **Legacy Format**:
    ```json
    "poly_81_0_0_instance": {
      "definition": { "name": "poly_81_0_0", "self_shape": [[x1, y1], [x2, y2], ...] },
      "instances": [{"origin": [0.0, 0.0], "rotation": 0.0}]
    }
    ```
* **Optimized Big Matrix Format (ver. 1.1.3+)**:
    ```json
    "CellName_merged_polys_81_0_instance": {
      "definition": {
        "name": "CellName_merged_polys_81_0",
        "self_shapes": [
          [[x1, y1], [x2, y2], ...],  // Polygon 1
          [[x5, y5], [x6, y6], ...]   // Polygon 2 (Stored in flat array)
        ]
      },
      "instances": [{"origin": [0.0, 0.0], "rotation": 0.0, "mirror": false, "magnification": 1.0}]
    }
    ```

---

## 🚀 Execution & Configuration

### 1. Prerequisites
Dependencies: `gdspy`, `klayout` (Python module `pya`), `numpy`, `matplotlib`.

### 2. Running the Pipeline
Execute the scripts in this exact order:
```bash
runfile('gds_to_json.py')           # Step 1: Parse & screen GDS to JSON
runfile('probe_hybrid_numbering.py') # Step 2: Purge placeholders & inject numbers
runfile('json_to_gds.py')           # Step 3: Rebuild JSON back to standard GDSII
```

### 3. Layer Configuration Maps
The system default layer whitelist is configured inside the gds_to_json.py main block:
allowed_layers = [(11, 0), (92, 0), (81, 0), (99, 0), (4, 0), (100, 0)]

Layer 81: Probe physical contour/boundary layer (used for height analysis and model classification).

Layer 100: Pre-tilted letter "O" placeholder layer.

Generated physical text polygons overwrite Layer 100:0 at the top level.


