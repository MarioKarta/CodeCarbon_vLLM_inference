import asyncio
from vllm.entrypoints.openai.cli_args import make_arg_parser
from vllm.entrypoints.openai.api_server import run_server
from vllm.utils import FlexibleArgumentParser  # Import FlexibleArgumentParser

def main():
    parser = FlexibleArgumentParser()  # Use FlexibleArgumentParser instead of argparse.ArgumentParser
    parser = make_arg_parser(parser)
    args = parser.parse_args([])

    # Override arguments as needed
    args.model = "meta-llama/Llama-3.1-8B"
    args.dtype = "float16"
    args.max_model_len = 4096
    args.tensor_parallel_size = 1
    args.max_batch_size = 4
    args.max_queue_size = 32
    args.num_batch_threads = 2
    args.uvicorn_log_level = "info"
    args.disable_uvicorn_access_log = False
    args.enable_request_id_headers = False
    args.chat_template_content_format = "auto"
    args.enable_ssl_refresh = False
    args.log_stats = True
    args.response_mode = "stream"


    asyncio.run(run_server(args))

if __name__ == "__main__":
    main()
