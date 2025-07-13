import requests
import re
import time
import urllib

# 根据url爬取单篇文章信息
def get_information(url):
    try:
        req = requests.get(url, timeout=200)
        if req.status_code != 200:
            print('网页异常:', url)
            return None
        data = req.text
    except Exception as e:
        print(f'请求失败: {e}, URL: {url}')
        return None

    # 正则表达式匹配所需信息
    title_p = re.compile(r'title = &#34;(.*?)&#34;')
    author_p = re.compile(r'author = &#34;([\s\S]*?)&#34;')
    link_p = re.compile(r'meta content=(https.*?pdf)')
    abs_p = re.compile(r'Abstract</h5><span>(.*?)</span></div>')

    # 提取信息
    title = title_p.findall(data)
    author = author_p.findall(data)
    link = link_p.findall(data)
    abstract = abs_p.findall(data)

    if len(title) > 0 and len(author) > 0 and len(link) > 0 and len(abstract) > 0:
        author[0] = author[0].replace('\n', '')
        return [title[0], author[0], link[0], abstract[0]]
    else:
        print(f"数据不全，跳过该URL：{url}")
        return None

# 下载单篇文章
def get_pdf(filename, url):
    try:
        response = urllib.request.urlopen(url)
        pdf_data = response.read()
        with open(filename, "wb") as f:
            f.write(pdf_data)
        print(f"✅ PDF已保存为: {filename}")
    except Exception as e:
        print(f"❌ 下载失败: {e}, URL: {url}")


# 测试函数
# if __name__ == '__main__':
#     keyword = 'Federated Learning' # 设置关键词
#     choose_year = '2024' # 选择对应年份
#     choose_number = 1 # 爬取数据总量
#     output_file = f'filtered_{choose_year}_acl.txt' #数据保存文件名称
#
#     # 打开输出文件
#     with open(output_file, 'w', encoding='utf-8') as f_out:
#         for i in range(1, choose_number):  # 总录取604篇论文
#             base_url = f'https://aclanthology.org/2024.acl-long.{i}/'
#             result = get_information(base_url)
#
#             if result is None:
#                 print(f"❌ 跳过无效页面: {base_url}")
#                 continue
#
#             title = result[0]
#             author = result[1]
#             pdf_url = result[2]
#             abstract = result[3]
#
#             # 判断标题是否包含关键词（忽略大小写）
#             if keyword.lower() in title.lower():
#                 print(f"🔍 匹配到关键词 '{keyword}': {title}")
#                 line = '\t'.join(result) + '\n'
#                 f_out.write(line)
#
#                 # 下载PDF
#                 pdf_name = f"{title.replace('/', '-').strip()}.pdf"
#                 get_pdf(pdf_name, pdf_url)
#
#             # 每次请求后加个短暂停顿，避免被服务器封禁
#             time.sleep(1)