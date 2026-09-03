#!/usr/bin/env python3
import argparse
import csv
import glob
import os
import re

try:
	from openpyxl import Workbook
except ImportError as exc:  # pragma: no cover - runtime dependency check
	raise SystemExit("openpyxl is required. Install it with: pip install openpyxl") from exc


def process_file(path: str, dry_run: bool = False) -> bool:
	with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
		text = f.read()

	# Replace runs of spaces/tabs with a single comma
	new = re.sub(r"[ \t]+", ",", text)
	# Remove leading commas at the start of any line (prevent a leading comma)
	new = re.sub(r"(?m)^[,]+", "", new)

	if new == text:
		return False

	if dry_run:
		print(f"DRY-RUN: would modify {path}")
		return True

	with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
		f.write(new)

	print(f"Updated {path}")
	return True


def sanitize_sheet_name(name: str) -> str:
	name = re.sub(r"[^A-Za-z0-9 _.-]", "", name)
	name = name.strip() or "Sheet"
	return name[:31]


def write_excel(files: list[str], output_path: str) -> None:
	wb = Workbook()
	default_sheet = wb.active
	wb.remove(default_sheet)

	seen_names: dict[str, int] = {}
	for path in files:
		base_name = os.path.splitext(os.path.basename(path))[0]
		count = seen_names.get(base_name, 0)
		seen_names[base_name] = count + 1
		sheet_name = sanitize_sheet_name(base_name if count == 0 else f"{base_name}_{count}")
		sheet = wb.create_sheet(title=sheet_name)

		with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
			reader = csv.reader(f)
			for row in reader:
				sheet.append(row)

	wb.save(output_path)
	print(f"Wrote workbook to {output_path}")


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Replace spaces/tabs with commas in files matching a pattern"
	)
	parser.add_argument(
		"dir",
		nargs="?",
		default=os.path.dirname(__file__) or ".",
		help="Directory to scan (defaults to script directory)",
	)
	parser.add_argument(
		"--pattern",
		default="nmos_gm_vgs_vds_*",
		help="Glob pattern for filenames to process",
	)
	parser.add_argument("--output", default=None, help="Path for the Excel workbook (default: <dir>/data.xlsx)")
	parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")

	args = parser.parse_args()

	target_dir = args.dir
	pattern = os.path.join(target_dir, args.pattern)
	files = sorted(glob.glob(pattern))

	if not files:
		print(f"No files found matching pattern: {pattern}")
		return

	modified = 0
	for fp in files:
		if os.path.isdir(fp):
			continue
		try:
			if process_file(fp, dry_run=args.dry_run):
				modified += 1
		except Exception as e:
			print(f"Error processing {fp}: {e}")

	if not args.dry_run:
		output_path = args.output or os.path.join(target_dir, "data.xlsx")
		write_excel(files, output_path)

	print(f"Scanned {len(files)} files, modified {modified} files.")


if __name__ == "__main__":
	main()

