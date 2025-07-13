from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from openai import OpenAI

client = OpenAI(api_key="", base_url="https://api.siliconflow.cn/v1")

def get_keywords_from_query(client, user_query: str, model_name) -> str:
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {'role': 'system', 'content': "你是一个有用的助手"},
            {'role': 'user', 'content': user_query}
        ]
    )
    return completion.choices[0].message.content

# 第一个 Agent：关键词提取
def summarizer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if "messages" not in state or not state["messages"]:
        return {"extracted_keywords": "错误：没有提供用户消息"}

    user_input = state["messages"][-1].content
    paper_source = state.get("paper_source")
    user_keywords = state.get("user_keywords")

    if user_keywords:
        en_keywords = ", ".join(user_keywords)
        response = f"英文关键词: {en_keywords};"
    else:
        prompt = f"""
            你是一个优秀的学术领域专家，能够根据用户的输入文本以及选择的文献信息来源{paper_source}, 总结出细分领域的科研关键词;

            以下是规则：
                1. 对于ArXiv或者IEEE：
                   - 返回中文关键词和英文缩写关键词，格式如下：
                     中文关键词: 大模型, 分层联邦学习, 模型蒸馏;
                     英文关键词: llm, hfl, md;

                2. 对于SciHub：
                   - 返回中文关键词和英文全称关键词，格式如下：
                     中文关键词: 大模型, 分层联邦学习, 模型蒸馏;
                     英文关键词: Large Language Models, Hierarchical Federated Learning, Model Distillation;

            注意：
                - 如果用户提供了关键词，则直接采用用户的关键词即可，不需要进一步分析。
                - 只会输入一个文献信息来源，所以上述两种规则最终只会返回一种格式的内容

            现在请根据以下输入生成关键词：
                "{user_input}"
            """
        result = get_keywords_from_query(client, prompt, model_name="Qwen/Qwen3-32B")
        response = result

    return {
        **state,
        "extracted_keywords": response,
        "error": False
    }

# 第二个 Agent：格式验证
def validator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    extracted = state.get("extracted_keywords", "")
    paper_source = state.get("paper_source", "")

    if not extracted:
        validation = "错误：没有提取到关键词"
    elif "英文关键词:" not in extracted:
        validation = "格式错误：缺少'英文关键词:'字段。"
    elif paper_source in ["ArXiv", "IEEE"] and any(
            len(kw.strip()) > 3 for kw in extracted.split("英文关键词:")[-1].split(",")):
        validation = "格式错误：ArXiv/IEEE 应使用缩写形式。"
    elif paper_source == "SciHub" and any(
            len(kw.strip().split()) != 1 for kw in extracted.split("英文关键词:")[-1].split(",")):
        validation = "格式错误：SciHub 应使用完整英文词组（不能拆分）。"
    else:
        validation = "格式正确。"

    return {
        **state,
        "validation_result": validation,
        "need_correction": not validation.startswith("格式正确") and not state.get("error")
    }

# 第三个 Agent：错误处理和重新生成
def correction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if not state.get("need_correction"):
        return state

    paper_source = state.get("paper_source")
    original_input = state["messages"][-1].content
    error_message = state.get("validation_result", "")
    original_output = state.get("extracted_keywords", "")

    prompt = f"""
    你是一个专业的学术关键词修正专家。之前的提取结果有误，请根据以下信息重新生成正确的关键词：

    原始输入: {original_input}
    文献来源: {paper_source}
    错误信息: {error_message}
    原输出: {original_output}

    生成要求:
        1. 对于ArXiv或者IEEE文献来源：
           - 返回中文关键词和英文缩写关键词，格式如下：
             中文关键词: 大模型, 分层联邦学习, 模型蒸馏;
             英文关键词: llm, hfl, md;

        2. 对于SciHub文献来源：
           - 返回中文关键词和英文全称关键词，格式如下：
             中文关键词: 大模型, 分层联邦学习, 模型蒸馏;
             英文关键词: Large Language Models, Hierarchical Federated Learning, Model Distillation;

        注意：
            - 如果用户提供了关键词，则直接采用用户的关键词即可，不需要进一步分析。
            - 只会输入一个文献信息来源，所以上述两种规则最终只会返回一种格式的内容

    请严格按照输出格式，直接输出修正后的关键词内容:
    """

    corrected = get_keywords_from_query(client, prompt, model_name="deepseek-ai/DeepSeek-V3")

    return {
        **state,
        "extracted_keywords": corrected,
        "validation_result": "已修正",
        "need_correction": False
    }

# 图构建
builder = StateGraph(dict)

# 添加节点
builder.add_node("summarizer", summarizer_node)
builder.add_node("validator", validator_node)
builder.add_node("corrector", correction_node)

# 添加边
builder.set_entry_point("summarizer")
builder.add_edge("summarizer", "validator")

# 修改条件边逻辑
def should_correct(state: Dict[str, Any]) -> str:
    if state.get("need_correction"):
        return "corrector"
    return END

# 使用条件边替代直接边
builder.add_conditional_edges(
    "validator",
    should_correct,
    {
        "corrector": "corrector",  # 需要修正时
        END: END  # 不需要修正时
    }
)

# 添加从corrector回到validator的边
builder.add_edge("corrector", "validator")

# 设置递归限制
config = {"recursion_limit": 10} 

# 构建图
graph = builder.compile()

# 测试输入
initial_state = {
    "messages": [HumanMessage(content="我需要查找与大模型，联邦学习相关的分层联邦学习文章。具体而言: 涉及到模型蒸馏")],
    "paper_source": "ArXiv",
    "user_keywords": None,
    "extracted_keywords": None,
    "validation_result": None,
    "need_correction": False,
    "error": False
}

# 运行流程
final_state = graph.invoke(initial_state)

# 流程图保存为 PNG 图片
try:
    graph.get_graph().draw_mermaid_png(output_file_path="multi_agent_workflow.png")
    print("✅ 流程图已保存为 multi_agent_workflow.png")
except Exception as e:
    print(f"⚠️ 无法生成流程图: {e}")

# 输出结果
print("✅ 最终提取结果：\n", final_state.get("extracted_keywords", "无结果"))
print("\n✅ 最终验证结果：\n", final_state.get("validation_result", "无结果"))