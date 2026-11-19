"""AdEx trigger sensitivity using the regular-spiking parameter set.

The biological parameters are taken from Brette and Gerstner (2005), Table 1.
The constant-current rheobase is derived from the stationary AdEx equations.
External drive is not fitted: the script sweeps the dimensionless ratio I/I_rheo
and reports the first-spike latency for a rested cell and for a cell carrying one
published spike-triggered adaptation increment b.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class AdExParams:
    c_m: float = 281e-12
    g_l: float = 30e-9
    e_l: float = -70.6e-3
    v_t: float = -50.4e-3
    delta_t: float = 2e-3
    tau_w: float = 144e-3
    a: float = 4e-9
    b: float = 80.5e-12
    v_reset: float = -70.6e-3
    v_peak: float = 20e-3


P = AdExParams()
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "adaptive_trigger_sensitivity.csv"
FIG_PATH = DATA_DIR / "adaptive_trigger_sensitivity.png"
FIG_PDF_PATH = DATA_DIR / "adaptive_trigger_sensitivity.pdf"

# Numerical controls. Convergence is checked against half the time step below.
DT_S = 0.05e-3
WINDOW_S = 1.0
DRIVE_RATIO = np.linspace(0.80, 1.80, 121)


def rheobase_current(p: AdExParams = P) -> float:
    """Stationary AdEx saddle-node current with subthreshold adaptation."""
    conductance = p.g_l + p.a
    v_rheo = p.v_t + p.delta_t * np.log(conductance / p.g_l)
    return conductance * (v_rheo - p.e_l - p.delta_t)


def first_spike_latency(current_a: float, w0_a: float, dt_s: float) -> float:
    v = P.e_l
    w = w0_a
    steps = int(WINDOW_S / dt_s)
    for step in range(steps):
        exp_arg = np.clip((v - P.v_t) / P.delta_t, -20.0, 20.0)
        dv = (
            -P.g_l * (v - P.e_l)
            + P.g_l * P.delta_t * np.exp(exp_arg)
            - w
            + current_a
        ) / P.c_m
        dw = (P.a * (v - P.e_l) - w) / P.tau_w
        v += dv * dt_s
        w += dw * dt_s
        if v >= P.v_peak:
            return (step + 1) * dt_s
    return np.nan


def latency_curves(dt_s: float) -> tuple[np.ndarray, np.ndarray, float]:
    i_rheo = rheobase_current()
    rested = np.array(
        [first_spike_latency(ratio * i_rheo, 0.0, dt_s) for ratio in DRIVE_RATIO]
    )
    adapted = np.array(
        [first_spike_latency(ratio * i_rheo, P.b, dt_s) for ratio in DRIVE_RATIO]
    )
    return rested, adapted, i_rheo


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rested, adapted, i_rheo = latency_curves(DT_S)
    rested_half, adapted_half, _ = latency_curves(DT_S / 2.0)

    finite_r = np.isfinite(rested) & np.isfinite(rested_half)
    finite_a = np.isfinite(adapted) & np.isfinite(adapted_half)
    max_dt_error_ms = max(
        np.max(np.abs(rested[finite_r] - rested_half[finite_r])) * 1e3,
        np.max(np.abs(adapted[finite_a] - adapted_half[finite_a])) * 1e3,
    )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "I_over_I_rheo",
                "rested_first_spike_ms",
                "one_spike_adapted_first_spike_ms",
                "adaptation_delay_ms",
            ]
        )
        for ratio, t_rest, t_adapt in zip(DRIVE_RATIO, rested, adapted):
            delay = t_adapt - t_rest
            writer.writerow(
                [
                    f"{ratio:.6f}",
                    "" if not np.isfinite(t_rest) else f"{t_rest * 1e3:.6f}",
                    "" if not np.isfinite(t_adapt) else f"{t_adapt * 1e3:.6f}",
                    "" if not np.isfinite(delay) else f"{delay * 1e3:.6f}",
                ]
            )

    fig, (ax_latency, ax_delay) = plt.subplots(2, 1, figsize=(8.2, 7.4), sharex=True)
    fig.subplots_adjust(left=0.13, right=0.97, bottom=0.10, top=0.88, hspace=0.28)
    fig.suptitle(
        "Adaptive AdEx trigger: source parameters and unfitted drive sweep",
        fontsize=13,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.91,
        rf"Brette-Gerstner regular-spiking set; analytically derived "
        rf"$I_{{\rm rheo}}={i_rheo * 1e12:.1f}$ pA",
        ha="center",
        fontsize=9,
    )

    ax_latency.plot(DRIVE_RATIO, rested * 1e3, color="black", lw=2, label=r"rested: $w_0=0$")
    ax_latency.plot(
        DRIVE_RATIO,
        adapted * 1e3,
        color="0.45",
        lw=2,
        ls="--",
        label=r"adapted: $w_0=b$",
    )
    ax_latency.set_ylabel("First-spike latency [ms]")
    ax_latency.set_title("A - Trigger latency across the complete drive sweep", fontsize=10)
    ax_latency.legend(frameon=True, fontsize=8)
    ax_latency.grid(True, color="0.86")

    delay_ms = (adapted - rested) * 1e3
    ax_delay.plot(DRIVE_RATIO, delay_ms, color="black", lw=2)
    ax_delay.axhline(0.0, color="0.5", lw=1)
    ax_delay.set_xlabel(r"External drive $I/I_{\rm rheo}$")
    ax_delay.set_ylabel("Adaptation-induced delay [ms]")
    ax_delay.set_title("B - Delay caused by one source-defined adaptation increment", fontsize=10)
    ax_delay.grid(True, color="0.86")

    fig.savefig(FIG_PATH, dpi=220, facecolor="white")
    fig.savefig(FIG_PDF_PATH, facecolor="white")
    plt.close(fig)

    print(f"Derived rheobase: {i_rheo * 1e12:.3f} pA")
    print(f"Maximum dt-halving latency change: {max_dt_error_ms:.4f} ms")
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {FIG_PATH}")
    print(f"Wrote {FIG_PDF_PATH}")


if __name__ == "__main__":
    main()
