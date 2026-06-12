# jsonIO.py
# ver. 1.0.2
# [Modifications]:
# - Translated all comments, docstrings, and print logs into English.
# - Maintained existing serialization configurations and error boundaries.

import numpy as np
import json
import os

def json_numpy_serializer(obj):
    """
    [Helper Function]
    A helper function for the 'default' parameter of json.dump().
    Handles NumPy specific data types (ndarray, integer, floating).
    Raises a TypeError for un-serializable types.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def save_to_json(data, filename):
    """
    Saves a recursive structure (a dictionary containing NumPy arrays) into a JSON file.
    
    Args:
        data (dict): The nested dictionary data to save.
        filename (str): The output JSON file path.
    """
    print(f"\n🔬 Attempting to save data to '{filename}'...")
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Extra step required to handle 'rotation' and 'translation' spec formats
            def custom_serializer(obj):
                # Check if it matches the instance format for Part 3/4 (with 'rotation' and 'translation')
                if isinstance(obj, dict) and 'rotation' in obj and 'translation' in obj:
                    # Ensure rotation is a pure number, translation is a list,
                    # and recursively process the nested 'definition'
                    return {
                        'definition': obj['definition'], 
                        'placements': obj['placements'], 
                        'rotation': obj['rotation'], 
                        'translation': obj['translation']
                    }
                # Use the standard serializer for other NumPy objects
                return json_numpy_serializer(obj)
                
            json.dump(data, f, indent=4, default=custom_serializer)
        print(f"✅ Data successfully saved to '{filename}'")
    except Exception as e:
        print(f"❌ Error occurred while saving JSON: {e}")
        
def _recursive_reconstruct(obj, current_key=None):
    """
    [Recursive Helper Function]
    Traverses Python objects (dicts or lists) and converts lists under specific keys back into np.array.
    [Fix]: Distinguishes between 'placements' in GDS-JSON format and Recursive format.

    Args:
        obj (any): The current object in recursion (dict, list, or primitive).
        current_key (str, optional): The key of the object in its parent dictionary.

    Returns:
        any: The reconstructed object (potentially containing np.array).
    """
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            # Pass the key 'k' to the next recursion level
            new_dict[k] = _recursive_reconstruct(v, current_key=k) 
        return new_dict

    elif isinstance(obj, list):
        # --- Convert lists only under specific mapped keys ---
        # These are keys that should map to NumPy arrays in our defined recursive structure
        if current_key in ['self_shape', 'translation']:
             # Assume the list is [x, y] or [[x1, y1], [x2, y2]]
             try:
                 return np.array(obj)
             except ValueError:
                 return obj # Fallback
        elif current_key == 'placements':
             # Check if it is [ [x, y], ... ] or [ {dict}, ... ]
             if obj and isinstance(obj[0], dict):
                 # GDS-JSON format (placements: [ {dict}, {dict} ])
                 # Keep intact, only recurse inside
                 return [_recursive_reconstruct(item, current_key=None) for item in obj]
             else:
                 # Recursive format (placements: [ [x, y], [x, y] ])
                 # Convert into a list of np.arrays
                 return [np.array(p) for p in obj]
        # --- ---
        else:
             # For other lists (e.g., polygon vertices in GDS-JSON), only recurse
             return [_recursive_reconstruct(item, current_key=None) for item in obj]
    else:
        return obj # Primitive types (str, int, float, bool, None)

def load_and_reconstruct_from_json(filename):
    """
    [General Function]
    Loads data from a JSON file and uses _recursive_reconstruct 
    to recursively reconstruct 'list' back into 'numpy.array'.

    Args:
        filename (str): The input JSON file path.
        
    Returns:
        dict or None: The reconstructed data dictionary, or None if failed.
    """
    print(f"🔬 Loading and reconstructing data from '{filename}'...")
    if not os.path.exists(filename):
        print(f"❌ Error: Cannot find JSON file '{filename}'")
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON decoding error: {e}")
        return None
        
    reconstructed_data = _recursive_reconstruct(data, current_key=None) # Start recursion
    print("✅ Data loading and reconstruction completed successfully.")
    return reconstructed_data