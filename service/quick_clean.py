import re
import pandas as pd

_ADDR_PAT = r"([A-ZÁÂÃÉÍÓÚ][\wÀ-ÿ .'-]+,\s*[A-ZÁÂÃÉÍÓÚ][\wÀ-ÿ .'-]+,\s*(?:Brasil|Brazil|Portugal|Spain|España))"
_DEG_PAT  = r"(?:Bachelor[^|\n]{10,140}|Master[^|\n]{10,140}|MBA[^|\n]{10,140}|B\.?Tech[^|\n]{10,140}|Bacharel[^|\n]{10,140}|Licenciatura[^|\n]{10,140}|Mestrado[^|\n]{10,140}|Doutor[^|\n]{10,140})"

def _slug_to_name(u: str) -> str:
    m = re.search(r"/in/([^/?#]+)", str(u) or "")
    if not m: return ""
    slug = re.sub(r"-\d{3,}$", "", m.group(1))
    return " ".join(w.capitalize() for w in slug.replace("-", " ").split())

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    addr = df["profile_text"].astype(str).str.extract(_ADDR_PAT, expand=False)
    df["address"] = df["address"].combine_first(addr)

    deg_series = (
        df["profile_text"].astype(str)
        .str.findall(_DEG_PAT, flags=re.I)
        .apply(lambda L: max(L, key=len) if L else "")
    )
    df["degree"] = df["degree"].where(df["degree"].astype(str).str.len().gt(0), deg_series)

    mask = df["name"].astype(str).str.match(r"(?i)^profile")
    df.loc[mask, "name"] = df.loc[mask, "url"].map(_slug_to_name).fillna(df.loc[mask, "name"])

    return df

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python quick_clean.py <in_csv> <out_csv>")
        raise SystemExit(1)
    _in, _out = sys.argv[1], sys.argv[2]
    _df = pd.read_csv(_in)
    _df = clean_df(_df)
    _df.to_csv(_out, index=False)
    print(f"Wrote {_out}")
