# Inputs: candidates_clean.csv from your pipeline
# Output: results.csv with scores and reasons
# Fields used: name, age, phone, email, address, degree, years_experience, skills, soft_skills, languages, profile_text, url

import argparse, math, re
import pandas as pd

def to_set(s):
    return {t.strip().lower() for t in str(s or "").replace(";", ",").split(",") if t.strip()}

def text_tokens(s):
    return set(re.findall(r"[a-zA-ZÀ-ÿ0-9\+\#\.]{2,}", str(s or "").lower()))

def jacc(a, b):
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def parse_years(x):
    try:
        v = float(str(x).replace(",", "."))
        if math.isfinite(v): return max(v, 0.0)
    except Exception:
        pass
    return 0.0

def has_all(have: set, need: set):
    missing = sorted([n for n in need if n not in have])
    return (len(missing) == 0, missing)

def normalize_langs(s: str):
    langs = {}
    for part in str(s or "").split(";"):
        k, *rest = part.split(":")
        k = k.strip().lower()
        v = ":".join(rest).strip().lower() if rest else ""
        if k:
            langs[k] = v or "unspecified"
    return langs

def score_row(row, cfg):
    hard = to_set(row.get("skills"))
    soft = to_set(row.get("soft_skills"))
    years = parse_years(row.get("years_experience"))
    degree_txt = str(row.get("degree") or "").lower()
    prof_txt = str(row.get("profile_text") or "").lower()
    words = text_tokens(prof_txt) | hard | soft
    langs_map = normalize_langs(row.get("languages"))
    langs_have = set(langs_map.keys())

    req = to_set(cfg.req)
    nice = to_set(cfg.nice)
    soft_req = to_set(cfg.soft_req)
    soft_nice = to_set(cfg.soft_nice)
    notes = to_set(cfg.notes)
    want_langs = to_set(cfg.langs)
    min_years = cfg.min_years
    want_degree = str(cfg.degree or "").lower()

    ok_req, miss_req = has_all(hard, req)
    sim_nice = jacc(hard, nice)
    ok_soft, miss_soft = has_all(soft, soft_req)
    sim_soft = jacc(soft, soft_nice)
    exp_score = min(years / min_years, 1.0) if min_years > 0 else 1.0
    deg_ok = True if not want_degree else (want_degree in degree_txt)
    notes_hit = jacc(words, notes) if notes else 1.0
    langs_ok, miss_langs = has_all(langs_have, want_langs) if want_langs else (True, [])
    langs_bonus = jacc(langs_have, want_langs) if want_langs else 1.0

    w_req_hard   = 0.32
    w_nice_hard  = 0.12
    w_req_soft   = 0.12
    w_nice_soft  = 0.06
    w_exp        = 0.18
    w_degree     = 0.08
    w_notes      = 0.06
    w_langs      = 0.06

    base = (
        w_req_hard  * (1.0 if ok_req  else 0.0) +
        w_nice_hard *  sim_nice +
        w_req_soft  * (1.0 if ok_soft else 0.0) +
        w_nice_soft *  sim_soft +
        w_exp       *  exp_score +
        w_degree    * (1.0 if deg_ok  else 0.0) +
        w_notes     *  notes_hit +
        w_langs     * (langs_bonus if langs_ok else 0.0)
    )

    if req and not ok_req: base *= 0.45
    if soft_req and not ok_soft: base *= 0.85

    score = round(base * 100, 1)

    reasons = []
    reasons.append("obrigatórios: ok" if ok_req else f"faltam obrigatórios: {', '.join(miss_req)}")
    if nice: reasons.append(f"desejáveis: {int(sim_nice*100)}%")
    reasons.append("soft req: ok" if ok_soft else (f"faltam soft: {', '.join(miss_soft)}" if soft_req else "soft req: n/a"))
    if soft_nice: reasons.append(f"soft desejáveis: {int(sim_soft*100)}%")
    reasons.append(f"experiência: {years} de {min_years} anos")
    reasons.append("grau: ok" if deg_ok else "grau: não evidenciado")
    if notes: reasons.append(f"observações: {int(notes_hit*100)}%")
    if want_langs:
        reasons.append("idiomas: ok" if langs_ok else f"idiomas faltando: {', '.join(miss_langs)}")

    return score, "; ".join(reasons)

def main():
    p = argparse.ArgumentParser(description="Score candidates against a job spec.")
    p.add_argument("--in_csv", required=True)
    p.add_argument("--out_csv", required=True)
    p.add_argument("--degree", default="")
    p.add_argument("--req", default="")          
    p.add_argument("--nice", default="")         
    p.add_argument("--soft_req", default="")    
    p.add_argument("--soft_nice", default="")   
    p.add_argument("--langs", default="")       
    p.add_argument("--min_years", type=float, default=0.0)
    p.add_argument("--notes", default="")     
    args = p.parse_args()

    df = pd.read_csv(args.in_csv)
    rows = []
    for _, r in df.iterrows():
        s, why = score_row(r, args)
        rows.append({**r.to_dict(), "score": s, "motivo": why})

    out = pd.DataFrame(rows).sort_values("score", ascending=False)
    out.to_csv(args.out_csv, index=False)

    cols = ["name", "score", "motivo"]
    print(out[cols].head(5).to_string(index=False))

if __name__ == "__main__":
    main()
