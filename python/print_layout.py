import json
import sys
import pandas as pd
from typing import Dict, Any, List, Optional

def load_layout_data(layout_path: str) -> Dict[str, Any]:
    """Load the layout JSON file."""
    with open(layout_path, 'r') as f:
        return json.load(f)

def load_actions_data(actions_path: str) -> Dict[str, Any]:
    """Load the actions JSON file and build a mapping from action codes to names."""
    with open(actions_path, 'r') as f:
        actions_list = json.load(f)
    
    # Build a mapping from action code (string) to action details
    # The actions JSON appears to be a list of objects with "actions" dictionaries
    action_map = {}
    
    for item in actions_list:
        if "actions" in item and isinstance(item["actions"], dict):
            for code_str, action_details in item["actions"].items():
                # Use "name" if available, otherwise use "id"
                action_name = action_details.get("name")
                if not action_name:
                    action_name = action_details.get("id")
                
                if action_name:
                    action_map[code_str] = action_name
                else:
                    action_map[code_str] = f"Unknown_{code_str}"
    
    return action_map

def convert_layer_to_names(layout_data: Dict[str, Any], 
                           action_map: Dict[str, str], 
                           layer_index: int) -> List[List[str]]:
    """
    Convert a specific layer of layout codes to action names.
    
    Args:
        layout_data: The layout JSON data
        action_map: Mapping from action codes (strings) to action names
        layer_index: Which layer to convert (0-3 for 4 layers)
    
    Returns:
        A 2D list of action names for the specified layer
    """
    # Get the layout array
    layout_array = layout_data.get("layout", [])
    
    if not layout_array:
        print("No layout data found in the layout JSON")
        return []
    
    if layer_index >= len(layout_array):
        print(f"Layer index {layer_index} is out of range. Layout has {len(layout_array)} layers.")
        return []
    
    # Get the specific layer
    layer_codes = layout_array[layer_index]
    
    # The layout appears to be a flat list representing a grid
    # We need to know the dimensions to convert to 2D
    # Based on the example, it looks like a 6x15 grid (90 keys)
    # But let's calculate based on the length
    total_keys = len(layer_codes)
    
    # Common keyboard layouts: 60%, 75%, TKL, full-size
    # Let's try to detect grid size
    # For a standard keyboard with 6 rows, we can calculate columns
    rows = 6  # Common for many keyboards
    
    if total_keys % rows != 0:
        print(f"Warning: Total keys ({total_keys}) is not divisible by {rows} rows.")
        # Try common row counts
        for test_rows in [4, 5, 6, 7]:
            if total_keys % test_rows == 0:
                rows = test_rows
                print(f"Using {rows} rows instead (columns: {total_keys // rows})")
                break
    
    cols = total_keys // rows
    
    # Convert to 2D grid
    grid = []
    for row in range(rows):
        start_idx = row * cols
        end_idx = start_idx + cols
        row_codes = layer_codes[start_idx:end_idx]
        
        row_names = []
        for code in row_codes:
            if code == 0:
                row_names.append("EMPTY")
            else:
                # Convert code to string for lookup
                code_str = str(code)
                if code_str in action_map:
                    row_names.append(action_map[code_str])
                else:
                    row_names.append(f"UNKNOWN_{code}")
        
        grid.append(row_names)
    
    return grid

def print_layer_grid(grid: List[List[str]], layer_index: int):
    """Print the layer grid in a readable format."""
    print(f"\nLayer {layer_index}:")
    print("=" * 80)
    
    for row_idx, row in enumerate(grid):
        print(f"Row {row_idx}: ", end="")
        for name in row:
            # Truncate long names for better display
            if len(name) > 12:
                display_name = name[:10] + ".."
            else:
                display_name = name.ljust(12)
            print(f"{display_name} ", end="")
        print()
    print("=" * 80)


def convert_layer_to_names_with_dims(layout_data: Dict[str, Any], 
                                     action_map: Dict[str, str], 
                                     layer_index: int,
                                     rows: Optional[int] = None,
                                     cols: Optional[int] = None) -> List[List[str]]:
    """
    Convert a specific layer of layout codes to action names with optional dimensions.
    
    Args:
        layout_data: The layout JSON data
        action_map: Mapping from action codes (strings) to action names
        layer_index: Which layer to convert (0-3 for 4 layers)
        rows: Number of rows in the grid (optional, will auto-detect if not provided)
        cols: Number of columns in the grid (optional, will auto-detect if not provided)
    
    Returns:
        A 2D list of action names for the specified layer
    """
    # Get the layout array
    layout_array = layout_data.get("layout", [])
    
    if not layout_array:
        print("No layout data found in the layout JSON")
        return []
    
    if layer_index >= len(layout_array):
        print(f"Layer index {layer_index} is out of range. Layout has {len(layout_array)} layers.")
        return []
    
    # Get the specific layer
    layer_codes = layout_array[layer_index]
    total_keys = len(layer_codes)
    
    # Determine grid dimensions
    if rows and cols:
        if rows * cols != total_keys:
            print(f"Warning: Specified dimensions {rows}x{cols}={rows*cols} don't match total keys {total_keys}")
    elif rows:
        # Calculate columns based on rows
        if total_keys % rows != 0:
            print(f"Warning: Total keys ({total_keys}) is not divisible by {rows} rows.")
            cols = total_keys // rows + 1
        else:
            cols = total_keys // rows
    elif cols:
        # Calculate rows based on columns
        if total_keys % cols != 0:
            print(f"Warning: Total keys ({total_keys}) is not divisible by {cols} columns.")
            rows = total_keys // cols + 1
        else:
            rows = total_keys // cols
    else:
        # Auto-detect
        # Try to find a reasonable grid size
        # Common keyboard layouts
        possible_dims = [
            (6, 15),  # 90 keys
            (5, 18),  # 90 keys
            (5, 15),  # 75 keys
            (6, 17),  # 102 keys
            (4, 12),  # 48 keys
            (5, 12),  # 60 keys
            (4, 14),  # 56 keys
        ]
        
        for test_rows, test_cols in possible_dims:
            if test_rows * test_cols == total_keys:
                rows, cols = test_rows, test_cols
                print(f"Auto-detected grid: {rows} rows x {cols} columns")
                break
        
        if not rows or not cols:
            # Use 6 rows as default
            rows = 6
            if total_keys % rows == 0:
                cols = total_keys // rows
            else:
                cols = total_keys // rows + 1
            print(f"Using default grid: {rows} rows x {cols} columns (approximate)")
    
    # Convert to 2D grid
    grid = []
    for row in range(rows):
        start_idx = row * cols
        end_idx = min(start_idx + cols, total_keys)
        row_codes = layer_codes[start_idx:end_idx]
        
        # Pad with EMPTY if row is shorter than cols
        if len(row_codes) < cols:
            row_codes = row_codes + [0] * (cols - len(row_codes))
        
        row_keys = []
        for code in row_codes:
            if code == 0:
                row_keys.append("EMPTY")
            else:
                code_str = str(code)
                if code_str in action_map:
                    row_keys.append(action_map[code_str])
                else:
                    row_keys.append(f"UNKNOWN_{code}")
        
        grid.append(row_keys)
    
    return grid

# You can modify the main function to accept optional rows/cols parameters
def main_with_dims():
    """Main function that accepts optional dimension parameters."""
    """
    if len(sys.argv) < 4:
        print("Usage: python convert_layout.py <layout_json> <actions_json> <layer> [rows] [cols]")
        print("Example: python convert_layout.py layout.json actions.json 0")
        print("Example: python convert_layout.py layout.json actions.json 0 6 15")
        sys.exit(1)
    
    layout_path = sys.argv[1]
    actions_path = sys.argv[2]
    layer_index = int(sys.argv[3])
    if len(sys.argv) >= 5:
        rows = int(sys.argv[4])
    if len(sys.argv) >= 6:
        cols = int(sys.argv[5])
    """
    layout_path = "../factory_layout.json"
    actions_path = "../actions.json"
    layer_index = 0
    
    rows = 18
    cols = 5
    
    
    # Load data
    layout_data = load_layout_data(layout_path)
    action_map = load_actions_data(actions_path)
    
    # Convert with dimensions
    grid = convert_layer_to_names_with_dims(layout_data, action_map, layer_index, rows, cols)
    df = pd.DataFrame(grid, columns=['c','e','n','w','s'])
    print(df)
    
    if grid:
        print_layer_grid(grid, layer_index)

if __name__ == "__main__":
    # Use the first version (auto-detect) or second version (with dims) as needed
    main_with_dims()
