# benchmark.py

import os
import csv
import glob
import re
from datetime import datetime

from codecarbon import EmissionsTracker
from transformers import AutoTokenizer
from data import prepare_prompts
from benchmark_util import run_workload, count_valid_tokens
from gcp_pue import fetch_google_html_pue


def run_benchmark(model_name, model_url, rps, ttft_thresh, tpot_thresh, facility_name, index):
    num_prompts = 200

    # Create folders if they don't exist
    os.makedirs("output", exist_ok=True)
    os.makedirs("results", exist_ok=True)

    # Load tokenizer and prompts
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    prompts = prepare_prompts(model_name, num_prompts)

    # Fetch PUE and start tracker
    pue_value = fetch_google_html_pue(facility_name=facility_name)
    tracker = EmissionsTracker(
        project_name="benchmark",
        pue=pue_value
    )
    tracker.start()

    # Run benchmark
    results = run_workload(model_name, model_url, prompts, rps, tokenizer)
    emissions = tracker.stop()
    total_output_tokens = sum(r["output_token_length"] for r in results)
    valid_tokens = count_valid_tokens(results, ttft_thresh, tpot_thresh)

    # Output data
    data = tracker.final_emissions_data
    ci_kg_per_kwh = data.emissions / data.energy_consumed if data.energy_consumed > 0 else 0.0
    raw_energy = (data.ram_energy + data.cpu_energy + data.gpu_energy) / pue_value
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # CFU logic
    if valid_tokens > 0:
        cfu = emissions / valid_tokens
        efu = data.energy_consumed / valid_tokens
        cfu_metrics = [
            ("Total amount of emissions (kgCO2eq)", f"{emissions:.10f}"),
            ("Total amount of functional‐unit tokens", str(valid_tokens)),
            ("Carbon Emission per Functional Unit (kgCO2eq/FU)", f"{cfu:.20f}"),
            ("Energy Consumption per Functional Unit (kWh/FU)", f"{efu:.20f}"),
        ]
    else:
        cfu = None
        efu = None
        cfu_metrics = [("No valid tokens met the serving constraints", "True")]

    # Save CSV
    csv_path = os.path.join("output", f"output_{index}.csv")
    with open(csv_path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["metric", "value"])
        writer.writerow(["Benchmark datetime", now_str])
        writer.writerow(["Model benchmarked", model_name])
        writer.writerow(["Total prompts", str(num_prompts)])
        writer.writerow(["Request rate (rps)", str(rps)])
        writer.writerow(["TTFT threshold (s)", str(ttft_thresh)])
        writer.writerow(["TPOT threshold (s/token)", str(tpot_thresh)])
        writer.writerow(["Datacenter location", facility_name])
        writer.writerow(["PUE used", f"{pue_value:.3f}"])
        writer.writerow(["RAM energy (kWh)", f"{data.ram_energy:.6f}"])
        writer.writerow(["CPU energy (kWh)", f"{data.cpu_energy:.6f}"])
        writer.writerow(["GPU energy (kWh)", f"{data.gpu_energy:.6f}"])
        writer.writerow(["Raw IT energy before PUE (kWh)", f"{raw_energy:.6f}"])
        writer.writerow(["Total energy after PUE (kWh)", f"{data.energy_consumed:.6f}"])
        writer.writerow(["Carbon intensity used (kgCO2eq/kWh)", f"{ci_kg_per_kwh:.6f}"])
        writer.writerow(["Total output tokens", str(total_output_tokens)])
        for metric_name, metric_value in cfu_metrics:
            writer.writerow([metric_name, metric_value])

    # Save response text
    txt_path = os.path.join("results", f"results_{index}.txt")
    with open(txt_path, mode="w", encoding="utf-8") as txtfile:
        txtfile.write(f"rps: {rps}\n")
        txtfile.write(f"TTFT threshold: {ttft_thresh} s\n")
        txtfile.write(f"TPOT threshold: {tpot_thresh} s/token\n")
        for r in results:
            txtfile.write(f"Prompt: {r['prompt']}\n")
            txtfile.write(f"Token Length: {r['token_length']}\n")
            txtfile.write(f"TTFT: {r['ttft']:.3f} s\n")
            txtfile.write(f"TPOT: {r['tpot']*1000:.3f} ms\n")
            txtfile.write(f"Output Tokens: {r['output_token_length']}\n")
            txtfile.write(f"Response: {r['response']}\n")
            txtfile.write("\n" + ("—" * 40) + "\n\n")

    return {
    "csv_path": csv_path,
    "txt_path": txt_path,
    "cfu": cfu,
    "efu": efu,
    "PUE": pue_value,
    "CI": ci_kg_per_kwh,
    "energy_consumed": data.energy_consumed,
    "emissions": emissions,
    "total_output_tokens": total_output_tokens,
    "valid_tokens": valid_tokens,
    "timestamp": now_str
    }


if __name__ == "__main__":
    # Manual test (optional usage)
    output_files = glob.glob(os.path.join("output", "output_*.csv"))
    indices = [int(re.search(r"output_(\d+)\.csv$", f).group(1)) for f in output_files if re.search(r"output_(\d+)\.csv$", f)]
    next_index = max(indices) + 1 if indices else 0

    run_benchmark(
        model_name="bigscience/bloom-7b1",
        model_url="http://localhost:8000/v1/completions",
        rps=2,
        ttft_thresh=10.0,
        tpot_thresh=1.0,
        facility_name="Council Bluffs, Iowa",
        index=next_index
    )
