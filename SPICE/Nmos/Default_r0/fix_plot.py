#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import os
import subprocess

import matplotlib.pyplot as plt
import numpy as np

try:
    import pandas as pd
except Exception:
    pd = None


def extract_bias(path: Path) -> float:
    # Supports:
    # nmos_id_vds_0.80.csv
    # nmos_id_vds_vgs_0.80.csv
    match = re.search(r"nmos_id_vds(?:_vgs)?_([0-9]+(?:\.[0-9]+)?)\.csv$", path.name)
    if not match:
        raise ValueError(f"Could not parse bias from filename: {path.name}")
    return float(match.group(1))


def run_ngspice(base: Path) -> None:
    cmd = ["ngspice", "-b", "nmos_dc_iv.spice", "-o", "nmos_dc_iv.log"]
    subprocess.run(cmd, cwd=base, check=True)
    print(f"Ran: {' '.join(cmd)} (cwd={base})")


def load_id_vds(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Supports:
    - old format: whitespace, no header, columns = vds id
    - csv format: header includes id,vds (or id,vds,r0)
    """
    with path.open("r", encoding="utf-8") as f:
        first = f.readline().strip().lower()

    if "," in first and ("id" in first and "vds" in first):
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        ids = data[:, 0]
        vds = data[:, 1]
    else:
        data = np.loadtxt(path)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        if data.shape[1] < 2:
            raise ValueError(f"Unexpected data format in {path.name}")
        vds = data[:, 0]
        ids = data[:, 1]

    return ids, vds


def compute_r0(ids: np.ndarray, vds: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # r0 = dVds/dId on unique sorted Id points
    order = np.argsort(ids)
    ids_s = ids[order]
    vds_s = vds[order]

    ids_u, uniq_idx = np.unique(ids_s, return_index=True)
    vds_u = vds_s[uniq_idx]

    if len(ids_u) < 2:
        r0_u = np.full_like(ids_u, np.nan, dtype=float)
        r0_full = np.full_like(ids, np.nan, dtype=float)
        return ids_u, r0_u, r0_full

    r0_u = np.gradient(vds_u, ids_u)

    finite = np.isfinite(r0_u)
    if finite.sum() >= 2:
        r0_full = np.interp(ids, ids_u[finite], r0_u[finite], left=r0_u[finite][0], right=r0_u[finite][-1])
    elif finite.sum() == 1:
        r0_full = np.full_like(ids, r0_u[finite][0], dtype=float)
    else:
        r0_full = np.full_like(ids, np.nan, dtype=float)

    return ids_u, r0_u, r0_full


def normalize_csv_to_id_vds_r0(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ids, vds = load_id_vds(path)
    ids_u, r0_u, r0_full = compute_r0(ids, vds)

    # Rewrite file as id,vds,r0
    out = np.column_stack([ids, vds, r0_full])
    np.savetxt(path, out, delimiter=",", header="id,vds,r0", comments="", fmt="%.10e")

    return ids, vds, ids_u, r0_u, r0_full


def sheet_name_from_path(p: Path) -> str:
    s = re.sub(r"[^0-9A-Za-z_]", "_", p.stem)
    return s[:31]


def combine_csv_to_excel(base: Path, csv_files: list[Path], outname: str = "data.xlsx") -> None:
    if pd is None:
        print("pandas/openpyxl not available; skipping data.xlsx creation")
        return
    out = base / outname
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for p in csv_files:
            try:
                df = pd.read_csv(p)
            except Exception as e:
                print(f"Skipping {p.name}: {e}")
                continue
            sheet = sheet_name_from_path(p)
            df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"Wrote: {out}")


def main() -> None:
    base = Path(__file__).resolve().parent

    # 1) Run ngspice
    run_ngspice(base)

    # 2) Find CSV outputs
    csv_files = sorted(base.glob("nmos_id_vds*.csv"), key=extract_bias)
    if not csv_files:
        raise SystemExit("No files found matching nmos_id_vds*.csv")

    fig1, ax1 = plt.subplots(figsize=(8.5, 5.5), dpi=130)  # id(Vds)
    fig2, ax2 = plt.subplots(figsize=(8.5, 5.5), dpi=130)  # r0(Id)

    for csv_path in csv_files:
        bias = extract_bias(csv_path)

        # 3) Reformat CSV to id,vds,r0 and load arrays
        ids, vds, ids_u, r0_u, _ = normalize_csv_to_id_vds_r0(csv_path)

        # 4) Plot id(Vds)
        ax1.plot(vds, ids, linewidth=2.0, label=f"bias={bias:.2f}")

        # 5) Plot r0(Id), r0 = dVds/dId
        mask = np.isfinite(r0_u)
        if mask.any():
            ax2.plot(ids_u[mask], r0_u[mask], linewidth=1.8, label=f"bias={bias:.2f}")

    ax1.set_title("NMOS: Id(Vds)")
    ax1.set_xlabel("Vds (V)")
    ax1.set_ylabel("Id (A)")
    ax1.grid(True, linestyle="--", alpha=0.45)
    ax1.legend(frameon=True)
    fig1.tight_layout()

    ax2.set_title("NMOS: r0(Id),  r0 = dVds/dId")
    ax2.set_xlabel("Id (A)")
    ax2.set_ylabel("r0 (Ohm)")
    ax2.grid(True, linestyle="--", alpha=0.45)
    ax2.legend(frameon=True)
    fig2.tight_layout()

    out1 = base / "nmos_id_vs_vds.png"
    out2 = base / "nmos_r0_vs_id.png"
    fig1.savefig(out1)
    fig2.savefig(out2)

    # combine CSVs into single Excel workbook with each CSV as a sheet
    combine_csv_to_excel(base, csv_files, outname="data.xlsx")

    print(f"Saved plot: {out1}")
    print(f"Saved plot: {out2}")

    if os.environ.get("DISPLAY"):
        plt.show()
    else:
        plt.close(fig1)
        plt.close(fig2)


if __name__ == "__main__":
    main()