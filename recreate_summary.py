# regenerate_summary.py

import os
import csv
import glob
import re
import statistics
from collections import defaultdict

# Configuration
SUMMARY_DIR = "summary"
OUTPUT_DIR = "output"
RESULTS_DIR = "Results/results"
NUM_REPEATS = 5
MODEL_NAME_FILTER = "bigscience/bloom-7b1"  # Change this as needed

os.makedirs(SUMMARY_DIR, exist_ok=True)

# Collect grouped benchmark results
grouped_results = defaultdict(list)

for csv_path in sorted(glob.glob(os.path.join(OUTPUT_DIR, "output_*.csv"))):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        values = {row[0]: row[1] for row in rows if len(row) == 2}

    if values.get("Model benchmarked") != MODEL_NAME_FILTER:
        continue

    try:
        rps = int(values["Request rate (rps)"])
        ttft = float(values["TTFT threshold (s)"])
        tpot = float(values["TPOT threshold (s/token)"])
        fu_key = "strict" if ttft <= 0.5 else "normal"
        key = (fu_key, rps)
    except Exception:
        continue

    # Extract the matching result file
    match = re.search(r"output_(\d+)\.csv$", csv_path)
    if not match:
        continue
    index = int(match.group(1))
    result_path = os.path.join(RESULTS_DIR, f"results_{index}.txt")

    output_token_count = 0
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as result_file:
            for line in result_file:
                if line.startswith("Output Tokens:"):
                    try:
                        output_token_count += int(line.strip().split(":")[1])
                    except ValueError:
                        pass

    result = {
        "cfu": float(values.get("Carbon Emission per Functional Unit (kgCO2eq/FU)", "0")),
        "efu": float(values.get("Energy Consumption per Functional Unit (kWh/FU)", "0")),
        "emissions": float(values.get("Total amount of emissions (kgCO2eq)", "0")),
        "energy": float(values.get("Total energy after PUE (kWh)", "0")),
        "tokens": int(values.get("Total amount of functional‐unit tokens", "0")),
        "output_tokens": output_token_count,
        "PUE": float(values.get("PUE used", "1")),
        "CI": float(values.get("Carbon intensity used (kgCO2eq/kWh)", "0")),
        "csv": os.path.basename(csv_path),
    }

    grouped_results[key].append(result)

# Write summary CSV
summary_path = os.path.join(SUMMARY_DIR, f"case_study_{MODEL_NAME_FILTER.replace('/', '_')}.csv")
with open(summary_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Model", "FU_Config", "RPS",
        "Avg CFU (kgCO2eq/FU)", "Std CFU",
        "Avg EFU (kWh/FU)", "Std EFU",
        "PUE", "CI (kgCO2/kWh)",
        "Avg Energy (kWh)", "Avg Output Tokens", "Avg Valid FU Tokens",
        "Avg Emissions (kgCO2eq)", "CSV Files"
    ])

    for (fu_label, rps), results in sorted(grouped_results.items()):
        if not results:
            continue

        def avg(key):
            return sum(r[key] for r in results) / len(results)

        def std(key):
            values = [r[key] for r in results]
            return statistics.stdev(values) if len(values) > 1 else 0.0

        writer.writerow([
            MODEL_NAME_FILTER,
            fu_label,
            rps,
            f"{avg('cfu'):.10f}",
            f"{std('cfu'):.10f}",
            f"{avg('efu'):.10f}",
            f"{std('efu'):.10f}",
            results[0]["PUE"],
            f"{avg('CI'):.6f}",
            f"{avg('energy'):.6f}",
            f"{avg('output_tokens'):.2f}",
            f"{avg('tokens'):.2f}",
            f"{avg('emissions'):.6f}",
            ";".join(r["csv"] for r in results)
        ])

print(f"✅ Summary regenerated at: {summary_path}")
