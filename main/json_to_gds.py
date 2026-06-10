# json_to_gds.py
# ver. 1.3.3
# [Modifications]:
# - Updated input and output file paths to use relative project directories aligned with the standard workflow.
# - Maintained full compatibility with the big matrix optimized structures (`self_shapes`) exported by ver. 1.1.6+.
# - All code comments and print logs translated to English.

import numpy as np
import json
import re
import sys
import os
import klayout.db as pya
from jsonIO import load_and_reconstruct_from_json 

def get_layer_for_name(name, layer_map, layout):
    for regex_str, layer_info in layer_map.items():
        if regex_str == 'default': continue
        if regex_str.startswith('re:'):
            pattern = regex_str[3:]
            if re.search(pattern, name): return layout.layer(layer_info[0], layer_info[1])
        elif name == regex_str: return layout.layer(layer_info[0], layer_info[1])
    default_info = layer_map.get('default', (100, 0))
    return layout.layer(default_info[0], default_info[1])

def create_gds_cell(layout, cell_definition_json, layer_map, existing_cells):
    cell_name = cell_definition_json.get('name', 'UNKNOWN_CELL')
    if cell_name in existing_cells: return existing_cells[cell_name]
        
    pya_cell = layout.create_cell(cell_name)
    existing_cells[cell_name] = pya_cell
    
    shape_data = cell_definition_json.get('self_shape')
    shape_list = cell_definition_json.get('self_shapes') 
    
    if shape_data is not None or shape_list is not None:
        original_layer_info = cell_definition_json.get('_gds_layer')
        if original_layer_info and len(original_layer_info) == 2:
            layer = layout.layer(int(original_layer_info[0]), int(original_layer_info[1]))
        else:
            layer = get_layer_for_name(cell_name, layer_map, layout)

        if shape_list is not None:
            for poly_verts in shape_list:
                pya_cell.shapes(layer).insert(pya.DPolygon([pya.DPoint(p[0], p[1]) for p in poly_verts]))
        elif isinstance(shape_data, np.ndarray):
            pya_cell.shapes(layer).insert(pya.DPolygon([pya.DPoint(p[0], p[1]) for p in shape_data]))

    for inst_name, sub_group in cell_definition_json.get('subcells', {}).items():
        sub_cell_def_json = sub_group.get('definition')
        if sub_cell_def_json is None: continue
        pya_sub_cell = create_gds_cell(layout, sub_cell_def_json, layer_map, existing_cells)
        for instance in sub_group.get('instances', []):
            origin = np.array(instance.get('origin', [0.0, 0.0]))
            rotation_deg = instance.get('rotation', 0.0)
            mirror = instance.get('mirror', False) 
            mag = instance.get('magnification', 1.0)
            trans = pya.DCplxTrans(mag, rotation_deg, mirror, origin[0], origin[1])
            pya_cell.insert(pya.DCellInstArray(pya_sub_cell.cell_index(), trans))
    return pya_cell

def convert_json_to_gds(input_json_path, output_gds_path, layer_map, top_cell_name="TOP"):
    top_cell_json_data = load_and_reconstruct_from_json(input_json_path)
    layout = pya.Layout()
    layout.dbu = 0.001 
    gds_top_cell = layout.create_cell(top_cell_name)
    existing_cells = {}
    pya_main_cell = create_gds_cell(layout, top_cell_json_data, layer_map, existing_cells)
    gds_top_cell.insert(pya.DCellInstArray(pya_main_cell.cell_index(), pya.DCplxTrans(1.0, 0.0, False, 0.0, 0.0)))
    layout.write(output_gds_path)
    print("✅ GDS export completed successfully.")

if __name__ == "__main__":
    layer_mapping = {"default": (100, 0)}
    # 🔥 Configured to use localized relative paths within the project structure
    input_file = r"../json/WAFER_numbered.json"
    output_file = r"../example/WAFER_numbered.gds"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    convert_json_to_gds(input_file, output_file, layer_mapping, top_cell_name="TOP")