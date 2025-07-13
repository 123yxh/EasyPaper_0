import json
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor


def fetch_single_pubmed_article(pmid, api_key):
    """
    获取PubMed文献的详细信息（DP, TI, AB, FAU），正确处理多行题目和摘要

    Args:
        pmid (str): PubMed ID
        api_key (str): NCBI API Key

    Returns:
        dict: 包含发表时间、题目、摘要和作者列表的字典
    """
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&api_key={api_key}&id={pmid}&rettype=medline&retmode=text'
    response = requests.get(url, timeout=5)
    # 打印返回的信息
    # print(response)
    content = response.text.split('\n')  # 按行分割

    # 初始化变量
    dp = None  # 发表日期
    ti_lines = []  # 题目行（可能多行）
    ab_lines = []  # 摘要行（可能多行）
    authors = []  # 作者列表

    i = 0
    while i < len(content):
        line = content[i].strip()
        if line.startswith("DP  -"):
            dp = line[5:].strip()
        elif line.startswith("TI  -"):
            # 提取题目首行
            ti_lines.append(line[5:].strip())
            i += 1
            # 检查后续行是否属于题目（以6空格开头）
            while i < len(content) and content[i].startswith("      "):
                ti_lines.append(content[i][6:].strip())
                i += 1
            continue  # 避免重复i += 1
        elif line.startswith("AB  -"):
            # 提取摘要首行
            ab_lines.append(line[5:].strip())
            i += 1
            # 检查后续行是否属于摘要（以6空格开头）
            while i < len(content) and content[i].startswith("      "):
                ab_lines.append(content[i][6:].strip())
                i += 1
            continue  # 避免重复i += 1
        elif line.startswith("FAU -"):
            authors.append(line[5:].strip())
        i += 1

    # 合并题目和摘要的多行内容
    ti = " ".join(ti_lines) if ti_lines else None
    ab = " ".join(ab_lines) if ab_lines else None

    print(f"✅ 已完成抓取 PMID: {pmid} | 标题: {ti}")
    return {
        "pmid": pmid,
        "publication_date": dp,
        "title": ti,
        "abstract": ab,
        "authors": authors
    }

def fetch_multiple_pubmed_articles(pmids: List[str], api_key: str, max_workers: int = 1) -> List[Dict]:
    """
    批量获取多个PubMed文献信息（支持多线程）
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_single_pubmed_article, pmid, api_key) for pmid in pmids]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                print(f"Error fetching PMID: {e}")
    return results

# 主函数
def get_sui_hub(year_range, key_word, max_number):
    # 如果 year_range 是一个字符串，直接使用
    if isinstance(year_range, str):
        year_query = year_range
    # 如果 year_range 是一个包含两个元素的列表或元组，e.g., [2020,2025]则构造 YYYY:YYYY 格式
    elif len(year_range) == 2:
        start_year, end_year = year_range
        year_query = f"{start_year}:{end_year}"
    else:
        raise ValueError("year_range 必须是一个字符串或包含两个元素的列表/元组")

    API_KEY = "77..."
    url_start = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&api_key={API_KEY}&term={key_word}+{year_query}[pdat]&retmax={max_number}'
    info_page = BeautifulSoup(requests.get(url_start, timeout=(5, 5)).text, 'html.parser')
    # 提取id列表
    ids = [id_tag.text for id_tag in info_page.find_all("id")]

    # 多个ids获取信息--返回PMID、Publication_Date、Title、Abstract、Authors
    articles = fetch_multiple_pubmed_articles(ids, API_KEY)

    return articles

# # 测试用例
# if __name__ == "__main__":
#
#     API_KEY = "77171ddeab5513e2fc9abb15972be62cec09"
#     term = "Federated Learning"
#     year = f"{2020}:{2025}"
#     max_number = 1000
#     url_start = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&api_key={API_KEY}&term={term}+{year}[pdat]&retmax={max_number}'
#     info_page = BeautifulSoup(requests.get(url_start, timeout=(5, 5)).text, 'html.parser')
#     # 提取id列表
#     ids = [id_tag.text for id_tag in info_page.find_all("id")]
#     print(len(ids))
#
#     # 打印单个id获取的信息
#     id_str = '40353340'
#     article_info = fetch_single_pubmed_article(id_str, API_KEY)
#     print(article_info)
#
#     # # 多个ids获取信息
#     # articles = fetch_multiple_pubmed_articles(ids, API_KEY)
#     # print(json.dumps(articles, indent=2, ensure_ascii=False))
#     #
#     # with open("pubmed_articles.json", "w", encoding="utf-8") as f:
#     #     json.dump(articles, f, indent=2, ensure_ascii=False)
#     # print("数据已保存到 pubmed_articles.json")
