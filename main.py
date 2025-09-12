import sys
import os
from pathlib import Path

# Add current directory to Python path for local imports
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
import tempfile
import json
import traceback
from typing import Optional

# Import our custom modules
try:
    from docx_to_json import convert_docx_to_json_memory
    from algorithm_from_json_to_required_json import parse_document_sections
    from ai_summarizer import JSONContentSummarizer
    from render_json_into_word import generate_document_in_memory
    print("All modules imported successfully!")
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required files are in the same directory:")
    print("- docx_to_json.py")
    print("- algorithm_from_json_to_required_json.py") 
    print("- ai_summarizer.py")
    print("- render_json_into_word.py")
    raise

app = FastAPI(title="Document Processing API", version="1.0.0")

# Configuration from environment variables
class Config:
    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION", "2024-02-15-preview")
    
    # Template configuration
    TEMPLATE_FILE = os.getenv("TEMPLATE_FILE", "word_template.docx")

config = Config()

# Sections list for document processing
sections_list = [
    "General Business Overview",
    "General Notes & “Wish List”",
    "Key Value Drivers",
    "Motivation(s) for Transformation",
    "Business Locations and Entities",
    "Technical Challenges and Requirements",

    "Idea to Market",
    "For R&D-driven industries (subset of I2M).",
    "General Notes & “Wish List”",
    "Product Design & Engineering",
    "Product Data Management (BOMs, Specs, Integrations)",
    "Testing & Approvals",
    "Production Execution",

    "Source to Pay (S2P)",
    "Broader view of Procure to Pay including sourcing.",
    "General Notes & “Wish List”",
    "Supplier Discovery & Data Management",
    "Contract Management",
    "Sourcing Methods",
    "Catalog Management",
    "Purchase Requisition / Order Management",
    "Goods/Services Receipt",
    "If the prospect needs (E)WM, place notes HERE",
    "Invoice & Payment",
    "Payment Processing",
    "Supplier / Procurement Analytics & Reporting",

    "Plan to Produce (P2P)",
    "General Notes & “Wish List”",
    "Production Planning (MPS, MRP)",
    "Forecasting & Demand Management",
    "Capacity Planning",
    "BOM & Routing Management",
    "Work Center Management",
    "Shop Floor Execution",
    "Order Release & Confirmation",
    "Quality Management in Production",
    "Production Costing",
    "Make-to-Order / Make-to-Stock / Engineer-to-Order Scenarios",
    "Manufacturing Analytics",

    "Detect to Correct (D2C)",
    "Managing quality and compliance issues.",
    "General Notes & “Wish List”",
    "Quality Planning",
    "Inspection Lot Processing",
    "Non-Conformance Management",
    "Corrective & Preventive Actions (CAPA)",
    "Audit Management",
    "Regulatory Compliance",
    "Issue Resolution & Documentation",

    "Forecast to Fulfill (F2F)",
    "Integrated supply chain and demand fulfillment.",
    "General Notes & “Wish List”",
    "Sales Forecasting",
    "Demand Planning",
    "Supply Network Planning",
    "Inventory Planning",
    "Distribution Requirement Planning (DRP)",
    "ATP / CTM (Capable to Match)",
    "Fulfillment Execution",
    "Logistics Optimization",

    "Warehouse Execution (WM / EWM)",
    "General Notes & “Wish List”",
    "Inbound / Put Away Processes",
    "Inventory & Count Processes",
    "Kitting, Assembly, & Value-Added Services",
    "Replenishment & Slotting",
    "Outbound / Staging Processes",

    "Lead to Cash (L2C)",
    "End-to-end customer engagement cycle (includes part of CRM and O2C).",
    "General Notes & “Wish List”",
    "Campaign Management",
    "Lead Generation & Scoring",
    "Opportunity Management",
    "Quotation Management",
    "Customer Master Data Management",
    "Sales Products (BOMs, VC, MTO, MTS)",
    "Sales Order Creation & Management",
    "Availability Check / ATP",
    "Pricing & Discounts",
    "Credit Management",
    "Outbound Delivery Processing",
    "If the prospect needs (E)WM, place notes HERE",
    "Shipping & Transportation",
    "If the prospect needs TM, place notes HERE",
    "Billing / Invoicing",
    "Complaints & Returns",
    "Sales Analytics & Reporting",

    "Logistics Planning & Transportation (TM)",
    "General Notes & “Wish List”",
    "% of parcel, LTL, and FTL",
    "Transportation Planning, Consolidation & Optimization",
    "Carrier Management & Network",
    "Freight Costing & Settlement",
    "Compliance & Documentation",

    "Request to Service (R2S)",
    "Service and support management.",
    "General Notes & “Wish List”",
    "Service Request / Ticket Management",
    "Service Level Agreement (SLA) Tracking",
    "Field Service Management",
    "Warranty & Returns",
    "Installed Base Management",
    "Customer Self-Service Portals",
    "Service Billing",
    "Customer Satisfaction & Feedback",

    "Record to Report (R2R)",
    "Accounting and financial closing activities.",
    "General Notes & “Wish List”",
    "General Ledger Accounting",
    "Accounts Payable / Receivable",
    "Asset Accounting",
    "Cost Center / Internal Order Accounting",
    "Profit Center Accounting",
    "Bank Reconciliation",
    "Intercompany Reconciliation",
    "Financial Closing (Month-End, Year-End)",
    "Consolidation",
    "Financial Reporting & Analytics",

    "Acquire to Dispose (A2D)",
    "Fixed asset lifecycle management.",
    "General Notes & “Wish List”",
    "Asset Master Data Management",
    "Capital Investment Management",
    "Asset Acquisition",
    "Asset Depreciation",
    "Asset Transfers",
    "Asset Retirement & Disposal",
    "Asset Reconciliation & Reporting",

    "Environmental, Social, and Governance (ESG) Processes",
    "Newer strategic reporting area.",
    "General Notes & “Wish List”",
    "Emission Data Collection",
    "ESG Goal Setting",
    "Sustainability Performance Management",
    "ESG Reporting & Audit Trails",
    "Risk & Impact Analysis",

    "Hire to Retire (H2R)",
    "Employee lifecycle management.",
    "General Notes & “Wish List”",
    "Organizational Management",
    "Position Management",
    "Recruiting & Onboarding",
    "Employee Master Data Management",
    "Time & Attendance",
    "Payroll Processing",
    "Benefits Administration",
    "Talent & Performance Management",
    "Learning Management",
    "Succession Planning",
    "Employee Offboarding",
    "HR Analytics",

    "Enterprise Reporting; Data & Analytics Strategy",
    "General Notes & “Wish List”",
    "Team Dynamics",
    "Data Warehousing",
    "“Must Keep” Reports",

    "Other Workstream(s)",
    "Additional Workstream 1 =",
    "Additional Workstream 2 =",
    "Additional Workstream 3 =",
    "Additional Workstream 4 =",
    "Additional Workstream 5 ="
]


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Document Processing API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "message": "API is running",
        "config": {
            "azure_openai_configured": bool(config.AZURE_OPENAI_ENDPOINT and config.AZURE_OPENAI_API_KEY),
            "template_file": config.TEMPLATE_FILE,
            "template_exists": os.path.exists(config.TEMPLATE_FILE)
        }
    }

@app.post("/process-docx-upload")
async def process_docx_upload(file: UploadFile = File(...)):
    """Process uploaded DOCX file and return summarized JSON"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.docx'):
            raise HTTPException(status_code=400, detail="Only .docx files are supported")
        
        print(f"Processing uploaded file: {file.filename}")
        
        # Create temporary file for uploaded DOCX
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_docx:
            content = await file.read()
            temp_docx.write(content)
            temp_docx_path = temp_docx.name
        
        try:
            # Step 1: Convert DOCX to JSON
            print("Converting DOCX to JSON...")
            json_data = convert_docx_to_json_memory(temp_docx_path)
            
            if not json_data:
                raise HTTPException(status_code=500, detail="Failed to convert DOCX to JSON")
            
            print(f"JSON data extracted with {len(json_data.get('sequence', []))} items")
            
            # Step 2: Parse document sections
            print("Parsing document sections...")
            parsed_data = parse_document_sections(sections_list, json_data)
            
            if not parsed_data:
                raise HTTPException(status_code=500, detail="Failed to parse document sections")
            
            print(f"Parsed into {len(parsed_data)} main sections")
            
            # Step 3: Summarize content
            print("Initializing AI summarizer...")
            summarizer = JSONContentSummarizer()
            
            print("Summarizing content...")
            summarized_data = summarizer.summarize_json(parsed_data)
            
            if not summarized_data:
                raise HTTPException(status_code=500, detail="Failed to summarize content")
            
            print("Content summarized successfully")
            
            # ✅ Return summarized data as JSON (instead of generating Word doc)
            return {"summarized_data": summarized_data}
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_docx_path):
                os.unlink(temp_docx_path)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in process_docx_upload: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/process-json")
async def process_json_data(request_data: dict):
    """Generate Word document directly from summarized JSON data"""
    try:
        print("Received request data...")
        
        # ✅ Handle both formats: direct summarized data or wrapped in "summarized_data" key
        if "summarized_data" in request_data:
            summarized_data = request_data["summarized_data"]
            print("Extracted summarized_data from request")
        else:
            summarized_data = request_data
            print("Using request data directly as summarized data")
        
        # Step 3: Generate Word document
        print("Checking template file...")
        if not os.path.exists(config.TEMPLATE_FILE):
            raise HTTPException(status_code=500, detail=f"Template file not found: {config.TEMPLATE_FILE}")
        
        print("Generating Word document...")
        document_bytes = generate_document_in_memory(config.TEMPLATE_FILE, summarized_data)
        
        if not document_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate Word document")
        
        print("Document generated successfully")
        
        # Return the document
        return Response(
            content=document_bytes.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": "attachment; filename=processed_document.docx",
                "Content-Length": str(len(document_bytes.getvalue()))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in process_json_data: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing JSON: {str(e)}")
    
@app.get("/status")
async def get_status():
    """Get status of the API"""
    return {
        "api_status": "running",
        "azure_openai_configured": bool(config.AZURE_OPENAI_ENDPOINT and config.AZURE_OPENAI_API_KEY),
        "template_file_exists": os.path.exists(config.TEMPLATE_FILE),
        "template_file_path": config.TEMPLATE_FILE,
        "current_directory": str(current_dir),
        "files_in_directory": [f for f in os.listdir(current_dir) if f.endswith('.py') or f.endswith('.docx')],
        "workflow": {
            "step_1": "Upload DOCX → Get AI-summarized JSON",
            "step_2": "Send JSON → Get Word document"
        },
        "endpoints": {
            "docx_to_json": "/process-docx-upload - Upload DOCX file, returns AI-summarized JSON",
            "json_to_word": "/process-json - Send JSON data, returns Word document"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Document Processing API...")
    print(f"Current directory: {current_dir}")
    print(f"Template file: {config.TEMPLATE_FILE}")
    print(f"Template exists: {os.path.exists(config.TEMPLATE_FILE)}")
    uvicorn.run(app, host="0.0.0.0", port=8000)