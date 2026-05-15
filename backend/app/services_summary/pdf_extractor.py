import os
import re
import tempfile
import unicodedata  # <-- mới thêm
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf4llm
import markdown
from bs4 import BeautifulSoup
from supabase import create_client, Client
from ..config import settings

logger = logging.getLogger(__name__)


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

# Figure / table caption lines
RE_CAPTION_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*)?"
    r"(?:"
    r"(?:Hình|Bảng|Figure|Fig\.?|Table|Chart|Biểu\s*đồ|Sơ\s*đồ|Ảnh)"
    r"\s*(?:\d+(?:\.\d+)*|[IVXLCDM]+)?\s*(?:[.:)\-–]|$)"
    r"|(?:Nguồn|Source)\s*[:.]"
    r")",
    re.IGNORECASE | re.UNICODE,
)

RE_MARKDOWN_IMAGE_LINE = re.compile(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$")
RE_IMAGE_ARTIFACT_LINE = re.compile(
    r"(?i)^\s*(?:\*{0,2})?(?:==>\s*)?"
    r"(?:picture|image|figure|graphic|formula|ảnh|hình)"
    r"\b.*(?:omitted|placeholder|block|intentionally|\[[0-9]+\s*x\s*[0-9]+\]|<==|\))"
)
RE_MARKDOWN_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
RE_GRID_TABLE_LINE = re.compile(r"^\s*\+[-=+:|\s]+\+\s*$")
RE_TABLE_SEPARATOR_LINE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
RE_DECORATIVE_SEPARATOR_LINE = re.compile(r"^\s*[-–—_=*·•]{3,}\s*$")
RE_SECTION_NUMBER_PREFIX = re.compile(
    r"^\s*(?:#{1,6}\s*)?"
    r"(?:"
    r"\d+(?:\.\d+)*\.?"
    r"|[IVXLCDM]+\.?"
    r"|[A-Z]\."
    r"|(?:Chương|Phần|Mục|Chapter|Part|Section)\s+\d+(?:\.\d+)*"
    r")\s+",
    re.IGNORECASE | re.UNICODE,
)
RE_PUBLICATION_METADATA_LINE = re.compile(
    r"(?ix)^\s*(?:\#{1,6}\s*)?(?:"
    r"(?:ngày\s+(?:nhận|gửi|sửa|duyệt|chấp\s*nhận|đăng|công\s*bố))\b"
    r"|(?:received|revised|accepted|published|available\s+online|submitted)\b"
    r"|(?:doi|issn|e-issn|isbn|udc|msc|jel|pacs)\s*[:/]"
    r"|(?:classification|classified|mã\s+số|chỉ\s*số\s*phân\s*loại)\b"
    r"|(?:copyright|©|bản\s+quyền|all\s+rights\s+reserved)\b"
    r"|(?:corresponding\s+author|tác\s+giả\s+liên\s+hệ|email\s*:|e-mail\s*:)"
    r"|(?:vol(?:ume)?\.?\s*\d+|no\.?\s*\d+|số\s+\d+|tập\s+\d+)\b"
    r")"
)
RE_EMAIL_OR_URL = re.compile(r"(?i)(?:[\w.+-]+@[\w-]+(?:\.[\w-]+)+|https?://|www\.)")

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


def _strip_accents(text: str) -> str:
    """Chuẩn hóa để so khớp mềm giữa tiếng Việt có dấu/không dấu."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def _normalize_for_match(text: str) -> str:
    text = strip_markdown(text)
    text = _strip_accents(text).lower()
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return normalize_whitespace(text)


def _remove_section_prefix(text: str) -> str:
    return RE_SECTION_NUMBER_PREFIX.sub("", strip_markdown(text)).strip(" .:-–—")


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _has_vietnamese_signal(text: str) -> bool:
    return bool(RE_VIET_UNICODE.search(text))


def _contains_any(normalized_text: str, terms: List[str]) -> bool:
    return any(term in normalized_text for term in terms)


HEADING_TAG_NAMES = ["h1", "h2", "h3", "h4", "h5", "h6"]

BODY_START_TERM_FAMILIES = [
    "mo dau",
    "dat van de",
    "gioi thieu",
    "tong quan",
    "boi canh",
    "co so",
    "ly thuyet",
    "muc tieu",
    "van de",
    "phuong phap",
    "vat lieu",
    "doi tuong",
    "noi dung",
    "nghien cuu lien quan",
    "cong trinh lien quan",
    "introduction",
    "background",
    "overview",
    "problem",
    "objective",
    "method",
    "methodology",
    "materials",
    "related work",
    "literature review",
]

BODY_STOP_TERM_FAMILIES = [
    "tai lieu tham khao",
    "references",
    "bibliography",
    "loi cam on",
    "loi cam ta",
    "acknowledg",
    "phu luc",
    "appendix",
    "funding",
    "kinh phi",
    "xung dot loi ich",
    "conflict of interest",
    "declaration",
    "tuyen bo",
    "supplement",
    "author contribution",
    "dong gop cua tac gia",
]

FRONT_MATTER_TERM_FAMILIES = [
    "tom tat",
    "abstract",
    "tu khoa",
    "keywords",
    "keyword",
    "classification",
    "phan loai",
    "ma so",
    "issn",
    "received",
    "accepted",
    "published",
    "ngay nhan",
    "ngay chap nhan",
    "ngay dang",
    "tac gia lien he",
    "corresponding author",
]

AFFILIATION_TERM_FAMILIES = [
    "truong dai hoc",
    "hoc vien",
    "khoa ",
    "vien ",
    "trung tam",
    "phong thi nghiem",
    "university",
    "faculty",
    "institute",
    "department",
    "laboratory",
    "school of",
]


def _is_markdown_table_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if RE_TABLE_SEPARATOR_LINE.match(stripped) or RE_GRID_TABLE_LINE.match(stripped):
        return True
    return bool(RE_MARKDOWN_TABLE_LINE.match(stripped) and stripped.count("|") >= 2)


def _is_image_artifact_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if RE_MARKDOWN_IMAGE_LINE.match(stripped):
        return True
    if RE_IMAGE_ARTIFACT_LINE.match(stripped):
        return True
    lowered = stripped.lower()
    return (
        lowered.startswith("(picture")
        or lowered.startswith("[image")
        or "data:image/" in lowered
        or "<img" in lowered
    )


def _is_publication_metadata_line(line: str) -> bool:
    stripped = strip_markdown(line)
    if not stripped:
        return False

    normalized = _normalize_for_match(stripped)
    if RE_PUBLICATION_METADATA_LINE.match(stripped) or RE_EMAIL_OR_URL.search(stripped):
        return True

    if _contains_any(normalized, FRONT_MATTER_TERM_FAMILIES) and _word_count(stripped) <= 20:
        return True

    has_affiliation_marker = bool(re.match(r"^\s*(?:\[\d+\]|\d+[,.\s]|[*†‡])", stripped))
    if has_affiliation_marker and _contains_any(normalized, AFFILIATION_TERM_FAMILIES):
        return True

    return False


def _is_front_matter_text(text: str) -> bool:
    normalized = _normalize_for_match(text)
    if not normalized:
        return False
    if _contains_any(normalized, FRONT_MATTER_TERM_FAMILIES) and (
        _looks_like_section_boundary(text) or _word_count(text) <= 28
    ):
        return True
    return _is_publication_metadata_line(text)


def _looks_like_section_boundary(text: str) -> bool:
    cleaned = strip_markdown(text)
    if not cleaned:
        return False
    if RE_SECTION_NUMBER_PREFIX.match(cleaned):
        return True
    if re.match(r"^\s*#{1,6}\s+", text):
        return True
    return _word_count(cleaned) <= 14 and len(cleaned) <= 140


def _has_body_start_term(text: str) -> bool:
    cleaned = strip_markdown(text)
    if not cleaned or _is_front_matter_text(cleaned) or _is_body_stop_text(cleaned):
        return False

    without_prefix = _remove_section_prefix(cleaned)
    normalized = _normalize_for_match(without_prefix)
    return _contains_any(normalized, BODY_START_TERM_FAMILIES) and _looks_like_section_boundary(cleaned)


def _is_body_start_text(text: str) -> bool:
    cleaned = strip_markdown(text)
    if not cleaned or _is_front_matter_text(cleaned) or _is_body_stop_text(cleaned):
        return False

    if _has_body_start_term(cleaned):
        return True

    # Flexible fallback: in academic PDFs the first real body heading is often
    # just a numbered Vietnamese section, even when the title is not recognized.
    return (
        bool(RE_SECTION_NUMBER_PREFIX.match(cleaned))
        and _has_vietnamese_signal(cleaned)
        and _word_count(cleaned) <= 16
    )


def _is_body_stop_text(text: str) -> bool:
    cleaned = strip_markdown(text)
    if not cleaned:
        return False

    without_prefix = _remove_section_prefix(cleaned)
    normalized = _normalize_for_match(without_prefix)
    if not _contains_any(normalized, BODY_STOP_TERM_FAMILIES):
        return False

    return _looks_like_section_boundary(cleaned)


def _is_non_body_artifact_line(line: str) -> bool:
    if not line.strip():
        return False
    return (
        RE_DECORATIVE_SEPARATOR_LINE.match(line.strip()) is not None
        or RE_CAPTION_LINE.match(line) is not None
        or _is_markdown_table_line(line)
        or _is_image_artifact_line(line)
        or _is_publication_metadata_line(line)
    )


def _is_preclean_artifact_line(line: str) -> bool:
    """
    Lọc artifact trước khi HTML hóa nhưng giữ các nhãn abstract/keywords làm mốc
    để bước tìm body biết cần bắt đầu sau front matter.
    """
    stripped = strip_markdown(line)
    return (
        RE_DECORATIVE_SEPARATOR_LINE.match(line.strip()) is not None
        or RE_CAPTION_LINE.match(line) is not None
        or _is_markdown_table_line(line)
        or _is_image_artifact_line(line)
        or RE_PUBLICATION_METADATA_LINE.match(stripped) is not None
        or RE_EMAIL_OR_URL.search(stripped) is not None
    )


def _drop_repeated_noise_lines(lines: List[str]) -> List[str]:
    counts: Dict[str, int] = {}
    for line in lines:
        key = _normalize_for_match(line)
        if key and len(key) <= 100:
            counts[key] = counts.get(key, 0) + 1

    filtered: List[str] = []
    for line in lines:
        key = _normalize_for_match(line)
        if (
            key
            and counts.get(key, 0) >= 2
            and len(key) <= 100
            and not _is_body_start_text(line)
            and not RE_SECTION_NUMBER_PREFIX.match(strip_markdown(line))
        ):
            continue
        filtered.append(line)

    return filtered


def _preclean_markdown(markdown_text: str) -> str:
    """
    Loại bỏ artifact hình/bảng/header/footer trước khi Markdown được đổi sang HTML.
    Bước này giữ nguyên heading Markdown và thứ tự đoạn văn cho phần xử lý sau.
    """
    markdown_text = unicodedata.normalize("NFC", markdown_text or "")
    markdown_text = RE_CONTROL_CHARS.sub("", markdown_text)

    lines = _drop_repeated_noise_lines(markdown_text.splitlines())
    cleaned: List[str] = []
    in_code_fence = False
    in_table_block = False
    caption_continuation = 0

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        if _is_markdown_table_line(line):
            in_table_block = True
            continue
        if in_table_block:
            if not stripped:
                in_table_block = False
            elif _is_markdown_table_line(line):
                continue
            else:
                in_table_block = False

        if caption_continuation:
            if not stripped:
                caption_continuation = 0
                cleaned.append("")
                continue
            if not _looks_like_section_boundary(line) and len(stripped) <= 170:
                caption_continuation -= 1
                continue
            caption_continuation = 0

        if RE_CAPTION_LINE.match(line):
            caption_continuation = 2
            continue

        if _is_preclean_artifact_line(line):
            continue

        cleaned.append(line)

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
    Làm sạch body text: xoá caption, citation, hình/bảng, metadata,
    dòng rác và chuẩn hoá khoảng trắng.
    """
    raw_body = unicodedata.normalize("NFC", raw_body or "")
    raw_body = RE_CONTROL_CHARS.sub("", raw_body)
    lines = _drop_repeated_noise_lines(raw_body.split("\n"))
    cleaned: List[str] = []
    in_table_block = False
    caption_continuation = 0

    for line in lines:
        if _is_body_stop_text(line):
            break

        if _is_markdown_table_line(line):
            in_table_block = True
            continue
        if in_table_block:
            if not line.strip():
                in_table_block = False
            elif _is_markdown_table_line(line):
                continue
            else:
                in_table_block = False

        if caption_continuation:
            if not line.strip():
                caption_continuation = 0
                cleaned.append("")
                continue
            if not _looks_like_section_boundary(line) and len(line.strip()) <= 170:
                caption_continuation -= 1
                continue
            caption_continuation = 0

        if RE_CAPTION_LINE.match(line):
            caption_continuation = 2
            continue

        if _is_non_body_artifact_line(line):
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
    body = re.sub(r"\s+([.,;:!?])", r"\1", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _clean_body_paragraph(text: str) -> str:
    """
    Làm sạch một đoạn văn bản body.
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

        self.temp_dir = tempfile.TemporaryDirectory()

        self.local_path: Optional[str] = None

        self.raw_markdown: Optional[str] = None
        self.html_content: Optional[str] = None

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
    # PYMUPDF4LLM / BODY BOUNDARIES
    # =========================================================================

    def _ensure_markdown_and_html(self) -> str:
        """
        Chuyển PDF sang Markdown bằng PyMuPDF4LLM, bỏ hình ảnh/header/footer
        ngay từ bước trích xuất rồi cache HTML cho các bước sau.
        """
        if self.html_content is not None:
            return self.html_content

        if not self.local_path:
            raise ValueError("PDF has not been downloaded yet")

        to_markdown_options = {
            "write_images": False,
            "embed_images": False,
            "page_chunks": False,
            "page_separators": False,
            "show_progress": False,
            "header": False,
            "footer": False,
            "ignore_code": True,
            "force_text": False,
        }
        try:
            raw_markdown = pymupdf4llm.to_markdown(self.local_path, **to_markdown_options)
        except ValueError as exc:
            if "Images and text on images cannot both be suppressed" not in str(exc):
                raise
            to_markdown_options["force_text"] = True
            raw_markdown = pymupdf4llm.to_markdown(self.local_path, **to_markdown_options)

        if isinstance(raw_markdown, list):
            raw_markdown = "\n\n".join(
                chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                for chunk in raw_markdown
            )

        self.raw_markdown = _preclean_markdown(str(raw_markdown or ""))
        self.html_content = markdown.markdown(
            self.raw_markdown,
            extensions=["extra", "sane_lists"],
        )
        return self.html_content

    @staticmethod
    def _is_body_start_heading(text: str) -> bool:
        return _is_body_start_text(text)

    @staticmethod
    def _is_body_stop_heading(text: str) -> bool:
        return _is_body_stop_text(text)

    @staticmethod
    def _tag_text(tag) -> str:
        return tag.get_text(" ", strip=True) if tag else ""

    @staticmethod
    def _is_heading_tag(tag) -> bool:
        return bool(tag and tag.name in HEADING_TAG_NAMES)

    def _is_body_heading_candidate(self, tag) -> bool:
        if not self._is_heading_tag(tag):
            return False

        text = self._tag_text(tag)
        if not text:
            return False
        if _is_body_stop_text(text) or _is_front_matter_text(text):
            return False
        if _is_non_body_artifact_line(text):
            return False

        cleaned = strip_markdown(text)
        return _looks_like_section_boundary(cleaned) and (
            _has_vietnamese_signal(cleaned)
            or bool(RE_SECTION_NUMBER_PREFIX.match(cleaned))
            or _word_count(cleaned) <= 14
        )

    def _is_meaningful_body_tag(self, tag) -> bool:
        text = self._tag_text(tag)
        if not text:
            return False
        if tag.name in ["table", "thead", "tbody", "tr", "td", "th", "img", "figure", "figcaption"]:
            return False
        if _is_body_stop_text(text) or _is_front_matter_text(text):
            return False
        if _is_non_body_artifact_line(text):
            return False
        if _is_body_start_text(text):
            return True
        if _looks_like_section_boundary(text):
            return bool(_has_vietnamese_signal(text) or RE_SECTION_NUMBER_PREFIX.match(text))
        return len(text) >= 50 and (_has_vietnamese_signal(text) or _word_count(text) >= 10)

    def _find_body_start_index(self, tags: List) -> Optional[int]:
        # 1) Ưu tiên các mốc section học thuật quen thuộc nếu có.
        in_front_matter_block = False
        for index, tag in enumerate(tags):
            text = self._tag_text(tag)
            if _is_front_matter_text(text) or _is_publication_metadata_line(text):
                in_front_matter_block = True
                continue
            if in_front_matter_block:
                if tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"] or _looks_like_section_boundary(text):
                    in_front_matter_block = False
                else:
                    continue
            if (
                _has_body_start_term(text)
                and (self._is_heading_tag(tag) or RE_SECTION_NUMBER_PREFIX.match(strip_markdown(text)))
            ):
                return index

        # 2) Nếu không có body-start term family, lấy heading hợp lệ đầu tiên
        # sau abstract/keywords/metadata làm mốc body.
        front_matter_index = -1
        in_front_matter_block = False
        scan_limit = min(len(tags), 80)
        for index, tag in enumerate(tags[:scan_limit]):
            text = self._tag_text(tag)
            if (
                _has_body_start_term(text)
                and (self._is_heading_tag(tag) or RE_SECTION_NUMBER_PREFIX.match(strip_markdown(text)))
            ):
                break
            if _is_front_matter_text(text) or _is_publication_metadata_line(text):
                front_matter_index = index
                in_front_matter_block = True
                continue
            if in_front_matter_block:
                if tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"] or _looks_like_section_boundary(text):
                    in_front_matter_block = False
                else:
                    front_matter_index = index

        if front_matter_index >= 0:
            for index in range(front_matter_index + 1, len(tags)):
                if self._is_body_heading_candidate(tags[index]):
                    return index
            for index in range(front_matter_index + 1, len(tags)):
                if self._is_meaningful_body_tag(tags[index]):
                    return index

        heading_candidates = [
            index
            for index, tag in enumerate(tags)
            if self._is_body_heading_candidate(tag)
        ]
        if heading_candidates:
            first_index = heading_candidates[0]
            first_tag = tags[first_index]
            first_text = strip_markdown(self._tag_text(first_tag))
            looks_like_title = (
                first_index <= 2
                and first_tag.name in ["h1", "h2"]
                and not RE_SECTION_NUMBER_PREFIX.match(first_text)
            )
            if looks_like_title and len(heading_candidates) > 1:
                return heading_candidates[1]
            return first_index

        for index, tag in enumerate(tags):
            text = self._tag_text(tag)
            if (
                RE_SECTION_NUMBER_PREFIX.match(strip_markdown(text))
                and self._is_meaningful_body_tag(tag)
            ):
                return index

        for index, tag in enumerate(tags):
            if index < 3 and tag.name in ["h1", "h2", "h3"]:
                continue
            if self._is_meaningful_body_tag(tag):
                return index

        return None

    def _tag_to_markdown(self, tag) -> str:
        if not tag:
            return ""

        if tag.name in ["table", "thead", "tbody", "tr", "td", "th", "img", "figure", "figcaption", "pre", "code"]:
            return ""

        text = self._tag_text(tag)
        if not text or _is_non_body_artifact_line(text) or _is_front_matter_text(text):
            return ""

        if tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(tag.name[1])
            content = clean_line(text)
            return f"{'#' * level} {content}" if content else ""

        if tag.name == "p":
            return _clean_body_paragraph(text)

        if tag.name in ["ul", "ol"]:
            items: List[str] = []
            list_items = tag.find_all("li", recursive=False) or tag.find_all("li")
            try:
                start = int(tag.get("start", 1))
            except (TypeError, ValueError):
                start = 1

            for offset, li in enumerate(list_items):
                item_text = _clean_body_paragraph(li.get_text(" ", strip=True))
                if not item_text or _is_non_body_artifact_line(item_text) or _is_front_matter_text(item_text):
                    continue
                marker = "-" if tag.name == "ul" else f"{start + offset}."
                items.append(f"{marker} {item_text}")
            return "\n".join(items)

        return _clean_body_paragraph(text)


    def extract_body_text(self) -> str:
        """
        Trích xuất body bằng PyMuPDF4LLM + BeautifulSoup.

        Cách làm:
          1. PDF → Markdown bằng pymupdf4llm
          2. Markdown → HTML bằng markdown
          3. Tìm ranh giới bắt đầu body bằng tín hiệu section học thuật
          4. Lấy nội dung đến trước ranh giới hậu kỳ như tài liệu tham khảo,
             phụ lục, lời cảm ơn, funding/conflict...
        """
        html_content = self._ensure_markdown_and_html()
        soup = BeautifulSoup(html_content, "html.parser")

        for non_text_tag in soup.find_all(["img", "figure", "figcaption", "table", "thead", "tbody", "tr", "td", "th", "pre", "code"]):
            non_text_tag.decompose()

        tags = [
            tag
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol"])
            if self._tag_text(tag)
        ]
        start_index = self._find_body_start_index(tags)
        if start_index is None:
            return ""

        parts: List[str] = []
        for tag in tags[start_index:]:
            text = self._tag_text(tag)
            if self._is_body_stop_heading(text):
                break
            if _is_non_body_artifact_line(text) or _is_publication_metadata_line(text):
                continue

            converted = self._tag_to_markdown(tag)
            if converted:
                parts.append(converted)

        raw_body = "\n\n".join(parts)
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
        self._ensure_markdown_and_html()

        # Lấy phần đầu Markdown (đủ chứa metadata) → chuyển thành HTML
        header_md = (self.raw_markdown or "")[:5000]
        html_content = markdown.markdown(header_md)

        return _extract_metadata_from_html(html_content)

    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================

    def extract(self) -> Dict:
        """
        Full extraction pipeline. Chỉ đưa body text sạch vào content; metadata
        học thuật ở đầu/cuối bài được bỏ khỏi luồng xử lý chính.
        """
        self.download_from_supabase()

        body_text = self.extract_body_text()
        try:
            metadata = self.extract_metadata()
        except Exception as exc:
            logger.warning(
                "Metadata extraction failed for %s: %s",
                self.storage_path,
                exc,
                exc_info=True,
            )
            metadata = {}

        return {
            "title": metadata.get("title", ""),
            "authors": metadata.get("authors", ""),
            "abstract": metadata.get("abstract", ""),
            "keywords": metadata.get("keywords", ""),
            "content": body_text,
            "storage_path": self.storage_path,
        }

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup(self):
        """Xóa thư mục tạm."""
        self.temp_dir.cleanup()
