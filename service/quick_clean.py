import re
import pandas as pd

_ADDR_PAT = r"(?i)([A-ZÁÂÃÉÍÓÚ][\wÀ-ÿ .'-]+,\s*[A-ZÁÂÃÉÍÓÚ][\wÀ-ÿ .'-]+,\s*(?:Brasil|Brazil|Portugal|Spain|España))"
_DEG_PAT = r"(?i)(?:(?!(\d+\s+(anos?|years?)|\(\d+\s+year|\bJan|Feb|Mar|Abr|Apr|Mai|Jun|Jul|Ago|Aug|Sep|Out|Oct|Nov|Dez|Dec\b)).){0,20}" \
           r"(Bachelor|Master|MBA|B\.?Tech|Bacharel|Licenciatura|Mestrado|Doutor)[^|\n]{10,140}"

def _slug_to_name(u: str) -> str:
    m = re.search(r"/in/([^/?#]+)", str(u) or "")
    if not m: return ""
    slug = re.sub(r"-\d{3,}$", "", m.group(1))
    return " ".join(w.capitalize() for w in slug.replace("-", " ").split())

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    addr = df["profile_text"].astype(str).str.extract(_ADDR_PAT, expand=False)
    df["address"] = df["address"].where(df["address"].astype(str).str.len().gt(0), addr)

    deg_series = (
        df["profile_text"].astype(str)
        .str.findall(_DEG_PAT, flags=re.I)
        .apply(lambda L: max(L, key=len) if L else "")
    )
    df["degree"] = df["degree"].where(df["degree"].astype(str).str.len().gt(0), deg_series)

    mask = df["name"].astype(str).str.match(r"(?i)^profile")
    df.loc[mask, "name"] = df.loc[mask, "url"].map(_slug_to_name).fillna(df.loc[mask, "name"])

    return df