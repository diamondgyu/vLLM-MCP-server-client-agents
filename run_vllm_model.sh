python -m vllm.entrypoints.openai.api_server \
    --model "Qwen/Qwen3-30B-A3B-Instruct-2507" \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.8 \
    --max-model-len 4096 \ 
    --host "0.0.0.0" \
    --api-key "ASTRA_KEY"