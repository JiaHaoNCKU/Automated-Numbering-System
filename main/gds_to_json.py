# gds_to_json.py
# ver. 1.1.7
# [Modifications]: 
# - Updated gds_file_path to use the relative project path "../example/Probes_test.GDS".
# - Fixed a critical geometric bug: incorporated grid offsets fully into mirror and rotation matrix calculations for gdspy.CellArray (AREF).
# - Completely resolved severe drifting and misalignment issues of detailed components when reconstructing back to GDS for wafer-level array elements.
# - Maintained big matrix optimized structure, layer whitelist, progress indicator, and all legacy features.

import gdspy
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import os
import sys
import numpy as np
import json 
import math
from jsonIO import save_to_json, json_numpy_serializer, load_and_reconstruct_from_json 

def plot_gds_cell(file_path, cell_name, layers_to_plot=None, show_plot=True, output_png_filename=None, highlight_points=None):
    if not os.path.exists(file_path): 
        print(f"❌ Error: File does not exist '{file_path}'")
        return None 
    gds_lib = gdspy.GdsLibrary(infile=file_path)
    if cell_name not in gds_lib.cells: return None
    cell_to_plot = gds_lib.cells[cell_name]
    all_polygons = cell_to_plot.get_polygons(by_spec=True)
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_aspect('equal', adjustable='box')
    if all_polygons:
        for i, (spec_key, polygons) in enumerate(all_polygons.items()):
            layer, datatype = spec_key[0], spec_key[1]; layer_key = f"{layer}:{datatype}"
            if layers_to_plot is not None and layer_key not in layers_to_plot: continue 
            for points in polygons: 
                ax.add_patch(Polygon(points, closed=True, facecolor='blue', edgecolor='black', linewidth=0.5, alpha=0.7))
    bbox = cell_to_plot.get_bounding_box()
    if bbox is not None:
        ax.set_xlim(bbox[0][0], bbox[1][0]); ax.set_ylim(bbox[0][1], bbox[1][1])
    if output_png_filename: plt.savefig(output_png_filename, dpi=150)
    if show_plot: plt.show()
    return gds_lib

def export_cell_to_recursive_dict(cell, memo=None, layers_to_keep=None):
    if memo is None: memo = {}
    if cell.name in memo: return memo[cell.name]

    print(f"  ⏳ [Processing] Parsing cell geometry structure: {cell.name} ...")

    our_cell_def = { 
        "name": cell.name, 
        "self_shape": None, 
        "subcells": {} 
    }
    memo[cell.name] = our_cell_def
    
    polygons_by_spec = cell.get_polygons(by_spec=True, depth=0)
    for spec_key, polygons in polygons_by_spec.items():
        layer = spec_key[0]; datatype = spec_key[1]
        if layers_to_keep is not None and (layer, datatype) not in layers_to_keep:
            continue
        layer_key = f"{layer}_{datatype}" 
        if len(polygons) > 0:
            prim_name = f"{cell.name}_merged_polys_{layer_key}" 
            poly_prim_def = {
                'name': prim_name,
                'self_shapes': polygons,  
                'subcells': {},
                '_gds_layer': [layer, datatype] 
            }
            inst_name = f"{prim_name}_instance"
            our_cell_def['subcells'][inst_name] = {
                'definition': poly_prim_def,
                'instances': [{
                    'origin': np.array([0.0, 0.0]), 
                    'rotation': 0.0,
                    'mirror': False,
                    'magnification': 1.0
                }] 
            }

    for element in cell.references:
        if isinstance(element, (gdspy.CellReference, gdspy.CellArray)):
            ref_cell = element.ref_cell
            sub_def = export_cell_to_recursive_dict(ref_cell, memo, layers_to_keep)
            instances_list = []
            
            rot = element.rotation or 0.0
            mirror = bool(element.x_reflection)
            mag = float(element.magnification) if element.magnification else 1.0
            
            if isinstance(element, gdspy.CellReference):
                instances_list.append({
                    'origin': element.origin, 
                    'rotation': rot,
                    'mirror': mirror,
                    'magnification': mag
                })
            
            elif isinstance(element, gdspy.CellArray):
                origin = element.origin
                cols, rows = element.columns, element.rows
                spacing = element.spacing
                angle_rad = math.radians(rot)
                
                # 🔥 [Critical Bug Fix]: Apply array grid spacing components accurately into mirror and rotation matrix coordinates
                for r in range(rows):
                    for c in range(cols):
                        x_local = c * spacing[0] * mag
                        y_local = r * spacing[1] * mag
                        
                        if mirror:
                            y_local = -y_local
                            
                        x_rot = x_local * math.cos(angle_rad) - y_local * math.sin(angle_rad)
                        y_rot = x_local * math.sin(angle_rad) + y_local * math.cos(angle_rad)
                        
                        actual_origin = np.array([origin[0] + x_rot, origin[1] + y_rot])
                        instances_list.append({
                            'origin': actual_origin,
                            'rotation': rot,
                            'mirror': mirror,
                            'magnification': mag
                        })
            
            inst_group_name = f"{ref_cell.name}_instance_group"
            n_conflict = 0
            while inst_group_name in our_cell_def['subcells']: 
                n_conflict += 1
                inst_group_name = f"{ref_cell.name}_instance_group_{n_conflict}"
                
            our_cell_def['subcells'][inst_group_name] = {
                'definition': sub_def,
                'instances': instances_list
            }
    return our_cell_def

def save_cell_to_json(gds_lib, cell_name, output_filename, trace_connection_points=None, layers_to_keep=None): 
    target_cell = gds_lib.cells[cell_name]
    recursive_data_structure = export_cell_to_recursive_dict(target_cell, memo={}, layers_to_keep=layers_to_keep)
    save_to_json(recursive_data_structure, output_filename)

if __name__ == "__main__":
    # 🔥 Updated to use relative path pointing to the project's example directory
    gds_file_path = r"../example/Probes_test.GDS" 
    target_cell_name = "WAFER"        
    output_json_path = rf"../json/{target_cell_name}.json" 
    output_png_highlight = rf"../resource/{target_cell_name}.png"
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_png_highlight), exist_ok=True)
    
    allowed_layers = [(11, 0), (92, 0), (81, 0), (99, 0), (4, 0), (100, 0)]
    gds_library = gdspy.GdsLibrary(infile=gds_file_path)
    save_cell_to_json(gds_library, target_cell_name, output_json_path, layers_to_keep=allowed_layers) 
    print("\n🎉 GDS to JSON conversion completed!")