import re
import glob
import os

print("Auditing codebase for ID strings...")
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = (
    glob.glob(os.path.join(root_dir, "backend", "**", "*.py"), recursive=True) +
    glob.glob(os.path.join(root_dir, "frontend*", "**", "*.js"), recursive=True) +
    glob.glob(os.path.join(root_dir, "hardware", "**", "*.*"), recursive=True)
)

id_pattern = re.compile(r'["\']([a-zA-Z0-9_-]{10,60})["\']')

too_long = []
all_seeded_ids = []

for f in files:
    if ".venv" in f or "__pycache__" in f or ".git" in f:
        continue
    rel_path = os.path.relpath(f, root_dir)
    try:
        content = open(f, encoding="utf-8").read()
        for m in id_pattern.finditer(content):
            val = m.group(1)
            # Check if looks like a fixed ID with hyphens or prefix
            if "-" in val and any(x in val.lower() for x in ["0001", "dept", "queue", "zone", "devi", "user", "staff", "admin"]):
                if len(val) > 36:
                    too_long.append((rel_path, val, len(val)))
                else:
                    all_seeded_ids.append((rel_path, val, len(val)))
    except Exception as e:
        pass

print(f"\n--- IDS LONGER THAN 36 CHARS ({len(too_long)}) ---")
for f, val, l in sorted(set(too_long)):
    print(f"FAIL [{l} chars]: {f} -> '{val}'")

print(f"\n--- SEEDED / HARDCODED IDS <= 36 CHARS ({len(all_seeded_ids)}) ---")
for f, val, l in sorted(set(all_seeded_ids)):
    print(f"OK   [{l} chars]: {f} -> '{val}'")
