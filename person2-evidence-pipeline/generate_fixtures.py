import csv
from pathlib import Path
import fitz
import openpyxl

fixtures_dir = Path("fixtures")
fixtures_dir.mkdir(parents=True, exist_ok=True)

# 1. Create AML_Q3_Report.pdf
doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(50, 50, 550, 800)
text = """AML Q3 Compliance Review Report
Executive Summary & Control Testing Evidence
Review Control ID: RC-00091
Evidence Request ID: REQ-00084

1. Scope of Testing
This document serves as testing evidence for second-line-of-defense (LOD2) control monitoring.
During Q3 2026, 12,482 high-risk customer accounts were evaluated under AML Screening Policy.

2. Sample Testing Summary
- Total High-Risk Population: 12,482
- Sample Size Selected: 250
- Exceptions Identified: 3
- Remediation Status: In Progress

3. Management Sign-Off
Control Owner: John Smith (AML Operations)
Sign-Off Date: 2026-09-30
Approval Status: Approved with observations
"""
page.insert_textbox(rect, text, fontsize=11, fontname="helv")
pdf_path = fixtures_dir / "AML_Q3_Report.pdf"
doc.save(str(pdf_path))
doc.close()
print(f"Created {pdf_path}")

# 2. Create high_risk_accounts.xlsx
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "HighRiskAccounts"

ws.append(["AccountId", "CustomerName", "RiskScore", "CountryCode", "PEPStatus", "ReviewDate"])
ws.append(["ACC-10091", "Acme Global Trading", 88.5, "GB", "No", "2026-09-15"])
ws.append(["ACC-10092", "Vanguard Horizons Ltd", 92.0, "CH", "Yes", "2026-09-18"])
ws.append(["ACC-10093", "Apex Capital Trust", 79.0, "AE", "No", "2026-09-21"])
ws.append(["ACC-10094", "Helios International", 85.5, "SG", "No", "2026-09-25"])

ws2 = wb.create_sheet(title="Summary")
ws2.append(["Metric", "Value"])
ws2.append(["TotalAccounts", 4])
ws2.append(["HighRiskThreshold", 75.0])
ws2.append(["PEPIdentified", 1])

xlsx_path = fixtures_dir / "high_risk_accounts.xlsx"
wb.save(str(xlsx_path))
print(f"Created {xlsx_path}")

# 3. Create exceptions.csv
csv_path = fixtures_dir / "exceptions.csv"
with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["ExceptionId", "AccountId", "ControlRule", "Severity", "IdentifiedDate", "Resolution"])
    writer.writerow(["EX-001", "ACC-10092", "PEP_ENHANCED_DUE_DILIGENCE", "HIGH", "2026-09-18", "EDD Form Pending"])
    writer.writerow(["EX-002", "ACC-10088", "ID_DOCUMENT_EXPIRED", "MEDIUM", "2026-09-19", "Client Contacted"])
    writer.writerow(["EX-003", "ACC-10041", "SOURCE_OF_FUNDS_MISSING", "HIGH", "2026-09-22", "Escalated to MLRO"])

print(f"Created {csv_path}")
