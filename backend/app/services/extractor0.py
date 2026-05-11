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


class FileExtractor:
    """
    Extractor cho bài báo khoa học tiếng Việt.
    """

    AFFILIATION_KEYWORDS = [
        "đại học",
        "trường",
        "viện",
        "khoa",
        "học viện",
        "university",
        "institute",
        "faculty",
        "department",
        "hospital",
    ]

    def __init__(
        self,
        storage_path: str
    ):
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
            settings.SUPABASE_KEY
        )

        self.grobid_client = GrobidClient(
            config_path=None,
            grobid_server="http://localhost:8070"
        )

        self.temp_dir = tempfile.TemporaryDirectory()

        self.local_path = None
        self.json_path = None

        self.raw_markdown = None
        self.grobid_data = None

    # =========================================================================
    # SUPABASE
    # =========================================================================

    def download_from_supabase(self) -> str:
        """
        Download file từ Supabase Storage về thư mục tạm.
        """

        file_bytes = (
            self.supabase
            .storage
            .from_(self.bucket_name)
            .download(self.storage_path)
        )

        file_name = Path(self.storage_path).name

        local_path = os.path.join(
            self.temp_dir.name,
            file_name
        )

        with open(local_path, "wb") as f:
            f.write(file_bytes)

        self.local_path = local_path

        return local_path

    # =========================================================================
    # GROBID
    # =========================================================================

    def run_grobid(self) -> str:
        """
        Parse PDF bằng GROBID.
        """

        if not self.local_path:
            self.download_from_supabase()

        output_dir = os.path.join(
            self.temp_dir.name,
            "grobid_output"
        )

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

        json_path = os.path.join(
            output_dir,
            f"{pdf_stem}.json"
        )

        if not os.path.exists(json_path):
            raise FileNotFoundError(
                f"Không tìm thấy file JSON: {json_path}"
            )

        self.json_path = json_path

        return json_path

    def load_json(self) -> dict:
        """
        Load file JSON output từ GROBID.
        """

        if not self.json_path:
            self.run_grobid()

        with open(
            self.json_path,
            "r",
            encoding="utf-8"
        ) as f:
            self.grobid_data = json.load(f)

        return self.grobid_data

    def extract_body_text(self) -> str:
        """
        Trích xuất body text từ GROBID JSON.
        """

        if not self.grobid_data:
            self.load_json()

        body_parts = []

        current_section = ""

        for para in self.grobid_data.get("body_text", []):

            section = para.get("head_section", "").strip()

            if section and section != current_section:
                current_section = section

                body_parts.append(
                    f"\n\n## {section}\n"
                )

            text = para.get("text", "").strip()

            if text:
                text = self._clean_body_text(text)
                body_parts.append(text)

        body = "\n\n".join(body_parts)

        body = re.sub(r"\n{3,}", "\n\n", body)

        return body.strip()

    def _clean_body_text(self, text: str) -> str:
        """
        Làm sạch body text.
        """

        text = text.replace("- ", "- ")
        text = text.replace(" -", "-")

        text = re.sub(
            r"\[\d+(?:,\s*\d+)*\]",
            "",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # =========================================================================
    # PYMUPDF4LLM
    # =========================================================================

    def extract_metadata(self) -> Dict:
        """
        Extract metadata bằng PyMuPDF4LLM.
        """

        if not self.local_path:
            self.download_from_supabase()

        self.raw_markdown = pymupdf4llm.to_markdown(
            self.local_path,
            header=False,
            footer=False,
            show_progress=False,
        )

        header_section = self.raw_markdown[:4000]

        metadata = {
            "title": self._extract_title(header_section),
            "authors": self._extract_authors(header_section),
            "abstract": self._extract_abstract(header_section),
            "keywords": self._extract_keywords(header_section),
        }

        return metadata

    # =========================================================================
    # METADATA HELPERS
    # =========================================================================

    def _extract_title(self, text: str) -> str:

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        for line in lines:

            if re.search(
                r"^(abstract|keywords|doi|received|accepted)",
                line,
                re.I
            ):
                continue

            if (
                20 < len(line) < 300
                and re.search(
                    r"[àáạảãăâđêôơư]",
                    line.lower()
                )
            ):
                return line

        return ""

    def _extract_authors(self, text: str) -> List[str]:

        authors = []

        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        title_found = False

        for line in lines:

            if not title_found:

                if (
                    20 < len(line) < 300
                    and re.search(
                        r"[àáạảãăâđêôơư]",
                        line.lower()
                    )
                ):
                    title_found = True

                continue

            if re.search(
                r"(tóm tắt|abstract|keywords|từ khóa)",
                line,
                re.I
            ):
                break

            lower = line.lower()

            if any(
                keyword in lower
                for keyword in self.AFFILIATION_KEYWORDS
            ):
                continue

            raw_names = re.split(r"[,;]", line)

            for name in raw_names:

                name = name.strip()

                name = re.sub(r"\[\*?\d+\]", "", name)

                name = re.sub(r"\d+$", "", name).strip()

                if len(name) < 4:
                    continue

                if any(
                    keyword in name.lower()
                    for keyword in self.AFFILIATION_KEYWORDS
                ):
                    continue

                if re.search(r"[àáạảãăâđêôơư]", name.lower()):
                    authors.append(name)

            if authors:
                break

        return list(dict.fromkeys(authors))

    def _extract_abstract(self, text: str) -> str:

        pattern = (
            r"(?:Tóm\s+tắt)"
            r"\s*[:\s]*"
            r"(.*?)"
            r"(?=\n\s*(?:Từ\s+khóa|Keywords|1\.|I\.|Đặt vấn đề))"
        )

        match = re.search(
            pattern,
            text,
            re.DOTALL | re.IGNORECASE
        )

        if not match:
            return ""

        abstract = match.group(1).strip()

        abstract = re.sub(
            r"\n{2,}",
            "\n",
            abstract
        )

        return abstract

    def _extract_keywords(self, text: str) -> List[str]:

        pattern = (
            r"(?:Từ\s+khóa|Keywords)"
            r"\s*[:\s]*"
            r"(.*?)(?=\n)"
        )

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            return []

        keyword_text = match.group(1)

        keywords = re.split(
            r"[,;]",
            keyword_text
        )

        return [
            kw.strip()
            for kw in keywords
            if kw.strip()
        ]

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

        result = {
            "title": metadata.get("title"),
            "authors": metadata.get("authors"),
            "abstract": metadata.get("abstract"),
            "keywords": metadata.get("keywords"),
            "content": body_text,
            "storage_path": self.storage_path,
        }

        return result

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup(self):
        """
        Xóa thư mục tạm.
        """

        self.temp_dir.cleanup()