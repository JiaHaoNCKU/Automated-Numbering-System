# probe_hybrid_numbering.py
# ver. 1.0.10
# [Modifications]: 
# - Incremented version to align with relative path standard workflow.
# - Fixed a global residual bug: moved the Layer 100 clearing logic outside the probe condition block to execute a "global unconditional purge".
# - Ensured that shared circular subcells (e.g., CIRCLE) inside alignment marks, test boxes, and other non-numbered components are completely wiped clean.
# - Completely eliminated geometric artifacts where old "O" characters stubbornly remained due to KLayout C++ low-level cache pollution.
# - Maintained composite matrix solver, variant-independent serial numbers, and top-level WAFER cell writing architecture.

import numpy as np
import os
import math
from jsonIO import load_and_reconstruct_from_json, save_to_json

def transform_polygon(poly, origin, rotation_deg, mirror, magnification):
    transformed = []
    for pt in poly:
        x_r = pt[0] * magnification
        y_r = pt[1] * magnification
        if mirror:
            y_r = -y_r
        angle_rad = math.radians(rotation_deg)
        x_g = origin[0] + x_r * math.cos(angle_rad) - y_r * math.sin(angle_rad)
        y_g = origin[1] + x_r * math.sin(angle_rad) + y_r * math.cos(angle_rad)
        transformed.append([x_g, y_g])
    return transformed

def transform_point(point, origin, rotation_deg, mirror=False, magnification=1.0):
    x_r, y_r = point[0] * magnification, point[1] * magnification
    if mirror: y_r = -y_r
    angle_rad = math.radians(rotation_deg)
    x_g = origin[0] + x_r * math.cos(angle_rad) - y_r * math.sin(angle_rad)
    y_g = origin[1] + x_r * math.sin(angle_rad) + y_r * math.cos(angle_rad)
    return [x_g, y_g]

def collect_layer_shapes_recursive(definition, target_layer_num, keys_to_delete=None, cur_rot=0.0, cur_mirror=False, cur_mag=1.0):
    results = []
    def_subcells = definition.get('subcells', {})
    
    # 1. Collect raw polygons directly contained in the current level
    for k, sub_item in list(def_subcells.items()):
        sub_def = sub_item.get('definition', {})
        gds_layer = sub_def.get('_gds_layer')
        
        if gds_layer and gds_layer[0] == target_layer_num:
            shapes = sub_def.get('self_shapes', [])
            for p in shapes:
                results.append({
                    'poly': p,
                    'rot': cur_rot,
                    'mirror': cur_mirror,
                    'mag': cur_mag,
                    'dict': def_subcells,
                    'key': k
                })
            if keys_to_delete is not None:
                keys_to_delete.append((def_subcells, k))
                
    # 2. Traversal deeper into nested children cells
    for inst_group_name, group_info in def_subcells.items():
        sub_definition = group_info.get('definition', {})
        if sub_definition.get('_gds_layer'): 
            continue 
            
        for inst in group_info.get('instances', []):
            origin = inst.get('origin', [0.0, 0.0])
            inst_rot = inst.get('rotation', 0.0)
            inst_mirror = inst.get('mirror', False)
            inst_mag = inst.get('magnification', 1.0)
            
            next_mag = cur_mag * inst_mag
            next_mirror = cur_mirror ^ inst_mirror
            if cur_mirror:
                next_rot = cur_rot - inst_rot
            else:
                next_rot = cur_rot + inst_rot
                
            child_results = collect_layer_shapes_recursive(sub_definition, target_layer_num, keys_to_delete, next_rot, next_mirror, next_mag)
            
            for cr in child_results:
                t_poly = transform_polygon(cr['poly'], origin, inst_rot, inst_mirror, inst_mag)
                results.append({
                    'poly': t_poly,
                    'rot': cr['rot'],
                    'mirror': cr['mirror'],
                    'mag': cr['mag'],
                    'dict': cr['dict'],
                    'key': cr['key']
                })
                
    return results

def get_digit_polygons(digit, center, size=10.0, gap=0.0):
    x, y = center
    w, h = size * 0.6, size
    t = size * 0.12  # Thickness of the digital segments
    
    # Define segments with an adjustable gap parameter (gap=0.0 means perfectly connected/overlapping)
    segments = {
        'a': np.array([[gap, h - t], [w - gap, h - t], [w - gap, h], [gap, h]]),
        'b': np.array([[w - t, h / 2 + gap], [w, h / 2 + gap], [w, h - gap], [w - t, h - gap]]),
        'c': np.array([[w - t, gap], [w, gap], [w, h / 2 - gap], [w - t, h / 2 - gap]]),
        'd': np.array([[gap, 0], [w - gap, 0], [w - gap, t], [gap, t]]),
        'e': np.array([[0, gap], [t, gap], [t, h / 2 - gap], [0, h / 2 - gap]]),
        'f': np.array([[0, h / 2 + gap], [t, h / 2 + gap], [t, h - gap], [0, h - gap]]),
        'g': np.array([[gap, h / 2 - t / 2], [w - gap, h / 2 - t / 2], [w - gap, h / 2 + t / 2], [gap, h / 2 + t / 2]])
    }
    
    digit_map = {
        '0': ['a', 'b', 'c', 'd', 'e', 'f'], '1': ['b', 'c'],
        '2': ['a', 'b', 'g', 'e', 'd'],       '3': ['a', 'b', 'g', 'c', 'd'],
        '4': ['f', 'g', 'b', 'c'],             '5': ['a', 'f', 'g', 'c', 'd'],
        '6': ['a', 'f', 'e', 'd', 'c', 'g'],   '7': ['a', 'b', 'c'],
        '8': ['a', 'b', 'c', 'd', 'e', 'f', 'g'], '9': ['a', 'b', 'c', 'd', 'f', 'g']
    }
    
    polygons = []
    for seg_key in digit_map.get(str(digit), []):
        poly = segments[seg_key] - np.array([w / 2, h / 2]) + np.array([x, y])
        polygons.append(poly.tolist())
    return polygons

def generate_number_polygons(number_str, center, size=10.0):
    str_num = str(number_str)
    num_digits = len(str_num)
    digit_w = size * 0.6
    spacing_ratio = 0.3
    start_x = center[0] - (digit_w * num_digits + (num_digits - 1) * (digit_w * spacing_ratio)) / 2 + digit_w / 2
    all_polys = []
    for i, char in enumerate(str_num):
        cur_x = start_x + i * (digit_w * (1 + spacing_ratio))
        all_polys.extend(get_digit_polygons(char if char.isdigit() else '1', (cur_x, center[1]), size))
    return all_polys

def process_hybrid_wafer_numbering(json_path, output_json_path):
    print(f"📂 Loading wafer layout JSON: {json_path}")
    data = load_and_reconstruct_from_json(json_path)
    subcells_dict = data.get('subcells', {})
    all_collected_probes = []
    
    print(f"\n📊 [Debug] Found {len(subcells_dict)} direct subcell groups under top-level WAFER, starting deep recursive sweep...")
    
    for inst_group_name, group_info in subcells_dict.items():
        definition = group_info.get('definition', {})
        def_name = definition.get('name', 'UNKNOWN')
        
        if definition.get('_gds_layer'):
            continue
            
        keys_to_delete_100 = []
        
        layer_81_results = collect_layer_shapes_recursive(definition, 81)
        layer_100_results = collect_layer_shapes_recursive(definition, 100, keys_to_delete_100)
        
        if keys_to_delete_100:
            print(f"🧹 [Global Purge] Erasing {len(keys_to_delete_100)} old Layer 100 placeholders from the structural subtree of cell [{def_name}]...")
            for target_dict, k in keys_to_delete_100:
                if k in target_dict: 
                    del target_dict[k]
        
        relative_100_center = None
        local_O_height = 0.0
        base_rot = 0.0
        base_mirror = False
        base_mag = 1.0
        
        if layer_100_results:
            base_rot = layer_100_results[0]['rot']
            base_mirror = layer_100_results[0]['mirror']
            base_mag = layer_100_results[0]['mag']
            
            unrotated_verts = []
            for r in layer_100_results:
                for pt in r['poly']:
                    angle_rad = math.radians(-base_rot)
                    x_unrot = pt[0] * math.cos(angle_rad) - pt[1] * math.sin(angle_rad)
                    y_unrot = pt[0] * math.sin(angle_rad) + pt[1] * math.cos(angle_rad)
                    if base_mirror: y_unrot = -y_unrot
                    unrotated_verts.append([x_unrot / base_mag, y_unrot / base_mag])
                    
            concat_verts = np.array(unrotated_verts)
            min_x, min_y = np.min(concat_verts, axis=0)
            max_x, max_y = np.max(concat_verts, axis=0)
            
            local_O_height = max_y - min_y 
            unrotated_center = [(min_x + max_x) / 2.0, (min_y + max_y) / 2.0]
            
            x_c, y_c = unrotated_center[0] * base_mag, unrotated_center[1] * base_mag
            if base_mirror: y_c = -y_c
            a_rad = math.radians(base_rot)
            relative_100_center = [
                x_c * math.cos(a_rad) - y_c * math.sin(a_rad),
                x_c * math.sin(a_rad) + y_c * math.cos(a_rad)
            ]

        if layer_81_results and relative_100_center is not None:
            probe_type = def_name
            print(f"   ⚡⚡⚡ [Unlock Success] Cell {def_name} meets hybrid positioning conditions! Creating independent serial group for probe model [{probe_type}]")
            
            for inst in group_info.get('instances', []):
                origin = inst.get('origin', [0.0, 0.0])
                rotation = inst.get('rotation', 0.0)
                mirror = inst.get('mirror', False)
                magnification = inst.get('magnification', 1.0)
                
                global_center = transform_point(relative_100_center, origin, rotation, mirror, magnification)
                
                final_mag = magnification * base_mag
                final_mirror = mirror ^ base_mirror
                if mirror:
                    final_rot = rotation - base_rot
                else:
                    final_rot = rotation + base_rot
                
                all_collected_probes.append({
                    'type': probe_type,
                    'global_center': global_center,
                    'local_size': local_O_height,
                    'final_origin': global_center,
                    'final_rot': final_rot,
                    'final_mirror': final_mirror,
                    'final_mag': final_mag
                })

    grouped_probes = {}
    for probe in all_collected_probes:
        grouped_probes.setdefault(probe['type'], []).append(probe)
        
    print(f"\n🧩 [Serialization Stage] Injecting new serial numbers directly into the structure of top-level WAFER cell...")
    for p_type, probes_list in grouped_probes.items():
        probes_list.sort(key=lambda p: (-p['global_center'][1], p['global_center'][0]))
        
        print(f"   ✍️ Assigning independent serial numbers for probe model [{p_type}] (Total: {len(probes_list)} probes)...")
        for idx, probe in enumerate(probes_list):
            serial_number = idx + 1
            display_str = f"{serial_number}" 
            
            digit_polys = generate_number_polygons(display_str, center=[0.0, 0.0], size=probe['local_size'])
            
            for p_idx, poly_verts in enumerate(digit_polys):
                prim_name = f"wafer_text_{p_type}_{serial_number}_p{p_idx}"
                inst_group_name = f"{prim_name}_instance_group"
                
                subcells_dict[inst_group_name] = {
                    'definition': {
                        'name': prim_name,
                        'self_shapes': [poly_verts],
                        'subcells': {},
                        '_gds_layer': [100, 0] 
                    },
                    'instances': [{
                        'origin': probe['final_origin'],
                        'rotation': probe['final_rot'],
                        'mirror': probe['final_mirror'],
                        'magnification': probe['final_mag']
                    }]
                }
        print(f"   ✅ Successfully completed height-matched and tilt-aligned numbering for model [{p_type}].")

    save_to_json(data, output_json_path)
    print("🎉 Hybrid positioning automated numbering completed successfully.")

if __name__ == "__main__":
    in_wafer_json = "../json/WAFER_optimized.json"
    out_wafer_json = "../json/WAFER_numbered.json"
    if os.path.exists(in_wafer_json):
        process_hybrid_wafer_numbering(in_wafer_json, out_wafer_json)