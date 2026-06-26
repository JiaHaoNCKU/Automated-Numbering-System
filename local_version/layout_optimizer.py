# layout_optimizer.py
# ver. 1.2.0
# [Modifications]: 
# - Upgraded to ver. 1.2.0 to support true Polygon-based Irregular Nesting (Nesting Algorithm).
# - Replaced bounding box restrictions with a two-tier geometric collision system (Coarse Box Filter + Fine Polygon Path Penetration).
# - Utilizes matplotlib.path.Path for high-performance point-in-polygon verification.
# - Applied user-defined 4-inch wafer configurations strictly: Wafer Radius = 45895 um, Edge Exclusion = 2790 um.

import numpy as np
import os
import math
from matplotlib.path import Path
from jsonIO import load_and_reconstruct_from_json, save_to_json

# User-defined Wafer Parameters (Units in micrometers)
WAFER_RADIUS = 45895     
EDGE_EXCLUSION = 2790    
EFFECTIVE_RADIUS = WAFER_RADIUS - EDGE_EXCLUSION # 43105 um

def transform_polygon(poly, origin, rotation_deg, mirror, magnification):
    transformed = []
    for pt in poly:
        x_r = pt[0] * magnification
        y_r = pt[1] * magnification
        if mirror: y_r = -y_r
        angle_rad = math.radians(rotation_deg)
        x_g = origin[0] + x_r * math.cos(angle_rad) - y_r * math.sin(angle_rad)
        y_g = origin[1] + x_r * math.sin(angle_rad) + y_r * math.cos(angle_rad)
        transformed.append([x_g, y_g])
    return np.array(transformed)

def collect_layer_polygons_recursive(definition, target_layer_num=81):
    """Recursively collect all raw polygons belonging to the target layer, keeping them in local coordinates."""
    polygons = []
    def_subcells = definition.get('subcells', {})
    
    for k, sub_item in def_subcells.items():
        sub_def = sub_item.get('definition', {})
        gds_layer = sub_def.get('_gds_layer')
        if gds_layer and gds_layer[0] == target_layer_num:
            shapes = sub_def.get('self_shapes', [])
            for p in shapes:
                polygons.append(np.array(p))
                
    for inst_group_name, group_info in def_subcells.items():
        sub_definition = group_info.get('definition', {})
        if sub_definition.get('_gds_layer'): continue
        
        child_polys = collect_layer_shapes_recursive_local(sub_definition, target_layer_num)
        for inst in group_info.get('instances', []):
            origin = inst.get('origin', [0.0, 0.0])
            rotation = inst.get('rotation', 0.0)
            mirror = inst.get('mirror', False)
            magnification = inst.get('magnification', 1.0)
            for cp in child_polys:
                t_poly = transform_polygon(cp, origin, rotation, mirror, magnification)
                polygons.append(t_poly)
    return polygons

def collect_layer_shapes_recursive_local(definition, target_layer_num):
    return collect_layer_polygons_recursive(definition, target_layer_num)

def get_polygons_summary(polygons):
    """Calculate the global width, height, center offset, and bounding box of a collection of polygons."""
    if not polygons: return None, None, None, None
    all_pts = np.concatenate(polygons, axis=0)
    min_x, min_y = np.min(all_pts, axis=0)
    max_x, max_y = np.max(all_pts, axis=0)
    
    w = max_x - min_x
    h = max_y - min_y
    offset = [(min_x + max_x) / 2.0, (min_y + max_y) / 2.0]
    bbox = (min_x, min_y, max_x, max_y)
    return w, h, offset, bbox

def is_polygon_inside_wafer(global_polygons, r_eff):
    """Strictly verify if every vertex of the irregular polygon falls inside the effective wafer radius."""
    for poly in global_polygons:
        r_squared = poly[:, 0]**2 + poly[:, 1]**2
        if np.any(r_squared > r_eff**2):
            return False
    return True

def check_polygon_collision(cand_polys, cand_bbox, placed_probes_list):
    """Two-tier collision detection: Coarse Bounding Box check followed by Fine Polygon Path penetration check."""
    cx1, cy1, cx2, cy2 = cand_bbox
    
    for p_name, p_polys, p_bbox in placed_probes_list:
        bx1, by1, bx2, by2 = p_bbox
        # Tier 1: Quick bounding box rejection
        if (cx2 <= bx1 or cx1 >= bx2 or cy2 <= by1 or cy1 >= by2):
            continue
            
        # Tier 2: Fine-grained point-in-polygon checking via Matplotlib Paths
        for c_poly in cand_polys:
            for p_poly in p_polys:
                path_p = Path(p_poly)
                path_c = Path(c_poly)
                if np.any(path_p.contains_points(c_poly)) or np.any(path_c.contains_points(p_poly)):
                    return True # True collision confirmed
    return False

def optimize_priority_wafer_layout(json_path, output_json_path, target_demands, fill_priority):
    print(f"📂 Loading layout JSON for polygon-based irregular nesting: {json_path}")
    data = load_and_reconstruct_from_json(json_path)
    subcells_dict = data.get('subcells', {})
    
    probe_specs = {}
    anchor_instances = {}
    
    # 1. Parse definitions and extract true irregular Layer 81 geometries
    for inst_group_name, group_info in list(subcells_dict.items()):
        definition = group_info.get('definition', {})
        def_name = definition.get('name', 'UNKNOWN')
        if definition.get('_gds_layer'):
            anchor_instances[inst_group_name] = group_info
            continue
            
        local_polys = collect_layer_polygons_recursive(definition, 81)
        if local_polys:
            w, h, offset, _ = get_polygons_summary(local_polys)
            probe_specs[def_name] = {
                'local_polys': local_polys,
                'width': w, 'height': h, 'center_offset': offset,
                'group_info': group_info
            }
        else:
            anchor_instances[inst_group_name] = group_info

    # 2. Advanced Multi-target / Multi-fill Queue Generation
    required_queue = []
    all_unique_models = list(target_demands.keys()) + [m for m in fill_priority if m not in target_demands]
    
    # Phase A: Guaranteed Minimum — At least 1 instance for every single model type
    for model in all_unique_models:
        if model in probe_specs: required_queue.append(model)
    # Phase B: Complete the remaining required target quotas
    for model, demand in target_demands.items():
        remaining_demand = demand - 1
        if remaining_demand > 0 and model in probe_specs:
            required_queue.extend([model] * remaining_demand)

    # 3. Dense Nested Packing Loop
    street = 80.0  # Safe spacing clearance between irregular edges
    placed_probes_history = []  # Stores tuple: (name, global_polygons, global_bbox)
    final_instances = {model: [] for model in all_unique_models}
    
    # Fine scan step resolution for dense interlocking penetration
    scan_step_x = 250.0 
    scan_step_y = 400.0 

    y_scan = EFFECTIVE_RADIUS
    while y_scan > -EFFECTIVE_RADIUS:
        x_scan = -EFFECTIVE_RADIUS
        while x_scan < EFFECTIVE_RADIUS:
            
            current_model = None
            if required_queue:
                current_model = required_queue[0]
            else:
                # Target accomplished, evaluate filling candidates by priority ranking
                current_model = None
                
            models_to_try = [current_model] if current_model else fill_priority
            placed_successfully = False
            
            for model_to_test in models_to_try:
                if model_to_test not in probe_specs: continue
                
                spec = probe_specs[model_to_test]
                cx, cy = spec['center_offset']
                
                # Propose center alignment on the current spatial mesh coordinate
                x_center, y_center = x_scan + spec['width']/2, y_scan - spec['height']/2
                origin_to_apply = [x_center - cx, y_center - cy]
                
                # Apply forward transformation to obtain temporary global polygons
                cand_global_polys = []
                for lp in spec['local_polys']:
                    gp = transform_polygon(lp, origin_to_apply, rotation_deg=0.0, mirror=False, magnification=1.0)
                    cand_global_polys.append(gp)
                    
                # Compute actual global bounding box padded with safety street clearance
                _, _, _, c_bbox = get_polygons_summary(cand_global_polys)
                padded_bbox = (c_bbox[0] - street/2, c_bbox[1] - street/2, c_bbox[2] + street/2, c_bbox[3] + street/2)
                
                # Execute two-tier checks boundary verification
                if is_polygon_inside_wafer(cand_global_polys, EFFECTIVE_RADIUS):
                    if not check_polygon_collision(cand_global_polys, padded_bbox, placed_probes_history):
                        # Pack successful! Lock the geometric area
                        final_instances[model_to_test].append({
                            'origin': origin_to_apply, 'rotation': 0.0, 'mirror': False, 'magnification': 1.0
                        })
                        placed_probes_history.append((model_to_test, cand_global_polys, padded_bbox))
                        
                        if required_queue and model_to_test == current_model:
                            required_queue.pop(0)
                            
                        x_scan += spec['width'] # Dynamic stride jump to optimize processing loop
                        placed_successfully = True
                        break
                        
            if placed_successfully: continue
            x_scan += scan_step_x
        y_scan -= scan_step_y

    # 4. Save and reconstruct back to JSON dictionary maps
    new_subcells_dict = anchor_instances.copy()
    for model, inst_list in final_instances.items():
        if inst_list:
            group_name = f"{model}_instance_group"
            new_subcells_dict[group_name] = {
                'definition': probe_specs[model]['group_info']['definition'],
                'instances': inst_list
            }
            
    data['subcells'] = new_subcells_dict
    save_to_json(data, output_json_path)
    
    print(f"\n🎉 Advanced Irregular Polygon-Nesting Optimization Complete:")
    print(f"   📊 Target Demands Summary (Placed / Demanded):")
    for m, d in target_demands.items():
        print(f"      -> {m}: {len(final_instances.get(m, []))} / {d}")
    print(f"   📊 Secondary Fill Probes Summary (Placed Count):")
    for m in fill_priority:
        if m not in target_demands:
            print(f"      -> {m}: {len(final_instances.get(m, []))}")

if __name__ == "__main__":
    in_json = "../json/WAFER.json"
    out_json = "../json/WAFER_optimized.json"
    
    my_target_demands = {
        "EdgeProbe_Assim_32":  10, 
        "PI32-100-S1-L50-181": 6,  
        "PI32-50-S1-L50-181":  6   
    }
    
    my_fill_priority = [
        "PI32-50-S1-L20-181",                  
        "PI64+R-30-S1-L10_200_BOND_v3",                  
        "PI32+R-30-S1-L10_102_BOND_v2",                  
        "PI32+R-25-Tri-S1-L10_135_v2_flat"                   
        "PI32+R-25-Tri-S1-L10_135_v2_flat"                   
        "PI32+R-25-Tri-S1-L10_135_v2_flat"                   
        "PI32+R-25-Tri-S1-L10_135_v2_flat"                   
        "PI32+R-25-Tri-S1-L10_135_v2_flat"                   
        "PI32+R-25-Tri-S1-L10_135_v2_flat"                   
        "PI32+R-30-S1-L10_102_ZIF"                   
        "PI16+R-50-S1-L10_65_ZIF_v2"                   
        "PI16+R-50-S1-L10_55_ZIF_v3"                   
    ]
    
    if os.path.exists(in_json):
        optimize_priority_wafer_layout(in_json, out_json, my_target_demands, my_fill_priority)