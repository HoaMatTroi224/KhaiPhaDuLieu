from supabase import create_client
from datetime import datetime
import re
from collections import Counter

# ==================== CẤU HÌNH ====================
SUPABASE_URL = "https://deuiktggjicajryfyqnb.supabase.co"
SUPABASE_KEY = "sb_publishable_fKFi1IErN9lYGvmVI3oQ3w_5dW_984R"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestSupabaseData:
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
    
    def print_result(self, name, status, detail=""):
        if status:
            icon = f"{Colors.GREEN}✅{Colors.END}"
            self.passed += 1
        else:
            icon = f"{Colors.RED}❌{Colors.END}"
            self.failed += 1
        print(f"{icon} {name}: {Colors.BOLD}{'PASS' if status else 'FAIL'}{Colors.END}")
        if detail:
            print(f"   {detail}")
    
    def print_warning(self, name, detail=""):
        icon = f"{Colors.YELLOW}⚠️{Colors.END}"
        self.warnings += 1
        print(f"{icon} {name}: {Colors.YELLOW}WARN{Colors.END}")
        if detail:
            print(f"   {detail}")
    
    def print_header(self, text):
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
    
    # ==================== 21 TEST CASES ====================
    
    def run_all(self):
        print(f"\n{Colors.BOLD}{'🔬'*35}{Colors.END}")
        print(f"{Colors.BOLD}   LUMEN RESEARCH HUB - DATA INTEGRITY TESTS (21 tests){Colors.END}")
        print(f"{Colors.BOLD}{'🔬'*35}{Colors.END}")
        
        # === PHẦN 1: KẾT NỐI (1 test) ===
        self.print_header("1. KẾT NỐI")
        self.test_01_connection()
        
        # === PHẦN 2: BẢNG USERS (4 tests) ===
        self.print_header("2. BẢNG USERS (4 tests)")
        self.test_02_users_count()
        self.test_03_users_email_valid()
        self.test_04_users_email_unique()
        self.test_05_users_created_at()
        
        # === PHẦN 3: BẢNG PROJECTS (5 tests) ===
        self.print_header("3. BẢNG PROJECTS (5 tests)")
        self.test_06_projects_count()
        self.test_07_projects_collection_name_unique()
        self.test_08_projects_user_id_valid()
        self.test_09_projects_timestamps()
        self.test_10_projects_is_draft()
        
        # === PHẦN 4: BẢNG DOCUMENTS (6 tests) ===
        self.print_header("4. BẠNG DOCUMENTS (6 tests)")
        self.test_11_documents_count()
        self.test_12_documents_missing_title()
        self.test_13_documents_missing_content()
        self.test_14_documents_status_valid()
        self.test_15_documents_foreign_keys()
        self.test_16_documents_abstract_quality()
        
        # === PHẦN 5: BẢNG DOCUMENT_CHUNKS (3 tests) ===
        self.print_header("5. BẢNG DOCUMENT_CHUNKS (3 tests)")
        self.test_17_chunks_have_embeddings()
        self.test_18_embedding_dimension()
        self.test_19_chunks_orphan()
        
        # === PHẦN 6: BẢNG SUMMARIES & CHAT (2 tests) ===
        self.print_header("6. BẢNG SUMMARIES & CHAT (2 tests)")
        self.test_20_summaries_not_empty()
        self.test_21_chat_role_valid()
        
        # === TỔNG KẾT ===
        self.print_summary()
    
    # ========== TEST 1: KẾT NỐI ==========
    def test_01_connection(self):
        try:
            resp = supabase.table("projects").select("count", count="exact").limit(0).execute()
            self.print_result("1.1 Kết nối Supabase", True, f"Projects: {resp.count}")
        except Exception as e:
            self.print_result("1.1 Kết nối Supabase", False, str(e))
    
    # ========== TEST 2-5: USERS ==========
    def test_02_users_count(self):
        try:
            resp = supabase.table("users").select("id", count="exact").execute()
            self.print_result("2.1 Số lượng users", True, f"{resp.count} users")
        except Exception as e:
            self.print_result("2.1 Số lượng users", False, str(e))
    
    def test_03_users_email_valid(self):
        try:
            resp = supabase.table("users").select("email").execute()
            invalid = [u['email'] for u in resp.data if not re.match(r'^[^@]+@[^@]+\.[^@]+$', u.get('email', ''))]
            self.print_result("2.2 Email đúng định dạng", len(invalid) == 0, f"Sai: {len(invalid)} emails")
        except Exception as e:
            self.print_result("2.2 Email đúng định dạng", False, str(e))
    
    def test_04_users_email_unique(self):
        try:
            resp = supabase.table("users").select("email").execute()
            emails = [u.get('email') for u in resp.data if u.get('email')]
            duplicates = len(emails) - len(set(emails))
            self.print_result("2.3 Email không trùng", duplicates == 0, f"Trùng: {duplicates} emails")
        except Exception as e:
            self.print_result("2.3 Email không trùng", False, str(e))
    
    def test_05_users_created_at(self):
        try:
            resp = supabase.table("users").select("id").is_("created_at", "null").execute()
            missing = len(resp.data)
            self.print_result("2.4 created_at không null", missing == 0, f"Thiếu: {missing} users")
        except Exception as e:
            self.print_result("2.4 created_at không null", False, str(e))
    
    # ========== TEST 6-10: PROJECTS ==========
    def test_06_projects_count(self):
        try:
            resp = supabase.table("projects").select("id", count="exact").execute()
            self.print_result("3.1 Số lượng projects", True, f"{resp.count} projects")
        except Exception as e:
            self.print_result("3.1 Số lượng projects", False, str(e))
    
    def test_07_projects_collection_name_unique(self):
        try:
            resp = supabase.table("projects").select("collection_name").execute()
            names = [p.get('collection_name') for p in resp.data if p.get('collection_name')]
            duplicates = len(names) - len(set(names))
            self.print_result("3.2 collection_name không trùng", duplicates == 0, f"Trùng: {duplicates}")
        except Exception as e:
            self.print_result("3.2 collection_name không trùng", False, str(e))
    
    def test_08_projects_user_id_valid(self):
        try:
            users = supabase.table("users").select("id").execute()
            valid_ids = {str(u['id']) for u in users.data}
            projects = supabase.table("projects").select("user_id").execute()
            invalid = [p for p in projects.data if str(p.get('user_id')) not in valid_ids]
            self.print_result("3.3 user_id hợp lệ (FK)", len(invalid) == 0, f"Invalid: {len(invalid)}")
        except Exception as e:
            self.print_result("3.3 user_id hợp lệ (FK)", False, str(e))
    
    def test_09_projects_timestamps(self):
        try:
            resp = supabase.table("projects").select("created_at, updated_at").execute()
            missing = [p for p in resp.data if not p.get('created_at') or not p.get('updated_at')]
            self.print_result("3.4 created_at và updated_at đầy đủ", len(missing) == 0, f"Thiếu: {len(missing)}")
        except Exception as e:
            self.print_result("3.4 created_at và updated_at đầy đủ", False, str(e))
    
    def test_10_projects_is_draft(self):
        try:
            resp = supabase.table("projects").select("is_draft").execute()
            draft_count = sum(1 for p in resp.data if p.get('is_draft') == True)
            published_count = sum(1 for p in resp.data if p.get('is_draft') == False)
            self.print_result("3.5 Phân bố is_draft", True, f"Draft: {draft_count}, Published: {published_count}")
        except Exception as e:
            self.print_result("3.5 Phân bố is_draft", False, str(e))
    
    # ========== TEST 11-16: DOCUMENTS ==========
    def test_11_documents_count(self):
        try:
            resp = supabase.table("documents").select("id", count="exact").execute()
            self.print_result("4.1 Số lượng documents", True, f"{resp.count} documents")
        except Exception as e:
            self.print_result("4.1 Số lượng documents", False, str(e))
    
    def test_12_documents_missing_title(self):
        try:
            resp = supabase.table("documents").select("id").is_("title", "null").execute()
            missing = len(resp.data)
            self.print_result("4.2 Documents thiếu title", missing == 0, f"Thiếu: {missing} documents")
        except Exception as e:
            self.print_result("4.2 Documents thiếu title", False, str(e))
    
    def test_13_documents_missing_content(self):
        try:
            resp = supabase.table("documents").select("id").is_("extracted_content", "null").execute()
            missing = len(resp.data)
            self.print_result("4.3 Documents thiếu extracted_content", missing == 0, f"Thiếu: {missing} documents")
        except Exception as e:
            self.print_result("4.3 Documents thiếu extracted_content", False, str(e))
    
    def test_14_documents_status_valid(self):
        try:
            valid = ["uploaded", "processing", "indexed", "failed"]
            resp = supabase.table("documents").select("status").execute()
            invalid = [d for d in resp.data if d.get('status') not in valid]
            status_counts = Counter([d.get('status') for d in resp.data])
            detail = ", ".join([f"{k}:{v}" for k, v in status_counts.items()])
            self.print_result("4.4 Status hợp lệ", len(invalid) == 0, detail)
        except Exception as e:
            self.print_result("4.4 Status hợp lệ", False, str(e))
    
    def test_15_documents_foreign_keys(self):
        try:
            users = supabase.table("users").select("id").execute()
            valid_users = {str(u['id']) for u in users.data}
            projects = supabase.table("projects").select("id").execute()
            valid_projects = {str(p['id']) for p in projects.data}
            
            docs = supabase.table("documents").select("user_id, project_id").limit(200).execute()
            invalid_user = [d for d in docs.data if str(d.get('user_id')) not in valid_users]
            invalid_project = [d for d in docs.data if str(d.get('project_id')) not in valid_projects]
            
            self.print_result("4.5 Foreign keys hợp lệ", 
                            len(invalid_user) == 0 and len(invalid_project) == 0,
                            f"Invalid user_id: {len(invalid_user)}, invalid project_id: {len(invalid_project)}")
        except Exception as e:
            self.print_result("4.5 Foreign keys hợp lệ", False, str(e))
    
    def test_16_documents_abstract_quality(self):
        try:
            resp = supabase.table("documents").select("abstract").execute()
            null_count = sum(1 for d in resp.data if not d.get('abstract'))
            short_count = sum(1 for d in resp.data if d.get('abstract') and len(d['abstract']) < 50)
            self.print_warning("4.6 Abstract quality", f"Null: {null_count}, Quá ngắn (<50): {short_count}")
        except Exception as e:
            self.print_result("4.6 Abstract quality", False, str(e))
    
    # ========== TEST 17-19: DOCUMENT_CHUNKS ==========
    def test_17_chunks_have_embeddings(self):
        try:
            resp = supabase.table("document_chunks").select("id").is_("embedding", "null").limit(200).execute()
            missing = len(resp.data)
            self.print_result("5.1 Chunks có embedding", missing == 0, f"Thiếu embedding: {missing}/200 chunks", 
                            is_warning=(missing>0) if missing>0 else None)
            if missing > 0:
                self.print_warning("   → Có thể đang xử lý", "")
        except Exception as e:
            self.print_result("5.1 Chunks có embedding", False, str(e))
    
    
    def test_19_chunks_orphan(self):
        try:
            docs = supabase.table("documents").select("id").execute()
            valid_ids = {str(d['id']) for d in docs.data}
            chunks = supabase.table("document_chunks").select("document_id").limit(300).execute()
            orphan = [c for c in chunks.data if str(c.get('document_id')) not in valid_ids]
            self.print_result("5.3 Chunks không orphan", len(orphan) == 0, f"Orphan: {len(orphan)} chunks")
        except Exception as e:
            self.print_result("5.3 Chunks không orphan", False, str(e))
    
    # ========== TEST 20-21: SUMMARIES & CHAT ==========
    def test_20_summaries_not_empty(self):
        try:
            resp = supabase.table("summaries").select("summary_text").execute()
            empty = [s for s in resp.data if not s.get('summary_text')]
            self.print_result("6.1 Summaries không rỗng", len(empty) == 0, f"Rỗng: {len(empty)} summaries")
        except Exception as e:
            self.print_result("6.1 Summaries không rỗng", False, str(e))
    
    def test_21_chat_role_valid(self):
        try:
            resp = supabase.table("chat_history").select("role").limit(200).execute()
            invalid = [c for c in resp.data if c.get('role') not in ['user', 'assistant']]
            role_counts = Counter([c.get('role') for c in resp.data])
            detail = ", ".join([f"{k}:{v}" for k, v in role_counts.items()])
            self.print_result("6.2 Chat role hợp lệ", len(invalid) == 0, detail)
        except Exception as e:
            self.print_result("6.2 Chat role hợp lệ", False, str(e))
    
    # ========== TỔNG KẾT ==========
    def print_summary(self):
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}📈 KẾT QUẢ TỔNG HỢP{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.GREEN}✅ PASSED: {self.passed}{Colors.END}")
        print(f"{Colors.RED}❌ FAILED: {self.failed}{Colors.END}")
        print(f"{Colors.YELLOW}⚠️ WARNINGS: {self.warnings}{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL 21 DATA TESTS PASSED!{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}⚠️ {self.failed} TESTS FAILED. Please check above.{Colors.END}")


if __name__ == "__main__":
    test = TestSupabaseData()
    test.run_all()