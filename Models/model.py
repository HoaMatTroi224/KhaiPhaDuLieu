import openai
import streamlit as st
import os
import tempfile
import pytesseract
from PIL import Image
from langchain_experimental.text_splitter import SemanticChunker 
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader, CSVLoader, UnstructuredImageLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')

@st.cache_data
def setup_documents(file_path,
                    breakpoint_type='percentile', 
                    breakpoint_threshold=90):
    """
    Xử lý file với Semantic Chunking
    
    Parameters:
    - file_path: đường dẫn file
    - breakpoint_type: 'percentile', 'standard_deviation', 'interquartile'
    - breakpoint_threshold: ngưỡng để xác định điểm cắt
    """
    # 1. Lấy đuôi file (extension) để chọn Loader
    ext = os.path.splitext(file_path)[-1].lower()
    
    try:
        if ext == '.pdf':
            loader = PyPDFLoader(file_path)
            docs_raw = loader.load()
        elif ext == '.txt':
            loader = TextLoader(file_path, encoding='utf-8')
            docs_raw = loader.load()
        elif ext in ['.png', '.jpg', '.jpeg']:
            loader = UnstructuredImageLoader(file_path)
            docs_raw = loader.load()
        else:
            st.error(f"Định dạng file {ext} chưa được hỗ trợ!")
            return []

        # 2. Gom tất cả nội dung văn bản lại
        full_text = "\n".join([doc.page_content for doc in docs_raw])
        
        # 3. TẠO SEMANTIC CHUNKER
        embeddings = GoogleGenerativeAIEmbeddings(
                        model="gemini-embedding-2-preview",
            google_api_key=google_api_key,
            task_type="RETRIEVAL_DOCUMENT"
        )
        text_splitter = SemanticChunker(
            embeddings,
            breakpoint_threshold_type=breakpoint_type,
            breakpoint_threshold_amount=breakpoint_threshold
        )
        
        # Tạo danh sách các Document nhỏ
        docs = text_splitter.create_documents([full_text])
        
        return docs

    except Exception as e:
        st.error(f"Lỗi khi xử lý file: {e}")
        return []
    
def custom_summary(docs, llm, custom_prompt, chain_type, num_summaries):
    combine_template = custom_prompt + ":\n\n{text}"
    COMBINE_PROMPT = PromptTemplate(template=combine_template, input_variables=["text"])
    MAP_PROMPT = PromptTemplate(template="Tóm tắt chi tiết:\n\n{text}", input_variables=["text"])
    
    if chain_type == "map_reduce":
        chain = load_summarize_chain(
            llm,
            chain_type=chain_type,
            map_prompt=MAP_PROMPT,
            combine_prompt=COMBINE_PROMPT,
            verbose=False
        )
    else:
        chain = load_summarize_chain(llm, chain_type=chain_type, verbose=False)
    
    summaries = []
    for i in range(num_summaries):
        try:
            result = chain.invoke({"input_documents": docs})
            summary_output = result["output_text"]
            summaries.append(summary_output)
        except Exception as e:
            summaries.append(f"Lỗi tóm tắt lần {i+1}: {str(e)}")
    
    return summaries
    
def color_semantic_chunks(docs, max_preview_length=1000, show_metadata=True):
    chunk_colors = ["#e8f5e9", "#fff3e0", "#e3f2fd", "#fce4ec", "#f3e5f5", "#e8f0fe"]
    
    # CSS nên được gọi bên ngoài vòng lặp (giữ nguyên của bạn là rất tốt)
    st.markdown("""
    <style>
    .chunk-container {
        padding: 15px; margin: 10px 0; border-radius: 10px;
        border-left: 5px solid #2c3e50; background-color: white;
        font-family: 'Segoe UI', sans-serif; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .chunk-label {
        font-size: 0.8em; font-weight: bold; color: #555;
        background: rgba(0,0,0,0.05); padding: 3px 10px;
        border-radius: 15px; margin-right: 5px;
    }
    .chunk-content { line-height: 1.6; color: #333; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)
    
    html_output = ""
    for i, doc in enumerate(docs):
        color = chunk_colors[i % len(chunk_colors)]
        content = doc.page_content.replace("\n", "<br>") # Thay thế xuống dòng
        
        # Metadata logic
        meta = getattr(doc, 'metadata', {})
        page_info = f"📄 Trang {meta.get('page', 0) + 1}" if 'page' in meta else ""
        
        # Xử lý độ dài hiển thị
        is_long = max_preview_length > 0 and len(doc.page_content) > max_preview_length
        display_text = content[:max_preview_length] + "..." if is_long else content
        
        html_output += f"""
        <div class='chunk-container' style='background-color: {color};'>
            <div>
                <span class='chunk-label'>📌 Đoạn {i+1}</span>
                <span class='chunk-label'>{page_info}</span>
            </div>
            <div class='chunk-content'>{display_text}</div>
        </div>
        """
    return html_output

def main():
    st.set_page_config(layout="wide", page_title="AI Research Paper Summarizer")
    st.title("Custom Summarization App")
    temperature = st.sidebar.slider("Temperature (Độ sáng tạo)", 0.0, 1.0, 0.0, 0.1)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_api_key)
    # 2. Cấu hình Semantic Chunking
    st.sidebar.subheader("🧠 Semantic Splitting")
    bp_type = st.sidebar.selectbox(
        "Breakpoint Type", 
        ['percentile', 'standard_deviation', 'interquartile'],
        help="Công thức xác định điểm cắt dựa trên độ lệch ngữ nghĩa."
    )
    bp_threshold = st.sidebar.slider(
        "Breakpoint Threshold", 
        min_value=0, max_value=100, value=95,
        help="Ngưỡng để cắt. Percentile nên từ 90-95. Std_dev nên từ 1-3."
    )
    # 3. Cấu hình Summarization
    st.sidebar.subheader("📝 Summary Settings")
    chain_type = st.sidebar.selectbox("Chain Type", ["map_reduce", "stuff", "refine"])
    num_summaries = st.sidebar.number_input("Number of Summaries", 1, 5, 1)

    # --- MAIN CONTENT ---
    tab1, tab2 = st.tabs(["🚀 Summarize Paper", "🔍 Debug & Visualize"])

    with tab1:
        user_prompt = st.text_input("Nhập yêu cầu tóm tắt (Prompt)", "Tóm tắt các luận điểm chính của bài báo này bằng tiếng Việt")
        uploaded_file = st.file_uploader("Chọn file tài liệu của bạn", type=['pdf', 'txt', 'png', 'jpg', 'jpeg'])

        if uploaded_file is not None:
            # Lưu file tạm thời
            with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                file_path = tmp_file.name

            if os.path.exists(file_path):
                # Xử lý file
                with st.spinner("Đang phân tích ngữ nghĩa và chia đoạn..."):
                    docs = setup_documents(
                        file_path, 
                        breakpoint_type=bp_type, 
                        breakpoint_threshold=bp_threshold
                    )
                
                if docs:
                    st.success(f"Đã tải xong! Tìm thấy {len(docs)} đoạn nội dung (chunks).")
                    
                    if st.button("🚀 Start Summarizing"):
                        with st.spinner("Đang tóm tắt..."):
                            result = custom_summary(docs, llm, user_prompt, chain_type, num_summaries)
                            st.write("### 📄 Kết quả tóm tắt:")
                            for i, summary in enumerate(result):
                                st.info(f"Bản tóm tắt #{i+1}:\n\n {summary}")
            else:
                st.error("Đường dẫn file không hợp lệ hoặc không tồn tại.")

    with tab2:
        st.header("Visualize Semantic Chunks")
        if 'docs' in locals() and docs:
            st.write("Dưới đây là cách AI 'nhìn' bài báo của bạn sau khi chia theo ngữ nghĩa:")
            # Gọi hàm hiển thị UX xịn của bạn
            html_view = color_semantic_chunks(docs)
            st.markdown(html_view, unsafe_allow_html=True)
        else:
            st.info("Hãy nhập đường dẫn file ở Tab 1 để xem trực quan hóa các đoạn cắt tại đây.")

if __name__ == "__main__":
    main()