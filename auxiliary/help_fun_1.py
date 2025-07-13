from typing import List

# 去除重复的文章
def remove_duplicates(articles: List, data_source) -> List:
    """
    articles: 文章列表
    data_source：文章来源
    """
    seen = set()
    unique_articles = []

    for article in articles:
        # 根据信息源检索id
        if data_source == "ArXiv":
            entry_id = article.pdf_url
        elif data_source == "IEEE":
            entry_id = article['paper_url']
        elif data_source == "SciHub":
            entry_id = article.get("pmid")  # 使用 PMID 去重 SciHub 数据
        else:
            raise ValueError(f"未知的数据来源: {data_source}")

        # 去重操作--只添加未重复的文章id
        if entry_id not in seen:
            seen.add(entry_id)
            unique_articles.append(article)
    return unique_articles