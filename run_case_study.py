# run_case_study.py

import os
import csv
import glob
import re
import statistics
from benchmark import run_benchmark

FACILITY_NAME = "Council Bluffs, Iowa"
NUM_REPEATS = 5

FU_CONFIGS = {
    "strict": {"ttft": 0.5, "tpot": 0.1},
    "normal": {"ttft": 1.0, "tpot": 0.2}
}

RPS_VALUES = [8, 16, 32, 64, 128]

SUMMARY_DIR = "summary"
os.makedirs(SUMMARY_DIR, exist_ok=True)

model_name = input("Enter model name (e.g., bigscience/bloom-7b1): ").strip()
model_url = input("Enter model URL (e.g., http://localhost:8000/v1/completions): ").strip()

output_files = glob.glob(os.path.join("output", "output_*.csv"))
existing_indices = [
    int(m.group(1)) for path in output_files
    if (m := re.search(r"output_(\d+)\.csv$", os.path.basename(path)))
]
benchmark_index = max(existing_indices) + 1 if existing_indices else 0

summary_path = os.path.join(SUMMARY_DIR, f"case_study_{model_name.replace('/', '_')}.csv")

with open(summary_path, mode="w", newline="") as summary_file:
    writer = csv.writer(summary_file)
    writer.writerow([
        "Model", "FU_Config", "RPS",
        "Avg CFU (kgCO2eq/FU)", "Std CFU", "Avg EFU (kWh/FU)", "Std EFU",
        "PUE", "CI (kgCO2/kWh)", "Avg Energy Consumed (kWh)", "Avg Output Tokens", "Avg Valid FU Tokens", "Avg Emissions (kgCO2eq)",
        "CSV Files", "TXT Files"
    ])

    for fu_label, fu in FU_CONFIGS.items():
        for rps in RPS_VALUES:
            print(f"\n▶ Running {model_name} | {fu_label} | RPS: {rps} (x{NUM_REPEATS})")
            cfu_list = []
            efu_list = []
            emissions_list = []
            energy_list = []
            output_tokens_list = []
            valid_tokens_list = []
            csv_files = []
            txt_files = []
            pue_used = None
            ci_list = []

            for i in range(NUM_REPEATS):
                result = run_benchmark(
                    model_name=model_name,
                    model_url=model_url,
                    rps=rps,
                    ttft_thresh=fu["ttft"],
                    tpot_thresh=fu["tpot"],
                    facility_name=FACILITY_NAME,
                    index=benchmark_index
                )
                benchmark_index += 1

                if result["cfu"] is not None:
                    cfu_list.append(result["cfu"])
                    efu_list.append(result["efu"])
                    emissions_list.append(result["emissions"])
                    energy_list.append(result["energy_consumed"])
                    output_tokens_list.append(result["total_output_tokens"])
                    valid_tokens_list.append(result["valid_tokens"])
                else:
                    # Fill in 0s for failed runs
                    cfu_list.append(0.0)
                    efu_list.append(0.0)
                    emissions_list.append(0.0)
                    energy_list.append(0.0)
                    output_tokens_list.append(0)
                    valid_tokens_list.append(0)

                print(f"RUN RESULTS {i}: Token ratio={result['valid_tokens']}/{result['total_output_tokens']}, CFU={result['cfu']}, EFU={result['efu']}, Emissions={result['emissions']}, Energy={result['energy_consumed']}")

                csv_files.append(os.path.basename(result["csv_path"]))
                txt_files.append(os.path.basename(result["txt_path"]))
                pue_used = result["PUE"]
                ci_list.append(result["CI"])

            def safe_avg(lst): return sum(lst) / len(lst) if lst else 0.0
            def safe_std(lst): return statistics.stdev(lst) if len(lst) > 1 else 0.0

            writer.writerow([
                model_name,
                fu_label,
                rps,
                f"{safe_avg(cfu_list):.20f}",
                f"{safe_std(cfu_list):.20f}",
                f"{safe_avg(efu_list):.20f}",
                f"{safe_std(efu_list):.20f}",
                pue_used,
                f"{safe_avg(ci_list):.6f}",
                f"{safe_avg(energy_list):.6f}",
                f"{safe_avg(output_tokens_list):.2f}",
                f"{safe_avg(valid_tokens_list):.2f}",
                f"{safe_avg(emissions_list):.6f}",
                ";".join(csv_files),
                ";".join(txt_files)
            ])

print(f"\n✅ Case study complete. Results saved to: {summary_path}")
