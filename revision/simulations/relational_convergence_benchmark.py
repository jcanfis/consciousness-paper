"""Create the source-auditable relational-convergence benchmark table."""

from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "relational_convergence_source_values.csv"
OUTPUT = ROOT / "data" / "relational_convergence_benchmark.csv"


def main() -> None:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    output_rows = []
    for row in rows:
        derived_dz = ""
        if row["statistic"] == "t":
            derived_dz = f"{float(row['statistic_value']) / math.sqrt(int(row['n'])):.3f}"

        output_rows.append(
            {
                **row,
                "derived_dz_t_over_sqrt_n": derived_dz,
                "value_status": "published; dz mathematically derived" if derived_dz else "published",
            }
        )

    fieldnames = list(output_rows[0])
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    expected = {
        "closed-loop dependency versus independent model": "0.504",
        "open-loop dependency versus independent model": "0.353",
        "closed-loop minus open-loop dependency": "0.543",
        "closed-loop non-target reinstatement": "0.667",
        "high minus low centrality hippocampal recall activity": "0.700",
    }
    actual = {
        row["measure"]: row["derived_dz_t_over_sqrt_n"]
        for row in output_rows
        if row["derived_dz_t_over_sqrt_n"]
    }
    for measure, value in expected.items():
        if actual.get(measure) != value:
            raise RuntimeError(f"Unexpected effect transformation for {measure}: {actual.get(measure)}")

    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
