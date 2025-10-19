import math, re
import pandas as pd

def _to_set(s):
    return {t.strip().lower() for t in str(s or "").replace(";", ",").split(",") if t.strip()}

def _text_tokens(s):
    return set(re.findall(r"[a-zA-ZÀ-ÿ0-9\+\#\.]{2,}", str(s or "").lower()))

def _jacc(a, b):
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def _parse_years(x):
    try:
        v = float(str(x).replace(",", "."))
        if math.isfinite(v): return max(v, 0.0)
    except Exception:
        pass
    return 0.0

def _has_all(have: set, need: set):
    missing = sorted([n for n in need if n not in have])
    return (len(missing) == 0, missing)

def _normalize_langs(s: str):
    langs = {}
    for part in str(s or "").split(";"):
        k, *rest = part.split(":")
        k = k.strip().lower()
        v = ":".join(rest).strip().lower() if rest else ""
        if k:
            langs[k] = v or "unspecified"
    return langs

def score_df(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    req        = _to_set(cfg.get("req"))
    nice       = _to_set(cfg.get("nice"))
    soft_req   = _to_set(cfg.get("soft_req"))
    soft_nice  = _to_set(cfg.get("soft_nice"))
    notes      = _to_set(cfg.get("notes"))
    want_langs = _to_set(cfg.get("langs"))
    min_years  = float(cfg.get("min_years") or 0.0)
    want_degree= str(cfg.get("degree") or "").lower()

    rows = []
    for _, row in df.iterrows():
        hard = _to_set(row.get("skills"))
        soft = _to_set(row.get("soft_skills"))
        years = _parse_years(row.get("years_experience"))
        degree_txt = str(row.get("degree") or "").lower()
        prof_txt = str(row.get("profile_text") or "").lower()
        words = _text_tokens(prof_txt) | hard | soft
        langs_map = _normalize_langs(row.get("languages"))
        langs_have = set(langs_map.keys())

        ok_req, miss_req = _has_all(hard, req)
        sim_nice = _jacc(hard, nice)
        ok_soft, miss_soft = _has_all(soft, soft_req)
        sim_soft = _jacc(soft, soft_nice)
        exp_score = min(years / min_years, 1.0) if min_years > 0 else 1.0
        deg_ok = True if not want_degree else (want_degree in degree_txt)
        notes_hit = _jacc(words, notes) if notes else 1.0
        langs_ok, miss_langs = _has_all(langs_have, want_langs) if want_langs else (True, [])
        langs_bonus = _jacc(langs_have, want_langs) if want_langs else 1.0

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
        reasons.append(f"experiência: {(_parse_years(row.get('years_experience')))} de {min_years} anos")
        reasons.append("grau: ok" if deg_ok else "grau: não evidenciado")
        if notes: reasons.append(f"observações: {int(notes_hit*100)}%")
        if want_langs:
            reasons.append("idiomas: ok" if langs_ok else f"idiomas faltando: {', '.join(miss_langs)}")

        rows.append({**row.to_dict(), "score": score, "motivo": "; ".join(reasons)})

    out = pd.DataFrame(rows).sort_values("score", ascending=False)
    return out.reset_index(drop=True)