import random
from datasets import load_dataset
from transformers import AutoTokenizer

def prepare_prompts(model_name: str, num_prompts: int):
    """
    Prepares random instruction-only prompts and their token lengths for testing.

    Args:
        model_name (str): The name of the model's tokenizer to calculate token lengths.
        num_prompts (int): The number of prompts to return.

    Returns:
        list[dict]: A list of dictionaries containing prompts and their token lengths.
    """
    ds = load_dataset("yahma/alpaca-cleaned")

    # Filter to only include examples with no input
    no_input_examples = [ex for ex in ds["train"] if ex["input"].strip() == ""]

    # Randomly select num_prompts from filtered examples
    selected_examples = random.sample(no_input_examples, k=num_prompts)

    # Load the tokenizer for the specified model
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Extract prompts and calculate token lengths
    prompts = []
    for example in selected_examples:
        prompt = example["instruction"]
        token_length = len(tokenizer.encode(prompt, add_special_tokens=False))
        prompts.append({"prompt": prompt, "token_length": token_length})

    return prompts
