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
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain, create_history_aware_retriever
from langchain_core.messages import HumanMessage, AIMessage
load_dotenv()
app = FastAPI(title="API for Summarization and RAG with Supabase")
google_api_key = os.getenv('GOOGLE_API_KEY')
database_url = os.getenv('DATABASE_URL')
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=google_api_key, 
    temperature=0.3 
)
embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001", 
            google_api_key = google_api_key,
            task_type="RETRIEVAL_DOCUMENT"
        )

@app.post("/upload_documents/")
async def upload_documents(files: List[UploadFile] = File(...), user_id: str = Form(...)):
    FAISS_INDEX_PATH = f"faiss_index_{user_id}"
    """Upload nhiều tài liệu, bóc tách OCR, Chunking và lưu vào FAISS"""
    supported_extensions = ['.pdf', '.txt', '.png', '.jpg', '.jpeg']
    all_chunks = []
    processed_files = []

    text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,      # phù hợp PDF học thuật
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " ", ""]
    )

    for file in files:
        ext = os.path.splitext(file.filename)[-1].lower()
        if ext not in supported_extensions:
            continue # Bỏ qua file không hợp lệ thay vì crash cả dàn

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if ext == '.pdf':
                loader = PyPDFLoader(tmp_path)
            elif ext == '.txt':
                loader = TextLoader(tmp_path, encoding='utf-8')
            elif ext in ['.png', '.jpg', '.jpeg']:
        
                loader = UnstructuredImageLoader(tmp_path, mode="single", strategy="auto", languages=["vie", "eng"])
            
            docs_raw = loader.load()
            full_text = "\n".join([doc.page_content for doc in docs_raw])
            
            if not full_text.strip():
                continue

            # Cắt chunk
            chunks = text_splitter.create_documents([full_text])
            
            # Gắn Metadata cực kỳ quan trọng để sau này TÍCH CHỌN file
            for chunk in chunks:
                chunk.metadata['source_file'] = file.filename
                chunk.metadata['user_id'] = user_id
            
            all_chunks.extend(chunks)
            processed_files.append({
                "filename": file.filename,
                "chunks": len(chunks)
            })

        except Exception as e:
            print(f"Lỗi khi xử lý file {file.filename}: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    if not all_chunks:
        raise HTTPException(status_code=400, detail="Không có tài liệu nào trích xuất được văn bản hợp lệ.")

    # Cập nhật VectorDB
    try:
        if os.path.exists(FAISS_INDEX_PATH):
            vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            vectorstore.add_documents(all_chunks)
        else:
            vectorstore = FAISS.from_documents(all_chunks, embeddings)
        vectorstore.save_local(FAISS_INDEX_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khởi tạo FAISS: {str(e)}")

    return {
        "message": "Upload và Vectorize thành công!",
        "processed_files": processed_files,
        "total_chunks": len(all_chunks)
    }    

class NotebookRequest(BaseModel):
    user_id: str # Thêm user_id để lưu database
    selected_files: List[str] # Danh sách tên file mà user tích chọn

system_prompt_notebook = (
    "Bạn là một Giáo sư đại học đầu ngành, khả năng sư phạm xuất sắc. "
    "Dựa vào các trích đoạn tài liệu dưới đây, hãy tạo ra một 'Bản tóm tắt học thuật' bao gồm:\n\n"
    "1. TỔNG QUAN (Ngắn gọn 4-5 câu về mục đích và điểm nhấn của các tài liệu này).\n"
    "2. 5 KHÁI NIỆM CỐT LÕI: Xác định 5 khái niệm/thuật ngữ quan trọng nhất mà mọi người trong lĩnh vực này cần hiểu. "
    "Với mỗi khái niệm, hãy giải thích bằng ngôn ngữ đơn giản, lý do nó quan trọng và nó liên kết với 4 khái niệm còn lại như thế nào.\n"
    "3. CÂU HỎI MỞ RỘNG: Đề xuất đúng 3 câu hỏi sâu sắc, mang tính phản biện để kích thích người học đào sâu hơn vào nội dung.\n\n"
    "Ngữ cảnh tài liệu:\n{context}"
)
def save_notebook_to_database(user_id: str, selected_files: List[str], generated_result: str):
    """Lưu vào Database Supabase theo đúng schema bạn đang có"""
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # original_text: Lưu danh sách file được chọn
        original_text_str = f"Tài liệu sử dụng: {', '.join(selected_files)}"
        
        # INSERT đúng các cột trong ảnh Supabase của bạn (user_id phải là kiểu UUID hợp lệ trên DB)
        sql = """
            INSERT INTO user_history (user_id, original_text, summarize_result)
            VALUES (%s, %s, %s) RETURNING id;
        """
        cur.execute(sql, (user_id, original_text_str, generated_result))
        inserted_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return inserted_id
        
    except Exception as e:
        print(f"Lỗi khi lưu vào Database: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
def update_chat_history_in_db(history_id: int, user_question: str, ai_answer: str):
    """Cập nhật thêm 1 cặp câu hỏi - câu trả lời vào cột chat_history"""
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Tạo object JSON cho lượt chat mới
        new_chat_turn = [
            {"role": "user", "content": user_question},
            {"role": "ai", "content": ai_answer}
        ]
        new_chat_json = json.dumps(new_chat_turn)
        
        # Dùng toán tử || của Postgres JSONB để append vào mảng cũ
        # Hàm COALESCE để xử lý trường hợp chat_history đang là NULL
        sql = """
            UPDATE user_history 
            SET chat_history = COALESCE(chat_history, '[]'::jsonb) || %s::jsonb
            WHERE id = %s;
        """
        cur.execute(sql, (new_chat_json, history_id))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Lỗi khi update chat_history: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
# ==========================================
# 2. API TẠO NOTEBOOK (TÓM TẮT CHUYÊN SÂU TỪ CÁC FILE ĐƯỢC CHỌN)
# ==========================================
@app.post("/generate_notebook/")
async def generate_notebook(req: NotebookRequest):
    """Lấy các chunk thuộc file được chọn -> Gọi AI tóm tắt -> Lưu DB"""
    FAISS_INDEX_PATH = f"faiss_index_{req.user_id}"
    if not os.path.exists(FAISS_INDEX_PATH):
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu. Hãy upload file trước.")

    vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    
    # Lấy ra tất cả các docs thuộc các file được chọn (Dùng as_retriever filter)
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": 15,
            "filter": {"source_file": {"$in": req.selected_files}, "user_id": req.user_id} # CHỈ TÌM TRONG FILE ĐƯỢC TÍCH CHỌN
        }
    )
    
    docs = retriever.invoke("Trích xuất thông tin tổng quan quan trọng nhất")
    combined_text = "\n\n".join([d.page_content for d in docs])

    if not combined_text:
         raise HTTPException(status_code=400, detail="Không tìm thấy nội dung từ các file được chọn.")

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_notebook),
        ("human", "Hãy thực hiện tóm tắt học thuật."),
    ])
    
    chain = prompt | llm
    response = chain.invoke({"context": combined_text})
    final_result = response.content

    # Lưu Database (Chạm vào database ở đây)
    db_id = save_notebook_to_database(req.user_id, req.selected_files, final_result)

    return {
        "history_id": db_id,
        "selected_files": req.selected_files,
        "notebook_summary": final_result
    }

class QuestionRequest(BaseModel):
    user_id: str 
    history_id: int # ID của cuộc hội thoại trong DB để sau này update
    selected_files: List[str] 
    question: str
    chat_history: List[Dict[str, str]] = []
# ==========================================
# API 3: HỎI ĐÁP VỚI TÀI LIỆU (Giống chat với file PDF)
# ==========================================
@app.post("/ask_question/")
async def ask_question(req: QuestionRequest):
    """Q&A dựa trên lịch sử chat và CÁC TÀI LIỆU ĐƯỢC TÍCH CHỌN"""
    FAISS_INDEX_PATH = f"faiss_index_{req.user_id}"
    try:
        if not os.path.exists(FAISS_INDEX_PATH):
            raise HTTPException(status_code=404, detail="Chưa có vector DB.")

        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        
        # Cấu hình bộ tìm kiếm: CHỈ TÌM TRONG CÁC FILE ĐƯỢC TÍCH CHỌN
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": 6,
                "filter": {"source_file": {"$in": req.selected_files}}
            }
        )
        
        langchain_history = []
        for msg in req.chat_history:
            if msg.get("role") == "user":
                langchain_history.append(HumanMessage(content=msg.get("content")))
            elif msg.get("role") == "ai":
                langchain_history.append(AIMessage(content=msg.get("content")))
                
        contextualize_q_system_prompt = (
            "Dựa trên lịch sử trò chuyện và câu hỏi mới nhất, "
            "hãy viết lại thành một câu hỏi độc lập."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        
        history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
        
        system_prompt = (
            "Bạn là trợ lý nghiên cứu khoa học công nghệ. "
            "Chỉ sử dụng các đoạn trích xuất sau để trả lời. Không bịa đặt.\n\n"
            "{context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("history"), 
            ("human", "{input}"),
        ])

        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        
        response = rag_chain.invoke({"input": req.question, "history": langchain_history})

        final_answer = response["answer"]
   
        update_chat_history_in_db(req.history_id, req.question, final_answer)

        return {
            "question": req.question,
            "answer": response["answer"],
            "sources": list(set([doc.metadata.get("source_file", "Không rõ nguồn") for doc in response["context"]]))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi RAG: {str(e)}")
