"""Data models for the Documentation Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DocType(Enum):
    API_DOCS = "api_docs"
    README = "readme"
    CONTRIBUTION_GUIDE = "contribution_guide"
    INLINE_DOCSTRINGS = "inline_docstrings"
    SEQUENCE_DIAGRAMS = "sequence_diagrams"
    CHANGELOG = "changelog"


class DocStatus(Enum):
    MISSING = "missing"
    OUTDATED = "outdated"
    INCOMPLETE = "incomplete"
    UP_TO_DATE = "up_to_date"


@dataclass
class DocSection:
    section_id: str
    file_path: str
    doc_type: DocType
    title: str
    content: str = ""
    status: DocStatus = DocStatus.MISSING
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())
    related_code_file: str = ""
    related_code_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "section_id": self.section_id,
            "file_path": self.file_path,
            "doc_type": self.doc_type.value,
            "title": self.title,
            "content": self.content,
            "status": self.status.value,
            "last_modified": self.last_modified,
            "related_code_file": self.related_code_file,
        }


@dataclass
class DocCoverage:
    total_functions: int = 0
    documented_functions: int = 0
    total_classes: int = 0
    documented_classes: int = 0
    coverage_percent: float = 0.0
    missing_docs: list[str] = field(default_factory=list)

    def compute_coverage(self) -> float:
        total = self.total_functions + self.total_classes
        documented = self.documented_functions + self.documented_classes
        self.coverage_percent = (documented / total * 100) if total > 0 else 0.0
        return self.coverage_percent

    def to_dict(self) -> dict:
        return {
            "total_functions": self.total_functions,
            "documented_functions": self.documented_functions,
            "total_classes": self.total_classes,
            "documented_classes": self.documented_classes,
            "coverage_percent": round(self.coverage_percent, 1),
            "missing_docs": self.missing_docs[:20],  # Cap at 20
        }


@dataclass
class DocGenerationResult:
    doc_type: DocType
    generated_sections: list[DocSection] = field(default_factory=list)
    updated_sections: list[DocSection] = field(default_factory=list)
    coverage_before: DocCoverage | None = None
    coverage_after: DocCoverage | None = None
    files_written: list[str] = field(default_factory=list)
    summary: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type.value,
            "generated_sections": [s.to_dict() for s in self.generated_sections],
            "updated_sections": [s.to_dict() for s in self.updated_sections],
            "coverage_before": self.coverage_before.to_dict()
            if self.coverage_before
            else None,
            "coverage_after": self.coverage_after.to_dict()
            if self.coverage_after
            else None,
            "files_written": self.files_written,
            "summary": self.summary,
            "errors": self.errors,
        }
