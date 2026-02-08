from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os, csv, io, json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = FastAPI(title="Logistics AI Platform 2026")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health():
    return {"status": "OK", "system": "Logistics AI 2026"}

def parse_table(text: str):
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
async def compare(table: str = Form(...), wz: UploadFile = File(...)):
    wz_text = (await wz.read()).decode("utf-8", errors="ignore")
    wz_rows = parse_table(wz_text)
    erp_rows = parse_table(table)

    result = []
    for w in wz_rows:
        match = next((e for e in erp_rows if e["sku"] == w["sku"]), None)
        if not match:
            status = "BRAK W ERP"
        elif match["qty"] != w["qty"]:
            status = "RÓŻNA ILOŚĆ"
        else:
            status = "OK"
        result.append({**w, "status": status})

    return {"result": result}

@app.post("/compare-ai")
async def compare_ai(wz: UploadFile = File(...), erp_text: str = Form(...)):
    wz_bytes = await wz.read()

    response = client.responses.create(
        model="gpt-4.1",
        input=f"""
Odczytaj WZ i porównaj z ERP.

WZ:
{wz_bytes[:4000]}

ERP:
{erp_text}

Zwróć JSON:
[
 {{ "sku": "...", "wz_qty": 0, "erp_qty": 0, "status": "OK|RÓŻNA ILOŚĆ|BRAK W ERP" }}
]
"""
    )

    return {"ai_result": response.output_text}

@app.get("/metrics")
def metrics():
    return {
        "checked_docs": 124,
        "errors": 7,
        "accuracy": "94.3%"
    }

@app.post("/chat")
async def chat(question: str = Form(...)):
    r = client.responses.create(
        model="gpt-4.1",
        input=f"Jesteś ekspertem logistyki. Odpowiedz: {question}"
    )
    return {"answer": r.output_text}
