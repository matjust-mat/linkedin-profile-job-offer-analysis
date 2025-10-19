# Requires:
#   profile_ingest_pdf.run(pdf_dir: str, out_csv: str, pattern: str)
#   quick_clean.clean_df(df: pandas.DataFrame) -> pandas.DataFrame
#   score_cli.score_df(df: pandas.DataFrame, cfg: dict) -> pandas.DataFrame

import io, os, tempfile, shutil
from typing import List, Dict, Any
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from profile_ingest_pdf import run as ingest_run
from quick_clean import clean_df
from scorer import score_df

app = FastAPI(title="Candidate Scorer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

NEEDED_COLS = [
    "name","age","phone","email","address","degree","years_experience",
    "skills","soft_skills","languages","profile_text","url"
]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/score/pdfs")
async def score_pdfs(
    files: List[UploadFile] = File(...),
    degree: str = Form(""),
    req: str = Form(""),
    nice: str = Form(""),
    soft_req: str = Form(""),
    soft_nice: str = Form(""),
    langs: str = Form(""),
    min_years: float = Form(0.0),
    notes: str = Form("")
):
    tmpdir = tempfile.mkdtemp(prefix="pdf_ingest_")
    out_csv = os.path.join(tmpdir, "candidates.csv")
    try:
        for f in files:
            path = os.path.join(tmpdir, f.filename)
            with open(path, "wb") as fh:
                fh.write(await f.read())

        ingest_run(tmpdir, out_csv, "*.pdf")
        df = pd.read_csv(out_csv)

        for c in NEEDED_COLS:
            if c not in df.columns:
                df[c] = ""

        df = clean_df(df)
        cfg: Dict[str, Any] = dict(
            degree=degree, req=req, nice=nice, soft_req=soft_req, soft_nice=soft_nice,
            langs=langs, min_years=min_years, notes=notes
        )
        out = score_df(df, cfg).reset_index(drop=True)
        top5 = out.head(5).to_dict(orient="records")
        return {"count": len(out), "top5": top5, "results": out.to_dict(orient="records")}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

@app.post("/score/csv")
async def score_csv(
    file: UploadFile = File(...),
    degree: str = Form(""),
    req: str = Form(""),
    nice: str = Form(""),
    soft_req: str = Form(""),
    soft_nice: str = Form(""),
    langs: str = Form(""),
    min_years: float = Form(0.0),
    notes: str = Form("")
):
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    for c in NEEDED_COLS:
        if c not in df.columns:
            df[c] = ""

    df = clean_df(df)
    cfg: Dict[str, Any] = dict(
        degree=degree, req=req, nice=nice, soft_req=soft_req, soft_nice=soft_nice,
        langs=langs, min_years=min_years, notes=notes
    )
    out = score_df(df, cfg).reset_index(drop=True)
    top5 = out.head(5).to_dict(orient="records")
    return {"count": len(out), "top5": top5, "results": out.to_dict(orient="records")}
