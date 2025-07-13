import requests
import time
import csv
import os
from bs4 import BeautifulSoup
import re
import json
from multiprocessing import Pool, Manager
import warnings
from functools import partial
from datetime import datetime

"""
动态爬取整个关键词下的ieee文献的id(可用于获取完整摘要)，title，authors以及abstract
1. 爬取单个收索词对应下的所有文章->get id，title，authors
2. 根据id爬取对应网页下abstract
3. 下载单篇文章
"""

# 禁用SSL警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# 初始化保存的excel文件地址以及信息
def init_csv(output_dir, file_name):
    csv_path = os.path.join(output_dir, f'{file_name}.csv')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Authors', 'Abstract', 'PDF Path'])
    return csv_path

# 根据id构造的单个url-->爬取 title, abstract
def scrape_ieee_paper(url):
    # Send a GET request to the URL
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the metadata in the JavaScript variable
    scripts = soup.find_all('script')
    metadata = None
    for script in scripts:
        if script.string and "xplGlobal.document.metadata" in script.string:
            # Extract the JSON data
            match = re.search(r'xplGlobal\.document\.metadata=(\{.*?\});', script.string, re.DOTALL)
            if match:
                metadata = json.loads(match.group(1))
                break

    if not metadata:
        return None

    # Extract the required information
    paper_info = {
        'title': metadata.get('displayDocTitle', ''),
        'abstract': metadata.get('abstract', ''),
        'publication_info': metadata.get('displayPublicationTitle', ''),
        'conference_date': metadata.get('displayPublicationDate', '')
    }

    return paper_info

# 打印返回后的数据信息
def format_paper_info(paper_info):
    if not paper_info:
        return "Could not extract paper information"

    formatted_info = f"""Paper Information:\n
    Title: {paper_info['title']}\n
    Abstract:{paper_info['abstract']}\n
    Publication Information: {paper_info['publication_info']}\n
    Conference Date: {paper_info['conference_date']}\n
    """
    return formatted_info

# 分页爬取对应link下的数据
def get_page_data(key, headers, page_number):
    url = 'https://ieeexplore.ieee.org/rest/search'
    data = {
        'highlight': 'true',
        'matchPubs': 'true',
        'newsearch': 'true' if page_number == 1 else 'false',
        'queryText': key,
        'returnFacets': ["ALL"],
        'returnType': "SEARCH",
        'pageNumber': page_number,
        'rowsPerPage': 25
    }
    try:
        response = requests.post(
            url,
            data=json.dumps(data),
            headers=headers,
            verify=False,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f'第 {page_number} 页请求失败: {e}')
        return {}

# 获取单篇文献信息->单独获取abstract
def download_paper(paper, counter, total_papers, lock):
    try:
        id = paper['articleNumber']
        title = paper['articleTitle']
        authors = paper['authors']
        # abstract = paper.get('abstract', 'N/A')

        doc_url = f'https://ieeexplore.ieee.org/document/{id}'

        # get abstract---
        paper_info = scrape_ieee_paper(doc_url)
        id_abstract_all = paper_info['abstract']
        conference_date = paper_info['conference_date']
        print(id_abstract_all)

        with lock:
            # 更新计数器
            counter.value += 1
            # 打印进度
            current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            print(f'[{current_time}] 已完成第 {counter.value}/{total_papers} 篇: {title}')

        time.sleep(1)

        return {
            'title': title,
            'authors': authors,
            'abstract': id_abstract_all,
            'paper_url': doc_url,
            'data_time': conference_date,
        }

    except Exception as e:
        print(f'获取信息失败 [{paper.get("articleTitle", "Unknown")}]: {e}')
        return None

# 下载单篇文献
def down_ieee_pdf(id, title):
    headers = {
        'Accept': 'application/json,text/plain,*/*',
        'Accept-Encoding': 'gzip,deflate,br',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Referer': f'https://ieeexplore.ieee.org/document/{id}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    pdf_url = f'https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={id}&ref='

    session = requests.Session()
    pdf_response = session.get(
        pdf_url,
        headers=headers,
        timeout=10,
        verify=False
    )
    #检查是否获取成功
    pdf_response.raise_for_status()

    # 获取pdf名称
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '.', '_')).rstrip()

    return  pdf_response, safe_title

# 包装函数，用于正确处理参数----多进程
def process_page_wrapper(args, papers_info_list, key, headers, output_dir, csv_path, lock, counter, total_papers):
    page_number = args
    page_data = get_page_data(key, headers, page_number)
    if not page_data or 'records' not in page_data:
        return 0

    papers = page_data.get('records', [])
    if not papers:
        return 0

    count = 0
    for paper in papers:
        paper_info = download_paper(paper, counter, total_papers, lock)
        if paper_info:
            full_info = {
                'id': paper['articleNumber'],
                'title': paper_info['title'],
                'abstract': paper_info['abstract'],
                'paper_url': paper_info['paper_url'],
                'authors': paper_info['authors'],
                'conference_date': paper_info['data_time'],
            }
            papers_info_list.append(full_info)

            with lock:
                with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([
                        paper_info['title'],
                        str(paper_info['authors']),
                        paper_info['abstract'],
                        paper_info['paper_url'],
                    ])
            count += 1
            time.sleep(2)
    return count

def get_ieee_results(key_words):
    # 基础信息准备
    # 输入--关键词
    records_per_page = 25
    output_dir = './ieee_Quan'
    save_csv_name = 'ieee_results'
    csv_path = init_csv(output_dir, save_csv_name)
    # start_year, end_year = year_range
    headers = {
        'Accept': 'application/json,text/plain,*/*',
        'Accept-Encoding': 'gzip,deflate,br',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Referer': f'https://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText={key_words}',
        # 'Referer': f'# https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={key_words}&highlight=true&returnFacets=ALL&returnType=SEARCH&matchPubs=true&ranges={start_year}_{end_year}_Year',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 如果说有输入年限--可以采用此替换关键词
    # https://ieeexplore.ieee.org/search/searchresult.jsp?queryText=hfl&highlight=true&returnFacets=ALL&returnType=SEARCH&matchPubs=true&ranges=2023_2025_Year

    # 检查是否能够正确获取信息
    first_page_response = get_page_data(key_words, headers, 1)
    if not first_page_response:
        print("获取搜索结果失败")
        return

    total_records = first_page_response.get('totalRecords', 0)
    total_pages = (total_records + records_per_page - 1) // records_per_page

    print(f'共发现 {total_records} 篇论文，预计 {total_pages} 页')

    with Manager() as manager:
        lock = manager.Lock()
        counter = manager.Value('i', 0)  # 共享计数器
        papers_info_list = manager.list()  # 共享列表

        with Pool(processes=2) as pool:
            worker = partial(
                process_page_wrapper,
                papers_info_list=papers_info_list,
                key=key_words,
                headers=headers,
                output_dir=output_dir,
                csv_path=csv_path,
                lock=lock,
                counter=counter,
                total_papers=total_records
            )
            results = pool.map(worker, range(1, total_pages + 1))
            total_downloaded = sum(results)
            print(f'共下载 {total_downloaded} 篇论文')

        return list(papers_info_list)  # 返回所有论文信息

    # print(f'\n爬取完成！')
    # print(f'共下载 {total_downloaded} 篇论文')

#　测试用例
# if __name__ == '__main__':
#     papers = get_ieee_results("VEF")
#     for paper in papers:
#         print(f"Title: {paper['title']}")
#         print(f"Abstract: {paper['abstract']}")
#         print(f"Authors: {paper['authors']}")