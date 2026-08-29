#!/usr/bin/env python3
"""Generate realistic test PDFs for all 6 Nutrient use cases."""

from fpdf import FPDF
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "test_pdfs")
os.makedirs(OUT, exist_ok=True)


class DocPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, self.doc_title, align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def section(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)

    def field(self, label, value):
        self.set_font("Helvetica", "B", 10)
        self.cell(60, 7, label + ":", new_x="END")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 7, str(value), new_x="LMARGIN", new_y="NEXT")

    def body_text(self, text):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 5, text)
        self.ln(2)


# ============================================================
# USE CASE 1: Procurement (original)
# ============================================================
def gen_procurement():
    pdf = DocPDF()
    pdf.doc_title = "Procurement Request"

    # Doc A: Purchase Request
    pdf.add_page()
    pdf.section("PROCUREMENT REQUEST")
    pdf.field("Legal Name", "Northstar Data Systems Ltd.")
    pdf.field("Requested Spend", "$42,500")
    pdf.field("Contract Start", "2026-10-01")
    pdf.field("Required Coverage Until", "2027-10-01")
    pdf.field("Payment Terms", "Net 60")
    pdf.field("Department", "Engineering")
    pdf.body_text(
        "Requesting annual software procurement for cloud platform license "
        "and support services. Vendor has been pre-qualified. Insurance must "
        "cover the full contract period plus 30 days."
    )
    pdf.output(os.path.join(OUT, "procurement_01_request.pdf"))

    # Doc B: Vendor Quote
    pdf = DocPDF()
    pdf.doc_title = "Vendor Quote"
    pdf.add_page()
    pdf.section("QUOTE - Northstar Data Systems Limited")
    pdf.field("Quote Number", "Q-2026-4891")
    pdf.field("Date", "2026-09-15")
    pdf.field("Valid Until", "2026-12-15")
    pdf.section("Line Items")
    pdf.field("Platform License (Annual)", "$35,000")
    pdf.field("Premium Support (Annual)", "$7,500")
    pdf.field("Total", "$42,500")
    pdf.field("Payment Terms", "Net 30")
    pdf.body_text(
        "This quote includes full platform access for up to 50 users, "
        "24/7 premium support, and quarterly business reviews."
    )
    pdf.output(os.path.join(OUT, "procurement_02_quote.pdf"))

    # Doc C: Insurance Certificate
    pdf = DocPDF()
    pdf.doc_title = "Certificate of Insurance"
    pdf.add_page()
    pdf.section("CERTIFICATE OF LIABILITY INSURANCE")
    pdf.field("Insured", "Northstar Data Systems Ltd.")
    pdf.field("Policy Type", "Commercial General Liability")
    pdf.field("Policy Number", "CGL-2026-88421")
    pdf.field("Effective Date", "2026-01-01")
    pdf.field("Expiry Date", "2027-08-31")
    pdf.field("Coverage Limit", "$2,000,000")
    pdf.field("Deductible", "$5,000")
    pdf.body_text(
        "This certificate is issued as evidence of insurance coverage "
        "for the named insured. Coverage is subject to terms and conditions."
    )
    pdf.output(os.path.join(OUT, "procurement_03_insurance.pdf"))

    # Doc D: Security Questionnaire
    pdf = DocPDF()
    pdf.doc_title = "Security Questionnaire"
    pdf.add_page()
    pdf.section("VENDOR SECURITY ASSESSMENT")
    pdf.field("Company", "Northstar Data Systems Ltd.")
    pdf.field("Data Retention", "30 days")
    pdf.field("Subprocessors", "3")
    pdf.field("Encryption at Rest", "Yes")
    pdf.field("SOC 2 Type II", "Yes")
    pdf.field("Penetration Test", "Annual, last: 2026-03-15")
    pdf.body_text(
        "All data is encrypted at rest using AES-256 and in transit using "
        "TLS 1.3. Subprocessors: AWS (hosting), Stripe (billing), "
        "Intercom (support). Data retained for 30 days after contract end."
    )
    pdf.output(os.path.join(OUT, "procurement_04_security.pdf"))
    print("✓ Procurement: 4 PDFs generated")


# ============================================================
# USE CASE 2: Customer Onboarding (ID + KYC)
# ============================================================
def gen_kyc():
    pdf = DocPDF()
    pdf.doc_title = "Identity Verification"

    # ID Document
    pdf.add_page()
    pdf.section("DRIVER'S LICENSE - STATE OF CALIFORNIA")
    pdf.field("Full Name", "Sarah Chen")
    pdf.field("Date of Birth", "1990-03-15")
    pdf.field("License Number", "D1234567")
    pdf.field("Address", "1847 Mission St, San Francisco, CA 94103")
    pdf.field("Class", "C")
    pdf.field("Expires", "2028-03-15")
    pdf.field("Restrictions", "CORRECTIVE LENSES")
    pdf.output(os.path.join(OUT, "kyc_01_drivers_license.pdf"))

    # Proof of Address
    pdf = DocPDF()
    pdf.doc_title = "Proof of Address"
    pdf.add_page()
    pdf.section("UTILITY BILL - PACIFIC GAS & ELECTRIC")
    pdf.field("Account Holder", "Sarah M Chen")
    pdf.field("Service Address", "1847 Mission St, San Francisco, CA 94103")
    pdf.field("Billing Period", "August 2026")
    pdf.field("Amount Due", "$142.37")
    pdf.field("Due Date", "2026-09-15")
    pdf.body_text(
        "This bill serves as proof of current residential address. "
        "Account has been active since 2019 with no lapses."
    )
    pdf.output(os.path.join(OUT, "kyc_02_proof_of_address.pdf"))

    # Bank Statement
    pdf = DocPDF()
    pdf.doc_title = "Bank Statement"
    pdf.add_page()
    pdf.section("WELLS FARGO - MONTHLY STATEMENT")
    pdf.field("Account Holder", "Sarah Chen")
    pdf.field("Statement Period", "Aug 1 - Aug 31, 2026")
    pdf.field("Opening Balance", "$12,847.52")
    pdf.field("Closing Balance", "$14,203.18")
    pdf.field("Account Type", "Checking")
    pdf.body_text(
        "Direct deposit from employer (TechCorp Inc.) received on 8/15. "
        "No overdrafts in the past 12 months."
    )
    pdf.output(os.path.join(OUT, "kyc_03_bank_statement.pdf"))
    print("✓ KYC: 3 PDFs generated")


# ============================================================
# USE CASE 3: Invoice → E-Invoice
# ============================================================
def gen_invoice():
    pdf = DocPDF()
    pdf.doc_title = "Vendor Invoice"
    pdf.add_page()
    pdf.section("INVOICE")
    pdf.field("Invoice Number", "INV-2026-7891")
    pdf.field("Invoice Date", "2026-08-20")
    pdf.field("Due Date", "2026-10-19")
    pdf.field("Payment Terms", "Net 60")
    pdf.ln(4)
    pdf.section("From")
    pdf.field("Company", "GlobalTech Manufacturing Co.")
    pdf.field("Address", "450 Industrial Blvd, Shanghai, China 200001")
    pdf.field("Tax ID", "CN-91310000MA1FL8XH42")
    pdf.ln(2)
    pdf.section("To")
    pdf.field("Company", "Pacific Imports Ltd.")
    pdf.field("Address", "2200 Harbor Blvd, Long Beach, CA 90802")
    pdf.field("Tax ID", "US-82-1234567")
    pdf.ln(4)
    pdf.section("Line Items")
    pdf.field("Industrial Servo Motors (240 units)", "$300,000.00")
    pdf.field("Shipping (FOB Shanghai)", "$12,500.00")
    pdf.field("Insurance", "$3,200.00")
    pdf.field("Subtotal", "$315,700.00")
    pdf.field("Tax (0% - export)", "$0.00")
    pdf.field("Total Due", "$315,700.00")
    pdf.body_text(
        "Payment wire to: HSBC Shanghai, SWIFT: HSBCSHSH, "
        "Account: 801-234567-838. Reference: INV-2026-7891."
    )
    pdf.output(os.path.join(OUT, "invoice_01_vendor_invoice.pdf"))
    print("✓ Invoice: 1 PDF generated")


# ============================================================
# USE CASE 4: Trade Documents (cross-check)
# ============================================================
def gen_trade():
    pdf = DocPDF()
    pdf.doc_title = "Commercial Invoice"
    pdf.add_page()
    pdf.section("COMMERCIAL INVOICE")
    pdf.field("Invoice No.", "INV-2026-7891")
    pdf.field("Date", "2026-08-15")
    pdf.field("Shipper", "GlobalTech Manufacturing Co.")
    pdf.field("Consignee", "Pacific Imports Ltd.")
    pdf.field("Origin", "China")
    pdf.field("Incoterm", "FOB Shanghai")
    pdf.field("Quantity", "240 units")
    pdf.field("Unit Price", "$1,250.00")
    pdf.field("Total Value", "$300,000.00")
    pdf.output(os.path.join(OUT, "trade_01_invoice.pdf"))

    # Bill of Lading
    pdf = DocPDF()
    pdf.doc_title = "Bill of Lading"
    pdf.add_page()
    pdf.section("BILL OF LADING")
    pdf.field("B/L Number", "COSU6280034100")
    pdf.field("Shipper", "GlobalTech Manufacturing Co.")
    pdf.field("Consignee", "Pacific Imports Ltd.")
    pdf.field("Port of Loading", "Shanghai, China")
    pdf.field("Port of Discharge", "Long Beach, CA")
    pdf.field("Quantity", "240 cartons")
    pdf.field("Freight", "Freight Prepaid")
    pdf.field("Weight", "4,800 kg")
    pdf.body_text(
        "Shipped on vessel COSCO Shipping Taurus V.2608E. "
        "ETD Shanghai: 2026-08-20. ETA Long Beach: 2026-09-05."
    )
    pdf.output(os.path.join(OUT, "trade_02_bill_of_lading.pdf"))

    # Certificate of Origin
    pdf = DocPDF()
    pdf.doc_title = "Certificate of Origin"
    pdf.add_page()
    pdf.section("CERTIFICATE OF ORIGIN")
    pdf.field("Certificate No.", "CO-2026-SH-4412")
    pdf.field("Country of Origin", "China")
    pdf.field("Invoice Reference", "INV-2026-7891")
    pdf.field("Quantity", "240 units")
    pdf.field("HS Code", "8501.53")
    pdf.field("Description", "AC Servo Motors, 3-phase, 5hp")
    pdf.body_text(
        "The undersigned hereby certifies that the goods described above "
        "originate in the People's Republic of China."
    )
    pdf.output(os.path.join(OUT, "trade_03_certificate_origin.pdf"))
    print("✓ Trade: 3 PDFs generated")


# ============================================================
# USE CASE 5: Mortgage Appraisal
# ============================================================
def gen_mortgage():
    pdf = DocPDF()
    pdf.doc_title = "Property Appraisal"
    pdf.add_page()
    pdf.section("RESIDENTIAL APPRAISAL REPORT")
    pdf.field("Property Address", "742 Evergreen Terrace, Springfield, IL 62704")
    pdf.field("Appraiser", "James Mitchell, licensed #APR-2024-8821")
    pdf.field("Date of Value", "2026-08-22")
    pdf.field("Effective Date", "2026-08-22")
    pdf.field("Property Type", "Single Family Residence")
    pdf.field("Year Built", "1998")
    pdf.field("Square Footage", "2,340 sq ft")
    pdf.field("Lot Size", "0.28 acres")
    pdf.field("Bedrooms", "4")
    pdf.field("Bathrooms", "2.5")
    pdf.field("Garage", "2-car attached")
    pdf.ln(4)
    pdf.section("Valuation")
    pdf.field("Comparable 1 (123 Oak St)", "$385,000")
    pdf.field("Comparable 2 (456 Elm St)", "$392,000")
    pdf.field("Comparable 3 (789 Maple Dr)", "$378,000")
    pdf.field("Adjusted Value", "$387,500")
    pdf.field("Final Appraised Value", "$387,500")
    pdf.ln(4)
    pdf.section("Condition Assessment")
    pdf.body_text(
        "Subject property is in good condition. Roof replaced 2022. "
        "HVAC system original (1998) - functional but aging. "
        "Kitchen updated 2020 with granite counters. "
        "No visible structural issues. Foundation sound."
    )
    pdf.output(os.path.join(OUT, "mortgage_01_appraisal.pdf"))
    print("✓ Mortgage: 1 PDF generated")


# ============================================================
# USE CASE 6: Redaction (PII in medical form)
# ============================================================
def gen_redaction():
    pdf = DocPDF()
    pdf.doc_title = "Patient Intake Form"
    pdf.add_page()
    pdf.section("PATIENT INTAKE - SPRINGFIELD MEDICAL CENTER")
    pdf.field("Patient Name", "Robert Johnson")
    pdf.field("Date of Birth", "1975-06-22")
    pdf.field("SSN", "123-45-6789")
    pdf.field("Phone", "(555) 234-5678")
    pdf.field("Email", "r.johnson@email.com")
    pdf.field("Address", "987 Pine Lane, Springfield, IL 62701")
    pdf.field("Insurance ID", "BC-9928371")
    pdf.field("Group Number", "GRP-44521")
    pdf.ln(4)
    pdf.section("Medical History")
    pdf.field("Chief Complaint", "Lower back pain, 3 weeks duration")
    pdf.field("Current Medications", "Ibuprofen 400mg PRN")
    pdf.field("Allergies", "Penicillin (rash)")
    pdf.field("Previous Surgeries", "Appendectomy (2012)")
    pdf.field("Family History", "Father: hypertension, Mother: diabetes type 2")
    pdf.ln(4)
    pdf.section("Vital Signs")
    pdf.field("Blood Pressure", "138/85 mmHg")
    pdf.field("Heart Rate", "72 bpm")
    pdf.field("Temperature", "98.6 F")
    pdf.field("Weight", "185 lbs")
    pdf.field("Height", "5'10\"")
    pdf.body_text(
        "Patient consents to treatment and acknowledges receipt of "
        "notice of privacy practices. Signature on file."
    )
    pdf.output(os.path.join(OUT, "redaction_01_intake_form.pdf"))
    print("✓ Redaction: 1 PDF generated")


if __name__ == "__main__":
    gen_procurement()
    gen_kyc()
    gen_invoice()
    gen_trade()
    gen_mortgage()
    gen_redaction()
    print(f"\nAll PDFs in: {OUT}")
