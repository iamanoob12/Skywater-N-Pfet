"""
fit_poles_zeros.py
-------------------
Fit a rational transfer function H(s) = N(s)/D(s) to AC-analysis (Bode) data
exported from ngspice with:

    wrdata ac_cascode.txt v(Vout) db(v(Vout)) ph(v(Vout))

Method: Sanathanan-Koerner (SK) iterative reweighted least squares
(a numerically stable variant of Levy's method). This is the same family
of algorithm used by classical "vector fitting" for extracting poles/zeros
from measured/simulated frequency response.

Usage:
    python fit_poles_zeros.py ac_cascode.txt --npoles 3 --nzeros 1

Requires: numpy, matplotlib
"""

import argparse
import os
import numpy as np
import matplotlib.pyplot as plt


def load_bode_data(path):
    """
    Loads ngspice wrdata output.
    Expected columns from ngspice wrdata:
    freq, Re(Vout), Im(Vout), freq, dB(Vout), freq, phase_deg(Vout)
    Falls back gracefully if only freq/dB/phase (3 cols) are present.
    """
    data = np.loadtxt(path)
    freq = data[:, 0]

    if data.shape[1] >= 7:
        db = data[:, 4]
        phase_deg = data[:, 6]
    elif data.shape[1] >= 5:
        db = data[:, 3]
        phase_deg = data[:, 4]
    elif data.shape[1] == 3:
        db = data[:, 1]
        phase_deg = data[:, 2]
    else:
        raise ValueError(f"Unexpected number of columns: {data.shape[1]}")

    mag = 10 ** (db / 20.0)
    phase_rad = np.deg2rad(phase_deg)
    H = mag * np.exp(1j * phase_rad)
    return freq, H


def fit_tf(freq_hz, H, n_poles, n_zeros, iterations=15):
    """
    Fit H(s) ~= N(s)/D(s) via Sanathanan-Koerner iteration.

    D(s) = 1 + a1*s + a2*s^2 + ... + an*s^n
    N(s) = b0 + b1*s + ... + bm*s^m

    Returns: poles (rad/s), zeros (rad/s), and the fitted b,a coefficients.
    """
    w = 2 * np.pi * freq_hz
    w_ref = np.sqrt(w.min() * w.max())
    s = 1j * w / w_ref

    weight = np.ones_like(s, dtype=complex)

    for it in range(iterations):
        # Columns for numerator: s^0 ... s^m
        A_num = np.vstack([s ** k for k in range(n_zeros + 1)]).T
        # Columns for denominator (excluding the fixed a0=1 term): -H*s^1 ... -H*s^n
        A_den = np.vstack([-H * s ** j for j in range(1, n_poles + 1)]).T

        A = np.hstack([A_num, A_den]) * weight[:, None]
        b_rhs = H * weight

        x, *_ = np.linalg.lstsq(A, b_rhs, rcond=None)
        b_coeffs = x[: n_zeros + 1]
        a_coeffs = x[n_zeros + 1:]  # a1..an

        # Update weight = 1/|D(jw)| using the fit we just found (SK reweighting)
        D_val = np.ones_like(s, dtype=complex)
        for j, aj in enumerate(a_coeffs, start=1):
            D_val += aj * s ** j
        weight = 1.0 / np.abs(D_val)

    # Convert coefficients from q = s / w_ref back to the physical s domain.
    b_coeffs = np.array([b / w_ref ** k for k, b in enumerate(b_coeffs)])
    a_coeffs = np.array([a / w_ref ** j for j, a in enumerate(a_coeffs, start=1)])
    return b_coeffs, a_coeffs


def poles_zeros_from_coeffs(b_coeffs, a_coeffs):
    # Denominator: 1 + a1 s + a2 s^2 + ... -> descending order for np.roots
    den_desc = np.concatenate(([1.0], a_coeffs))[::-1]
    poles = np.roots(den_desc)

    # Numerator: b0 + b1 s + ... -> descending order
    num_desc = b_coeffs[::-1]
    zeros = np.roots(num_desc) if len(num_desc) > 1 else np.array([])

    return poles, zeros


def report(poles, zeros):
    print("\n--- Fitted poles (rad/s | Hz) ---")
    for p in poles:
        f_hz = abs(p.imag) / (2 * np.pi)
        print(f"  s = {p: .6e}   ->  f = {f_hz: .6e} Hz, "
              f"sigma = {p.real: .6e} rad/s"
              f"{' (complex pair)' if abs(p.imag) > 1e-6 else ''}")

    print("\n--- Fitted zeros (rad/s | Hz) ---")
    if len(zeros) == 0:
        print("  (none / numerator is a constant)")
    for z in zeros:
        f_hz = abs(z.imag) / (2 * np.pi)
        print(f"  s = {z: .6e}   ->  f = {f_hz: .6e} Hz, "
              f"sigma = {z.real: .6e} rad/s"
              f"{' (RHP zero!)' if z.real > 0 else ''}")


def plot_fit_vs_data(freq_hz, H, b_coeffs, a_coeffs):
    w = 2 * np.pi * freq_hz
    s = 1j * w

    N_val = sum(b * s ** k for k, b in enumerate(b_coeffs))
    D_val = 1.0 + sum(a * s ** j for j, a in enumerate(a_coeffs, start=1))
    H_fit = N_val / D_val

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)

    ax1.semilogx(freq_hz, 20 * np.log10(np.abs(H)), 'o', ms=3, label='ngspice data')
    ax1.semilogx(freq_hz, 20 * np.log10(np.abs(H_fit)), '-', label='fitted TF')
    ax1.set_ylabel('Magnitude (dB)')
    ax1.legend()
    ax1.grid(True, which='both', alpha=0.3)

    ax2.semilogx(freq_hz, np.rad2deg(np.unwrap(np.angle(H))), 'o', ms=3, label='ngspice data')
    ax2.semilogx(freq_hz, np.rad2deg(np.unwrap(np.angle(H_fit))), '-', label='fitted TF')
    ax2.set_ylabel('Phase (deg)')
    ax2.set_xlabel('Frequency (Hz)')
    ax2.grid(True, which='both', alpha=0.3)

    plt.tight_layout()
    plt.savefig('fit_vs_data.png', dpi=150)
    print("\nSaved comparison plot to fit_vs_data.png")


def main():
    parser = argparse.ArgumentParser()
    default_datafile = os.path.join(os.path.dirname(__file__), '..', 'ac_cascode.txt')
    parser.add_argument('datafile', nargs='?', default=default_datafile,
                        help='wrdata output file, e.g. ac_cascode.txt')
    parser.add_argument('--npoles', type=int, default=3, help='number of poles to fit')
    parser.add_argument('--nzeros', type=int, default=1, help='number of zeros to fit')
    parser.add_argument('--iters', type=int, default=15, help='SK iterations')
    args = parser.parse_args()

    freq, H = load_bode_data(args.datafile)
    b_coeffs, a_coeffs = fit_tf(freq, H, args.npoles, args.nzeros, args.iters)
    poles, zeros = poles_zeros_from_coeffs(b_coeffs, a_coeffs)

    report(poles, zeros)
    plot_fit_vs_data(freq, H, b_coeffs, a_coeffs)


if __name__ == '__main__':
    main()