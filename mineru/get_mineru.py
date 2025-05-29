import os
import zipfile
from io import BytesIO
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

def process_pdf(pdf_file_path, progress_callback=None):
    """Process the PDF file and return markdown content and images directory"""
    # 获取文件路径不带扩展名
    pdf_file_path_without_suff = os.path.splitext(pdf_file_path)[0]
    # 文件目录
    pdf_file_path_parent_dir = os.path.dirname(pdf_file_path)
    image_dir = os.path.join(pdf_file_path_parent_dir, "images")

    # 创建 writer
    writer_markdown = FileBasedDataWriter()
    writer_image = FileBasedDataWriter(image_dir)

    # 读取 PDF 文件
    reader_pdf = FileBasedDataReader("")
    bytes_pdf = reader_pdf.read(pdf_file_path)
    dataset_pdf = PymuDocDataset(bytes_pdf)

    # 第一步：分类
    if progress_callback:
        progress_callback(0.2, "正在分析文档结构...")
    doc_type = dataset_pdf.classify()

    # 第二步：OCR 或非 OCR 处理
    if progress_callback:
        progress_callback(0.4, "正在提取内容...")
    if doc_type == SupportedPdfParseMethod.OCR:
        infer_result = dataset_pdf.apply(doc_analyze, ocr=True)
        pipe_result = infer_result.pipe_ocr_mode(writer_image)
    else:
        infer_result = dataset_pdf.apply(doc_analyze, ocr=False)
        pipe_result = infer_result.pipe_txt_mode(writer_image)

    # 第三步：生成 Markdown
    if progress_callback:
        progress_callback(0.8, "正在生成 Markdown...")
    markdown_content = pipe_result.get_markdown(image_dir)

    return markdown_content, image_dir

def create_zip(image_dir):
    """Create a zip file from the images directory"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(image_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(image_dir))
                zipf.write(file_path, arcname)
    zip_buffer.seek(0)
    return zip_buffer
