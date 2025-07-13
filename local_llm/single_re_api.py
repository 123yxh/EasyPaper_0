from openai import OpenAI

client = OpenAI(api_key="", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

def get_keywords_from_query(client, user_query: str) -> list:
    completion = client.chat.completions.create(
        model="qwen-turbo",
        messages=[
            {'role': 'system', 'content': "你是一个有用的助手"},
            {'role': 'user', 'content': user_query}
        ]
    )
    return completion.choices[0].message.content

user_input = "你好呀，你是谁呢？"

print(get_keywords_from_query(client, user_input))