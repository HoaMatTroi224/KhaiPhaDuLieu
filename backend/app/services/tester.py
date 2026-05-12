import sys
import os
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load biến môi trường từ .env
from dotenv import load_dotenv
load_dotenv()

from .extractor import FileExtractor

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

extractor = FileExtractor(
    storage_path="69490c3a-9e0f-43ca-865f-3b3e4f832496/55207ad7-069d-4924-b791-e6f89544ba61/1778505097842_7sm9ux_2521-V_n_b_n_c_a_b_i_b_o-6912-2-10-20240315.pdf"
)

try:
    result = extractor.extract()
    
    print("\n=== TIÊU ĐỀ ===")
    print(result["title"])
    
    print("\n=== TÁC GIẢ ===")
    print(result["authors"])
    
    print("\n=== TÓM TẮT ===")
    print(result["abstract"])
    
    print("\n=== TỪ KHÓA ===")
    print(result["keywords"])
    
    print("\n=== NỘI DUNG ===")
    print(result["content"])
    
finally:
    extractor.cleanup()