from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import csv
import io
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import tempfile

app = FastAPI(title="WZ Verifier 2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_text(text: str):
    rows = []
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    for r in reader:
        if len(r) >= 2:
            try:
                qty = float(r[1].replace(",", "."))
            except ValueError:
                qty = 0
            rows.append({"sku": r[0].strip(), "qty": qty})
    return rows

def parse_file(file: UploadFile):
    if file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        img = Image.open(file.file)
        text = pytesseract.image_to_string(img, lang='pol')
    elif file.filename.lower().endswith(".pdf"):
        pages = convert_from_bytes(file.file.read())
        text = "\n".join(pytesseract.image_to_string(p, lang='pol') for p in pages)
    else:
        text = file.file.read().decode(errors="ignore")
    return text

@app.post("/compare-ai")
async def compare_ai(
    table: str = Form(...),
    wz: UploadFile = File(...)
):
    wz_text = parse_file(wz)
    wz_rows = parse_text(wz_text)
    erp_rows = parse_text(table)

    result = []
    for i, w in enumerate(wz_rows):
        match = next((e for e in erp_rows if e["sku"] == w["sku"]), None)
        if not match:
            status = "BRAK W ERP"
        elif match["qty"] != w["qty"]:
            status = "RÓŻNA ILOŚĆ"
        else:
            status = "OK"
        result.append({**w, "status": status, "progress": round((i+1)/len(wz_rows)*100, 1)})

    return {"result": result, "ocr_preview": wz_text[:1000]}  # first 1000 chars for preview
