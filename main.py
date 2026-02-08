from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import csv, io, os
from typing import Optional

app = FastAPI(
    title="Logistics AI Verifier",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "OK"}

def parse_text(text: str):
    rows = []
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    for r in reader:
        if len(r) >= 2:
            try:
                qty = float(r[1].replace(",", "."))
            except:
                qty = 0
            rows.append({"sku": r[0].strip(), "qty": qty})
    return rows

@app.post("/compare")
async def compare(
    wz: UploadFile = File(...),
    erp_text: Optional[str] = Form(None),
    erp_file: Optional[UploadFile] = File(None),
):
    wz_raw = await wz.read()
    wz_text = wz_raw.decode("utf-8", errors="ignore")

    if erp_file:
        erp_text = (await erp_file.read()).decode("utf-8", errors="ignore")

    if not erp_text:
        return {"error": "Brak danych ERP"}

    wz_rows = parse_text(wz_text)
    erp_rows = parse_text(erp_text)

    result = []
    for w in wz_rows:
        e = next((x for x in erp_rows if x["sku"] == w["sku"]), None)
        if not e:
            status = "BRAK W ERP"
            erp_qty = None
        elif e["qty"] != w["qty"]:
            status = "RÓŻNA ILOŚĆ"
            erp_qty = e["qty"]
        else:
            status = "OK"
            erp_qty = e["qty"]

        result.append({
            "sku": w["sku"],
            "wz_qty": w["qty"],
            "erp_qty": erp_qty,
            "status": status
        })

    return {"result": result}
