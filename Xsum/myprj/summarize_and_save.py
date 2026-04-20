import os
import psycopg2
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# 1. Load biến môi trường
load_dotenv()
google_api_key = os.getenv('GOOGLE_API_KEY')
database_url = os.getenv('DATABASE_URL')

if not google_api_key or not database_url:
    raise ValueError("Vui lòng cấu hình GOOGLE_API_KEY và DATABASE_URL trong file .env")

# 2. Khởi tạo Mô hình AI
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash", 
    google_api_key=google_api_key, 
    temperature=0.3 
)

# 3. Định nghĩa các Hệ thống Prompt
# Prompt 1 (Sơ lược)
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
# 6. Chạy thử nghiệm (Main execution)
if __name__ == "__main__":
    # Dữ liệu mẫu (Giả lập văn bản được bóc tách từ PDF của bạn)
    sample_text = """
    Mô hình RAG (Retrieval-Augmented Generation) là một kỹ thuật tiên tiến trong lĩnh vực Xử lý Ngôn ngữ Tự nhiên (NLP). 
    Nó kết hợp sức mạnh của các mô hình ngôn ngữ lớn (LLM) với khả năng truy xuất thông tin từ một cơ sở kiến thức bên ngoài. 
    Thay vì chỉ dựa vào dữ liệu được huấn luyện, RAG trước tiên tìm kiếm các tài liệu liên quan đến câu hỏi, sau đó nhồi chúng vào Prompt 
    để AI tạo ra câu trả lời chính xác và cập nhật hơn. Trái tim của quá trình truy xuất này là các Vector Embedding, 
    nơi văn bản được biến đổi thành các chuỗi số trong không gian nhiều chiều. Một Vector Store (ví dụ: FAISS) được sử dụng 
    để lưu trữ và tìm kiếm các Vector này một cách hiệu quả dựa trên độ tương đồng Cosine (Cosine Similarity).
    """
    
    # BƯỚC 1: Gọi AI để tạo tóm tắt
    summary_1_brief, summary_2_detailed = generate_summaries(sample_text)
    
    # BƯỚC 2: In kết quả ra màn hình để kiểm tra
    print("\n" + "="*50)
    print("BẢN TÓM TẮT SƠ LƯỢC (5 gạch đầu dòng):")
    print("-" * 30)
    print(summary_1_brief)
    print("\n" + "="*50)
    print("BẢN TÓM TẮT CHUYÊN SÂU (Giáo sư):")
    print("-" * 30)
    print(summary_2_detailed)
    print("="*50 + "\n")
    
    # BƯỚC 3: Lưu kết quả vào Database
    save_to_database(sample_text, summary_1_brief, summary_2_detailed)