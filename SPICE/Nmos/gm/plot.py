#!/usr/bin/env python3
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_series(path: Path):
    x_values = []
    y_values = []

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)  # skip header
        for row in reader:
            if not row:
                continue
            values = [item.strip() for item in row if item.strip()]
            if len(values) < 3:
                continue
            try:
                x_values.append(float(values[0]))
                y_values.append(float(values[2]))
            except ValueError:
                continue

    return x_values, y_values


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    files = sorted(base_dir.glob("nmos_gm_vgs_vds_*.csv"))
    if not files:
        raise FileNotFoundError("No gm CSV files found in the gm folder")

    fig, ax = plt.subplots(figsize=(10, 6))

    for path in files:
        stem = path.stem
        value = stem.rsplit("_", 1)[-1]
        try:
            vds_value = float(value)
        except ValueError:
            continue

        x_vals, y_vals = load_series(path)
        if not x_vals:
            continue
        ax.plot(x_vals, y_vals, label=f"Vds = {vds_value:.2f}", linewidth=1.5)

    ax.set_title("gm vs V-sweep for NMOS gm curves")
    ax.set_xlabel("V-sweep")
    ax.set_ylabel("gm")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()

    output_path = base_dir / "gm_curves.png"
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
