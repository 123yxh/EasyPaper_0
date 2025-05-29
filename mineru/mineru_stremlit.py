import os
import streamlit as st
import shutil
import zipfile
from io import BytesIO
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
import streamlit_ext as ste

def process_pdf(pdf_file_path):
    """Process the PDF file and return markdown content and images directory"""
    # Get the PDF file path without extension
    pdf_file_path_without_suff = os.path.splitext(pdf_file_path)[0]

    # File directory
    pdf_file_path_parent_dir = os.path.dirname(pdf_file_path)
    image_dir = os.path.join(pdf_file_path_parent_dir, "images")

    # Create writers
    writer_markdown = FileBasedDataWriter()
    writer_image = FileBasedDataWriter(image_dir)

    # Read PDF file
    reader_pdf = FileBasedDataReader("")
    bytes_pdf = reader_pdf.read(pdf_file_path)

    # Process data
    dataset_pdf = PymuDocDataset(bytes_pdf)

    # Check if OCR is needed
    if dataset_pdf.classify() == SupportedPdfParseMethod.OCR:
        # With OCR
        infer_result = dataset_pdf.apply(doc_analyze, ocr=True)
        pipe_result = infer_result.pipe_ocr_mode(writer_image)
    else:
        # Without OCR
        infer_result = dataset_pdf.apply(doc_analyze, ocr=False)
        pipe_result = infer_result.pipe_txt_mode(writer_image)

    # Get markdown content
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


def main():
    st.title("PDF to Markdown Converter")

    # File uploader
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

    if uploaded_file is not None:
        # Create a temporary directory to store the uploaded file
        temp_dir = "temp_pdf_processing"
        os.makedirs(temp_dir, exist_ok=True)

        # Save the uploaded file
        pdf_path = os.path.join(temp_dir, uploaded_file.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Process the PDF
        with st.spinner("Processing PDF..."):
            try:
                markdown_content, image_dir = process_pdf(pdf_path)

                # Display markdown content
                st.subheader("Markdown Output")
                st.markdown(markdown_content)

                # Check if images directory exists and has files
                if os.path.exists(image_dir) and os.listdir(image_dir):
                    st.success("PDF processed successfully with images!")

                    # Create download button for images
                    zip_buffer = create_zip(image_dir)
                    ste.download_button(
                        label="Download Images as ZIP",
                        data=zip_buffer,
                        file_name="images.zip",
                        mime="application/zip"
                    )
                else:
                    st.success("PDF processed successfully (no images generated)")

            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}")
            finally:
                # Clean up temporary files
                shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()