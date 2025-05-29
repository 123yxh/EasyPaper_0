import streamlit as st
st.set_page_config(page_title="文献调研助手", page_icon="🤖", layout="wide")
from datetime import datetime
import tempfile
import sys
import os
# 获取当前脚本所在目录的父目录，并将其加入到Python的搜索路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import streamlit_ext as ste
import base64
from PyPDF2 import PdfReader
from mineru.get_mineru import process_pdf, create_zip
from nabc_lab.get_nabc import get_sui_hub
from ieee_lab.get_ieee import get_ieee_results
from auxiliary.help_fun_1 import remove_duplicates
from arxiv_lab.get_arxiv import get_multiple_arxiv_results
from llm_prompt.model_config import MODEL_PROVIDERS
from llm_prompt.prompt_config import ACADEMIC_PROMPTS
from llm_prompt.academic_expert import get_keywords_from_query, get_openai_client, sort_score, get_chinese_summary, render_chat_area, get_reference

# 设置主界面
if 'current_page' not in st.session_state:
    st.session_state.current_page = "main"

# 模型服务商以及模型选择
def initialize_session_state():
    if 'model_provider' not in st.session_state:
        st.session_state.model_provider = list(MODEL_PROVIDERS.keys())[0]
    if 'api_key' not in st.session_state:
        st.session_state.api_key = "-" # 调试时使用
        # st.session_state.api_key = ""
    if 'keyword_model' not in st.session_state:
        st.session_state.keyword_model = MODEL_PROVIDERS[st.session_state.model_provider]["models"][1]
    if 'similarity_model' not in st.session_state:
        st.session_state.similarity_model = MODEL_PROVIDERS[st.session_state.model_provider]["models"][0]
    if 'operation_type_pdf_jiexi' not in st.session_state:
        st.session_state.operation_type_pdf_jiexi = "pdfreader"


# 设置背景图片
def local_bg_image(image_path):
    if not os.path.exists(image_path):
        st.error(f"图片文件 {image_path} 不存在")
        return
    with open(image_path, "rb") as img_file:
        img_bytes = img_file.read()
        encoded = base64.b64encode(img_bytes).decode()
    # 动态检测图片格式
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "jpg" if ext in [".jpg", ".jpeg"] else "png" if ext == ".png" else "jpeg"
    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/{mime_type};base64,{encoded}") !important;
        background-size: cover !important;
        background-position: center center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# 设置背景视频# 设置背景视频
def local_bg_video(video_path):
    if not os.path.exists(video_path):
        st.error(f"视频文件 {video_path} 不存在")
        return
    with open(video_path, "rb") as video_file:
        video_bytes = video_file.read()
        encoded = base64.b64encode(video_bytes).decode()
    css = f"""
    <style>
    .stApp {{
        position: relative;
        overflow: hidden;
        background: transparent;
    }}
    .bg-video {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        z-index: -1000; /* 确保视频在最底层 */
    }}
    /* 确保内容区域可见 */
    .centered-container, .form-box, .st-emotion-cache-1r4qj8v, .st-emotion-cache-1v0mbdj {{
        background-color: rgba(30, 30, 30, 0.9) !important; /* 半透明深色背景 */
        color: white !important; /* 提高文字对比度 */
        border-radius: 10px;
        padding: 1rem;
        position: relative;
        z-index: 10; /* 确保内容在视频之上 */
    }}
    .st-emotion-cache-1r4qj8v * {{
        color: white !important; /* 确保侧边栏文字可见 */
    }}
    .stTextInput, .stButton, .stSelectbox, .stSlider, .stRadio, .stFileUploader {{
        background-color: rgba(50, 50, 50, 0.9) !important; /* 控件背景 */
        color: white !important;
        border-radius: 5px;
    }}
    </style>
    <video class="bg-video" autoplay loop muted playsinline>
        <source src="data:video/mp4;base64,{encoded}" type="video/mp4">
        Your browser does not support the video tag.
    </video>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_model_settings(st, sidebar=True):
    container = st.sidebar if sidebar else st

    # 添加模型提供商选择
    st.session_state.model_provider = container.selectbox(
        "模型提供商",
        options=list(MODEL_PROVIDERS.keys()),
        key="provider_select"
    )

    # 添加API key输入
    st.session_state.api_key = container.text_input(
        "API Key",
        value=st.session_state.api_key,
        type="password",
        key="api_key_input"
    )

    # 获取当前提供商的可用模型
    available_models = MODEL_PROVIDERS[st.session_state.model_provider]["models"]

    # 添加关键词提取模型选择
    st.session_state.keyword_model = container.selectbox(
        "关键词提取模型",
        options=available_models,
        key="keyword_model_select"
    )

    # 添加相似度匹配模型选择
    st.session_state.similarity_model = container.selectbox(
        "相似度匹配/文献分析模型",
        options=available_models,
        key="similarity_model_select"
    )

def main():

    # 初始化
    initialize_session_state()

    # 页面状态初始化
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "login"

    if 'user_login' not in st.session_state:
        st.session_state.user_login = None

    # ✅ 如果用户未登录，只能进入登录或注册页
    if st.session_state.user_login is None:
        local_bg_image("figure_file/43.png")
        if st.session_state.current_page == "register":
            # 页面样式美化
            st.markdown("""
                    <style>
                    .centered-container {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding-top: 5vh;
                    }
                    .form-box {
                        background-color: #1e1e1e;
                        padding: 2rem 3rem;
                        border-radius: 10px;
                        box-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
                        max-width: 500px;
                        width: 100%;
                    }
                    .button-row {
                        display: flex;
                        justify-content: space-between;
                        gap: 1rem;
                    }
                    .title-text {
                        text-align: center;
                        font-size: 2.2rem;
                        font-weight: bold;
                        margin-bottom: 1rem;
                    }
                    .subtitle {
                        text-align: center;
                        font-size: 1.3rem;
                        margin-bottom: 2rem;
                    }
                    </style>
                """, unsafe_allow_html=True)

            # 页面结构布局
            st.markdown('<div class="centered-container">', unsafe_allow_html=True)
            st.markdown('<div class="title-text">📚 文献调研系统</div>', unsafe_allow_html=True)
            st.markdown('<div class="subtitle">📝 用户注册</div>', unsafe_allow_html=True)

            username = st.text_input("设置用户名", key="reg_user")
            password = st.text_input("设置密码", type="password", key="reg_pwd")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("注册", use_container_width=True):
                    import mysql.connector
                    import bcrypt
                    try:
                        conn = mysql.connector.connect(
                            host="--",
                            user="---",
                            password="----",
                            database="easypaper",
                            port=""
                        )
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                        if cursor.fetchone():
                            st.warning("用户名已存在，请更换")
                        else:
                            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                                           (username, hashed))
                            conn.commit()
                            st.success("注册成功，请返回登录")
                    except Exception as e:
                        st.error(f"注册失败: {e}")
                    finally:
                        if cursor:
                            cursor.close()
                        if conn:
                            conn.close()
            with col2:
                if st.button("返回登录", use_container_width=True):
                    st.session_state.current_page = "login"
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)  # form-box
            st.markdown('</div>', unsafe_allow_html=True)  # centered-container

        else:
            # 页面样式美化
            st.markdown("""
                    <style>
                    .centered-container {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        padding-top: 5vh;
                    }
                    .form-box {
                        background-color: #1e1e1e;
                        padding: 2rem 3rem;
                        border-radius: 10px;
                        box-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
                        max-width: 500px;
                        width: 100%;
                    }
                    .button-row {
                        display: flex;
                        justify-content: space-between;
                        gap: 1rem;
                    }
                    .title-text {
                        text-align: center;
                        font-size: 2.2rem;
                        font-weight: bold;
                        margin-bottom: 1rem;
                    }
                    .subtitle {
                        text-align: center;
                        font-size: 1.3rem;
                        margin-bottom: 2rem;
                    }
                    </style>
                """, unsafe_allow_html=True)
            # 添加自定义 CSS 控制输入框和按钮大小
            st.markdown("""
                    <style>
                    .custom-input {
                        width: 50% !important;
                        height: 48px !important;
                        font-size: 16px !important;
                        border-radius: 8px;
                    }
                    .custom-button {

                        height: 42px !important;
                        font-size: 16px !important;
                        border-radius: 6px;
                    }
                    </style>
                """, unsafe_allow_html=True)

            # 页面结构布局
            st.markdown('<div class="centered-container">', unsafe_allow_html=True)
            st.markdown('<div class="title-text">📚 文献调研系统</div>', unsafe_allow_html=True)
            st.markdown('<div class="subtitle">🔐 用户登录</div>', unsafe_allow_html=True)
            # 让输入框只占页面1/3宽度
            left, center, right = st.columns([2, 2, 2])  # 3个列，比例为2:2:2
            with center:
                st.markdown("用户名")
                username = st.text_input("用户名", key="login_user", label_visibility="collapsed",
                                         placeholder="请输入用户名")
                st.markdown("密码")
                password = st.text_input("密码", type="password", key="login_pwd", label_visibility="collapsed",
                                         placeholder="请输入密码")
            st.markdown('</div>', unsafe_allow_html=True)

            # 两个按钮并排
            _, col1, col2, _ = st.columns([3, 1.5, 1.5, 3])  # 4个列，比例为6:6:6:6
            with col1:
                st.markdown('<div class="custom-button">', unsafe_allow_html=True)
                if st.button("登录", use_container_width=True):
                    import mysql.connector
                    import bcrypt
                    try:
                        conn = mysql.connector.connect(
                            host="47.122.37.248",
                            user="yxh",
                            password="iMn2bZDnyNyNtRFW",
                            database="easypaper",
                            port=3306
                        )
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                        user = cursor.fetchone()
                        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                            st.success("登录成功！")
                            st.session_state.user_login = username
                            st.session_state.current_page = "main"
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")
                    except Exception as e:
                        st.error(f"登录失败: {e}")
                    finally:
                        if cursor:
                            cursor.close()
                        if conn:
                            conn.close()
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="custom-button">', unsafe_allow_html=True)
                if st.button("前往注册", use_container_width=True):
                    st.session_state.current_page = "register"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)  # form-box
            st.markdown('</div>', unsafe_allow_html=True)  # centered-container

        return  # ⛔️ 阻止未登录用户访问后续页面

    # 开始选择与操作
    if st.session_state.current_page == "main":
        # Streamlit界面
        st.title("🔍 文献调研助手")
        st.markdown("---")

        # 初始化会话状态
        if 'search_history' not in st.session_state:
            st.session_state.search_history = []

        # 侧边栏
        with st.sidebar:

            st.title("👤 用户状态")
            if st.session_state.user_login:
                st.success(f"欢迎，{st.session_state.user_login}")
                if st.button("退出登录", use_container_width=True):
                    del st.session_state.user_login
                    st.rerun()
            st.title("🛠️ 设置")

            render_model_settings(st)

            # 添加数据源选择
            data_source = st.radio(
                "选择文献来源",
                ["ArXiv", "IEEE", "SciHub"],
                help="检索文献数据库"
            )
            paper_number = st.slider("每个关键词检索文章数", min_value=5, max_value=20, value=8)
            paper_return = st.slider("推荐排序的文章数目", min_value=1, max_value=25, value=5)
            # 仅在选择ArXiv时显示文章数量选择
            if data_source == "ArXiv":
                # 新增ArXiv检索方式选择
                arxiv_sort_method = st.selectbox(
                    "ArXiv检索排序方式",
                    ["文献上传时间", "文献最后更新时间", "相关性"]
                )
            elif data_source == "SciHub":
                col1, col2 = st.columns(2)
                with col1:
                    start_year = st.number_input("开始年份", min_value=1900, max_value=2100, value=2020)
                with col2:
                    end_year = st.number_input("结束年份", min_value=1900, max_value=2100, value=2025)
                year_range = [start_year, end_year]


            # 在清除搜索历史的按钮处理中添加：
            if st.button("清空搜索历史", use_container_width=True):
                # 清除所有以"pdf_"开头的session state键
                pdf_keys = [key for key in st.session_state.keys() if key.startswith("pdf_")]
                for key in pdf_keys:
                    del st.session_state[key]
                st.session_state.search_history = []
                st.rerun()


            # 添加文献分析按钮
            if st.button("📚 进入文献分析", use_container_width=True):
                st.session_state.current_page = "analysis"
                st.rerun()

        query = st.text_input(
            "请输入您的研究需求描述:",
            placeholder="例如：我需要查找与大模型和联邦学习相关的文章...",
            key="search_input",
            on_change=lambda: st.session_state.update(submitted=True)  # 关键修改
        )
        # 主界面
        if st.session_state.get('submitted') and query:
            st.session_state.submitted = False  # 立即重置状态
            with st.spinner("正在分析您的需求..."):
                client = get_openai_client()
                keywords = get_keywords_from_query(client, query, data_source)
                st.write(f"📝 识别到的关键词: {', '.join(keywords)}")

                with st.spinner("正在检索相关文章..."):
                    # 根据选择的数据源调用不同的检索函数
                    if data_source == "ArXiv":
                        articles = get_multiple_arxiv_results(keywords, arxiv_sort_method, paper_number)
                        articles = remove_duplicates(articles, data_source)
                        st.write(f"🔍 共检索到 {len(articles)} 篇相关文章")
                    elif data_source == "IEEE": # IEEE
                        articles = []
                        for keyword in keywords[:1]: # 在测试阶段只选择了一个关键词
                            ieee_results = get_ieee_results(keyword)
                            if ieee_results:
                                articles.extend(ieee_results)
                        articles = remove_duplicates(articles, data_source)
                        st.write(f"🔍 共检索到 {len(articles)} 篇相关文章")
                    elif data_source == "SciHub": # SciHub
                        articles = []
                        for keyword in keywords[:1]:
                            scihub_results = get_sui_hub(year_range, keyword, paper_number)
                            if scihub_results:
                                articles.extend(scihub_results)
                        articles = remove_duplicates(articles, data_source)
                        st.write(f"🔍 共检索到 {len(articles)} 篇相关文章")

                    with st.spinner("正在评分和排序..."):
                        scored_articles = sort_score(client, articles, query)
                        scored_articles.sort(reverse=True, key=lambda x: x[0])

                        st.markdown("## 📚 推荐文章")  # 这里设置了返回推荐的文章数目
                        for i, (score, article) in enumerate(scored_articles[:paper_return]):
                            with st.expander(f"第 {i + 1} 名 (相关度: {score})"):
                                # 统一返回后的格式信息
                                if data_source == "ArXiv":
                                    # ArXiv文章的显示格式 - 使用对象属性访问
                                    title = article.title
                                    authors = ', '.join(a.name for a in article.authors[:3])
                                    abstract = article.summary
                                    url = article.pdf_url
                                    date = article.published.strftime('%Y-%m-%d')

                                    print("title:", title)
                                    print("authors:", authors)
                                    print("abstract:", abstract)
                                    print("url:", url)
                                    print("date:", date)

                                elif data_source == "IEEE":  # IEEE
                                    # IEEE文章的显示格式 - 使用字典键值访问
                                    title = article['title']
                                    authors = ', '.join([
                                        a.get('preferredName', 'Unknown')
                                        for a in article.get('authors', [])
                                    ])
                                    abstract = article['abstract']
                                    url = article['paper_url']
                                    date = article['conference_date']

                                elif data_source == "SciHub":  # SciHub
                                    title = article.get('title')
                                    # 获取作者并且展示前3位
                                    authors = article.get('authors', [])
                                    if len(authors) > 3:
                                        authors = ", ".join(authors[:3]) + " et al."
                                    else:
                                        authors = ", ".join(authors)
                                    abstract = article.get('abstract')
                                    url = f"https://pubmed.ncbi.nlm.nih.gov/{article.get('pmid')}/"
                                    date = article.get('publication_date')


                                st.markdown(f"**标题**: {title}")
                                st.markdown(f"**作者**: {authors}等")

                                with st.spinner("正在翻译摘要..."):
                                    chinese_summary = get_chinese_summary(client, abstract)
                                    st.markdown("**中文摘要**:")
                                    st.text_area("", chinese_summary, height=200, disabled=True)

                                col1, col2 = st.columns([3, 1])

                                with col1:
                                    st.markdown(f"**链接**: [{url}]({url})")

                                if date:
                                    st.markdown(f"**发表日期**: {date}")

                        # 保存搜索历史
                        st.session_state.search_history.append({
                            'query': query,
                            'keywords': keywords,
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                        })

        # 显示搜索历史
        if st.session_state.search_history:
            st.sidebar.markdown("## 📜 搜索历史")
            for item in reversed(st.session_state.search_history):
                st.sidebar.markdown(f"""
                    🕒 {item['timestamp']}
                    > {item['query']}
                    Keywords: {', '.join(item['keywords'])}
                    ---
                    """)
    elif st.session_state.current_page == "analysis":
        # 在页面开始处添加全局CSS样式
        st.markdown("""
            <style>
                /* 移除页面顶部空白 */
                .main {
                    padding-top: 0rem;
                }
                .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                }
                /* 固定容器高度和滚动样式 */
                .fixed-content {
                    height: 0px;  /* 设置固定高度 */
                    overflow-y: auto;  /* 添加垂直滚动条 */
                    padding: 0rem;
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
        st.markdown('----')
        client = get_openai_client()
        st.title("📚 文献分析")
        left_col, middle_col, right_col = st.columns([1, 2, 2])

        # 左侧区域设计
        with left_col:
            st.markdown('<div class="fixed-content">', unsafe_allow_html=True)
            st.markdown("## 📝 分析操作")
            operations = {
                "📊 论文总结": "summary",
                "🔍 方法解析": "method",
                "📈 创新点分析": "innovation",
                "💡 实验评估": "experiment",
                "❓ 提出问题": "question",
                "📝 公式markdown提取": "markdown",
                "👤 自由问答": "free"
            }
            selected_operation = st.radio(
                "选择分析类型",
                list(operations.keys()),
                key="analysis_type"
            )
            # 存储选择的操作类型对应的标识符
            st.session_state.operation_type = operations[selected_operation]
            print("[DEBUG] 用户选择分析类型:", st.session_state.operation_type)  # 添加调试输出
            if "messages" in st.session_state and len(st.session_state.messages) > 0:
                print("[DEBUG] 切换分析类型后的系统提示语:", st.session_state.messages[0]["content"])
            else:
                print("[DEBUG] messages 尚未初始化")

            operations_1 = {
                "📊 PdfReader": "pdfreader",
                "🔍 MinerU": "mineru",
            }
            selected_operation_1 = st.radio(
                "选择pdf解析工具",
                list(operations_1.keys()),
                key="pdf_jiexi"
            )
            st.session_state.operation_type_pdf_jiexi = operations_1[selected_operation_1]

            if st.button("📥 下载参考文献", key="download_ref", use_container_width=True):
                if 'pdf_content' not in st.session_state:
                    st.warning("请先上传PDF文件")
                else:
                    with st.spinner("正在准备参考文献..."):
                        try:
                            # 1. 获取参考文献内容
                            content = st.session_state.pdf_content
                            ref_section = content[-int(len(content) * 0.2):]
                            citations = get_reference(client, ref_section)

                            # 2. 创建内存中的文本文件
                            txt_bytes = citations.encode('utf-8')
                            b64 = base64.b64encode(txt_bytes).decode()

                            # 3. 使用双重下载保障机制
                            file_name = f"参考文献_{datetime.now().strftime('%Y%m%d')}.txt"

                            # # 方法1：直接下载按钮（确保至少有一种方式可用）
                            # st.download_button(
                            #     label="⬇️ 点击下载（备用方式）",
                            #     data=txt_bytes,
                            #     file_name=file_name,
                            #     mime="text/plain",
                            #     key="secure_download"
                            # )

                            # 方法2：自动触发下载（与之前成功的结构相同）
                            download_js = f"""
                            <script>
                            function downloadFile() {{
                                // 创建隐藏链接
                                const link = document.createElement('a');
                                link.href = 'data:text/plain;base64,{b64}';
                                link.download = '{file_name}';
                                link.style.display = 'none';

                                // 添加到页面
                                document.body.appendChild(link);

                                // 触发点击
                                link.click();

                                // 延迟移除
                                setTimeout(() => {{
                                    document.body.removeChild(link);
                                    // 自动点击备用下载按钮（如果方法1未执行）
                                    try {{
                                        document.querySelector('button[data-testid="secure_download"]').click();
                                    }} catch(e) {{}}
                                }}, 500);
                            }}

                            // 确保页面加载完成后执行
                            if (document.readyState === 'complete') {{
                                downloadFile();
                            }} else {{
                                window.addEventListener('load', downloadFile);
                            }}
                            </script>
                            """

                            # 渲染下载组件
                            st.components.v1.html(download_js, height=0)

                            # 显示成功提示
                            st.toast("参考文献已开始下载，请检查浏览器下载列表", icon="✅")

                        except Exception as e:
                            st.error(f"生成失败: {str(e)}")

            if st.button("🧹 清空对话记录", key="clear_chat", use_container_width=True):
                if "messages" in st.session_state:
                    # 保留系统提示，只清空用户和AI的对话
                    st.session_state.messages = [msg for msg in st.session_state.messages
                                                 if msg["role"] == "system"]
                else:
                    st.warning("没有可清空的对话记录")

            # 返回主页按钮
            if st.button("返回文献检索", use_container_width=True):
                # 清除所有上传相关的状态
                for key in ["upload_time", "total_pages", "pdf_content", "user_login"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.current_page = "main"
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        # 中间对话设计
        operation_type = st.session_state.get("operation_type", "summary")  # 默认为summary
        render_chat_area(middle_col, client, operation_type)

        with right_col:
            st.markdown('<div class="fixed-content">', unsafe_allow_html=True)
            st.markdown("## 📄 PDF文档预览")

            # 创建一个可滚动的容器
            st.markdown("""
                <style>
                    .pdf-container {
                        height: 600px;
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
                </style>
            """, unsafe_allow_html=True)

            # 修改为多文件上传
            uploaded_files = st.file_uploader("上传PDF文件(可多选)", type="pdf", accept_multiple_files=True)
            print("uploaded_files:", uploaded_files)
            if uploaded_files and len(uploaded_files) > 0:
                try:
                    # 只处理第一个上传的文件用于显示
                    first_file = uploaded_files[0]
                    file_contents = first_file.getvalue()
                    current_file_hash = hash(file_contents)

                    # 检查是否是新的上传或更改
                    if "last_file_hash" not in st.session_state or st.session_state.last_file_hash != current_file_hash:
                        st.session_state.last_file_hash = current_file_hash
                        st.session_state.upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        st.session_state.user_login = "123yxh"

                        # 存储所有上传的文件内容
                        st.session_state.all_pdf_contents = []

                        # 处理所有上传的PDF文件
                        for uploaded_file in uploaded_files:
                            print("uploaded_file:", uploaded_file)
                            print("state:",st.session_state.operation_type_pdf_jiexi)
                            if st.session_state.operation_type_pdf_jiexi == "pdfreader":
                                print("正在使用 PdfReader 解析PDF...")
                                pdf_reader = PdfReader(uploaded_file)
                                pdf_text = ""
                                total_pages = len(pdf_reader.pages)

                                # 计算要提取的页数(前15%)
                                extract_pages = max(1, int(total_pages * 0.15))

                                # 只提取前15%的页面内容
                                for page in pdf_reader.pages[:extract_pages]:
                                    pdf_text += page.extract_text()

                                st.session_state.all_pdf_contents.append(pdf_text)
                            elif st.session_state.operation_type_pdf_jiexi == "mineru":
                                try:
                                    print("正在使用 MinerU 解析PDF...")
                                    # 创建临时文件保存上传的PDF
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
                                        tmpfile.write(uploaded_file.getvalue())
                                        tmpfile_path = tmpfile.name

                                    # 使用临时文件路径调用 MinerU 的 process_pdf
                                    pdf_text, image_dir = process_pdf(tmpfile_path)
                                    # print("pdf_text:", pdf_text)
                                    # 如果需要处理图片，可以在这里添加代码
                                    # 删除临时文件
                                    os.unlink(tmpfile_path)

                                    # Check if images directory exists and has files
                                    if os.path.exists(image_dir) and os.listdir(image_dir):
                                        st.success("PDF processed successfully with images!")

                                        # Create download button for images
                                        zip_buffer = create_zip(image_dir)
                                        ste.download_button(
                                            label="下载文献中的图片",
                                            data=zip_buffer,
                                            file_name="images.zip",
                                            mime="application/zip",
                                        )
                                    else:
                                        st.success("PDF processed successfully (no images generated)")

                                    st.session_state.all_pdf_contents.append(pdf_text)
                                except Exception as e:
                                    st.error(f"MinerU 解析失败: {str(e)}")
                            
                        # 使用第一篇PDF的全部内容作为主要分析内容(如果只上传1篇)
                        if len(uploaded_files) == 1:
                            # 单篇文献时使用完整内容
                            pdf_reader = PdfReader(uploaded_files[0])
                            full_text = ""
                            for page in pdf_reader.pages:
                                full_text += page.extract_text()
                            st.session_state.pdf_content = full_text
                        else:
                            # 多篇文献时使用第一篇的前15%内容
                            st.session_state.pdf_content = st.session_state.all_pdf_contents[0]

                        st.session_state.total_pages = len(PdfReader(uploaded_files[0]).pages)
                        # 更新系统提示
                        if len(uploaded_files) == 1:
                            # 单篇文献时使用完整内容
                            st.session_state.messages[0]["content"] = (
                                f"\n Prompt: {ACADEMIC_PROMPTS[operation_type]}\n\nPDF Content:\n{st.session_state.pdf_content}"
                            )
                        else:
                            # 多篇文献时使用每篇的前15%内容
                            combined_content = "\n\n".join([f"PDF {i + 1} (前15%内容):\n{content}"
                                                            for i, content in
                                                            enumerate(st.session_state.all_pdf_contents)])
                            st.session_state.messages[0]["content"] = (
                                f"\n Prompt: {ACADEMIC_PROMPTS[operation_type]}\n\nPDF Contents:\n{combined_content}"
                            )

                    # 显示第一篇PDF文件在滚动容器中
                    base64_pdf = base64.b64encode(file_contents).decode('utf-8')
                    pdf_display = f"""
                            <div class="pdf-container">
                                <iframe src="data:application/pdf;base64,{base64_pdf}" type="application/pdf"></iframe>
                            </div>
                        """
                    st.markdown(pdf_display, unsafe_allow_html=True)

                    # 显示上传的文件数量信息
                    if len(uploaded_files) == 1:
                        st.info("已上传1篇文献 (完整内容已用于分析)")
                    else:
                        st.info(f"已上传 {len(uploaded_files)} 篇文献 (每篇前15%内容用于分析，仅展示第一篇)")

                except Exception as e:
                    st.error(f"PDF处理出错: {str(e)}")
            else:
                # 当没有上传文件时显示提示
                if "total_pages" in st.session_state:
                    del st.session_state.total_pages
                if "upload_time" in st.session_state:
                    del st.session_state.upload_time
                if "all_pdf_contents" in st.session_state:
                    del st.session_state.all_pdf_contents
                st.info("请上传PDF文件以开始分析")
            st.markdown('</div>', unsafe_allow_html=True)


if __name__ == '__main__':
    main()
