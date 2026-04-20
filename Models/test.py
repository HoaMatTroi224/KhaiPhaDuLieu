import asyncio
import shutil
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
import os
import tempfile
from typing import List, Dict, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import psycopg2
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredImageLoader, UnstructuredPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker 
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain, create_history_aware_retriever
from langchain_core.messages import HumanMessage, AIMessage # Thêm để phân biệt người và AI
load_dotenv()
app = FastAPI(title="AI Document Processing API")
google_api_key = os.getenv('GOOGLE_API_KEY')
database_url = os.getenv('DATABASE_URL')
@app.post("/upload_document/")
async def upload_and_read_document(file: UploadFile = File(...)):
    """Nhận file (PDF, TXT, PNG, JPG) và bóc tách thành văn bản"""
    
    # 1. Lấy đuôi file (extension)
    ext = os.path.splitext(file.filename)[-1].lower()
    
    # Danh sách các đuôi file được hỗ trợ
    supported_extensions = ['.pdf', '.txt', '.png', '.jpg', '.jpeg']
    if ext not in supported_extensions:
        raise HTTPException(status_code=400, detail=f"Định dạng file {ext} chưa được hỗ trợ!")

    # 2. Lưu file tạm thời vào ổ cứng với đúng cái đuôi của nó
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
    
        if ext == '.pdf':
            loader = PyPDFLoader(tmp_path)
            docs_raw = loader.load()
            
        elif ext == '.txt':
            loader = TextLoader(tmp_path, encoding='utf-8')
            docs_raw = loader.load()
            
        elif ext in ['.png', '.jpg', '.jpeg']:
            loader = UnstructuredImageLoader(tmp_path, mode="elements", strategy="hi_res", languages=["vie", "eng"])
            docs_raw = loader.load()

        # 4. Gom tất cả nội dung văn bản lại
        full_text = "\n".join([doc.page_content for doc in docs_raw])
        if not full_text:
            raise HTTPException(status_code=400, detail="Không extract được nội dung từ file")
        # 5. Tạo title mặc định (có thể để frontend gửi thêm title sau này)
        sample_title = file.filename.rsplit('.', 1)[0].replace('_', ' ').title()

        # 5. Prompt cho Overview
        overview_prompt = ChatPromptTemplate.from_template(
            "Đọc tiêu đề và nội dung của tài liệu sau:\n"
            "Tiêu đề: {title}\n"
            "Nội dung chính: {content}\n\n"
            "Hãy viết một đoạn Tổng quan (Overview) thật hấp dẫn, dễ hiểu dành cho người không chuyên. "
            "Giải thích tại sao tài liệu này quan trọng và điểm nhấn chính là gì. Giới hạn trong 4-5 câu."
        )
        overview_chain = overview_prompt | llm
        overview_result = overview_chain.invoke({"title": sample_title, "content": full_text[:8000]})  # cắt bớt nếu quá dài để tiết kiệm token

        # 6. Prompt cho 3 câu hỏi gợi ý
        question_prompt = ChatPromptTemplate.from_template(
            "Đọc tiêu đề và nội dung của tài liệu sau:\n"
            "Tiêu đề: {title}\n"
            "Nội dung chính: {content}\n\n"
            "Hãy đóng vai một người học tò mò, viết ra đúng 3 câu hỏi ngắn gọn, sâu sắc mà bạn muốn hỏi để hiểu rõ hơn về nội dung này. "
            "Trả lời dưới dạng danh sách gạch đầu dòng."
        )
        question_chain = question_prompt | llm
        questions_result = question_chain.invoke({"title": sample_title, "content": full_text[:8000]})

        # Xử lý output câu hỏi thành list sạch
        suggested_questions = []
        for line in questions_result.content.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("1.") or line.startswith("•"):
                cleaned = line.lstrip("-*• 1234567890.").strip()
                if cleaned:
                    suggested_questions.append(cleaned)
        suggested_questions = suggested_questions[:3]  # đảm bảo không quá 3
        return {
            "filename": file.filename,
            "file_type": ext,
            "total_pages_or_elements": len(docs_raw),
            "extracted_text_preview": full_text[:1000] + "..." if len(full_text) > 1000 else full_text,
            "title": sample_title,
            "overview": overview_result.content.strip(),
            "suggested_questions": suggested_questions,
            "full_text_length": len(full_text)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý file: {str(e)}")
    finally:
        # 5. Xóa file tạm sau khi đọc xong để tránh rác máy
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    

@app.post("/process_kpdl/")
async def process_kpdl_data():
    """Lấy dữ liệu từ Supabase và cắt bằng Semantic Chunker"""
    
    # 1. Lấy dữ liệu từ Supabase 
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        query = "SELECT id, title, content FROM kpdl;" 
        kpdl = pd.read_sql_query(query, conn)
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi kết nối Supabase: {str(e)}")

    # 2. Khởi tạo Mô hình Embedding & Semantic Chunker
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", 
            google_api_key = google_api_key,
            task_type="RETRIEVAL_DOCUMENT"
        )
        
        text_splitter = SemanticChunker(
            embeddings,
            breakpoint_threshold_type='percentile',
            breakpoint_threshold_amount=90
        )
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Lỗi khởi tạo AI: {str(e)}")
    # 3. Xóa index cũ nếu có
    try:
        if os.path.exists("faiss_index_kpdl"):
            shutil.rmtree("faiss_index_kpdl")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xóa thư mục cũ: {str(e)}")

    vectorstore = None
    total_chunks = 0
    # 3. Tiến hành cắt Chunk cho từng bài báo
    results = []

    try:
        for index, row in kpdl.iterrows():
            text_content = str(row["content"]).strip()
            if not text_content or text_content == "None": # Bỏ qua nếu bài viết bị trống
                continue
            
            # Semantic Chunker cắt văn bản
            chunks = text_splitter.create_documents([text_content])
        
            # Gắn thêm Metadata (quan trọng để sau này biết chunk này của bài báo nào)
            for chunk in chunks:
                chunk.metadata['source_id'] = row['id']
                chunk.metadata['title'] = row['title']
            total_chunks += len(chunks)
            if vectorstore is None:
                vectorstore = FAISS.from_documents(chunks, embeddings)
            else:
                vectorstore.add_documents(chunks)

            await asyncio.sleep(1)
            if vectorstore:
                vectorstore.save_local("faiss_index_kpdl")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình xử lý FAISS: {str(e)}")


    return {
        "message": "Cập nhật dữ liệu vào FAISS thành công",
        "total_documents_processed": len(kpdl),
        "total_chunks_created": total_chunks
    }

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=google_api_key, 
    temperature=0.3 
)

class QuestionRequest(BaseModel):
    question: str
    chat_history: List[Dict[str, str]] = []
# ==========================================
# API 3: HỎI ĐÁP VỚI TÀI LIỆU (Giống chat với file PDF)
# ==========================================
@app.post("/ask_question/")
async def ask_question(req: QuestionRequest):
    """Nhận câu hỏi -> Tìm trong FAISS -> AI trả lời"""
    try:
        # 1. Lấy tủ sách FAISS ra
        if not os.path.exists("faiss_index_kpdl"):
            raise HTTPException(
                status_code=404, 
                detail="Chưa có dữ liệu FAISS Index. Vui lòng chạy API /process_kpdl/ trước để nhúng dữ liệu!"
            )
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=google_api_key)
        vectorstore = FAISS.load_local("faiss_index_kpdl", embeddings, allow_dangerous_deserialization=True)
        
        # Cấu hình bộ tìm kiếm (Tìm 6 đoạn văn liên quan nhất)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
        langchain_history = []
        for msg in req.chat_history:
            if msg.get("role") == "user":
                langchain_history.append(HumanMessage(content=msg.get("content")))
            elif msg.get("role") == "ai":
                langchain_history.append(AIMessage(content=msg.get("content")))
        contextualize_q_system_prompt = (
            "Dựa trên lịch sử trò chuyện và câu hỏi mới nhất của người dùng, "
            "có thể câu hỏi mới đang tham chiếu đến ngữ cảnh trước đó. "
            "Hãy viết lại thành một câu hỏi độc lập mà không cần lịch sử trò chuyện để hiểu. "
            "KHÔNG trả lời câu hỏi, chỉ định dạng lại nó nếu cần, ngược lại giữ nguyên câu gốc."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"), # Nhét lịch sử vào đây
            ("human", "{input}"),
        ])
        
        # Tạo bộ truy xuất có nhận thức về lịch sử
        history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
        # 2. Tạo câu lệnh (Prompt) cho AI
        system_prompt = (
            "Bạn là một trợ lý nghiên cứu khoa học tận tâm đực biệt về lĩnh vực khoa học công nghệ. "
            "Sử dụng các đoạn trích xuất sau đây để trả lời câu hỏi của người dùng. "
            "Nếu bạn không biết câu trả lời từ tài liệu, hãy nói rằng bạn không biết, đừng cố bịa ra. "
            "\n\n"
            "{context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("history"), 
            ("human", "{input}"),
        ])

        # 3. Nối các bước lại thành 1 chuỗi (Chain) và chạy
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        
        response = rag_chain.invoke({"input": req.question, "history": langchain_history})

        return {
            "question": req.question,
            "answer": response["answer"],
            "sources": list(set([doc.metadata.get("title", "Không rõ nguồn") for doc in response["context"]]))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi RAG: {str(e)}")


# ==========================================
# API 4: TẠO OVERVIEW VÀ CÂU HỎI GỢI Ý (NOTEBOOKLM CLONE)
# ==========================================
@app.get("/get_overview_and_questions/{paper_id}")
async def get_overview_and_questions(paper_id: int):
    """Nhận ID bài báo -> AI tự tóm tắt Overview -> AI tự gợi ý 3 câu hỏi"""
    
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        # Query lấy đúng bài báo theo ID
        query = f"SELECT title, abstract FROM kpdl WHERE id = {paper_id} LIMIT 1;"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Nếu không tìm thấy bài báo trong Database
        if df.empty:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy bài báo với id = {paper_id}")
            
        # Lấy dữ liệu dạng text từ dataframe
        sample_title = df['title'].iloc[0]
        sample_abstract = df['abstract'].iloc[0]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy dữ liệu từ Database: {str(e)}")

    try:
        # 1. Prompt để đẻ ra 3 câu hỏi (Lấy cảm hứng từ logic của repo XSum)
        question_prompt = ChatPromptTemplate.from_template(
            "Đọc tiêu đề và tóm tắt của bài báo khoa học sau:\n"
            "Tiêu đề: {title}\n"
            "Tóm tắt: {abstract}\n\n"
            "Hãy đóng vai một sinh viên tò mò, viết ra đúng 3 câu hỏi ngắn gọn, sâu sắc mà bạn muốn hỏi để hiểu rõ hơn về phương pháp và kết quả của nghiên cứu này. "
            "Trả lời dưới dạng danh sách gạch đầu dòng."
        )
        question_chain = question_prompt | llm
        questions_result = question_chain.invoke({"title": sample_title, "abstract": sample_abstract})
        
        # 2. Prompt để viết Overview (Tổng quan)
        overview_prompt = ChatPromptTemplate.from_template(
            "Đọc tiêu đề và tóm tắt của bài báo khoa học sau:\n"
            "Tiêu đề: {title}\n"
            "Tóm tắt: {abstract}\n\n"
            "Hãy viết một đoạn Tổng quan (Overview) thật hấp dẫn, dễ hiểu dành cho người không chuyên. "
            "Giải thích tại sao nghiên cứu này lại quan trọng và điểm nhấn chính của nó là gì. Giới hạn trong 4-5 câu."
        )
        overview_chain = overview_prompt | llm
        overview_result = overview_chain.invoke({"title": sample_title, "abstract": sample_abstract})

        # Xử lý string để biến 3 câu hỏi thành dạng list cho đẹp
        suggested_questions = [q.strip("- *") for q in questions_result.content.split("\n") if q.strip()]

        return {
            "paper_id": paper_id,
            "title": sample_title,
            "overview": overview_result.content,
            "suggested_questions": suggested_questions[:3] # Lấy chắc chắn 3 câu
        }
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Lỗi tạo Overview: {str(e)}")

class SummaryRequest(BaseModel):
    raw_text: str
system_prompt_brief = (
    "Bạn là một chuyên gia phân tích dữ liệu và tóm tắt thông tin chuyên nghiệp. "
    "Mục tiêu của bạn là tóm tắt văn bản dưới đây thành đúng 5 gạch đầu dòng ngắn gọn, súc tích."
    "\n\n"
    "{context}"
)

# Prompt 2 (Chuyên sâu)
system_prompt_detailed = (
    "Bạn là một giáo sư đại học đầu ngành, có khả năng truyền đạt kiến thức phức tạp một cách dễ hiểu. "
    "Mục tiêu của bạn là viết một bản tóm tắt chi tiết về văn bản dưới đây, đồng thời trích xuất và giải thích các thuật ngữ khó, từ chuyên ngành xuất hiện trong văn bản đó."
    "\n\n"
    "{context}"
)

# 4. Logic Tóm tắt Văn bản
def generate_summaries(text_content):
    """Sử dụng AI để tạo ra 2 bản tóm tắt khác nhau"""
    
    # Tạo Prompt cho tóm tắt sơ lược
    prompt_brief = ChatPromptTemplate.from_messages([
        ("system", system_prompt_brief),
        ("human", "Hãy tóm tắt văn bản này."),
    ])
    
    # Tạo Prompt cho tóm tắt chuyên sâu
    prompt_detailed = ChatPromptTemplate.from_messages([
        ("system", system_prompt_detailed),
        ("human", "Hãy tóm tắt và giải thích các thuật ngữ trong văn bản này."),
    ])
    
    # Nối các bước lại thành 1 chuỗi (Chain) và chạy
    chain_brief = prompt_brief | llm
    chain_detailed = prompt_detailed | llm
    
    # Gửi yêu cầu đến AI
    print("Đang tạo tóm tắt sơ lược...")
    summary_brief = chain_brief.invoke({"context": text_content})
    
    print("Đang tạo tóm tắt chuyên sâu...")
    summary_detailed = chain_detailed.invoke({"context": text_content})
    
    return summary_brief.content, summary_detailed.content

def save_to_database(original_text, summary_1, summary_2):
    """Lưu tóm tắt vào bảng user_history đã có sẵn trên Supabase"""
    
    conn = None
    try:
        print("Đang kết nối Database...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # INSERT trực tiếp vào các cột đã có sẵn trong ảnh của bạn
        sql = """
            INSERT INTO user_history (raw_text, summary_1_slc, summary_2_chsu)
            VALUES (%s, %s, %s);
        """
        
        # Thực thi câu lệnh
        cur.execute(sql, (original_text, summary_1, summary_2))
        conn.commit()
        
        print("Đã lưu dữ liệu vào bảng user_history thành công!")
        cur.close()
        
    except Exception as e:
        print(f"Lỗi khi lưu vào Database: {str(e)}")
        if conn:
            conn.rollback() # Rollback nếu có lỗi
            
    finally:
        if conn:
            conn.close()
@app.post("/generate_and_save_summary/")
async def create_and_save_summary(request: SummaryRequest):
    """API nhận văn bản, gọi AI tóm tắt 2 phiên bản và lưu luôn vào user_history"""
    
    if not request.raw_text or len(request.raw_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Văn bản không được để trống")

    try:
        # BƯỚC 1: Gọi hàm đẻ ra tóm tắt
        summary_1_brief, summary_2_detailed = generate_summaries(request.raw_text)
        
        # BƯỚC 2: Gọi hàm lưu vào Database
        save_to_database(request.raw_text, summary_1_brief, summary_2_detailed)
        
        # Trả về kết quả cho client (Frontend) hiển thị
        return {
            "message": "Đã tạo và lưu tóm tắt thành công vào user_history!",
            "raw_text_length": len(request.raw_text),
            "summary_1_slc": summary_1_brief,
            "summary_2_chsu": summary_2_detailed
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")