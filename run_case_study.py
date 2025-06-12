import os
import csv
import glob
import re
import statistics
from benchmark import run_benchmark
from benchmark_util import count_valid_tokens

FACILITY_NAME = "Council Bluffs, Iowa"
NUM_REPEATS = 5

FU_CONFIGS = {
    "strict": {"ttft": 0.5, "tpot": 0.1},
    "normal": {"ttft": 1.0, "tpot": 0.2}
}

RPS_VALUES = [8, 16, 32, 64, 128]
SUMMARY_DIR = "summary"
os.makedirs(SUMMARY_DIR, exist_ok=True)


def load_txt_result(result_path):
    parsed = []
    current = {}
    with open(result_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("TTFT:"):
                current["ttft"] = float(line.split(":")[1].strip().split()[0])
            elif line.startswith("TPOT:"):
                current["tpot"] = float(line.split(":")[1].strip().split()[0]) / 1000
            elif line.startswith("Output Tokens:"):
                current["output_token_length"] = int(line.split(":")[1].strip())
                parsed.append(current)
                current = {}
    return parsed


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
        "Avg CFU (kgCO2eq/FU)", "Std CFU",
        "Avg EFU (kWh/FU)", "Std EFU",
        "PUE", "CI (kgCO2/kWh)",
        "Avg Energy Consumed (kWh)", "Avg Output Tokens", "Avg Valid FU Tokens", "Avg Emissions (kgCO2eq)",
        "CSV Files", "TXT Files"
    ])

    for rps in RPS_VALUES:
        print(f"\n▶ Running {model_name} | RPS: {rps} (x{NUM_REPEATS})")

        results_per_fu = {label: {
            "cfus": [], "efus": [], "valid_tokens": []
        } for label in FU_CONFIGS}
        emissions_list, energy_list, output_tokens_list = [], [], []
        csv_files, txt_files = [], []
        pue_used, ci_used = None, None

        for i in range(NUM_REPEATS):
            result = run_benchmark(
                model_name=model_name,
                model_url=model_url,
                rps=rps,
                ttft_thresh=999,
                tpot_thresh=999,
                facility_name=FACILITY_NAME,
                index=benchmark_index
            )
            benchmark_index += 1

            parsed = load_txt_result(result["txt_path"])

            for label, fu in FU_CONFIGS.items():
                valid = count_valid_tokens(parsed, fu["ttft"], fu["tpot"])
                if valid > 0:
                    cfu = result["emissions"] / valid
                    efu = result["energy_consumed"] / valid
                else:
                    cfu = 0.0
                    efu = 0.0
                results_per_fu[label]["cfus"].append(cfu)
                results_per_fu[label]["efus"].append(efu)
                results_per_fu[label]["valid_tokens"].append(valid)
                print(f"FU {label}, RUN {i}: {valid} valid tokens, {cfu:.20f} kgCO2eq/FU, {efu:.20f} kWh/FU")

            emissions_list.append(result["emissions"])
            energy_list.append(result["energy_consumed"])
            output_tokens_list.append(result["total_output_tokens"])
            pue_used = result["PUE"]
            ci_used = result["CI"]
            csv_files.append(os.path.basename(result["csv_path"]))
            txt_files.append(os.path.basename(result["txt_path"]))
            print(f"RESULTS RUN {i}: {result['CI']:.6f} kgCo2eq/kWh, {result['energy_consumed']:.6f} kWh, {result['emissions']:.6f} kgCO2eq")

        def avg(lst): return sum(lst) / len(lst) if lst else 0.0
        def std(lst): return statistics.stdev(lst) if len(lst) > 1 else 0.0

        for label in FU_CONFIGS:
            cfus = results_per_fu[label]["cfus"]
            efus = results_per_fu[label]["efus"]
            valid_tokens = results_per_fu[label]["valid_tokens"]

            writer.writerow([
                model_name,
                label,
                rps,
                f"{avg(cfus):.20f}",
                f"{std(cfus):.20f}",
                f"{avg(efus):.20f}",
                f"{std(efus):.20f}",
                pue_used,
                f"{ci_used:.6f}",
                f"{avg(energy_list):.6f}",
                f"{avg(output_tokens_list):.2f}",
                f"{avg(valid_tokens):.2f}",
                f"{avg(emissions_list):.6f}",
                ";".join(csv_files),
                ";".join(txt_files)
            ])

print(f"\n✅ Case study complete. Results saved to: {summary_path}")
