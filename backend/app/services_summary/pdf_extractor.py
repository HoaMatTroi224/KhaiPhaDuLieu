import io
import os
import re
import json
import tempfile
import unicodedata  # <-- mới thêm
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf4llm
import markdown
from bs4 import BeautifulSoup
from supabase import create_client, Client
from grobid_client.grobid_client import GrobidClient
from ..config import settings


# =============================================================================
# REGEX CONSTANTS (dành cho làm sạch body text)
# =============================================================================

# --- Markdown stripping helpers (giữ lại cho body cleaning) ---

RE_MARKDOWN_EMPHASIS = re.compile(r"[_*]{1,3}(.*?)[_*]{1,3}")
RE_MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s*")
RE_MARKDOWN_CODE = re.compile(r"`[^`]*`")

# Citation / reference artifacts in body text
RE_CITATION_BRACKET = re.compile(r"\[\d+(?:[,\-–]\s*\d+)*\](\[\d+(?:[,\-–]\s*\d+)*\])*")
RE_CITATION_PAREN = re.compile(r"\(\d+(?:,\s*\d+)*\)")

# Figure / table caption lines (GROBID false headings)
RE_CAPTION_LINE = re.compile(
    r"^\s*#{1,6}\s*"
    r"(?:Hình|Bảng|Figure|Table|Chart|Biểu\s*đồ|Sơ\s*đồ|Ảnh)\s*\d+",
    re.IGNORECASE | re.UNICODE,
)

# Vietnamese Unicode detector (dùng trong body cleaning nếu cần)
RE_VIET_UNICODE = re.compile(r"[àáạảãăắặẳẵâấậẩẫèéẹẻẽêếệểễìíịỉĩòóọỏõôốộổỗơớợởỡùúụủũưứựửữỳýỵỷỹđ]", re.IGNORECASE)

# Định dạng chỉ số liên kết tác giả: [1], [1,2], [1*], [*], [2,3,4*]...
RE_AFFILIATION_MARKER = re.compile(r"\[\*?[\d,\s*]+\*?\]")
# Đuôi số không nằm trong ngoặc: "Nguyễn Văn A1,2,3" → bỏ ",1,2,3"
RE_TRAILING_SUPERSCRIPT = re.compile(r"[\d,\s]+$")

# Regex loại bỏ ký tự điều khiển (trừ tab, newline)
RE_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


# =============================================================================
# SHARED NORMALIZATION HELPERS (giữ nguyên cho body text)
# =============================================================================

def strip_markdown(text: str) -> str:
    """Loại bỏ cú pháp markdown khỏi đoạn văn bản."""
    text = unicodedata.normalize('NFC', text)
    text = RE_CONTROL_CHARS.sub('', text)
    text = RE_MARKDOWN_HEADING.sub("", text)
    text = RE_MARKDOWN_CODE.sub("", text)
    for _ in range(3):
        new = RE_MARKDOWN_EMPHASIS.sub(r"\1", text)
        if new == text:
            break
        text = new
    text = re.sub(r"(?<!\w)[*_]+(?!\w)", "", text)
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Thu gọn khoảng trắng thừa."""
    return re.sub(r"[ \t]+", " ", text).strip()


def clean_line(line: str) -> str:
    """
    Làm sạch một dòng: chuẩn hóa Unicode NFC, xóa ký tự điều khiển,
    bỏ markdown và chuẩn hoá khoảng trắng.
    """
    line = unicodedata.normalize('NFC', line)
    line = RE_CONTROL_CHARS.sub('', line)
    line = strip_markdown(line)          # lưu ý: strip_markdown đã gọi normalize/control bên trong
    return normalize_whitespace(line)

def clean_authors(raw_authors: str) -> str:
    """
    Làm sạch chuỗi tác giả từ HTML:
    - Xóa các chỉ số liên kết dạng [1], [1,2], [*]...
    - Xóa các dấu * _ # không cần thiết
    - Chuẩn hoá khoảng trắng, tách tên theo dấu phẩy
    - Trả về chuỗi tác giả sạch, phân cách bởi dấu phẩy
    """
    # Loại bỏ markdown còn sót (nếu có)
    raw_authors = unicodedata.normalize('NFC', raw_authors)
    raw_authors = RE_CONTROL_CHARS.sub('', raw_authors)
    raw_authors = strip_markdown(raw_authors)  # dùng helper có sẵn

    # Tách thành các token theo dấu phẩy hoặc chấm phẩy
    tokens = re.split(r"[,;]", raw_authors)

    cleaned = []
    seen = set()
    for token in tokens:
        token = token.strip()
        # Xóa các marker affiliation [1], [*]...
        token = RE_AFFILIATION_MARKER.sub("", token)
        # Xóa đuôi số nếu còn (trường hợp không có ngoặc)
        token = RE_TRAILING_SUPERSCRIPT.sub("", token)
        token = token.strip()

        # Bỏ token quá ngắn, toàn số, hoặc rỗng
        if len(token) < 4 or token.isdigit():
            continue
        # Loại bỏ các dòng chỉ chứa dấu câu
        if not any(c.isalpha() for c in token):
            continue
        if token not in seen:
            seen.add(token)
            cleaned.append(token)

    return ", ".join(cleaned)


# =============================================================================
# HTML METADATA EXTRACTOR (mới)
# =============================================================================

def _extract_metadata_from_html(html_content: str) -> Dict:
    """
    Trích xuất metadata (title, authors, abstract, keywords) từ HTML
    được chuyển đổi từ Markdown của PyMuPDF4LLM.

    Cấu trúc kỳ vọng (xem ví dụ từ các bài báo mẫu):
      - Tiêu đề: thẻ Heading đầu tiên (<h1> hoặc <h2>)
      - Tác giả: thẻ ngay sau tiêu đề, chứa dấu ngoặc vuông ([1], [*], …)
      - Tóm tắt: tìm thẻ Heading chứa "Tóm tắt" (có thể viết sai chính tả)
                 rồi lấy thẻ <p> kế tiếp
      - Từ khóa: thẻ <p> chứa "Từ khóa"/"Từ khoá", loại bỏ nhãn
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. Title: heading đầu tiên
    title_tag = soup.find(['h1', 'h2'])
    title = title_tag.get_text(strip=True) if title_tag else ""

    # 2. Authors: sibling ngay sau title, chứa dấu ngoặc vuông
    author_tag = None
    if title_tag:
        for sibling in title_tag.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
                text = sibling.get_text(strip=True)
                if re.search(r'\[.*?\]', text):
                    author_tag = sibling
                    break
    authors = clean_authors(author_tag.get_text(strip=True)) if author_tag else ""

    # 3. Abstract: heading chứa "Tóm tắt" (chấp nhận lỗi chính tả)
    abstract_heading = soup.find(
        lambda tag: tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        and re.search(r'T[oó]m\s*t[ắă]t', tag.get_text(), re.I)
    )
    abstract = ""
    if abstract_heading:
        abstract_p = abstract_heading.find_next('p')
        if abstract_p:
            abstract = abstract_p.get_text(strip=True)

    # 4. Keywords: thẻ <p> chứa nhãn "Từ khóa"/"Từ khoá"
    kw_tag = soup.find(
        lambda tag: tag.name == 'p'
        and re.search(r'Từ\s*kh[oó]a', tag.get_text(), re.I)
    )
    keywords = ""
    if kw_tag:
        full = kw_tag.get_text(strip=True)
        keywords = re.sub(r'^.*?Từ\s*kh[oó]a\s*:?\s*', '', full, flags=re.I).strip()

    return {
        'title': title,
        'authors': authors,
        'abstract': abstract,
        'keywords': keywords,
    }


# =============================================================================
# BODY TEXT CLEANING HELPERS (giữ nguyên)
# =============================================================================

def _is_junk_line(line: str) -> bool:
    """
    Kiểm tra xem dòng có phải là dòng vô nghĩa (rác từ PDF) hay không.
    Mở rộng để bắt cả dòng chứa ký tự đặc biệt, số lẻ, dấu chấm.
    Mẫu: "R w B S j = * P R m N", "68. 2086", "76 27560"
    """
    if not line.strip():
        return False

    # Chuẩn hóa Unicode NFC, xóa ký tự điều khiển
    line = unicodedata.normalize('NFC', line)
    line = RE_CONTROL_CHARS.sub('', line)

    # Nếu có chứa ký tự tiếng Việt thì chắc chắn không phải rác
    if RE_VIET_UNICODE.search(line):
        return False

    tokens = line.split()
    if not tokens:
        return False

    # Định nghĩa token "rác"
    def is_junk_token(tok: str) -> bool:
        # Số nguyên hoặc số có dấu chấm cuối (vd: "68.", "2086")
        if re.fullmatch(r'\d{1,4}\.*', tok):
            return True
        # Chỉ toàn dấu câu / ký tự đặc biệt (không chứa chữ cái hay số)
        if not any(c.isalnum() for c in tok):
            return True
        # Token dài 1-2 ký tự, không phải từ viết tắt phổ biến (vd: "et", "al")
        # Ta coi là rác nếu không chứa chữ cái hoặc độ dài <=2 và không phải từ có nghĩa
        # (để an toàn, ta đánh dấu rác nếu độ dài <=2 và không phải chữ số thuần)
        if len(tok) <= 2 and not tok.isdigit():
            # Nếu là chữ cái đơn lẻ hoặc cặp chữ-số lộn xộn
            return True
        # Còn lại không phải rác
        return False

    # Nếu tất cả token đều là rác → dòng rác
    if all(is_junk_token(t) for t in tokens):
        return True

    # Dòng quá ngắn (dưới 10 ký tự sau khi xóa khoảng trắng) và không có chữ cái liên tục
    stripped = line.replace(' ', '')
    if len(stripped) < 10 and not any(c.isalpha() for c in stripped):
        return True

    return False


def clean_body_text(raw_body: str) -> str:
    """
    Làm sạch body text từ GROBID: xoá caption, citation, dòng rác,
    chuẩn hoá khoảng trắng.
    """
    lines = raw_body.split("\n")
    cleaned: List[str] = []

    for line in lines:
        if RE_CAPTION_LINE.match(line):
            continue

        # Lọc dòng rác vô nghĩa (dòng ngắn, lộn xộn số / chữ)
        if _is_junk_line(line):
            continue

        line = RE_CITATION_BRACKET.sub("", line)
        line = RE_CITATION_PAREN.sub("", line)

        if re.match(r"^\s*#{1,6}\s", line):
            heading_match = re.match(r"^(\s*#{1,6}\s+)(.*)", line)
            if heading_match:
                marker = heading_match.group(1)
                content = clean_line(heading_match.group(2))
                line = marker + content
        else:
            line = normalize_whitespace(line)

        if not line.strip():
            cleaned.append("")
            continue

        cleaned.append(line)

    body = "\n".join(cleaned)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _clean_body_paragraph(text: str) -> str:
    """
    Làm sạch một đoạn văn bản trích từ GROBID body_text.
    """
    # Chuẩn hóa Unicode NFC và loại bỏ ký tự điều khiển
    text = unicodedata.normalize('NFC', text)
    text = RE_CONTROL_CHARS.sub('', text)

    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = RE_CITATION_BRACKET.sub("", text)
    text = RE_CITATION_PAREN.sub("", text)
    text = normalize_whitespace(text)
    return text


# =============================================================================
# FILE EXTRACTOR
# =============================================================================

class PDFExtractor:
    """
    Extractor cho bài báo khoa học tiếng Việt.
    """

    def __init__(self, storage_path: str):
        """
        Parameters
        ----------
        storage_path:
            documents/user_id/project_id/unique_name.pdf
        """
        self.bucket_name = "documents"
        self.storage_path = storage_path

        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )

        self.grobid_client = GrobidClient(
            config_path=None,
            grobid_server="http://grobid:8070",
        )

        self.temp_dir = tempfile.TemporaryDirectory()

        self.local_path: Optional[str] = None
        self.json_path: Optional[str] = None

        self.raw_markdown: Optional[str] = None
        self.grobid_data: Optional[dict] = None

    # =========================================================================
    # SUPABASE
    # =========================================================================

    # def download_from_supabase(self) -> str:
    #     """Download file từ Supabase Storage về thư mục tạm."""
    #     file_bytes = (
    #         self.supabase
    #         .storage
    #         .from_(self.bucket_name)
    #         .download(self.storage_path)
    #     )

    #     # Kiểm tra magic number của PDF
    #     if not file_bytes[:5] == b'%PDF':
    #         raise ValueError(
    #             f"File '{self.storage_path}' không phải là PDF hợp lệ "
    #             f"(thiếu header %PDF)."
    #         )

    #     file_name = Path(self.storage_path).name
    #     local_path = os.path.join(self.temp_dir.name, file_name)

    #     with open(local_path, "wb") as f:
    #         f.write(file_bytes)

    #     self.local_path = local_path
    #     return local_path

    def download_from_supabase(self) -> str:
        """Download file từ Supabase Storage về thư mục tạm."""
        try:
            file_bytes = (
                self.supabase
                .storage
                .from_(self.bucket_name)
                .download(self.storage_path)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to download from Supabase: {e}") from e
        
        # Kiểm tra PDF header
        if not file_bytes.startswith(b'%PDF'):
            # Thử decode để xem có phải HTML/JSON error không
            try:
                preview = file_bytes[:200].decode('utf-8', errors='ignore')
                print(f"[ERROR] File content preview: {preview[:200]}")
            except:
                pass
            raise ValueError(
                f"File '{self.storage_path}' không phải là PDF hợp lệ "
                f"(expected header b'%PDF-', got: {file_bytes[:5]!r})."
            )

        file_name = Path(self.storage_path).name
        local_path = os.path.join(self.temp_dir.name, file_name)

        with open(local_path, "wb") as f:
            f.write(file_bytes)

        self.local_path = local_path
        return local_path

    # =========================================================================
    # GROBID
    # =========================================================================

    def run_grobid(self) -> str:
        """Parse PDF bằng GROBID."""
        if not self.local_path:
            self.download_from_supabase()

        output_dir = os.path.join(self.temp_dir.name, "grobid_output")
        os.makedirs(output_dir, exist_ok=True)

        input_dir = os.path.dirname(self.local_path)

        self.grobid_client.process(
            service="processFulltextDocument",
            input_path=input_dir,
            output=output_dir,
            n=1,
            json_output=True,
        )

        pdf_stem = Path(self.local_path).stem
        json_path = os.path.join(output_dir, f"{pdf_stem}.json")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Không tìm thấy file JSON: {json_path}")

        self.json_path = json_path
        return json_path

    def load_json(self) -> dict:
        """Load file JSON output từ GROBID."""
        if not self.json_path:
            self.run_grobid()

        with open(self.json_path, "r", encoding="utf-8") as f:
            self.grobid_data = json.load(f)

        return self.grobid_data

    def extract_body_text(self) -> str:
        """
        Trích xuất và làm sạch body text từ GROBID JSON.
        """
        if not self.grobid_data:
            self.load_json()

        body_parts: List[str] = []
        current_section = ""

        for para in self.grobid_data.get("body_text", []):
            section = para.get("head_section", "").strip()

            if section and section != current_section:
                current_section = section
                body_parts.append(f"\n\n## {section}\n")

            text = para.get("text", "").strip()
            if text:
                text = _clean_body_paragraph(text)
                body_parts.append(text)

        raw_body = "\n\n".join(body_parts)
        return clean_body_text(raw_body)

    # =========================================================================
    # PYMUPDF4LLM → MARKDOWN → HTML → METADATA (đã thay đổi)
    # =========================================================================

    def extract_metadata(self) -> Dict:
        """
        Trích xuất metadata bằng cách:
          1. Dùng PyMuPDF4LLM chuyển PDF → Markdown
          2. Chuyển Markdown → HTML (dùng thư viện 'markdown')
          3. Dùng BeautifulSoup phân tích HTML để lấy title, authors, abstract, keywords
        """
        if not self.local_path:
            self.download_from_supabase()

        self.raw_markdown = pymupdf4llm.to_markdown(
            self.local_path,
            header=False,
            footer=False,
            show_progress=False,
        )

        # Lấy phần đầu Markdown (đủ chứa metadata) → chuyển thành HTML
        header_md = self.raw_markdown[:5000]
        html_content = markdown.markdown(header_md)

        return _extract_metadata_from_html(html_content)

    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================

    def extract(self) -> Dict:
        """
        Full extraction pipeline.
        """
        self.download_from_supabase()

        metadata = self.extract_metadata()

        self.run_grobid()
        body_text = self.extract_body_text()

        return {
            "title": metadata.get("title"),
            "authors": metadata.get("authors"),
            "abstract": metadata.get("abstract"),
            "keywords": metadata.get("keywords"),
            "content": body_text,
            "storage_path": self.storage_path,
        }

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup(self):
        """Xóa thư mục tạm."""
        self.temp_dir.cleanup()