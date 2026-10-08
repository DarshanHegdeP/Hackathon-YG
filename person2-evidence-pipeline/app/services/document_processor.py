from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def extract_text_from_file(file_path: Path) -> dict[str, Any]:
    if file_path.suffix.lower() == ".pdf":
        return _extract_pdf_text(file_path)
    return _extract_text_file(file_path)


def _extract_text_file(file_path: Path) -> dict[str, Any]:
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = file_path.read_bytes().decode("latin-1", errors="replace")

    return {
        "raw_text": text,
        "pages": 1,
        "method": "plain-text",
    }


def _extract_pdf_text(file_path: Path) -> dict[str, Any]:
    try:
        import fitz  # type: ignore

        document = fitz.open(file_path)
        page_texts = [page.get_text() for page in document]
        text = "\n\n".join(page_texts)
        return {
            "raw_text": text,
            "pages": len(document),
            "method": "PyMuPDF",
        }
    except Exception:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(file_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
            return {
                "raw_text": text,
                "pages": len(reader.pages),
                "method": "pypdf",
            }
        except Exception:
            return {
                "raw_text": "",
                "pages": 0,
                "method": "unavailable",
            }


def build_normalized_facts(file_name: str, extracted_text: str) -> dict[str, Any]:
    lower_text = extracted_text.lower()
    return {
        "documentType": _detect_document_type(file_name, lower_text),
        "reportingPeriod": _detect_period(extracted_text),
        "businessUnit": _detect_business_unit(lower_text),
        "controlIds": _detect_control_ids(extracted_text),
        "dates": _detect_dates(extracted_text),
        "owners": _detect_owners(extracted_text),
        "metrics": _detect_metrics(extracted_text),
        "exceptions": _detect_exceptions(extracted_text),
        "approvals": _detect_approvals(extracted_text),
        "rawText": extracted_text[:20000],
    }


def _detect_document_type(file_name: str, lower_text: str) -> str:
    lower_name = file_name.lower()
    if "aml" in lower_name or "aml" in lower_text:
        return "AML_REPORT"
    if "kyc" in lower_name or "kyc" in lower_text:
        return "KYC_REPORT"
    if "access" in lower_name or "access" in lower_text:
        return "ACCESS_REVIEW"
    if "vendor" in lower_name or "vendor" in lower_text:
        return "VENDOR_RISK"
    return "GENERAL_EVIDENCE"


def _detect_period(text: str) -> str | None:
    match = re.search(r"(Q[1-4])[\s-]*(\d{4})|(?:FY[\s-]*)(\d{4})", text, re.IGNORECASE)
    if match:
        if match.group(1):
            return f"{match.group(1).upper()}-{match.group(2)}"
        return f"FY-{match.group(3)}"
    return None


def _detect_business_unit(lower_text: str) -> str | None:
    keywords = [
        "retail banking",
        "commercial banking",
        "risk",
        "compliance",
        "operations",
        "aml",
        "it security",
        "credit",
        "vendor management",
    ]
    for keyword in keywords:
        if keyword in lower_text:
            return keyword.title()
    return None


def _detect_control_ids(text: str) -> list[str]:
    matches = re.findall(r"(?:CTRL|CONTROL|CTRL-)[A-Z0-9-]+", text, flags=re.IGNORECASE)
    return [match.upper() for match in matches] or []


def _detect_dates(text: str) -> list[str]:
    matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b", text)
    return matches[:20]


def _detect_owners(text: str) -> list[str]:
    # Simple detection based on common owner labels.
    owners = []
    for label in ["owner", "business unit", "team", "function", "control owner"]:
        for match in re.finditer(rf"{label}[:\s]+([A-Za-z0-9 &/.-]+)", text, flags=re.IGNORECASE):
            owners.append(match.group(1).strip())
    return owners[:10]


def _detect_metrics(text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    population_match = re.search(r"(\d[\d,]*)\s*(customers|records|transactions|users)", text, flags=re.IGNORECASE)
    if population_match:
        metrics["population"] = int(population_match.group(1).replace(",", ""))

    exception_match = re.search(r"(\d[\d,]*)\s*(exceptions|exceptions? population)", text, flags=re.IGNORECASE)
    if exception_match:
        metrics["exceptions"] = int(exception_match.group(1).replace(",", ""))

    approvals_match = re.search(r"(\d[\d,]*)\s*(approvals|approvals provided)", text, flags=re.IGNORECASE)
    if approvals_match:
        metrics["approvals"] = int(approvals_match.group(1).replace(",", ""))

    return metrics


def _detect_exceptions(text: str) -> list[str]:
    matches = re.findall(r"(?:exception|missing|missing evidence|no approval|variance|gap)[A-Za-z0-9 ,.-]{0,120}", text, flags=re.IGNORECASE)
    return [m.strip() for m in matches[:10]]


def _detect_approvals(text: str) -> list[str]:
    approvals = []
    if "approved" in text.lower() or "approval" in text.lower():
        approvals.append("approval_present")
    if "no approval" in text.lower() or "approval missing" in text.lower():
        approvals.append("approval_missing")
    return approvals
