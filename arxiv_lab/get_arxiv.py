import arxiv

# 根据单个关键词获取arxiv的文章
def get_arxiv(key_word, arxiv_sort_method, articles_per_keyword=10):
    #
    sort_criterion = {
        "文献上传时间": arxiv.SortCriterion.SubmittedDate,
        "文献最后更新时间": arxiv.SortCriterion.LastUpdatedDate,
        "相关性": arxiv.SortCriterion.Relevance
    }.get(arxiv_sort_method, arxiv.SortCriterion.SubmittedDate)  # 默认使用SubmittedDate

    search = arxiv.Search(
        query=key_word,
        max_results=articles_per_keyword,
        sort_by=sort_criterion
    )
    return list(search.results())

# 根据多个关键词获取arxiv的文章
def get_multiple_arxiv_results(keywords, arxiv_sort_method, articles_per_keyword=10):
    """
    keywords: 输入的查询关键词
    articles_per_keyword: 每个关键词最多的查询数量
    return: 查询到的信息-标题、作者、摘要、链接
    """
    all_results = []

    for keyword in keywords:
        try:
            print(f"正在获取关键词 '{keyword}' 的文章...")
            results = get_arxiv(keyword, arxiv_sort_method, articles_per_keyword)
            all_results.extend(results)
            print(f"已找到 {len(results)} 篇关于 '{keyword}' 的文章")
        except Exception as e:
            print(f"获取关键词 '{keyword}' 时出错: {e}")

    print(f"\n总计获取 {len(all_results)} 篇文章")
    return all_results


# 测试用例
# if __name__ == "__main__":
#     keywords = ["large language model", "hierarchical federated learning", "model distillation"]
#     articles = get_multiple_arxiv_results(keywords)
#
#     # 打印前3篇文章信息示例
#     for i, article in enumerate(articles[:3]):
#         print(f"\n文章 {i + 1}:")
#         print(f"标题: {article.title}")
#         print(f"作者: {', '.join(a.name for a in article.authors)}")
#         print(f"摘要: {article.summary[:200]}...")  # 只显示前200字符
#         print(f"链接: {article.pdf_url}")