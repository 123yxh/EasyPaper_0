import os
import re
import torch
import warnings
from FlagEmbedding import FlagReranker
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader, UnstructuredWordDocumentLoader, CSVLoader
warnings.filterwarnings("ignore")

# GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_data_from_path(knowledge_path):
    # load RAG data
    all_data = []
    for filename in os.listdir(knowledge_path):
        file_path = os.path.join(knowledge_path, filename)

        # .txt
        if filename.endswith('.txt'):
            loader = TextLoader(file_path=file_path, encoding='utf-8')
            data = loader.load()
            all_data.extend(data)

        # .pdf
        elif filename.endswith('.pdf'):
            loader = PyMuPDFLoader(file_path=file_path)
            data = loader.load()
            all_data.extend(data)

        # .csv
        elif filename.endswith('.csv'):
            loader = CSVLoader(file_path=file_path)
            data = loader.load()
            all_data.extend(data)

        # .word
        elif filename.endswith('.docx'):
            loader = UnstructuredWordDocumentLoader(file_path=file_path)
            data = loader.load()
            all_data.extend(data)

    return all_data


def rag_model_set(embedding_model_path, rerank_model_path):
    # load embedding_model and rerank_model
    embedding_model_kwargs = {"device": device}
    embedding_model_encode_kwargs = {"normalize_embeddings": True}

    embedding_model = HuggingFaceBgeEmbeddings(
        model_name=embedding_model_path,
        model_kwargs=embedding_model_kwargs,
        encode_kwargs=embedding_model_encode_kwargs
    )

    rerank_model = FlagReranker(
        model_name_or_path=rerank_model_path,
        use_fp16=True,
        device=device.type,
    )

    return embedding_model, rerank_model

# Post-retrieval processing
def post_process_text(text):
    # 1. Remove incomplete sentences
    sentences = re.split(r'(?<=[。？！.])\s*', text)
    complete_sentences = [s for s in sentences if s.strip() and s.endswith(('。', '！', '？', '.'))]

    # 2. if '\n\n' appears consecutively, keep the content before the first '\n\n'
    processed_text = ''.join(complete_sentences)
    first_double_newline_index = processed_text.find('\n\n')
    if first_double_newline_index != -1:
        processed_text = processed_text[:first_double_newline_index]

    return processed_text.strip()

def rag_process(input_question: str, vector_store_manager, rerank_model_path, top_k: int):
    """
    优化后的RAG处理函数
    :param input_question: 输入问题
    :param vector_store_manager: 向量存储管理器实例
    :param rerank_model_path: 重排序模型
    :param top_k: 返回结果数量
    :return: 处理后的输入和相关内容
    """
    # 直接从向量存储中检索相关内容
    re_results = vector_store_manager.search(input_question, k=5)

    rerank_model = FlagReranker(
        model_name_or_path=rerank_model_path,
        use_fp16=True,
        device=device.type,
    )

    related_contents = [doc.page_content for doc in re_results]

    # 重排序处理
    score_input = [(input_question, related) for related in related_contents]
    score = rerank_model.compute_score(score_input, normalize=True)
    scored_results = list(zip(score, related_contents))
    sorted_results = sorted(scored_results, key=lambda x: x[0], reverse=True)

    # 获取top-k结果
    top_results = sorted_results[:top_k]
    grt_back = [result[1] for result in top_results]
    cleaning_data = [post_process_text(text) for text in grt_back]

    final_input = '请根据我提供的知识库回答我的问题. 知识库是: {grt_back};我的问题是: {user_input}'.format(
        grt_back=cleaning_data, user_input=input_question)

    return final_input, cleaning_data

# test
# embedding_model = "../../EmoLLM-main/rag/model/embedding_model/bge-large-zh-v15"
# rerank_model = '../../EmoLLM-main/rag/model/rerank_model/bge-reranker-base'
# top_k = 1
# chunk_size = 1000
# chunk_overlap = 125
# rag_data_path = Config.UPLOAD_DIR
# message = '你好呀。你是谁呢？'
# print(rag_data_path)
# final_input, retrieved_contexts = rag_process(
#                     message,
#                     rag_data_path,
#                     embedding_model,
#                     rerank_model,
#                     top_k,
#                     chunk_size,
#                     chunk_overlap
#                 )
# print(final_input)




















