"""Place published thermal measurements along a processing chain.

Tan reaction times are retained as within-session values but excluded from the
thermal timing comparison because all intervention trials became faster. The
calculation does not identify an ERP or button-press latency with an Orch-OR interval.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RNG = np.random.default_rng(20260810)
BOOTSTRAPS = 100_000


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def paired_bootstrap(post: np.ndarray, pre: np.ndarray) -> tuple[float, float, float]:
    indices = RNG.integers(0, len(pre), size=(BOOTSTRAPS, len(pre)))
    changes = 100.0 * (post[indices].mean(axis=1) / pre[indices].mean(axis=1) - 1.0)
    low, high = np.quantile(changes, [0.025, 0.975])
    observed = 100.0 * (post.mean() / pre.mean() - 1.0)
    return float(observed), float(low), float(high)


def nakata_results(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for condition in ("congruent", "incongruent"):
        subset = [row for row in rows if row["condition"] == condition]
        pre_temp = np.array([float(row["ear_temp_pre_c"]) for row in subset])
        heat_temp = np.array([float(row["ear_temp_heat_c"]) for row in subset])
        result: dict[str, object] = {
            "study": "Nakata 2021",
            "condition": condition,
            "temperature_metric": "ear-canal temperature",
            "delta_temperature_c": float((heat_temp - pre_temp).mean()),
        }
        for name, pre_key, heat_key in (
            ("rt", "rt_pre_ms", "rt_heat_ms"),
            ("p300_latency", "p300_latency_pre_ms", "p300_latency_heat_ms"),
            ("p300_amplitude", "p300_amplitude_pre_uv", "p300_amplitude_heat_uv"),
        ):
            pre = np.array([float(row[pre_key]) for row in subset])
            heat = np.array([float(row[heat_key]) for row in subset])
            mean, low, high = paired_bootstrap(heat, pre)
            result[f"{name}_change_pct"] = mean
            result[f"{name}_ci_low_pct"] = low
            result[f"{name}_ci_high_pct"] = high
        results.append(result)
    return results


def tan_results(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for row in rows:
        rt_pre = float(row["rt_pre_ms"])
        rt_heat = float(row["rt_heat_ms"])
        acc_pre = float(row["accuracy_pre_pct"])
        acc_heat = float(row["accuracy_heat_pct"])
        results.append(
            {
                "study": "Tan 2024",
                "condition": row["condition"],
                "temperature_metric": "brain temperature (1H-MRS)",
                "delta_temperature_c": float(row["brain_temp_delta_c"]),
                "rt_change_pct": 100.0 * (rt_heat / rt_pre - 1.0),
                "accuracy_change_pct": 100.0 * (acc_heat / acc_pre - 1.0),
                "timing_role": "within-session change; not heat-specific",
                "integrity_role": "overall passive-heating accuracy loss p=0.017",
            }
        )
    return results


def shibasaki_results() -> list[dict[str, object]]:
    return [
        {
            "study": "Shibasaki 2016",
            "condition": "severe heat vs time control",
            "temperature_metric": "esophageal temperature",
            "delta_temperature_c": 2.0,
            "p300_latency_change_pct": 100.0 * (278.0 / 287.0 - 1.0),
            "p300_amplitude_change_pct": 100.0 * (8.3 / 12.2 - 1.0),
            "timing_role": "time-controlled thermal comparison",
            "integrity_role": "heat baseline to severe heat; p<0.01",
        },
        {
            "study": "Shibasaki 2016",
            "condition": "short cooling vs time control",
            "temperature_metric": "esophageal temperature",
            "delta_temperature_c": "",
            "p300_latency_change_pct": 100.0 * (285.0 / 310.0 - 1.0),
            "timing_role": "time-controlled persistence after heat",
        },
    ]


def write_results(results: list[dict[str, object]]) -> None:
    columns = sorted({key for row in results for key in row})
    preferred = [
        "study",
        "condition",
        "temperature_metric",
        "delta_temperature_c",
        "rt_change_pct",
        "rt_ci_low_pct",
        "rt_ci_high_pct",
        "p300_latency_change_pct",
        "p300_latency_ci_low_pct",
        "p300_latency_ci_high_pct",
        "accuracy_change_pct",
        "p300_amplitude_change_pct",
        "p300_amplitude_ci_low_pct",
        "p300_amplitude_ci_high_pct",
        "timing_role",
        "integrity_role",
    ]
    columns = [name for name in preferred if name in columns]
    with (DATA / "thermal_load_comparison.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in columns} for row in results)


def plot_results(
    tan: list[dict[str, object]],
    nakata: list[dict[str, object]],
    shibasaki: list[dict[str, object]],
) -> None:
    colors = {"congruent": "#1f77b4", "incongruent": "#d62728"}
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3))

    x_labels = []
    timing_values = []
    timing_errors = []
    timing_colors = []
    for metric, label in (("rt", "Nakata RT"), ("p300_latency", "Nakata P300")):
        for row in nakata:
            value = float(row[f"{metric}_change_pct"])
            low = float(row[f"{metric}_ci_low_pct"])
            high = float(row[f"{metric}_ci_high_pct"])
            x_labels.append(f"{label}\n{str(row['condition'])[:3]}")
            timing_values.append(value)
            timing_errors.append((value - low, high - value))
            timing_colors.append(colors[str(row["condition"])])
    for row in shibasaki:
        x_labels.append(
            "Shibasaki P300\n" + ("heat" if "severe" in str(row["condition"]) else "cooling")
        )
        timing_values.append(float(row["p300_latency_change_pct"]))
        timing_errors.append((0.0, 0.0))
        timing_colors.append("#6a3d9a")
    x = np.arange(len(x_labels))
    error_array = np.array(timing_errors).T
    axes[0].bar(x, timing_values, color=timing_colors, alpha=0.86)
    axes[0].errorbar(x, timing_values, yerr=error_array, fmt="none", color="black", capsize=3)
    axes[0].axhline(0, color="black", linewidth=0.9)
    axes[0].set_xticks(x, x_labels, rotation=35, ha="right")
    axes[0].set_ylabel("Change from baseline [%]")
    axes[0].set_title("Controlled timing observations")

    integrity_labels = []
    integrity_values = []
    integrity_errors = []
    integrity_colors = []
    for row in tan:
        integrity_labels.append(f"Tan accuracy\n{str(row['condition'])[:3]}")
        integrity_values.append(float(row["accuracy_change_pct"]))
        integrity_errors.append((0.0, 0.0))
        integrity_colors.append(colors[str(row["condition"])])
    for row in nakata:
        value = float(row["p300_amplitude_change_pct"])
        low = float(row["p300_amplitude_ci_low_pct"])
        high = float(row["p300_amplitude_ci_high_pct"])
        integrity_labels.append(f"Nakata P300 amp.\n{str(row['condition'])[:3]}")
        integrity_values.append(value)
        integrity_errors.append((value - low, high - value))
        integrity_colors.append(colors[str(row["condition"])])
    severe = shibasaki[0]
    integrity_labels.append("Shibasaki P300 amp.\nsevere heat")
    integrity_values.append(float(severe["p300_amplitude_change_pct"]))
    integrity_errors.append((0.0, 0.0))
    integrity_colors.append("#6a3d9a")
    x = np.arange(len(integrity_labels))
    axes[1].bar(x, integrity_values, color=integrity_colors, alpha=0.86)
    axes[1].errorbar(
        x,
        integrity_values,
        yerr=np.array(integrity_errors).T,
        fmt="none",
        color="black",
        capsize=3,
    )
    axes[1].axhline(0, color="black", linewidth=0.9)
    axes[1].set_xticks(x, integrity_labels, rotation=35, ha="right")
    axes[1].set_title("P300 amplitude and task accuracy")

    axes[2].axis("off")
    chain = (
        "Cross-study processing sequence\n\n"
        "Thermal state\n"
        "  Tan: brain +0.9 C; cortical perfusion lower\n\n"
        "Early sensory registration\n"
        "  Shibasaki: N100 latency and amplitude unchanged\n\n"
        "P300 latency\n"
        "  Nakata/Shibasaki: P300 latency shorter\n\n"
        "P300 amplitude\n"
        "  P300 amplitude lower\n\n"
        "Behaviour and motor output\n"
        "  RT is composite; Tan timing is not heat-specific"
    )
    axes[2].text(0.02, 0.98, chain, va="top", ha="left", fontsize=9.5, linespacing=1.25)

    fig.suptitle(
        "Passive thermal load: measurements assigned to processing stages",
        fontsize=12,
    )
    fig.text(
        0.5,
        0.015,
        "Nakata: paired data with 95% bootstrap intervals. Shibasaki: published means. "
        "Tan RT changes are excluded from thermal timing because all intervention trials became faster.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.93))
    fig.savefig(DATA / "thermal_load_comparison.png", dpi=220)
    fig.savefig(DATA / "thermal_load_comparison.pdf")
    plt.close(fig)


def plot_effect_overview(
    nakata: list[dict[str, object]],
    shibasaki: list[dict[str, object]],
) -> None:
    """Plot the cross-modal result without mixing timing and amplitude units."""
    severe = shibasaki[0]
    timing_labels = [
        "Auditory P300\nShibasaki",
        "Visual P300\ncongruent",
        "Visual P300\nincongruent",
    ]
    timing_values = [
        float(severe["p300_latency_change_pct"]),
        float(nakata[0]["p300_latency_change_pct"]),
        float(nakata[1]["p300_latency_change_pct"]),
    ]
    timing_errors = [
        (0.0, 0.0),
        (
            timing_values[1] - float(nakata[0]["p300_latency_ci_low_pct"]),
            float(nakata[0]["p300_latency_ci_high_pct"]) - timing_values[1],
        ),
        (
            timing_values[2] - float(nakata[1]["p300_latency_ci_low_pct"]),
            float(nakata[1]["p300_latency_ci_high_pct"]) - timing_values[2],
        ),
    ]

    strength_labels = [
        "Auditory P300\nShibasaki",
        "Visual P300\ncongruent",
        "Visual P300\nincongruent",
    ]
    strength_values = [
        float(severe["p300_amplitude_change_pct"]),
        float(nakata[0]["p300_amplitude_change_pct"]),
        float(nakata[1]["p300_amplitude_change_pct"]),
    ]
    strength_errors = [
        (0.0, 0.0),
        (
            strength_values[1] - float(nakata[0]["p300_amplitude_ci_low_pct"]),
            float(nakata[0]["p300_amplitude_ci_high_pct"]) - strength_values[1],
        ),
        (
            strength_values[2] - float(nakata[1]["p300_amplitude_ci_low_pct"]),
            float(nakata[1]["p300_amplitude_ci_high_pct"]) - strength_values[2],
        ),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5))
    panels = (
        (axes[0], timing_labels, timing_values, timing_errors, "P300 latency", "#277da1"),
        (axes[1], strength_labels, strength_values, strength_errors, "P300 amplitude", "#d1495b"),
    )
    for axis, labels, values, errors, title, color in panels:
        y = np.arange(len(labels))
        axis.barh(y, values, color=color, alpha=0.9)
        axis.errorbar(
            values,
            y,
            xerr=np.array(errors).T,
            fmt="none",
            color="black",
            capsize=3,
            linewidth=1,
        )
        axis.axvline(0, color="black", linewidth=0.9)
        axis.set_yticks(y, labels)
        axis.invert_yaxis()
        axis.set_xlabel("Change under heat [%]")
        axis.set_title(title)
        axis.grid(axis="x", color="#dddddd", linewidth=0.7)
        for row, value in enumerate(values):
            axis.text(-0.35, row - 0.23, f"{value:.1f}%", va="center", ha="right", color="white", fontsize=9)

    fig.suptitle("Relative P300 changes under passive heating", fontsize=13)
    fig.text(
        0.5,
        0.035,
        "Auditory N100 latency and amplitude remained unchanged. "
        "Nakata intervals are paired 95% bootstrap intervals; Shibasaki values are published means.",
        ha="center",
        fontsize=8.5,
    )
    fig.tight_layout(rect=(0, 0.075, 1, 0.92), w_pad=3.0)
    fig.savefig(DATA / "thermal_effect_overview.png", dpi=220)
    fig.savefig(DATA / "thermal_effect_overview.pdf")
    plt.close(fig)


def main() -> None:
    nakata = nakata_results(read_csv(DATA / "thermal_nakata_individual.csv"))
    tan = tan_results(read_csv(DATA / "thermal_tan_group.csv"))
    shibasaki = shibasaki_results()
    results = tan + nakata + shibasaki
    write_results(results)
    plot_results(tan, nakata, shibasaki)
    plot_effect_overview(nakata, shibasaki)

    print("Tan RT excluded from heat-specific timing interpretation.")
    for row in results:
        print(row)


if __name__ == "__main__":
    main()
