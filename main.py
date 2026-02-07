from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import csv
import io

app = FastAPI(title="WZ Verify API")

# --- Healthcheck / root ---
@app.get("/")
def root():
    return {"status": "ok"}

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helpers ---
def parse_table(text: str):
    rows = []
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    for r in reader:
        if len(r) >= 2:
            rows.append({
                "sku": r[0].strip(),
                "qty": float(r[1].replace(",", "."))
            })
    return rows

# --- API ---
@app.post("/compare")
async def compare(
    table: str = Form(...),
    wz: UploadFile = File(...)
):
    wz_text = (await wz.read()).decode(errors="ignore")

    wz_rows = parse_table(wz_text)
    erp_rows = parse_table(table)

    result = []
    for w in wz_rows:
        match = next((e for e in erp_rows if e["sku"] == w["sku"]), None)
        if not match:
            result.append({**w, "status": "BRAK W ERP"})
        elif match["qty"] != w["qty"]:
            result.append({**w, "status": "RÓŻNA ILOŚĆ"})
        else:
            result.append({**w, "status": "OK"})

    return {"result": result}
