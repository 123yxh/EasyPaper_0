from openai import OpenAI
import re
import streamlit as st
from .prompt_config import ACADEMIC_PROMPTS, SYSTEM_PROMPTS
from .model_config import MODEL_PROVIDERS

# 辅助函数--提取英文关键词
# def extract_english_keywords(text: str) -> list:
#     match = re.search(r'英文关键词:\s*([^\n;]+)', text)
#     if not match:
#         return []
#     keywords_str = match.group(1).strip().rstrip(';')
#     return [kw.strip() for kw in keywords_str.split(',')]

def extract_english_keywords(text: str) -> list:
    """
    英文关键词提取函数
    1. 不依赖严格的标点符号格式
    2. 支持多种分隔符（逗号、分号、空格等）
    3. 自动过滤空白和无效项
    """
    # 正则表达式，匹配多种格式
    match = re.search(
        r'(?:英文关键词|keywords?)[:\s]*([^;\n]+)',
        text,
        re.IGNORECASE  # 不区分大小写
    )

    if not match:
        return []

    # 提取关键词部分并处理
    keywords_str = match.group(1).strip()

    # 支持多种分隔符：逗号、分号、空格等
    keywords = re.split(r'[,;\s]\s*', keywords_str)

    # 过滤处理
    return [kw.strip() for kw in keywords if kw.strip()]

# 辅助函数--提取分数
# def extract_score(text: str) -> int:
#
#     parts = text.split(":")
#     if len(parts) == 2:
#         return int(parts[1].strip())
#     else:
#         raise ValueError("文本格式不符合预期")

def extract_score(text: str) -> dict:
    """
    LLM响应中提取评分信息

    返回: {
        "total": int,
        "keyword": int,
        "semantic": int
    }
    """
    patterns = {
        "total": r"总评分:\s*(\d+)",
        "keyword": r"关键词得分:\s*(\d+)",
        "semantic": r"语义得分:\s*(\d+)"
    }

    scores = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            try:
                scores[key] = int(match.group(1))
            except (ValueError, IndexError):
                scores[key] = 0

    # 确保至少返回总分
    if "total" not in scores:
        raise ValueError("无法从文本中提取评分信息: \n" + text)

    return scores

# 定义访问url
def get_openai_client():
    if not st.session_state.api_key:
        st.error("请输入API Key")
        return None

    return OpenAI(
        api_key=st.session_state.api_key,
        base_url=MODEL_PROVIDERS[st.session_state.model_provider]["base_url"]
    )

# 提取关键词的llm设置
def get_keywords_from_query(client, user_query: str, data_source) -> list:
    completion = client.chat.completions.create(
        model=st.session_state.keyword_model,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPTS["keyword_expert"].format(paper_source=data_source)},
            {'role': 'user', 'content': user_query}
        ]
    )
    return extract_english_keywords(completion.choices[0].message.content)

# 获取reference的llm设置
def get_reference(client, english_summary: str) -> str:
    completion = client.chat.completions.create(
        model=st.session_state.similarity_model,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPTS["reference_expert"]},
            {'role': 'user', 'content': english_summary}
        ],
        temperature=0  # 完全确定性输出
    )
    return completion.choices[0].message.content


# 获取中文摘要的llm设置
def get_chinese_summary(client, english_summary: str) -> str:
    completion = client.chat.completions.create(
        model=st.session_state.similarity_model,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPTS["translation_expert"]},
            {'role': 'user', 'content': english_summary}
        ]
    )
    return completion.choices[0].message.content

# 对所有文章计算评分并返回结果
def sort_score(client, results, query) -> list:
    scored_articles = []
    for article in results:
        # 统一获取摘要以及标题--Arxiv与IEEE
        abstract = getattr(article, 'summary', getattr(article, 'Abstract', article.get('abstract') if isinstance(article, dict) else None))
        # title = article.title if hasattr(article, 'title') else article['title']
        completion = client.chat.completions.create(
            model=st.session_state.similarity_model,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPTS["similarity_expert"]},
                {'role': 'user', 'content': f"用户需求: {query}\n文章摘要: {abstract}"}
            ]
        )
        try:
            score_dict  = extract_score(completion.choices[0].message.content)
            scored_articles.append((score_dict["total"], article))
        except Exception as e:
            st.error(f"评分出错: {str(e)}")
            scored_articles.append((0, article))
    return scored_articles

st.markdown(
    """
        <style>
            /* 固定容器高度和滚动样式 */
            .fixed-content {
                height: 10px;  /* 设置固定高度 */
                overflow-y: auto;  /* 添加垂直滚动条 */
                padding: 1rem;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
    
            /* 美化滚动条 */
            .fixed-content::-webkit-scrollbar {
                width: 12px;
                background-color: #F5F5F5;
            }
    
            .fixed-content::-webkit-scrollbar-thumb {
                border-radius: 10px;
                -webkit-box-shadow: inset 0 0 6px rgba(0,0,0,.3);
                background-color: #555;
            }
    
            /* PDF容器样式保持不变 */
            .pdf-container {
                height: 800px;
                overflow-y: scroll;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
            }
    
            .pdf-container iframe {
                width: 100%;
                height: 100%;
                border: none;
            }
    
            /* 确保列内容不会超出 */
            .stColumn {
                height: 800px;
                overflow-y: auto;
            }
        </style>
    """, unsafe_allow_html=True)

# 文献分析---流式输出
def get_streaming_response(client, messages):
    """获取流式响应"""
    try:
        # 创建流式响应
        stream = client.chat.completions.create(
            model=st.session_state.similarity_model,
            messages=messages,
            stream=True  # 启用流式输出
        )
        return stream
    except Exception as e:
        st.error(f"获取响应时出错: {str(e)}")
        return None

# 显示流式响应
def display_streaming_response(stream, placeholder):
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            full_response += chunk.choices[0].delta.content
            # 实时更新显示的内容
            placeholder.markdown(full_response + "▌")
    # 完成后移除光标
    placeholder.markdown(full_response)
    return full_response

# 对话魔板设置
def render_chat_area(middle_col, client, operation_type):
    with middle_col:
        st.markdown('<div class="fixed-content">', unsafe_allow_html=True)
        st.markdown("## 💬 对话区域")

        # 原子化状态管理（确保即时更新）
        current_prompt = f"{ACADEMIC_PROMPTS[operation_type]}\n\nPDF内容:\n{st.session_state.get('pdf_content', '')}"
        
        # 使用深层状态对比
        if "messages" not in st.session_state or \
           st.session_state.messages[0]["content"] != current_prompt:
            
            # 保留非系统消息的历史
            preserved_messages = [msg for msg in st.session_state.get("messages", []) 
                                 if msg["role"] != "system"]
            
            # 原子化更新系统提示
            st.session_state.messages = [
                {"role": "system", "content": current_prompt},
                *preserved_messages
            ]
            
            # 强制同步渲染
            st.rerun()

        # 显示即时更新的对话
        for message in st.session_state.messages[1:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # 即时响应用户输入
        if user_input := st.chat_input("请输入您的问题..."):
            # 使用最新上下文生成响应
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # 流式响应处理
            with st.chat_message("assistant"):
                full_response = ""
                placeholder = st.empty()
                
                # 获取最新消息上下文
                messages = st.session_state.messages + [
                    {"role": "user", "content": user_input}
                ]
                
                stream = client.chat.completions.create(
                    model=st.session_state.similarity_model,
                    messages=messages,
                    stream=True
                )
                
                for chunk in stream:
                    text = chunk.choices[0].delta.content or ""
                    full_response += text
                    placeholder.markdown(full_response + "▌")
                
                placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

        st.markdown('</div>', unsafe_allow_html=True)
