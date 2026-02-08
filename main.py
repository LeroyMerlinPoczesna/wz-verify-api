from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import csv
import io
import os
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")

app = FastAPI(title="Logistics AI Verifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_text_table(text: str):
    rows = []
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    for r in reader:
        if len(r) >= 2:
            try:
                rows.append({"sku": r[0].strip(), "qty": float(r[1].replace(",", ".") )})
            except:
                rows.append({"sku": r[0].strip(), "qty": 0})
    return rows

@app.post("/compare")
async def compare(
    wz: UploadFile = File(...),
    erp_text: str = Form(None),
    erp_file: UploadFile = File(None)
):
    # wczytaj WZ
    wz_data = (await wz.read()).decode("utf-8", errors="ignore")

    # ERP – z pliku lub z textarea
    erp_data = ""
    if erp_text:
        erp_data = erp_text
    elif erp_file:
        erp_data = (await erp_file.read()).decode("utf-8", errors="ignore")

    wz_rows = parse_text_table(wz_data)
    erp_rows = parse_text_table(erp_data)

    # AI-Agent prompt
    system_prompt = """
You are a smart logistics assistant.
Compare two lists of items (WZ and ERP).
Return a JSON array with: sku, qty_wz, qty_erp, status.
Status = OK, DIFFERENT, MISSING.
"""
    wz_list_str = "\n".join([f"{r['sku']}\t{r['qty']}" for r in wz_rows])
    erp_list_str = "\n".join([f"{r['sku']}\t{r['qty']}" for r in erp_rows])

    user_prompt = f"""
WZ:
{wz_list_str}

ERP:
{erp_list_str}
"""

    completion = openai.ChatCompletion.create(
      model="gpt-4.1",
      messages=[
        {"role":"system","content":system_prompt},
        {"role":"user","content":user_prompt}
      ],
      temperature=0.1
    )

    # parse response
    text = completion.choices[0].message["content"]
    return {"result": text}
