"""Evaluate geometric Penrose self-energy for recruited tubulin domains.

The calculation implements the Gaussian mass-density integral used by Tomaz,
Mattos, and Barbatti (2024, doi:10.1039/D4CP02364A). Nuclear counts and the
intra-dimer geometry come from the alpha-beta tubulin structure 1JFF
(doi:10.1006/jmbi.2001.5077). No per-tubulin energy is calibrated to a target
collapse time.

Self terms use the exact Gaussian kernel. Cross terms within and between dimers
use the second-order expansion of the same kernel. This is numerically stable for
femtometre branch shifts across Angstrom-to-nanometre separations; the neglected
generic term is O(delta^3/R^4), or O(delta/R) relative to the retained cross
term. For a common rigid displacement, odd orders cancel and the leading relative
error is O((delta/R)^2).
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq
from scipy.special import erf


G_SI = 6.67430e-11
HBAR_JS = 1.054571817e-34
ATOMIC_MASS_KG = 1.66053906660e-27

ELEMENT_MASS_NUMBER = {"C": 12.0, "N": 14.0, "O": 16.0, "S": 32.0}
DEPOSITED_RESIDUES = 896
RCSB_DIMER_MASS_KDA = 101.93

PROTOFILAMENTS = 13
MICROTUBULE_CENTRE_RADIUS_M = 10.5e-9
DIMER_AXIAL_SPACING_M = 8.0e-9
CARBON_PROFILE_RADIUS_M = 2.5e-15

PROFILE_MODELS = {
    "sphere-equivalent Gaussian": 1.0 / math.sqrt(5.0),
    "direct Gaussian width": 1.0,
}
DISPLACEMENT_PROFILES = ("axial", "radial", "cross-neutral")
TARGET_TAU_S = (0.025, 0.500)
MAX_AXIAL_LAYERS = 262_144

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PDB_PATH = DATA_DIR / "sources" / "1JFF.pdb"
SWEEP_CSV_PATH = DATA_DIR / "geometric_eg_sweep.csv"
DOMAIN_CSV_PATH = DATA_DIR / "geometric_eg_domain_scaling.csv"
SOURCE_CSV_PATH = DATA_DIR / "geometric_eg_source_values.csv"
FIG_PATH = DATA_DIR / "geometric_eg_sweep.png"
FIG_PDF_PATH = DATA_DIR / "geometric_eg_sweep.pdf"


@dataclass(frozen=True)
class TubulinStructure:
    coordinates_m: np.ndarray
    masses_kg: np.ndarray
    elements: tuple[str, ...]
    modeled_residues: int
    completeness_scale: float
    principal_axes: np.ndarray


def load_tubulin_structure(path: Path) -> TubulinStructure:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Download PDB 1JFF from "
            "https://files.rcsb.org/download/1JFF.pdb"
        )

    coordinates = []
    masses = []
    elements = []
    residues: set[tuple[str, str, str]] = set()

    for line in path.read_text(encoding="ascii").splitlines():
        if not line.startswith("ATOM"):
            continue
        chain = line[21]
        alternate = line[16]
        if chain not in {"A", "B"} or alternate not in {" ", "A"}:
            continue
        element = line[76:78].strip().upper()
        if element not in ELEMENT_MASS_NUMBER:
            continue
        coordinates.append(
            [float(line[30:38]), float(line[38:46]), float(line[46:54])]
        )
        masses.append(ELEMENT_MASS_NUMBER[element] * ATOMIC_MASS_KG)
        elements.append(element)
        residues.add((chain, line[22:26], line[26]))

    coordinates_m = np.asarray(coordinates, dtype=float) * 1e-10
    masses_kg = np.asarray(masses, dtype=float)
    modeled_residues = len(residues)
    completeness_scale = DEPOSITED_RESIDUES / modeled_residues

    centre = np.average(coordinates_m, axis=0, weights=masses_kg)
    centred = coordinates_m - centre
    covariance = (centred * masses_kg[:, None]).T @ centred / masses_kg.sum()
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    principal_axes = eigenvectors[:, order]

    return TubulinStructure(
        coordinates_m=centred,
        masses_kg=masses_kg,
        elements=tuple(elements),
        modeled_residues=modeled_residues,
        completeness_scale=completeness_scale,
        principal_axes=principal_axes,
    )


def profile_sigma_m(mass_number: np.ndarray, width_factor: float) -> np.ndarray:
    return (
        CARBON_PROFILE_RADIUS_M
        * width_factor
        * np.power(mass_number / 12.0, 1.0 / 3.0)
    )


def gaussian_self_energy_j(
    structure: TubulinStructure, displacement_m: np.ndarray | float, width_factor: float
) -> np.ndarray:
    displacement = np.atleast_1d(np.asarray(displacement_m, dtype=float))
    mass_numbers = structure.masses_kg / ATOMIC_MASS_KG
    sigma = profile_sigma_m(mass_numbers, width_factor)
    kernel_zero = 1.0 / (math.sqrt(math.pi) * sigma)
    x = displacement[:, None]
    kernel_shifted = np.where(
        x > 0.0,
        erf(x / (2.0 * sigma[None, :])) / x,
        kernel_zero[None, :],
    )
    per_atom = G_SI * structure.masses_kg[None, :] ** 2 * (
        kernel_zero[None, :] - kernel_shifted
    )
    result = structure.completeness_scale * per_atom.sum(axis=1)
    return result if np.ndim(displacement_m) else result[0]


def gaussian_saturation_energy_j(
    structure: TubulinStructure, width_factor: float
) -> float:
    mass_numbers = structure.masses_kg / ATOMIC_MASS_KG
    sigma = profile_sigma_m(mass_numbers, width_factor)
    return float(
        structure.completeness_scale
        * np.sum(
            G_SI
            * structure.masses_kg**2
            / (math.sqrt(math.pi) * sigma)
        )
    )


def internal_cross_coefficients_j_m2(
    structure: TubulinStructure,
) -> dict[str, float]:
    """Return E_cross/delta^2 along the three principal dimer axes."""

    directions = structure.principal_axes
    sums = np.zeros(3, dtype=float)
    coordinates = structure.coordinates_m
    masses = structure.masses_kg

    for index in range(len(masses) - 1):
        separation = coordinates[index] - coordinates[index + 1 :]
        radius_squared = np.einsum("ij,ij->i", separation, separation)
        projections = separation @ directions
        hessian_contractions = (
            3.0 * projections**2 - radius_squared[:, None]
        ) / radius_squared[:, None] ** 2.5
        sums += masses[index] * np.sum(
            masses[index + 1 :, None] * hessian_contractions, axis=0
        )

    coefficients = -G_SI * structure.completeness_scale**2 * sums
    return {
        "axial": coefficients[0],
        "radial": coefficients[1],
        "tangential": coefficients[2],
    }


def displacement_directions(profile: str) -> np.ndarray:
    theta = 2.0 * math.pi * np.arange(PROTOFILAMENTS) / PROTOFILAMENTS
    if profile == "axial":
        return np.tile(np.array([0.0, 0.0, 1.0]), (PROTOFILAMENTS, 1))
    if profile == "radial":
        return np.column_stack((np.cos(theta), np.sin(theta), np.zeros_like(theta)))
    if profile == "cross-neutral":
        return np.zeros((PROTOFILAMENTS, 3))
    raise ValueError(f"Unknown displacement profile: {profile}")


def domain_cross_coefficient_j_m2(layers: int, profile: str) -> float:
    """Return the inter-dimer cross contribution divided by delta^2."""

    if profile == "cross-neutral" or layers < 1:
        return 0.0

    theta = 2.0 * math.pi * np.arange(PROTOFILAMENTS) / PROTOFILAMENTS
    centres = np.column_stack(
        (
            MICROTUBULE_CENTRE_RADIUS_M * np.cos(theta),
            MICROTUBULE_CENTRE_RADIUS_M * np.sin(theta),
            np.zeros(PROTOFILAMENTS),
        )
    )
    directions = displacement_directions(profile)
    hessian_sum = 0.0

    if layers > 1:
        dz = np.arange(1, layers, dtype=float)
        multiplicity = layers - dz
        for protofilament in range(PROTOFILAMENTS):
            separation = np.column_stack(
                (
                    np.zeros_like(dz),
                    np.zeros_like(dz),
                    -dz * DIMER_AXIAL_SPACING_M,
                )
            )
            radius_squared = np.einsum("ij,ij->i", separation, separation)
            direction = directions[protofilament]
            projection = separation @ direction
            contraction = (
                3.0 * projection**2 - radius_squared * np.dot(direction, direction)
            ) / radius_squared**2.5
            hessian_sum += float(np.sum(multiplicity * contraction))

    dz = np.arange(-(layers - 1), layers, dtype=float)
    multiplicity = layers - np.abs(dz)
    for first in range(PROTOFILAMENTS):
        for second in range(first + 1, PROTOFILAMENTS):
            base = centres[first] - centres[second]
            separation = np.column_stack(
                (
                    np.full_like(dz, base[0]),
                    np.full_like(dz, base[1]),
                    base[2] - dz * DIMER_AXIAL_SPACING_M,
                )
            )
            radius_squared = np.einsum("ij,ij->i", separation, separation)
            first_projection = separation @ directions[first]
            second_projection = separation @ directions[second]
            direction_dot = float(np.dot(directions[first], directions[second]))
            contraction = (
                3.0 * first_projection * second_projection
                - radius_squared * direction_dot
            ) / radius_squared**2.5
            hessian_sum += float(np.sum(multiplicity * contraction))

    dimer_mass_kg = RCSB_DIMER_MASS_KDA * 1e3 * ATOMIC_MASS_KG
    return -G_SI * dimer_mass_kg**2 * hessian_sum


def axial_tail_bound_j_per_dimer(layers: int, displacement_m: float) -> float:
    """Bound omitted pair-Hessian terms beyond ``layers`` axial spacings."""

    dimer_mass_kg = RCSB_DIMER_MASS_KDA * 1e3 * ATOMIC_MASS_KG
    return (
        2.0
        * PROTOFILAMENTS
        * G_SI
        * dimer_mass_kg**2
        * displacement_m**2
        / (DIMER_AXIAL_SPACING_M**3 * layers**2)
    )


def saturation_displacement_m(
    structure: TubulinStructure, width_factor: float, fraction: float
) -> float:
    saturation = gaussian_saturation_energy_j(structure, width_factor)

    def residual(displacement_fm: float) -> float:
        return (
            gaussian_self_energy_j(
                structure, displacement_fm * 1e-15, width_factor
            )
            / saturation
            - fraction
        )

    return brentq(residual, 1e-3, 1e5, xtol=1e-10) * 1e-15


def write_source_values(structure: TubulinStructure, pdb_sha256: str) -> None:
    element_counts = Counter(structure.elements)
    rows = [
        ("PDB structure", "1JFF", "RCSB PDB; doi:10.1006/jmbi.2001.5077"),
        ("PDB SHA-256", pdb_sha256, "Downloaded coordinate-file checksum"),
        ("modeled heavy atoms", len(structure.elements), "ATOM records in chains A/B"),
        ("modeled residues", structure.modeled_residues, "Residues represented in chains A/B"),
        ("deposited residues", DEPOSITED_RESIDUES, "RCSB 1JFF entry"),
        ("completeness scale", structure.completeness_scale, "896 / modeled residues"),
        ("dimer mass kDa", RCSB_DIMER_MASS_KDA, "RCSB 1JFF structure weight"),
        ("protofilaments", PROTOFILAMENTS, "Fourniol et al. 2010; doi:10.1083/jcb.201007081"),
        ("centre radius nm", MICROTUBULE_CENTRE_RADIUS_M * 1e9, "Cylindrical domain-model input"),
        ("axial dimer spacing nm", DIMER_AXIAL_SPACING_M * 1e9, "Fourniol et al. 2010; doi:10.1083/jcb.201007081"),
        ("maximum axial layers", MAX_AXIAL_LAYERS, "numerical lattice-tail control"),
        ("maximum dimers", PROTOFILAMENTS * MAX_AXIAL_LAYERS, "13 protofilaments times maximum axial layers"),
        ("carbon profile radius fm", CARBON_PROFILE_RADIUS_M * 1e15, "Hameroff-Penrose model input"),
    ]
    rows.extend(
        (f"modeled {element} nuclei", count, "1JFF ATOM records")
        for element, count in sorted(element_counts.items())
    )
    with SOURCE_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parameter", "value", "provenance"])
        writer.writerows(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    structure = load_tubulin_structure(PDB_PATH)
    pdb_sha256 = hashlib.sha256(PDB_PATH.read_bytes()).hexdigest()
    write_source_values(structure, pdb_sha256)

    internal_coefficients = internal_cross_coefficients_j_m2(structure)
    test_ratio = 1e-3
    exact_axial = 2.0 - 1.0 / (1.0 - test_ratio) - 1.0 / (1.0 + test_ratio)
    exact_radial = 2.0 - 2.0 / math.sqrt(1.0 + test_ratio**2)
    assert math.isclose(exact_axial, -2.0 * test_ratio**2, rel_tol=1.1e-6)
    assert math.isclose(exact_radial, test_ratio**2, rel_tol=1.1e-6)
    layers_sweep = np.unique(
        np.rint(np.geomspace(1, MAX_AXIAL_LAYERS, 30)).astype(int)
    )
    domain_coefficients = {
        profile: np.array(
            [domain_cross_coefficient_j_m2(int(layers), profile) for layers in layers_sweep]
        )
        for profile in DISPLACEMENT_PROFILES
    }

    displacement_fm = np.unique(
        np.sort(
            np.append(
                np.geomspace(0.25, 100.0, 100),
                [2.5, 5.0, 25.0, 50.0],
            )
        )
    )
    displacement_m = displacement_fm * 1e-15
    representative_displacement_m = 2.5e-15
    max_layers = int(layers_sweep[-1])
    max_dimers = PROTOFILAMENTS * max_layers

    sweep_rows = []
    saturation_results: dict[str, dict[str, float]] = {}
    required_curves: dict[tuple[str, float], np.ndarray] = {}

    for width_name, width_factor in PROFILE_MODELS.items():
        self_energy = gaussian_self_energy_j(
            structure, displacement_m, width_factor
        )
        saturation = gaussian_saturation_energy_j(structure, width_factor)
        saturation_fraction = self_energy / saturation
        saturation_results[width_name] = {
            "50": saturation_displacement_m(structure, width_factor, 0.50),
            "90": saturation_displacement_m(structure, width_factor, 0.90),
            "energy": saturation,
        }

        axial_cross_per_dimer = (
            internal_coefficients["axial"]
            + domain_coefficients["axial"][-1] / max_dimers
        ) * displacement_m**2
        total_per_dimer = self_energy + axial_cross_per_dimer
        assert np.all(np.diff(self_energy) > 0.0)
        assert np.all((saturation_fraction > 0.0) & (saturation_fraction < 1.0))
        assert np.all(total_per_dimer > 0.0)

        for tau_s in TARGET_TAU_S:
            required_curves[(width_name, tau_s)] = HBAR_JS / (
                tau_s * total_per_dimer
            )
        assert np.allclose(
            required_curves[(width_name, 0.025)]
            / required_curves[(width_name, 0.500)],
            20.0,
            rtol=1e-12,
        )

        for index, displacement in enumerate(displacement_fm):
            for tau_s in TARGET_TAU_S:
                sweep_rows.append(
                    (
                        width_name,
                        f"{width_factor:.12g}",
                        f"{displacement:.9g}",
                        f"{self_energy[index]:.9e}",
                        f"{axial_cross_per_dimer[index]:.9e}",
                        f"{total_per_dimer[index]:.9e}",
                        f"{saturation_fraction[index]:.9e}",
                        f"{tau_s * 1000.0:.0f}",
                        f"{required_curves[(width_name, tau_s)][index]:.9e}",
                    )
                )

    with SWEEP_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "profile_width_model",
                "sigma_C_over_a_C",
                "displacement_fm",
                "nuclear_self_e_G_per_dimer_J",
                "axial_cross_e_G_per_dimer_J",
                "total_e_G_per_dimer_J",
                "self_saturation_fraction",
                "tau_ms",
                "stationary_geometric_dimers_required",
            ]
        )
        writer.writerows(sweep_rows)

    domain_rows = []
    reference_width_name = "sphere-equivalent Gaussian"
    reference_width_factor = PROFILE_MODELS[reference_width_name]
    reference_self = gaussian_self_energy_j(
        structure, representative_displacement_m, reference_width_factor
    )
    for profile in DISPLACEMENT_PROFILES:
        internal_coefficient = (
            0.0 if profile == "cross-neutral" else internal_coefficients[profile]
        )
        for layers, domain_coefficient in zip(
            layers_sweep, domain_coefficients[profile]
        ):
            dimers = PROTOFILAMENTS * int(layers)
            internal_cross = dimers * internal_coefficient * representative_displacement_m**2
            domain_cross = domain_coefficient * representative_displacement_m**2
            self_total = dimers * reference_self
            total = self_total + internal_cross + domain_cross
            assert total > 0.0
            domain_rows.append(
                (
                    profile,
                    int(layers),
                    dimers,
                    f"{self_total:.9e}",
                    f"{internal_cross:.9e}",
                    f"{domain_cross:.9e}",
                    f"{total:.9e}",
                    f"{(internal_cross + domain_cross) / self_total:.9e}",
                )
            )

    with DOMAIN_CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "displacement_profile",
                "axial_layers",
                "tubulin_dimers",
                "nuclear_self_E_G_J",
                "intra_dimer_cross_E_G_J",
                "inter_dimer_cross_E_G_J",
                "total_E_G_J",
                "cross_over_self",
            ]
        )
        writer.writerows(domain_rows)

    fig, axes = plt.subplots(2, 2, figsize=(9.0, 8.2))
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.09, top=0.90, wspace=0.28, hspace=0.34)
    fig.suptitle("Geometric $E_G$ test for recruited tubulin domains", fontsize=13, fontweight="bold")

    ax_sat, ax_required, ax_cross, ax_scale = axes.flat
    line_styles = {
        "sphere-equivalent Gaussian": "-",
        "direct Gaussian width": "--",
    }
    for width_name, width_factor in PROFILE_MODELS.items():
        self_energy = gaussian_self_energy_j(structure, displacement_m, width_factor)
        saturation = gaussian_saturation_energy_j(structure, width_factor)
        ax_sat.plot(
            displacement_fm,
            self_energy / saturation,
            line_styles[width_name],
            color="black",
            linewidth=1.8,
            label=width_name,
        )
        delta90_fm = saturation_results[width_name]["90"] * 1e15
        ax_sat.axvline(delta90_fm, color="0.65", linewidth=0.7, linestyle=":")
    ax_sat.axvline(2.5, color="0.35", linewidth=0.9, linestyle="-.")
    ax_sat.text(2.5, 0.015, r"$a_C$", rotation=90, ha="right", va="bottom", fontsize=7)
    ax_sat.set_xscale("log")
    ax_sat.set_ylim(0.0, 1.04)
    ax_sat.set_xlabel(r"Branch displacement $\Delta R$ [fm]")
    ax_sat.set_ylabel(r"Nuclear self term $e_G/e_G(\infty)$")
    ax_sat.set_title("A - Displacement saturation", fontsize=10)
    ax_sat.legend(fontsize=7, loc="lower right")

    colours = {0.025: "black", 0.500: "0.45"}
    for width_name in PROFILE_MODELS:
        for tau_s in TARGET_TAU_S:
            ax_required.plot(
                displacement_fm,
                required_curves[(width_name, tau_s)],
                line_styles[width_name],
                color=colours[tau_s],
                linewidth=1.6,
                label=f"{tau_s * 1000:.0f} ms, {width_name}",
            )
    ax_required.axhline(1e9, color="0.75", linewidth=0.8, linestyle=":")
    ax_required.axhline(2e10, color="0.75", linewidth=0.8, linestyle=":")
    ax_required.text(95.0, 1.05e9, r"HP 500 ms", ha="right", va="bottom", fontsize=6.5, color="0.4")
    ax_required.text(95.0, 2.1e10, r"HP 25 ms", ha="right", va="bottom", fontsize=6.5, color="0.4")
    ax_required.set_xscale("log")
    ax_required.set_yscale("log")
    ax_required.set_xlabel(r"Branch displacement $\Delta R$ [fm]")
    ax_required.set_ylabel(r"Stationary geometric $N_G^*(\tau)$")
    ax_required.set_title("B - Threshold count without calibration", fontsize=10)
    ax_required.legend(fontsize=6.4, loc="upper right")

    profile_markers = {"axial": "o", "radial": "s", "cross-neutral": "^"}
    for profile in DISPLACEMENT_PROFILES:
        rows = [row for row in domain_rows if row[0] == profile]
        dimers = np.array([row[2] for row in rows], dtype=float)
        cross_fraction = np.abs(np.array([float(row[7]) for row in rows]))
        ax_cross.plot(
            dimers,
            np.maximum(cross_fraction, 1e-30),
            marker=profile_markers[profile],
            markersize=3,
            linewidth=1.0,
            color="black" if profile == "axial" else "0.5",
            linestyle="-" if profile != "cross-neutral" else ":",
            label=profile,
        )
    ax_cross.set_xscale("log")
    ax_cross.set_yscale("log")
    ax_cross.set_xlabel("Recruited tubulin dimers")
    ax_cross.set_ylabel(r"$|E_{\rm cross}|/E_{\rm self}$")
    ax_cross.set_title(r"C - Cross terms at $\Delta R=2.5$ fm", fontsize=10)
    ax_cross.legend(fontsize=7)
    ax_cross.text(
        16.0,
        2e-30,
        "cross-neutral: zero expectation (plot floor)",
        fontsize=6.5,
        color="0.4",
    )

    for profile in ("axial", "radial"):
        rows = [row for row in domain_rows if row[0] == profile]
        dimers = np.array([row[2] for row in rows], dtype=float)
        total_energy = np.array([float(row[6]) for row in rows])
        ax_scale.plot(
            dimers,
            total_energy,
            marker=profile_markers[profile],
            markersize=3,
            linewidth=1.2,
            color="black" if profile == "axial" else "0.5",
            label=profile,
        )
    ax_scale.plot(
        layers_sweep * PROTOFILAMENTS,
        layers_sweep * PROTOFILAMENTS * reference_self,
        ":",
        color="0.25",
        linewidth=1.0,
        label="self terms only",
    )
    ax_scale.set_xscale("log")
    ax_scale.set_yscale("log")
    ax_scale.set_xlabel("Recruited tubulin dimers")
    ax_scale.set_ylabel(r"Domain $E_G$ [J]")
    ax_scale.set_title("D - Computed domain scaling", fontsize=10)
    ax_scale.legend(fontsize=7)

    for axis in axes.flat:
        axis.grid(True, which="both", color="0.88", linewidth=0.6)

    fig.savefig(FIG_PATH, dpi=220, facecolor="white")
    fig.savefig(FIG_PDF_PATH, facecolor="white")
    plt.close(fig)

    print("Geometric E_G sweep from finite Gaussian nuclear profiles")
    print(f"PDB: 1JFF, SHA-256 {pdb_sha256}")
    print(
        f"Modeled atoms: {len(structure.elements)}; residues: "
        f"{structure.modeled_residues}/{DEPOSITED_RESIDUES}; "
        f"scale={structure.completeness_scale:.6f}"
    )
    print("Internal cross coefficients [J m^-2]:", internal_coefficients)
    trace_scale = max(abs(value) for value in internal_coefficients.values())
    trace_residual = sum(internal_coefficients.values())
    assert abs(trace_residual) <= 1e-12 * trace_scale
    print(f"Internal Hessian trace residual: {trace_residual:.3e} J m^-2")
    for width_name, width_factor in PROFILE_MODELS.items():
        delta50 = saturation_results[width_name]["50"] * 1e15
        delta90 = saturation_results[width_name]["90"] * 1e15
        self_at_reference = gaussian_self_energy_j(
            structure, representative_displacement_m, width_factor
        )
        cross_at_reference = (
            internal_coefficients["axial"]
            + domain_coefficients["axial"][-1] / max_dimers
        ) * representative_displacement_m**2
        total_at_reference = self_at_reference + cross_at_reference
        print(
            f"{width_name}: delta_50={delta50:.3f} fm; delta_90={delta90:.3f} fm; "
            f"N500(2.5 fm)={HBAR_JS / (0.500 * total_at_reference):.3e}; "
            f"N25(2.5 fm)={HBAR_JS / (0.025 * total_at_reference):.3e}"
        )
    for profile in ("axial", "radial"):
        coefficient = domain_coefficients[profile][-1]
        fraction = (
            max_dimers
            * internal_coefficients[profile]
            + coefficient
        ) * representative_displacement_m**2 / (max_dimers * reference_self)
        print(
            f"{profile} cross/self at N={max_dimers}: {fraction:.3e}"
        )
    tail_bound = axial_tail_bound_j_per_dimer(
        max_layers, representative_displacement_m
    )
    print(
        f"Axial lattice tail beyond L={max_layers}: "
        f"{tail_bound:.3e} J/dimer; "
        f"{tail_bound / reference_self:.3e} of the self term"
    )
    print(f"Wrote {SOURCE_CSV_PATH}")
    print(f"Wrote {SWEEP_CSV_PATH}")
    print(f"Wrote {DOMAIN_CSV_PATH}")
    print(f"Wrote {FIG_PATH}")
    print(f"Wrote {FIG_PDF_PATH}")


if __name__ == "__main__":
    main()
