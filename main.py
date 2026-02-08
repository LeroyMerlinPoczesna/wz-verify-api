from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import re

app = FastAPI(title="Logistics AI – WZ Verify")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True}


# =========================
# ENTERPRISE TEXT PARSER
# =========================
def parse_text(raw: str):
    rows = []

    # normalizacja
    raw = raw.replace("\r", "\n")
    lines = raw.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # usuwamy śmieci OCR
        line = re.sub(r"[|;,]", " ", line)
        line = re.sub(r"\s+", " ", line)

        parts = line.split(" ")

        if len(parts) < 2:
            continue

        sku = parts[0]

        try:
            qty = float(parts[1].replace(",", "."))
        except ValueError:
            continue

        rows.append({
            "sku": sku,
            "qty": qty
        })

    return rows


# =========================
# COMPARE
# =========================
@app.post("/compare-ai")
async def compare_ai(
    erp_text: str = Form(...),
    wz: UploadFile = File(...)
):
    try:
        wz_text = (await wz.read()).decode(errors="ignore")
    except Exception:
        raise HTTPException(400, "Nie można odczytać pliku WZ")

    wz_rows = parse_text(wz_text)
    erp_rows = parse_text(erp_text)

    result = []

    for w in wz_rows:
        match = next((e for e in erp_rows if e["sku"] == w["sku"]), None)

        if not match:
            result.append({
                "sku": w["sku"],
                "wz_qty": w["qty"],
                "erp_qty": None,
                "status": "BRAK W ERP"
            })
        elif match["qty"] != w["qty"]:
            result.append({
                "sku": w["sku"],
                "wz_qty": w["qty"],
                "erp_qty": match["qty"],
                "status": "RÓŻNA ILOŚĆ"
            })
        else:
            result.append({
                "sku": w["sku"],
                "wz_qty": w["qty"],
                "erp_qty": match["qty"],
                "status": "OK"
            })

    return {
        "count_wz": len(wz_rows),
        "count_erp": len(erp_rows),
        "items": result
    }
