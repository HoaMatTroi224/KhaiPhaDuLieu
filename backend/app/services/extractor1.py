"""
extractor.py
------------

Pipeline trích xuất bài báo khoa học tiếng Việt:

1. Download PDF từ Supabase Storage
2. Parse structured body bằng GROBID
3. Extract metadata bằng PyMuPDF4LLM
4. Trả về dict unified output

Yêu cầu:
- GROBID server chạy tại: http://localhost:8070
- Bucket Supabase chứa PDF
"""

import io
import os
import re
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf4llm
from supabase import create_client, Client
from grobid_client.grobid_client import GrobidClient
from ..config import settings


# =============================================================================
# REGEX CONSTANTS
# =============================================================================

# --- Markdown stripping ---

# Removes bold/italic markdown: **text**, *text*, __text__, _text_
RE_MARKDOWN_EMPHASIS = re.compile(r"[_*]{1,3}(.*?)[_*]{1,3}")

# Removes heading markers: ##, ###, etc. at the start of a line
RE_MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s*")

# Removes inline code: `code`
RE_MARKDOWN_CODE = re.compile(r"`[^`]*`")

# --- Affiliation / superscript markers ---

# Removes markers like [1], [1*], [1,2], [1, 2, 3], [*], [2,3,4*]
# These appear as footnote references after author names.
RE_AFFILIATION_MARKER = re.compile(r"\[\*?[\d,\s*]+\*?\]")

# Removes trailing bare numeric superscripts directly after a name,
# e.g. "Nguyễn Văn A1,2,3" → "Nguyễn Văn A"
RE_TRAILING_SUPERSCRIPT = re.compile(r"[\d,\s]+$")

# --- Citation / reference artifacts in body text ---

# Matches inline citations: [1], [1,2], [1, 2], [1-3], [1][2]
RE_CITATION_BRACKET = re.compile(r"\[\d+(?:[,\-–]\s*\d+)*\](\[\d+(?:[,\-–]\s*\d+)*\])*")

# Matches parenthetical citations: (1), (1,2), (1, 2)
RE_CITATION_PAREN = re.compile(r"\(\d+(?:,\s*\d+)*\)")

# --- Figure / table caption lines ---

# Matches markdown headings that are actually captions (Hình, Bảng, Figure, Table, Chart, Biểu đồ)
# These come from GROBID body_text labelled as section headers incorrectly.
RE_CAPTION_LINE = re.compile(
    r"^\s*#{1,6}\s*"                      # heading marker
    r"(?:Hình|Bảng|Figure|Table|Chart|Biểu\s*đồ|Sơ\s*đồ|Ảnh)\s*\d+",
    re.IGNORECASE | re.UNICODE,
)

# --- Section delimiters used to stop abstract extraction ---

# Vietnamese / English section openers that mark the end of the abstract block
RE_SECTION_STOP = re.compile(
    r"^\s*(?:"
    r"Từ\s+khoá|Từ\s+khóa|Keywords?"          # keyword section
    r"|Đặt\s+vấn\s+đề|Mở\s+đầu|Introduction"  # intro section
    r"|(?:\d+\.?\s+\w)|[IVX]+\."               # numbered / roman section
    r")",
    re.IGNORECASE | re.UNICODE,
)

# --- Abstract / keyword section openers ---

RE_ABSTRACT_HEADER = re.compile(
    r"Tóm\s+tắt|Abstract",
    re.IGNORECASE | re.UNICODE,
)

RE_KEYWORD_HEADER = re.compile(
    r"Từ\s+khoá|Từ\s+khóa|Keywords?",
    re.IGNORECASE | re.UNICODE,
)

# Trailing metadata that may appear after the keyword list
RE_KEYWORD_TRAILER = re.compile(
    r"(?:Chỉ\s+số\s+phân\s+loại|Classification\s+index|JEL|MSC).*$",
    re.IGNORECASE | re.UNICODE,
)

# --- Vietnamese Unicode detector ---
# Used to distinguish genuine text lines from noise / numbers-only lines.
RE_VIET_UNICODE = re.compile(r"[àáạảãăắặẳẵâấậẩẫèéẹẻẽêếệểễìíịỉĩòóọỏõôốộổỗơớợởỡùúụủũưứựửữỳýỵỷỹđ]", re.IGNORECASE)

# --- Affiliation keyword list ---
# Lines containing these are affiliation lines, not author names.
AFFILIATION_KEYWORDS = [
    "đại học", "trường", "viện", "khoa", "học viện",
    "bệnh viện", "bộ môn", "trung tâm", "công ty", "tnhh",
    "university", "institute", "faculty", "department",
    "hospital", "center", "college", "school",
]


# =============================================================================
# SHARED NORMALIZATION HELPERS
# =============================================================================

def strip_markdown(text: str) -> str:
    """
    Remove common markdown syntax from a text fragment.

    Handles: **bold**, *italic*, __bold__, _italic_, `code`, ## headings.
    Preserves the inner text content and Vietnamese characters.

    Strategy: iteratively unwrap emphasis markers to handle nesting like
    _**text**_ or **_text_** which appear frequently in pymupdf4llm output.
    """
    # Remove heading markers at start of line
    text = RE_MARKDOWN_HEADING.sub("", text)

    # Remove inline code
    text = RE_MARKDOWN_CODE.sub("", text)

    # Unwrap emphasis markers (up to 3 passes handles nesting)
    for _ in range(3):
        new = RE_MARKDOWN_EMPHASIS.sub(r"\1", text)
        if new == text:
            break
        text = new

    # Strip any residual bare asterisks or underscores used as decorators
    text = re.sub(r"(?<!\w)[*_]+(?!\w)", "", text)

    return text.strip()


def normalize_whitespace(text: str) -> str:
    """
    Collapse runs of whitespace (spaces, tabs) to a single space.
    Preserves newlines intentionally — callers join when needed.
    """
    return re.sub(r"[ \t]+", " ", text).strip()


def clean_line(line: str) -> str:
    """Strip markdown and normalize whitespace for a single line."""
    return normalize_whitespace(strip_markdown(line))


def remove_affiliation_markers(text: str) -> str:
    """
    Remove footnote-style affiliation markers from author name strings.

    Handles:
      - [1], [2], [1*], [1, 2], [2, 3, 4*]  → bracket style
      - trailing bare digits after name: "Nguyễn Văn A1,2" → "Nguyễn Văn A"
    """
    text = RE_AFFILIATION_MARKER.sub("", text)
    # Remove trailing bare digit sequences (superscript style without brackets)
    text = re.sub(r"[\d,]+\s*$", "", text)
    return text.strip()


def is_affiliation_line(line: str) -> bool:
    """
    Return True if the line looks like an institutional affiliation,
    not an author name list.

    Heuristics used:
    - Contains a known institution keyword (case-insensitive)
    - Starts with a digit followed by a word (numbered affiliation)
    - Contains a full address fragment (số, phường, quận, tỉnh, TP.)
    """
    lower = line.lower()

    if any(kw in lower for kw in AFFILIATION_KEYWORDS):
        return True

    # Numbered affiliation lines like "1Trường Đại học Y Hà Nội, ..."
    if re.match(r"^\d+\s*[A-ZĐÀÁẠẢÃ]", line):
        return True

    # Address fragments
    if re.search(r"\b(?:phường|quận|tỉnh|huyện|TP\.|thành phố|số \d)", line, re.IGNORECASE):
        return True

    return False


# =============================================================================
# METADATA EXTRACTION HELPERS
# =============================================================================

def _extract_title(header_text: str) -> str:
    """
    Extract the paper title from the header section produced by pymupdf4llm.

    Observed patterns across Vietnamese papers:
      ## **Title text**
      ## _**Title text**_
      # **Title text**   (less common)

    Strategy:
    1. Scan non-empty lines.
    2. The title is usually the FIRST line that:
       - Starts with a markdown heading marker (`##`, `#`), OR
       - Is a bold/bold-italic block that is longer than 20 chars.
    3. Stop before the author block (lines with Vietnamese names + markers)
       or any recognized section header (abstract, keywords, dates).
    4. Support multiline titles: if consecutive heading-marked lines share
       the same heading level and the first doesn't end with a full stop,
       concatenate them.

    Returns: plain text string, no markdown.
    """
    lines = [l for l in header_text.split("\n") if l.strip()]

    title_parts: List[str] = []
    in_title = False

    # Compiled stoppers for title block end
    title_stop = re.compile(
        r"Tóm\s+tắt|Abstract|Từ\s+kh[oó]a|Keywords?"
        r"|Ngày\s+nhận|Received|Accepted|doi|DOI"
        r"|^\d{1,2}/\d{1,2}/\d{4}",  # date lines
        re.IGNORECASE | re.UNICODE,
    )

    for line in lines:
        stripped = line.strip()

        # Hard stop at known section headers
        if title_stop.search(stripped):
            break

        is_heading = bool(re.match(r"^\s*#{1,6}\s+", stripped))
        cleaned = clean_line(stripped)

        # Skip very short lines (noise)
        if len(cleaned) < 10:
            continue

        # Skip lines that look like author/affiliation blocks
        if is_affiliation_line(cleaned):
            if in_title:
                break
            continue

        # Detect title start: heading line with Vietnamese chars, or long bold line
        if is_heading or (not in_title and RE_VIET_UNICODE.search(cleaned) and len(cleaned) > 20):
            # Once we've started collecting and hit a non-heading line that isn't
            # obviously a continuation, stop.
            if in_title and not is_heading and title_parts:
                break

            in_title = True
            title_parts.append(cleaned)

            # If the title line ends with a full stop, it's complete
            if cleaned.endswith("."):
                break
        elif in_title:
            # A blank-ish or very short line ends the title block
            break

    title = " ".join(title_parts)
    title = normalize_whitespace(title)
    return title


def _extract_authors(header_text: str) -> str:
    """
    Extract and clean the author list from the header section.

    Observed patterns:
      **Hồ Thị Huyền Trang[1] , Vũ Thị Hà[2] , ...**
      **Tưởng Thị Nguyệt Ánh[*] , Hoàng Thị Hương, ...**

    Strategy:
    1. Find the title line (first long heading line with Vietnamese chars).
    2. From the next non-empty line, scan for the author block:
       - Lines with Vietnamese names (contain Vietnamese chars)
       - That are NOT affiliation lines
       - Stop at abstract / keywords / date headers
    3. Split by comma, clean each fragment, filter short/affiliation tokens.

    Returns: "Author A, Author B, Author C" — comma-separated string.
    """
    lines = [l for l in header_text.split("\n") if l.strip()]

    author_stop = re.compile(
        r"Tóm\s+tắt|Abstract|Từ\s+kh[oó]a|Keywords?"
        r"|Ngày\s+nhận|Received|Accepted",
        re.IGNORECASE | re.UNICODE,
    )

    # ── Step 1: locate the title line ──
    title_idx = 0
    for i, line in enumerate(lines):
        cleaned = clean_line(line)
        if (
            re.match(r"^\s*#{1,6}\s+", line)
            and RE_VIET_UNICODE.search(cleaned)
            and len(cleaned) > 20
            and not is_affiliation_line(cleaned)
        ):
            title_idx = i
            break

    # ── Step 2: collect raw author line(s) after the title ──
    raw_author_lines: List[str] = []

    for line in lines[title_idx + 1:]:
        stripped = line.strip()

        if not stripped:
            continue

        if author_stop.search(stripped):
            break

        cleaned = clean_line(stripped)

        if is_affiliation_line(cleaned):
            # If we already have author lines, affiliation marks the end
            if raw_author_lines:
                break
            continue

        # Accept lines that contain Vietnamese characters and look name-like
        if RE_VIET_UNICODE.search(cleaned) and len(cleaned) > 3:
            raw_author_lines.append(cleaned)
            # Author block is typically one or two lines; stop after
            # first accepted line if the next is an affiliation
            # (handled above), so we just keep collecting until stop.

    if not raw_author_lines:
        return ""

    # ── Step 3: merge, split, clean ──
    raw = ", ".join(raw_author_lines)

    # Split on comma or semicolon
    tokens = re.split(r"[,;]", raw)

    cleaned_authors: List[str] = []
    seen: set = set()

    for token in tokens:
        name = remove_affiliation_markers(token)
        name = strip_markdown(name)
        name = normalize_whitespace(name)

        # Skip if too short, purely numeric, or an affiliation fragment
        if len(name) < 4:
            continue
        if re.match(r"^\d+$", name):
            continue
        if is_affiliation_line(name):
            continue
        # Skip if no Vietnamese char (filters stray Latin abbreviations)
        if not RE_VIET_UNICODE.search(name.lower()):
            continue

        if name not in seen:
            seen.add(name)
            cleaned_authors.append(name)

    return ", ".join(cleaned_authors)


def _extract_abstract(header_text: str) -> str:
    """
    Extract the abstract body from the header section.

    Observed patterns:
      _**Tóm tắt:**_ **Mục tiêu: ... Kết luận: ...**
      **Tóm tắt:** **Polymer blend ...**

    Strategy:
    1. Find the line containing "Tóm tắt" or "Abstract".
    2. Collect all text after the header label until a stop marker
       (Từ khóa / Keywords / numbered section / date line).
    3. Strip markdown from the collected text.

    Edge cases handled:
    - Abstract label on the same line as the first sentence.
    - Multiline abstract spread across several bold-wrapped lines.
    - Bold-wrapped paragraphs that pymupdf4llm emits as separate lines.
    """
    # Regex that captures everything after the abstract label on the same line
    # and across subsequent lines until a stop marker.
    pattern = re.compile(
        r"(?:Tóm\s+tắt|Abstract)"    # header label
        r"\s*[:\s]*"                   # optional colon + whitespace
        r"(.*?)"                       # content (lazy)
        r"(?="                         # lookahead for stop
        r"\n\s*(?:"
        r"Từ\s+kh[oó]a|Keywords?"
        r"|Đặt\s+vấn\s+đề|Mở\s+đầu|Introduction"
        r"|(?:\d+\.\s+\w)"
        r"|Ngày\s+nhận|Received"
        r"|[IVX]+\."
        r")"
        r"|\Z)",                       # or end of string
        re.DOTALL | re.IGNORECASE | re.UNICODE,
    )

    match = pattern.search(header_text)
    if not match:
        return ""

    raw = match.group(1).strip()

    # Strip markdown from each line and rejoin
    lines = raw.split("\n")
    cleaned_lines = []
    for line in lines:
        cl = clean_line(line)
        if cl:
            cleaned_lines.append(cl)

    abstract = " ".join(cleaned_lines)
    abstract = normalize_whitespace(abstract)
    return abstract


def _extract_keywords(header_text: str) -> str:
    """
    Extract the keyword list and return as a comma-separated string.

    Observed patterns:
      _**Từ khóa:**_ **word1, word2, word3.**
      **Từ khoá:**_ **word1, word2.**  _**Chỉ số phân loại:**_ **3.4**
      Keywords: word1, word2.

    Strategy:
    1. Find the keyword label line.
    2. Capture the remainder of that line (keywords are always inline).
    3. Strip trailing metadata (Chỉ số phân loại, classification index, etc.)
    4. Split on commas/semicolons, clean each keyword.

    Returns: "keyword1, keyword2, keyword3" — comma-separated string.
    """
    pattern = re.compile(
        r"(?:Từ\s+kh[oó]a|Keywords?)"  # header label (note: both ó and o appear)
        r"\s*[:\s]*"
        r"([^\n]+)",                    # rest of the same line
        re.IGNORECASE | re.UNICODE,
    )

    match = pattern.search(header_text)
    if not match:
        return ""

    raw = match.group(1)

    # Remove trailing classification / index metadata
    raw = RE_KEYWORD_TRAILER.sub("", raw)

    # Strip markdown
    raw = strip_markdown(raw)

    # Split and clean individual keywords
    tokens = re.split(r"[,;]", raw)
    keywords = []
    for token in tokens:
        kw = normalize_whitespace(token)
        # Remove trailing period
        kw = kw.rstrip(".")
        if kw:
            keywords.append(kw)

    return ", ".join(keywords)


# =============================================================================
# BODY TEXT CLEANING HELPERS
# =============================================================================

def clean_body_text(raw_body: str) -> str:
    """
    Clean the body text produced by the GROBID extraction pipeline.

    Steps applied in order:
    1. Remove inline citation artifacts.
    2. Remove figure / table / chart caption lines (## Hình 1. ...).
    3. Preserve real section headers (## Đặt vấn đề, ## Kết quả, ...).
    4. Normalize whitespace within paragraphs.
    5. Normalize paragraph spacing (max 2 consecutive newlines).

    Returns cleaned markdown-compatible body text suitable for chunking,
    embedding, and RAG pipelines.
    """
    lines = raw_body.split("\n")
    cleaned: List[str] = []

    for line in lines:
        # ── Drop caption lines before any other processing ──
        # Captions are markdown headings whose content starts with a
        # figure/table/chart label followed by a number.
        if RE_CAPTION_LINE.match(line):
            continue

        # ── Remove inline citation brackets ──
        line = RE_CITATION_BRACKET.sub("", line)
        line = RE_CITATION_PAREN.sub("", line)

        # ── Normalize whitespace within the line ──
        # (do not strip leading ## for headings)
        if re.match(r"^\s*#{1,6}\s", line):
            # Heading: clean heading text but keep marker
            heading_match = re.match(r"^(\s*#{1,6}\s+)(.*)", line)
            if heading_match:
                marker = heading_match.group(1)
                content = clean_line(heading_match.group(2))
                line = marker + content
        else:
            line = normalize_whitespace(line)

        # ── Remove lines that became empty after cleaning ──
        if not line.strip():
            cleaned.append("")  # preserve paragraph break
            continue

        cleaned.append(line)

    body = "\n".join(cleaned)

    # Collapse more than 2 consecutive blank lines
    body = re.sub(r"\n{3,}", "\n\n", body)

    return body.strip()


def _clean_body_paragraph(text: str) -> str:
    """
    Clean a single body paragraph extracted from GROBID body_text.

    Removes:
    - Citation markers
    - Hyphenation artifacts from PDF line breaks ("word- word" → "word word")
    - Excess whitespace

    Preserves:
    - Vietnamese Unicode
    - Legitimate hyphens within compound words (short, no surrounding spaces)
    """
    # Fix soft-hyphen line breaks: "meth- od" → "method"
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)

    # Remove citation artifacts
    text = RE_CITATION_BRACKET.sub("", text)
    text = RE_CITATION_PAREN.sub("", text)

    # Normalize whitespace
    text = normalize_whitespace(text)

    return text


# =============================================================================
# FILE EXTRACTOR
# =============================================================================

class FileExtractor:
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
            grobid_server="http://localhost:8070",
        )

        self.temp_dir = tempfile.TemporaryDirectory()

        self.local_path: Optional[str] = None
        self.json_path: Optional[str] = None

        self.raw_markdown: Optional[str] = None
        self.grobid_data: Optional[dict] = None

    # =========================================================================
    # SUPABASE
    # =========================================================================

    def download_from_supabase(self) -> str:
        """Download file từ Supabase Storage về thư mục tạm."""
        file_bytes = (
            self.supabase
            .storage
            .from_(self.bucket_name)
            .download(self.storage_path)
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

        Pipeline:
        1. Iterate over body_text paragraphs.
        2. Emit section headers as ## headings.
        3. Clean each paragraph with _clean_body_paragraph().
        4. Post-process the assembled body with clean_body_text()
           to remove caption lines and normalize spacing.
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

        # Apply global cleaning pass (captions, spacing, residual artifacts)
        return clean_body_text(raw_body)

    # =========================================================================
    # PYMUPDF4LLM — METADATA
    # =========================================================================

    def extract_metadata(self) -> Dict:
        """
        Extract metadata bằng PyMuPDF4LLM.

        Uses the first 4000 characters of the markdown output as the
        header section — this reliably covers title, authors, abstract,
        and keywords for standard Vietnamese journal papers.
        """
        if not self.local_path:
            self.download_from_supabase()

        self.raw_markdown = pymupdf4llm.to_markdown(
            self.local_path,
            header=False,
            footer=False,
            show_progress=False,
        )

        # Use a slightly larger window to handle long abstracts
        header_section = self.raw_markdown[:5000]

        metadata = {
            "title": _extract_title(header_section),
            "authors": _extract_authors(header_section),
            "abstract": _extract_abstract(header_section),
            "keywords": _extract_keywords(header_section),
        }

        return metadata

    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================

    def extract(self) -> Dict:
        """
        Full extraction pipeline.

        Recommended extraction order:
        1. download_from_supabase() — ensures local_path is set
        2. extract_metadata()       — uses PyMuPDF4LLM on the raw PDF
        3. run_grobid()             — parse structured body
        4. extract_body_text()      — assemble + clean body
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