python -m vllm.entrypoints.openai.api_server \
    --model "google/gemma-3n-E4B-it" \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.8 \
    --max-model-len 8192 \ 
    --host "0.0.0.0" \
    --api-key "ASTRA_KEY"