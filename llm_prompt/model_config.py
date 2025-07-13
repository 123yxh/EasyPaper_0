# Define providers and their available models
MODEL_PROVIDERS = {
    "Silicon Flow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "models": [
            "Qwen/Qwen2.5-14B-Instruct",
            "Qwen/QwQ-32B",
            "Qwen/Qwen1.5-72B"
        ]
    },
    "DeppSeek": {
        "base_url": "https://api.deepseek.com",
        "models": [
            "deepseek-reasoner",
            "deepseek-chat"
        ]
    }
}