import io, os, tempfile, shutil
from typing import List, Dict, Any
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from profile_ingest_pdf import run_to_df
from quick_clean import clean_df
from scorer import score_df

app = FastAPI(title="Candidate Scorer API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEEDED_COLS = ["name","age","phone","email","address","degree","years_experience",
               "skills","soft_skills","languages","profile_text","url"]

def _ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in NEEDED_COLS:
        if c not in df.columns: df[c] = ""
    return df[NEEDED_COLS]

@app.get("/health")
def health(): return {"ok": True}

@app.post("/score/pdfs")
async def score_pdfs(
    files: List[UploadFile] = File(..., description="One or more PDFs"),
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
    try:
        # persist uploads
        for f in files:
            with open(os.path.join(tmpdir, f.filename), "wb") as fh:
                fh.write(await f.read())

        df = run_to_df(tmpdir, "*.pdf")
        df = _ensure_cols(df)
        df = clean_df(df)

        cfg: Dict[str, Any] = dict(
            degree=degree, req=req, nice=nice, soft_req=soft_req,
            soft_nice=soft_nice, langs=langs, min_years=min_years, notes=notes
        )
        out = score_df(df, cfg).reset_index(drop=True)
        return {
            "count": len(out),
            "top5": out.head(5).to_dict(orient="records"),
            "results": out.to_dict(orient="records"),
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)