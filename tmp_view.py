from pathlib import Path
for line in Path("README.md").read_text(encoding="utf-8").splitlines():
    if "copy_schema_kubota_to_tiera_auto.sql" in line:
        print(line.encode("unicode_escape").decode())
