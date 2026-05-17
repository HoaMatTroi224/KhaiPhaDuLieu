import re
import pymupdf
from pathlib import Path


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Nhận raw bytes của file PDF, trả về text đã được làm sạch.
    Hỗ trợ xử lý bảng, công thức toán học, và layout 2 cột.
    """
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    for page in doc:
        page_text = _extract_page_text(page)
        if page_text.strip():
            pages_text.append(page_text)
    doc.close()
    raw_text = "\n".join(pages_text)
    return clean_academic_text(raw_text)


def _extract_page_text(page) -> str:
    """
    Trích xuất text từ một trang, xử lý bảng riêng.
    """
    # Lấy các blocks để phát hiện bảng
    blocks = page.get_text("blocks")  # [(x0,y0,x1,y1, text, block_no, block_type)]

    text_parts = []
    for block in blocks:
        block_type = block[6]  # 0=text, 1=image
        if block_type == 1:
            # Bỏ qua image blocks
            continue
        block_text = block[4].strip()
        if block_text:
            text_parts.append(block_text)

    return "\n".join(text_parts)


def clean_academic_text(text: str) -> str:
    """
    Làm sạch text từ PDF bài báo khoa học:
    - Bỏ phần References/Tài liệu tham khảo
    - Bỏ số trang, header/footer
    - Làm sạch artifacts từ công thức toán học
    - Gộp dòng bị ngắt do layout cột
    """
    # ── 1. Cắt tại phần References ──
    ref_pattern = re.compile(
        r'\n(references|TÀI LIỆU THAM KHẢO|Tài liệu tham khảo|bibliography|danh mục tài liệu)\s*\n',
        re.IGNORECASE
    )
    match = ref_pattern.search(text)
    if match:
        text = text[:match.start()]

    # ── 2. Bỏ số trang đơn lẻ ──
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # ── 3. Làm sạch artifacts công thức toán học ──
    # Dòng chứa chủ yếu ký hiệu toán (%, $, =, +, -, *, /, ^, ký tự Unicode math)
    # mà không có chữ thực sự → xóa dòng đó
    text = re.sub(
        r'^\s*[^a-zA-ZÀ-ỹ\d\s]{3,}\s*$',
        '',
        text,
        flags=re.MULTILINE
    )
    # Xóa chuỗi ký tự đặc biệt xen lẫn trong text (artifact từ PDF encoding)
    # Ví dụ: "kết quảỴẼỠẪẲẰÕẺ" → xóa chuỗi ký tự không thuộc bảng chữ cái Việt
    text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00C0-\u024F\u1E00-\u1EFF\u0300-\u036F]+', ' ', text)

    # ── 4. Gộp dòng bị wrap trong layout cột ──
    lines = text.split('\n')
    merged = []
    for line in lines:
        line = line.strip()
        if not line:
            merged.append('')
            continue
        if (merged and
                len(merged[-1]) > 0 and
                len(line) < 60 and
                not merged[-1].endswith(('.', ':', '?', '!', ';'))):
            merged[-1] += ' ' + line
        else:
            merged.append(line)

    text = '\n'.join(merged)

    # ── 5. Dọn khoảng trắng thừa ──
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def chunk_text_for_model(text: str, max_chars: int = 3000) -> str:
    """
    Giữ lại để backward-compat. Với Map-Reduce, hàm này không còn dùng trong app.py.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
