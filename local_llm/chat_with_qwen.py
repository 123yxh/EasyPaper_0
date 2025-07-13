from modelscope import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

# 加载本地大模型
model_dir = snapshot_download('qwen/Qwen-14B-Chat')

tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    device_map="auto",
    trust_remote_code=True
).eval()

# 获得回复
response, history = model.chat(tokenizer, "你好", history=None)
print(response)