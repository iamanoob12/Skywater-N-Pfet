#!/usr/bin/env python3
import argparse
import csv
import glob
import os
import re
from pathlib import Path

import pandas as pd


def normalize_line(line: str) -> str:
    text = line.rstrip("\n")
    text = re.sub(r"[ \t]+", ",", text)
    if text.startswith(","):
        text = text[1:]
    return text


def process_file(path: Path, dry_run: bool = False) -> bool:
    with path.open("r", encoding="utf-8", errors="surrogateescape") as handle:
        lines = handle.readlines()

    new_lines = []
    changed = False
    for line in lines:
        normalized = normalize_line(line)
        if line.endswith("\n"):
            normalized += "\n"
        if normalized != line:
            changed = True
        new_lines.append(normalized)

    if not changed:
        return False

    if dry_run:
        print(f"DRY-RUN: would modify {path}")
        return True

    with path.open("w", encoding="utf-8", errors="surrogateescape") as handle:
        handle.writelines(new_lines)

    print(f"Updated {path}")
    return True


def write_excel(output_path: Path, csv_files: list[Path]) -> None:
    with pd.ExcelWriter(output_path) as writer:
        for csv_path in csv_files:
            sheet_name = csv_path.stem[:31]
            with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                rows = list(csv.reader(handle))
            if not rows:
                continue
            header = rows[0]
            data_rows = rows[1:]
            df = pd.DataFrame(data_rows, columns=header)
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process PMOS gm CSV files and export an Excel workbook")
    parser.add_argument("dir", nargs="?", default=str(Path(__file__).resolve().parent), help="Directory to scan")
    parser.add_argument("--pattern", default="pmos_gm_vgs_vds_*", help="Glob pattern for CSV filenames")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    args = parser.parse_args()

    target_dir = Path(args.dir)
    pattern = str(target_dir / args.pattern)
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No files found matching pattern: {pattern}")
        return

    csv_files = [Path(path) for path in files if os.path.isfile(path)]
    modified = 0
    for csv_path in csv_files:
        if process_file(csv_path, dry_run=args.dry_run):
            modified += 1

    output_path = target_dir / "data.xlsx"
    write_excel(output_path, csv_files)
    print(f"Wrote workbook to {output_path}")
    print(f"Scanned {len(csv_files)} files, modified {modified} files.")


if __name__ == "__main__":
    main()
