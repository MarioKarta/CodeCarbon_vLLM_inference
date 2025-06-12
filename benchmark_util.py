import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def send_request(url, payload, tokenizer):
    start_time = time.time()
    response = requests.post(url, json=payload, stream=True)

    # Measure TTFT
    full_text = ""
    ttft = None
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            data = json.loads(line[len("data: "):])
            chunk = data["choices"][0].get("text", "")
            if ttft is None:
                ttft = time.time() - start_time
            full_text += chunk
        except Exception:
            continue

    if ttft is None:
        ttft = float('inf')  # no output

    full_response_time = time.time() - start_time
    output_tokens = tokenizer.encode(full_text, add_special_tokens=False)
    num_output_tokens = len(output_tokens)
    tpot_avg = (full_response_time - ttft) / max(1, num_output_tokens)

    return {"choices": [{"text": full_text}]}, ttft, tpot_avg, num_output_tokens


def run_workload(model_name, url, prompts, rps, tokenizer):
    """
    Executes inference requests at the target rate using a thread pool,
    collecting per-prompt measurements of TTFT, TPOT, and token counts.
    """
    results = []
    interval = 1.0 / rps

    # Use ThreadPoolExecutor to maintain concurrency
    with ThreadPoolExecutor(max_workers=rps) as executor:
        future_to_prompt = {}
        next_call = time.time()

        # Schedule prompts at the specified rate
        for prompt_data in prompts:
            # Sleep until next scheduled time
            delay = next_call - time.time()
            if delay > 0:
                time.sleep(delay)

            payload = {
                "model": model_name,
                "prompt": prompt_data["prompt"],
                "temperature": 0,
                "max_tokens": 200,
                "stream": True
            }
            future = executor.submit(send_request, url, payload, tokenizer)
            future_to_prompt[future] = prompt_data
            next_call += interval

        # Gather results as they complete
        for future in as_completed(future_to_prompt):
            prompt_data = future_to_prompt[future]
            try:
                response, ttft, tpot, out_tokens = future.result()
            except Exception as e:
                # On failure, record dummy values
                response, ttft, tpot, out_tokens = {}, float('inf'), float('inf'), 0

            results.append({
                "prompt": prompt_data["prompt"],
                "token_length": prompt_data["token_length"],
                "ttft": ttft,
                "tpot": tpot,
                "output_token_length": out_tokens,
                "response": response
            })

    return results

def count_valid_tokens(results, ttft_thresh, tpot_thresh):
    """
    Counts the total number of output tokens whose TTFT and TPOT meet
    the specified thresholds.
    """
    valid_token_count = 0
    for r in results:
        if r["ttft"] <= ttft_thresh and r["tpot"] <= tpot_thresh:
            valid_token_count += r["output_token_length"]
    return valid_token_count
