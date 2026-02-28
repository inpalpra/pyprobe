import re

files_to_merge = [
    ("PARK", "tests/gui/test_park_all_graphs_e2e_fast.py"),
    ("HL", "tests/gui/test_highlight_lifecycle_fast.py"),
    ("FOLDER", "tests/gui/test_folder_browsing_fast.py"),
    ("NONE", "tests/gui/test_reprobe_highlight_and_gutter_fast.py")
]

imports = set()
body_lines = []

for prefix, filepath in files_to_merge:
    with open(filepath, "r") as f:
        content = f.read()
    
    # Extract imports
    # Simple regex to find imports at start of lines
    import_lines = re.findall(r'^(?:import|from) .+', content, flags=re.MULTILINE)
    for line in import_lines:
        if "pytestmark =" not in line:
            imports.add(line)
            
    # Remove imports from content
    content = re.sub(r'^(?:import|from) .+\n', '', content, flags=re.MULTILINE)
    
    # Handle pytestmark
    content = re.sub(r'^pytestmark = .+\n', '', content, flags=re.MULTILINE)
    
    # Remove module docstring
    content = re.sub(r'^\"\"\"[\s\S]*?\"\"\"\n', '', content)
    
    if prefix != "NONE":
        # Rename _STATE
        content = content.replace("_STATE", f"_STATE_{prefix}")
        # Rename the autouse fixture
        content = content.replace("def _run_all_scenarios", f"def _run_{prefix}_scenarios")
    
    body_lines.append(f"\n# {'='*40}\n# From {filepath}\n# {'='*40}\n")
    body_lines.append(content)

with open("tests/gui/test_unified_window_lifecycle_fast.py", "w") as f:
    f.write('"""\nUnified fast GUI tests.\nConsolidates park graphs, highlight lifecycle, folder browsing, and reprobe into a single file.\n"""\n')
    f.write('import os\nimport pytest\n')
    f.write('pytestmark = pytest.mark.skipif("GITHUB_ACTIONS" in os.environ, reason="Requires GUI head for accurate geometry rendering")\n\n')
    
    for imp in sorted(imports):
        if "pytest" not in imp and "os" not in imp.split():
            f.write(imp + "\n")
            
    f.write("\n")
    f.write("".join(body_lines))

print("Created tests/gui/test_unified_window_lifecycle_fast.py successfully.")
