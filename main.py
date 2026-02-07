from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import csv
import io

app = FastAPI(title="WZ Verify API")

# --- Healthcheck / root ---
@app.get("/")
def root():
    return {"status": "ok"}

# --- CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper: parsowanie tabeli ---
def parse_table(text: str):
    rows = []
    reader = csv.reader(io.StringIO(text, newline=''), delimiter="\t")
    for r in reader:
        if len(r) >= 2:
            try:
                rows.append({
                    "sku": r[0].strip(),
                    "qty": float(r[1].replace(",", "."))
                })
            except ValueError:
                # jeśli ilość nie da się sparsować, oznacz jako błąd
                rows.append({
                    "sku": r[0].strip(),
                    "qty": r[1].strip(),
                    "status": "BŁĘDNE DANE"
                })
    return rows

# --- Endpoint: porównanie ---
@app.post("/compare")
async def compare(
    table: str = Form(...),
    wz: UploadFile = File(...)
):
    wz_text = (await wz.read()).decode(errors="ignore")
    erp_rows = parse_table(table)
    wz_rows = parse_table(wz_text)

    result = []
    for w in wz_rows:
        match = next((e for e in erp_rows if e["sku"] == w["sku"]), None)
        if not match:
            result.append({**w, "status": "BRAK W ERP"})
        elif isinstance(match.get("qty"), float) and match["qty"] != w.get("qty"):
            result.append({**w, "status": "RÓŻNA ILOŚĆ"})
        elif "status" in w and w["status"] == "BŁĘDNE DANE":
            result.append(w)
        else:
            result.append({**w, "status": "OK"})

    return {"result": result}
