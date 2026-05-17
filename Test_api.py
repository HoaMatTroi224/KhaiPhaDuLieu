import requests
import time
import json

# ==================== CẤU HÌNH ====================
BASE_URL = "https://khaiphadulieu-backend-954130532427.us-central1.run.app/"

# Token JWT (đã được cấp)
AUTH_TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6ImE2ZmFkMTgyLWQ1OGEtNGYxYS1iZjMwLTFjNTNlZTA5OGQ2OSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2RldWlrdGdnamljYWpyeWZ5cW5iLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI2OWU5NTJlOS00N2Y0LTQ5NDQtOWYyYy05MTA4ZGYxNjEwOTgiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzc5MDEzMjIzLCJpYXQiOjE3NzkwMDk2MjMsImVtYWlsIjoiMjMwMDE1MDFAaHVzLmVkdS52biIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiIyMzAwMTUwMUBodXMuZWR1LnZuIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImZ1bGxfbmFtZSI6ImJuIiwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiI2OWU5NTJlOS00N2Y0LTQ5NDQtOWYyYy05MTA4ZGYxNjEwOTgifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc3OTAwOTYyM31dLCJzZXNzaW9uX2lkIjoiMWVhMzUzMTUtNDNkZS00ZTUyLTk0N2QtMDMxZGQwNWVlNTJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.b4SVjRuHyQ9VqZMeMfRomH0VD2aPtUFJMJ4deBlMwngOG7pyweEg9FSsqZFSXWJsg70L8EHqyP0jGD10AxFKjQ"

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestAPI:
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.project_id = None
        self.document_id = None
    
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
    
    def print_header(self, text):
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'='*70}{Colors.END}")
    
    def run_all(self):
        print(f"\n{Colors.BOLD}{'🔬'*35}{Colors.END}")
        print(f"{Colors.BOLD}   LUMEN RESEARCH HUB - API BACKEND TESTS (13 tests){Colors.END}")
        print(f"{Colors.BOLD}{'🔬'*35}{Colors.END}")
        print(f"📍 Backend: {BASE_URL}")
        print(f"🔑 Token: {AUTH_TOKEN[:50]}...")
        
        # === 13 TEST CASES ===
        self.print_header("1. KIỂM TRA CƠ BẢN (2 tests)")
        self.test_01_health_check()
        self.test_02_api_docs()
        
        self.print_header("2. KIỂM TRA PROJECTS (3 tests)")
        self.test_03_get_projects()
        self.test_04_create_project()
        self.test_05_get_project_detail()
        
        self.print_header("3. KIỂM TRA DOCUMENTS (3 tests)")
        self.test_06_get_documents()
        self.test_07_get_document_detail()
        self.test_08_count_documents()
        
        self.print_header("4. KIỂM TRA CHAT & TÓM TẮT (3 tests)")
        self.test_09_chat_ask()
        self.test_10_chat_history()
        self.test_11_generate_summary()
        
        self.print_header("5. KIỂM TRA XỬ LÝ LỖI (2 tests)")
        self.test_12_not_found_error()
        self.test_13_cors_headers()
        
        # Tổng kết
        self.print_summary()
    
    # ========== TEST 1-2: CƠ BẢN ==========
    def test_01_health_check(self):
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=10)
            self.print_result("1.1 Health Check", resp.status_code == 200, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("1.1 Health Check", False, str(e))
    
    def test_02_api_docs(self):
        try:
            resp = requests.get(f"{BASE_URL}/docs", timeout=10)
            self.print_result("1.2 API Docs (Swagger)", resp.status_code == 200, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("1.2 API Docs (Swagger)", False, str(e))
    
    # ========== TEST 3-5: PROJECTS ==========
    def test_03_get_projects(self):
        try:
            resp = requests.get(f"{BASE_URL}/projects/", headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    self.project_id = data[0].get('id')
                self.print_result("2.1 GET /projects/", True, f"{len(data)} projects")
            else:
                self.print_result("2.1 GET /projects/", False, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("2.1 GET /projects/", False, str(e))
    
    def test_04_create_project(self):
        try:
            project_name = f"API_Test_{int(time.time())}"
            resp = requests.post(
                f"{BASE_URL}/projects/",
                headers=HEADERS,
                json={"name": project_name, "domain": "Testing"},
                timeout=10
            )
            is_ok = resp.status_code in [200, 201]
            self.print_result("2.2 POST /projects/", is_ok, f"Name: {project_name}, Status: {resp.status_code}")
        except Exception as e:
            self.print_result("2.2 POST /projects/", False, str(e))
    
    def test_05_get_project_detail(self):
        if not self.project_id:
            self.print_result("2.3 GET /projects/{id}", False, "No project ID available")
            return
        try:
            resp = requests.get(f"{BASE_URL}/projects/{self.project_id}", headers=HEADERS, timeout=10)
            self.print_result("2.3 GET /projects/{id}", resp.status_code == 200, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("2.3 GET /projects/{id}", False, str(e))
    
    # ========== TEST 6-8: DOCUMENTS ==========
    def test_06_get_documents(self):
        try:
            resp = requests.get(f"{BASE_URL}/documents/", headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    self.document_id = data[0].get('id')
                self.print_result("3.1 GET /documents/", True, f"{len(data)} documents")
            else:
                self.print_result("3.1 GET /documents/", False, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("3.1 GET /documents/", False, str(e))
    
    def test_07_get_document_detail(self):
        if not self.document_id:
            self.print_result("3.2 GET /documents/{id}", False, "No document ID available")
            return
        try:
            resp = requests.get(f"{BASE_URL}/documents/{self.document_id}", headers=HEADERS, timeout=10)
            self.print_result("3.2 GET /documents/{id}", resp.status_code == 200, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("3.2 GET /documents/{id}", False, str(e))
    
    def test_08_count_documents(self):
        try:
            resp = requests.get(f"{BASE_URL}/documents/", headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                count = len(resp.json())
                self.print_result("3.3 Tổng số documents", True, f"{count} documents in API")
            else:
                self.print_result("3.3 Tổng số documents", False, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("3.3 Tổng số documents", False, str(e))
    
    # ========== TEST 9-11: CHAT & SUMMARY ==========
    def test_09_chat_ask(self):
        if not self.project_id:
            self.print_result("4.1 POST /chat/ask", False, "No project ID available")
            return
        try:
            payload = {
                "project_id": self.project_id,
                "thread_id": f"test-thread-{int(time.time())}",
                "content": "Mục tiêu nghiên cứu của các bài báo trong project này là gì?"
            }
            resp = requests.post(f"{BASE_URL}/chat/ask", headers=HEADERS, json=payload, timeout=30)
            is_ok = resp.status_code == 200
            detail = f"Status: {resp.status_code}"
            if is_ok:
                data = resp.json()
                has_answer = "answer" in data or "response" in data
                detail += f", Has answer: {has_answer}"
            self.print_result("4.1 POST /chat/ask", is_ok, detail)
        except Exception as e:
            self.print_result("4.1 POST /chat/ask", False, str(e))
    
    def test_10_chat_history(self):
        if not self.project_id:
            self.print_result("4.2 GET /chat/history", False, "No project ID available")
            return
        try:
            resp = requests.get(f"{BASE_URL}/chat/history?project_id={self.project_id}", headers=HEADERS, timeout=10)
            self.print_result("4.2 GET /chat/history", resp.status_code == 200, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("4.2 GET /chat/history", False, str(e))
    
    def test_11_generate_summary(self):
        if not self.document_id:
            self.print_result("4.3 POST /summaries/generate", False, "No document ID available")
            return
        try:
            payload = {"document_ids": [self.document_id]}
            resp = requests.post(f"{BASE_URL}/summaries/generate", headers=HEADERS, json=payload, timeout=60)
            self.print_result("4.3 POST /summaries/generate", resp.status_code == 200, f"Status: {resp.status_code}")
        except Exception as e:
            self.print_result("4.3 POST /summaries/generate", False, str(e))
    
    # ========== TEST 12-13: ERROR HANDLING ==========
    def test_12_not_found_error(self):
        try:
            fake_id = "00000000-0000-0000-0000-000000000000"
            resp = requests.get(f"{BASE_URL}/projects/{fake_id}", headers=HEADERS, timeout=10)
            self.print_result("5.1 404 Error Handling", resp.status_code == 404, f"Status: {resp.status_code} (expected 404)")
        except Exception as e:
            self.print_result("5.1 404 Error Handling", False, str(e))
    
    def test_13_cors_headers(self):
        try:
            resp = requests.options(f"{BASE_URL}/projects/", headers={"Origin": "http://localhost:3000"}, timeout=10)
            has_cors = "access-control-allow-origin" in resp.headers
            self.print_result("5.2 CORS Headers", has_cors, "CORS present" if has_cors else "Missing CORS")
        except Exception as e:
            self.print_result("5.2 CORS Headers", False, str(e))
    
    # ========== TỔNG KẾT ==========
    def print_summary(self):
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}📈 KẾT QUẢ API TESTS{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.GREEN}✅ PASSED: {self.passed}{Colors.END}")
        print(f"{Colors.RED}❌ FAILED: {self.failed}{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL 13 API TESTS PASSED!{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}⚠️ {self.failed} TESTS FAILED. Please check above.{Colors.END}")


if __name__ == "__main__":
    test = TestAPI()
    test.run_all()