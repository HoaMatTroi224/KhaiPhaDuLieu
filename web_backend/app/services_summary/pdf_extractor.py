import os
import re
import tempfile
import unicodedata  # <-- mới thêm
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf4llm
import pymupdf
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

# Thay RE_AFFILIATION_MARKER cũ bằng regex rộng hơn
RE_AFFILIATION_MARKER = re.compile(r"\[[^\]]*\]")  # xóa mọi [...] bất kể nội dung
# Đuôi số không nằm trong ngoặc: "Nguyễn Văn A1,2,3" → bỏ ",1,2,3"
RE_TRAILING_SUPERSCRIPT = re.compile(r"[\d,\s]+$")

# Regex loại bỏ ký tự điều khiển (trừ tab, newline)
RE_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

RE_VIET_FULLNAME_LIST = re.compile(
    r"^[A-ZĐÀÁẠẢÃĂẮẶẲẴÂẤẬẨẪÈÉẸẺẼÊẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỐỘỔỖƠỚỢỞỠÙÚỤỦŨƯỨỰỬỮỲÝỴỶỸ]"
    r"[a-zđàáạảãăắặẳẵâấậẩẫèéẹẻẽêếệểễìíịỉĩòóọỏõôốộổỗơớợởỡùúụủũưứựửữỳýỵỷỹ]+"
    r"(?:\s+"
    r"[A-ZĐÀÁẠẢÃĂẮẶẲẴÂẤẬẨẪÈÉẸẺẼÊẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỐỘỔỖƠỚỢỞỠÙÚỤỦŨƯỨỰỬỮỲÝỴỶỸ]"
    r"[a-zđàáạảãăắặẳẵâấậẩẫèéẹẻẽêếệểễìíịỉĩòóọỏõôốộổỗơớợởỡùúụủũưứựửữỳýỵỷỹ]+"
    r"){1,4}$",
    re.UNICODE,
)

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
ABSTRACT_LABEL_TERMS = ["tom tat"]
KEYWORD_LABEL_TERMS = ["tu khoa"]
RE_ABSTRACT_LABEL = re.compile(r"(?is)T[oó]m\s*t[aăắ]t\s*:?\s*")
RE_KEYWORD_LABEL = re.compile(r"(?is)T(?:ừ|u)\s*kh(?:[oó]a|oá)\s*:?\s*")

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

def _looks_like_author_name(token: str) -> bool:
    """Kiểm tra token có phải tên người (Việt/Hán/Latin) không."""
    token = token.strip()
    if not token or len(token) < 4:
        return False
    if not any(c.isalpha() for c in token):
        return False
    # Tên người: mỗi từ viết hoa chữ đầu, không chứa số
    parts = token.split()
    if not (2 <= len(parts) <= 5):
        return False
    return all(
        p[0].isupper() and not any(c.isdigit() for c in p)
        for p in parts
        if p
    )


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


def _extract_plain_text_with_pymupdf(local_path: str) -> str:
    pages: List[str] = []
    with pymupdf.open(local_path) as doc:
        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                pages.append(page_text)
    return "\n\n".join(pages)


# =============================================================================
# HTML METADATA EXTRACTOR (mới)
# =============================================================================

def _clean_metadata_text(text: str) -> str:
    text = strip_markdown(unicodedata.normalize("NFC", text or ""))
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return normalize_whitespace(text)


def _find_metadata_label_match(
    text: str,
    label_pattern: re.Pattern,
    label_terms: List[str],
):
    cleaned = _clean_metadata_text(text)
    if not cleaned or not _contains_any(_normalize_for_match(cleaned), label_terms):
        return None

    label_match = label_pattern.search(cleaned)
    if not label_match:
        return None

    prefix = cleaned[:label_match.start()].strip()
    suffix = cleaned[label_match.end():].strip()
    matched_label = label_match.group(0)
    has_colon = ":" in matched_label
    starts_text = not prefix
    label_only = starts_text and not suffix

    return label_match if (has_colon or starts_text or label_only) else None


def _tag_contains_metadata_label(
    tag,
    label_pattern: re.Pattern,
    label_terms: List[str],
) -> bool:
    if not tag or tag.name in ["script", "style"]:
        return False
    return _find_metadata_label_match(
        tag.get_text(" ", strip=True),
        label_pattern,
        label_terms,
    ) is not None


def _find_tags_containing_label(
    soup: BeautifulSoup,
    label_pattern: re.Pattern,
    label_terms: List[str],
) -> List:
    return [
        tag
        for tag in soup.find_all(True)
        if _tag_contains_metadata_label(tag, label_pattern, label_terms)
    ]


def _strip_metadata_label(
    text: str,
    label_pattern: re.Pattern,
    label_terms: List[str],
) -> str:
    cleaned = _clean_metadata_text(text)
    if not cleaned or not _contains_any(_normalize_for_match(cleaned), label_terms):
        return ""

    label_match = _find_metadata_label_match(cleaned, label_pattern, label_terms)
    if label_match:
        return cleaned[label_match.end():].strip(" :.-–—")

    return ""


def _extract_labeled_metadata_value(
    tag,
    label_pattern: re.Pattern,
    label_terms: List[str],
    stop_label_pattern: Optional[re.Pattern] = None,
    stop_terms: Optional[List[str]] = None,
) -> str:
    candidates = [tag]
    parent = getattr(tag, "parent", None)
    while parent and getattr(parent, "name", None) not in [None, "[document]", "html", "body"]:
        candidates.append(parent)
        parent = getattr(parent, "parent", None)

    for candidate in candidates:
        text = candidate.get_text(" ", strip=True)
        if candidate is not tag and _word_count(text) > 220:
            continue

        value = _strip_metadata_label(text, label_pattern, label_terms)
        if not value:
            continue

        if stop_label_pattern:
            value = stop_label_pattern.split(value, maxsplit=1)[0].strip(" :.-–—")
        if value and stop_terms and _contains_any(_normalize_for_match(value), stop_terms):
            value = re.split(stop_label_pattern, value, maxsplit=1)[0].strip(" :.-–—") if stop_label_pattern else value

        if value:
            return value

    for next_tag in tag.find_all_next(True):
        next_text = _clean_metadata_text(next_tag.get_text(" ", strip=True))
        if not next_text:
            continue
        if stop_terms and _contains_any(_normalize_for_match(next_text), stop_terms):
            break
        if _find_metadata_label_match(next_text, label_pattern, label_terms):
            continue
        return next_text

    return ""


def _extract_metadata_from_html(html_content: str) -> Dict:
    """
    Trích xuất metadata (title, authors, abstract, keywords) từ HTML
    được chuyển đổi từ Markdown của PyMuPDF4LLM.

    Cấu trúc kỳ vọng (xem ví dụ từ các bài báo mẫu):
      - Tiêu đề: thẻ Heading đầu tiên (<h1> hoặc <h2>)
      - Tác giả: thẻ ngay sau tiêu đề
      - Tóm tắt: tìm mọi tag có text chứa "Tóm tắt", rồi lấy phần sau nhãn
                 hoặc tag text kế tiếp nếu nhãn đứng riêng
      - Từ khóa: tìm mọi tag có text chứa "Từ khóa"/"Từ khoá", loại bỏ nhãn
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. Title: heading đầu tiên
    title_tag = soup.find(['h1', 'h2'])
    title = title_tag.get_text(strip=True) if title_tag else ""

    # 2. Authors: sibling ngay sau title
    author_tag = None
    if title_tag:
        for sibling in title_tag.find_next_siblings():
            if sibling.name in ["script", "style", "table", "thead", "tbody",
                                 "tr", "td", "th", "img", "figure", "figcaption"]:
                continue

            sibling_text = sibling.get_text(" ", strip=True)
            if not sibling_text:
                continue

            # Dừng sớm nếu sibling rõ ràng là abstract/section body
            if _is_body_start_text(sibling_text):
                break

            child_tags = [
                tag for tag in sibling.find_all(True)
                if tag.name not in ["script", "style", "table", "thead", "tbody",
                                    "tr", "td", "th", "img", "figure", "figcaption"]
            ] or [sibling]

            for candidate in child_tags:
                text = candidate.get_text(" ", strip=True)
                if not text:
                    continue

                # Bỏ qua affiliation rõ ràng
                if _contains_any(_normalize_for_match(text), AFFILIATION_TERM_FAMILIES):
                    continue

                # Bỏ qua publication metadata
                if _is_publication_metadata_line(text):
                    continue

                # Bỏ qua nếu là abstract/keywords label
                if _is_front_matter_text(text) and _looks_like_section_boundary(text):
                    break

                # Nhận dạng danh sách tên tác giả
                tokens = [t.strip() for t in re.split(r"[,;]", text) if t.strip()]
                if 1 <= len(tokens) <= 8 and all(_looks_like_author_name(t) for t in tokens):
                    author_tag = candidate
                    break

            if author_tag:
                break

    authors = clean_authors(author_tag.get_text(strip=True)) if author_tag else ""

    abstract = ""
    for tag in _find_tags_containing_label(soup, RE_ABSTRACT_LABEL, ABSTRACT_LABEL_TERMS):
        abstract = _extract_labeled_metadata_value(
            tag,
            RE_ABSTRACT_LABEL,
            ABSTRACT_LABEL_TERMS,
            stop_label_pattern=RE_KEYWORD_LABEL,
            stop_terms=KEYWORD_LABEL_TERMS,
        )
        if abstract:
            break

    keywords = ""
    for tag in _find_tags_containing_label(soup, RE_KEYWORD_LABEL, KEYWORD_LABEL_TERMS):
        keywords = _extract_labeled_metadata_value(
            tag,
            RE_KEYWORD_LABEL,
            KEYWORD_LABEL_TERMS,
        )
        if keywords:
            break

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
                content = clean_line(heading_match.group(2))
                line = content
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
            if "Images and text on images cannot both be suppressed" in str(exc):
                to_markdown_options["force_text"] = True
                try:
                    raw_markdown = pymupdf4llm.to_markdown(self.local_path, **to_markdown_options)
                except Exception as fallback_exc:
                    logger.warning(
                        "PyMuPDF4LLM force_text extraction failed for %s: %s. Falling back to plain PyMuPDF text.",
                        self.storage_path,
                        fallback_exc,
                    )
                    raw_markdown = _extract_plain_text_with_pymupdf(self.local_path)
            else:
                logger.warning(
                    "PyMuPDF4LLM extraction failed for %s: %s. Falling back to plain PyMuPDF text.",
                    self.storage_path,
                    exc,
                )
                raw_markdown = _extract_plain_text_with_pymupdf(self.local_path)
        except Exception as exc:
            logger.warning(
                "PyMuPDF4LLM extraction failed for %s: %s. Falling back to plain PyMuPDF text.",
                self.storage_path,
                exc,
            )
            raw_markdown = _extract_plain_text_with_pymupdf(self.local_path)

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

    def extract_raw_text(self) -> str:
        """
        Trích xuất toàn bộ nội dung bài báo dưới dạng plain text thuần —
        không tách metadata/body, không markdown heading, không phân vùng.

        Pipeline:
        1. PDF → Markdown (pymupdf4llm) → _preclean_markdown (bỏ hình/bảng/code)
        2. Markdown → HTML → BeautifulSoup (bỏ tag phi văn bản)
        3. Tag → text sạch: heading dùng clean_line, p/list dùng _clean_body_paragraph
        4. Gộp thành raw_body → clean_body_text (bỏ junk, citation, normalize)
        5. Prepend "Tiêu đề" và "Tác giả" từ extract_metadata()

        Khác extract_body_text:
        - Không cắt front matter (abstract, keywords được giữ lại)
        - Không dừng ở body-stop heading (references, appendix bị giữ lại)
        - Output là plain text, heading KHÔNG có ký tự '#'
        - Title và authors được format rõ ràng ở đầu output
        """
        html_content = self._ensure_markdown_and_html()
        soup = BeautifulSoup(html_content, "html.parser")

        # Loại bỏ tag phi văn bản
        for non_text_tag in soup.find_all([
            "img", "figure", "figcaption",
            "table", "thead", "tbody", "tr", "td", "th",
            "pre", "code",
        ]):
            non_text_tag.decompose()

        tags = [
            tag
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol"])
            if self._tag_text(tag)
        ]

        # Lấy metadata để xác định title tag cần bỏ qua khi render body
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

        title = metadata.get("title", "")
        authors = metadata.get("authors", "")

        # Chuẩn hóa title để so khớp mềm với heading đầu tiên trong HTML
        _title_normalized = _normalize_for_match(title) if title else None

        parts: List[str] = []
        _title_skipped = not bool(_title_normalized)  # Nếu không có title thì không cần skip

        for tag in tags:
            text = self._tag_text(tag)

            # Bỏ artifact rõ ràng (hình placeholder, bảng sót, decorative line)
            if _is_non_body_artifact_line(text):
                continue

            # Bỏ qua heading đầu tiên khớp với title (đã được prepend ở header)
            if not _title_skipped and tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                if _normalize_for_match(text) == _title_normalized:
                    _title_skipped = True
                    continue

            if tag.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                # Làm sạch đầy đủ nhưng KHÔNG thêm '#' — output là plain text
                content = clean_line(text)
                if content:
                    parts.append(content)

            elif tag.name == "p":
                content = _clean_body_paragraph(text)
                if content:
                    parts.append(content)

            elif tag.name in ["ul", "ol"]:
                list_items = tag.find_all("li", recursive=False) or tag.find_all("li")
                try:
                    start = int(tag.get("start", 1))
                except (TypeError, ValueError):
                    start = 1
                for offset, li in enumerate(list_items):
                    item_text = _clean_body_paragraph(li.get_text(" ", strip=True))
                    if not item_text or _is_non_body_artifact_line(item_text):
                        continue
                    marker = "-" if tag.name == "ul" else f"{start + offset}."
                    parts.append(f"{marker} {item_text}")

            else:
                content = _clean_body_paragraph(text)
                if content:
                    parts.append(content)

        raw_body = "\n\n".join(parts)
        body_text = clean_body_text(raw_body)

        # Tạo header block
        header_lines: List[str] = []
        if title:
            header_lines.append(f"Tiêu đề: {title}")
        if authors:
            header_lines.append(f"Tác giả: {authors}")

        if header_lines:
            return "\n".join(header_lines) + "\n\n" + body_text
        return body_text

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup(self):
        """Xóa thư mục tạm."""
        self.temp_dir.cleanup()
