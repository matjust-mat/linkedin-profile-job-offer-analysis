# Output CSV columns:
# name,age,phone,email,address,degree,years_experience,skills,soft_skills,languages,profile_text,url
# PT/EN aware. Robust against noisy PDFs. Tuned for LinkedIn "Save as PDF" layout.

import re, os, sys, glob, argparse
import pandas as pd
from pdfminer.high_level import extract_text

# ---------------- vocab ----------------
HARD_SKILLS = [
    # general
    "software development", "graphic design", "ui design", "ux design",
    # backend
    "java", "spring", "spring boot", "quarkus", "hibernate", "jpa",
    "kotlin", "scala", "python", "django", "flask", "fastapi",
    "node", "node.js", "express", "nestjs", "go", "golang", "c++", "c#",
    ".net", "asp.net", "php", "laravel", "symfony", "ruby", "rails",
    # frontend
    "javascript", "typescript", "react", "next.js", "angular", "vue",
    # data
    "sql", "postgresql", "mysql", "mariadb", "sql server", "oracle",
    "mongodb", "redis", "kafka", "spark", "hadoop",
    # devops
    "docker", "kubernetes", "helm", "aws", "gcp", "azure",
    "terraform", "ansible", "github actions", "gitlab ci", "ci/cd",
]

HARD_SKILLS = [s for s in HARD_SKILLS if len(s) > 1]

SOFT_SKILLS = [
    "communication","teamwork","leadership","problem solving","critical thinking",
    "adaptability","flexibility","ownership","proactivity","creativity",
    "time management","negotiation","empathy","collaboration","conflict resolution",
    "decision making","attention to detail","organization","resilience",
    # PT
    "comunicação","trabalho em equipe","liderança","resolução de problemas",
    "pensamento crítico","adaptabilidade","flexibilidade","senso de dono",
    "proatividade","criatividade","gestão do tempo","negociação","empatia",
    "colaboração","resolução de conflitos","tomada de decisão","atenção aos detalhes",
    "organização","resiliência",
]

LANG_MAP = {
    "english":"english","inglês":"english","ingles":"english",
    "portuguese":"portuguese","português":"portuguese","portugues":"portuguese",
    "spanish":"spanish","espanhol":"spanish","español":"spanish",
    "french":"french","francês":"french","frances":"french","francés":"french",
    "german":"german","alemão":"german","alemao":"german",
    "italian":"italian","italiano":"italian",
    "japanese":"japanese","japonês":"japanese","japones":"japanese",
    "chinese":"chinese","chinês":"chinese","chines":"chinese","mandarin":"chinese","mandarim":"chinese",
    "korean":"korean","coreano":"korean",
    "russian":"russian","russo":"russian",
    "arabic":"arabic","árabe":"arabic","arabe":"arabic",
    "hindi":"hindi",
}
LEVEL_ALIASES = {
    "native": ["native","nativo","língua materna","lingua materna","mother tongue"],
    "fluent": ["fluent","fluente","full professional","profissional completo"],
    "advanced": ["advanced","avançado","avancado","c2","c1","upper intermediate"],
    "intermediate": ["intermediate","intermediário","intermediario","b2","b1"],
    "professional": ["professional working","profissional"],
    "basic": ["basic","básico","basico","beginner","iniciante","a2","a1","limited"],
}
LEVEL_RANK = {"":0,"basic":1,"professional":2,"intermediate":3,"advanced":4,"fluent":5,"native":6}

COUNTRIES = [
    "brazil","brasil","portugal","spain","españa","argentina","chile","uruguay","paraguay",
    "bolivia","peru","colombia","mexico","united states","usa","canada","germany","france","italy",
]
COUNTRY_RE = re.compile(r"\b(" + "|".join(COUNTRIES) + r")\b", re.I)

# ---------------- regex ----------------
EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
# BR-friendly phone. Require 10–15 digits. Ignore things inside URLs.
PHONE_DIGITS_RE = re.compile(r"(?:\+?\d[\d\-\s\(\)]{8,}\d)")
LINKEDIN_URL_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/[^\s)]+", re.I)

DEGREE_LINE_RE = re.compile(
    r"(Bachelor[^,\n]*|Master[^,\n]*|MBA[^,\n]*|B\.Tech[^,\n]*|Tecnólogo[^,\n]*|Bacharel[^,\n]*|Licenciatura[^,\n]*|Mestrado[^,\n]*|Doutor[^,\n]*)",
    re.I,
)

YEARS_YM_RE = re.compile(r"(\d{1,2})\s+years?\s+(\d{1,2})\s+months?", re.I)
YEARS_PT_YM_RE = re.compile(r"(\d{1,2})\s+anos?\s+(\d{1,2})\s+meses?", re.I)
YEARS_SIMPLE_RE = re.compile(r"(\d{1,2})(?:[.,](\d))?\s*(?:years?|anos?)", re.I)

SECTION_STOP = re.compile(r"^(experience|experiência|education|formação|about|summary|resumo)\b", re.I)
NAME_LINE_RE = re.compile(r"^[A-ZÁÉÍÓÚÂÊÔÃÕÄËÏÖÜ][A-Za-zÀ-ÿ'’´`\-]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÄËÏÖÜ][A-Za-zÀ-ÿ'’´`\-]+){1,4}$")

LANG_TOKEN_RE = re.compile(r"\b(" + "|".join(map(re.escape, LANG_MAP.keys())) + r")\b", re.I)

# ---------------- helpers ----------------
def norm(s: str) -> str:
    return " ".join(str(s or "").split())

def lines(txt: str):
    return [l.strip() for l in txt.splitlines() if l.strip()]

def first_match(rex, text, default=""):
    m = rex.search(text)
    return m.group(0) if m else default

def clean_urls(text: str) -> str:
    return LINKEDIN_URL_RE.sub("", text)

def extract_email(text: str) -> str:
    return first_match(EMAIL_RE, text)

def extract_linkedin_url(text: str) -> str:
    cleaned = text.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"-\s+", "-", cleaned)
    m = re.search(r"(https?://(?:www\.)?linkedin\.com/in/[^\s)\/]{3,}[^\s)]*)", cleaned, re.I)
    if m: return m.group(1).rstrip(").,;")
    m = re.search(r"((?:www\.)?linkedin\.com/in/[^\s)\/]{3,}[^\s)]*)", cleaned, re.I)
    return ("https://" + m.group(1).rstrip(").,;")) if m else ""

def extract_phone(text: str) -> str:
    t = LINKEDIN_URL_RE.sub(" ", text)
    candidates = []
    for m in PHONE_DIGITS_RE.finditer(t):
        digits = re.sub(r"\D", "", m.group(0))
        if 10 <= len(digits) <= 15:
            candidates.append(digits)
    if not candidates:
        return ""
    d = candidates[0]
    if len(d) in (10,11):
        dd, rest = d[:2], d[2:]
        if len(rest) == 9:
            return f"+55 ({dd}) {rest[:5]}-{rest[5:]}"
        elif len(rest) == 8:
            return f"+55 ({dd}) {rest[:4]}-{rest[4:]}"
    return d

def extract_address(text_lines: list[str], full_text: str) -> str:
    m = re.search(
        r"([A-ZÁÂÃÉÍÓÚ][\wÀ-ÿ .'-]+,\s*[A-ZÁÂÃÉÍÓÚ][\wÀ-ÿ .'-]+,\s*(?:Brasil|Brazil|Portugal|Spain|España))",
        full_text, re.I)
    if m:
        return ", ".join(p.strip() for p in m.group(1).split(","))
    for l in text_lines:
        if COUNTRY_RE.search(l) and "," in l and 8 <= len(l) <= 120:
            return ", ".join(p.strip() for p in l.split(","))
    return ""

def canonical_level(raw: str) -> str:
    if not raw:
        return ""
    r = raw.lower()
    for k, variants in LEVEL_ALIASES.items():
        for v in variants:
            if v in r:
                return k
    return ""

def extract_languages(text: str) -> dict:
    langs = {}
    block = text
    m = re.search(r"(languages|idiomas)\s*[:\-]?\s*(.+)", text, re.I | re.S)
    if m:
        block = m.group(2)
    toks = block.split()
    low = [t.lower() for t in toks]
    for i, tok in enumerate(low):
        if tok not in LANG_MAP:
            continue
        lang = LANG_MAP[tok]
        window = " ".join(low[i+1:i+8])
        lvl = canonical_level(window)
        prev = langs.get(lang, "")
        rank_new = LEVEL_RANK.get(lvl, 0)
        rank_old = LEVEL_RANK.get(prev, 0)
        if rank_new > rank_old:
            langs[lang] = lvl or prev
        else:
            langs.setdefault(lang, prev)
    return langs

def extract_degree(full_text: str) -> str:
    sec = re.search(r"(education|formação)\b\s*(.+)", full_text, re.I | re.S)
    block = sec.group(2) if sec else full_text
    best = ""
    for l in lines(block):
        if SECTION_STOP.match(l): break
        if re.search(r"(wise up|ingl[eê]s|english course)", l, re.I): 
            continue
        if re.search(r"(bachelor|master|mba|b\.?tech|bacharel|licenciatura|mestrado|doutor)", l, re.I):
            cand = l.strip()
            if "page" in cand.lower(): 
                continue
            if 15 <= len(cand) <= 140 and len(cand) > len(best):
                best = cand
    return best

def extract_years(full_text: str) -> str:
    m = YEARS_YM_RE.search(full_text) or YEARS_PT_YM_RE.search(full_text)
    if m:
        y = int(m.group(1)); mo = int(m.group(2))
        val = round(y + mo/12.0, 1)
        return str(val).rstrip("0").rstrip(".")
    m2 = YEARS_SIMPLE_RE.search(full_text)
    if m2:
        y = int(m2.group(1))
        frac = m2.group(2)
        if frac:
            return f"{y}.{frac}"
        return str(y)
    return ""

def tokenize(text: str):
    return re.findall(r"[a-zA-ZÀ-ÿ0-9\.\+\#]+", text.lower())

def contains_phrase(text_lc: str, phrase: str) -> bool:
    p = re.escape(phrase.lower())
    p = p.replace("\\ ", r"\s+")
    return re.search(rf"(?<![A-Za-z0-9#\+]){p}(?![A-Za-z0-9#\+])", text_lc) is not None

def extract_skills(full_text: str):
    t = full_text.lower()
    hard = sorted({s for s in HARD_SKILLS if contains_phrase(t, s)})
    soft = sorted({s for s in SOFT_SKILLS if contains_phrase(t, s)})
    m = re.search(r"top\s+skills\s*(.+?)(?:experience|education|formação|experiência|\Z)", full_text, re.I | re.S)
    if m:
        blob = m.group(1).lower()
        for token in re.split(r"[,\n•\-\u2022]", blob):
            tok = token.strip()
            if 2 <= len(tok) <= 40:
                if tok in SOFT_SKILLS and tok not in soft:
                    soft.append(tok)
                if tok in HARD_SKILLS and tok not in hard:
                    hard.append(tok)
    return sorted(hard), sorted(soft)

def strip_boilerplate(text: str) -> str:
    t = text
    t = re.sub(r"(contact|contato)\b.*?(?=(experience|experiência|education|formação)\b)", "", t, flags=re.I | re.S)
    t = re.sub(r"\btop\s+skills\b.*?(?=\n|$)", "", t, flags=re.I)
    t = LINKEDIN_URL_RE.sub("", t)
    t = EMAIL_RE.sub("", t)
    return norm(t)

def name_from_email(email: str) -> str:
    if not email: return ""
    local = email.split("@",1)[0]
    local = re.sub(r"\d+", " ", local)
    parts = re.split(r"[._\-]+", local)
    parts = [p for p in parts if p and len(p) > 1]
    if len(parts) >= 2:
        return " ".join(w.capitalize() for w in parts[:4])
    return ""

def name_from_url(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"/in/([^/?#]+)", url)
    if not m:
        return ""
    slug = m.group(1)
    slug = re.sub(r"-\d{4,}$", "", slug)
    name = slug.replace("-", " ").strip()
    return " ".join(w.capitalize() for w in name.split())

def name_from_url(url: str) -> str:
    m = re.search(r"/in/([^/?#]+)", url or "")
    if not m: return ""
    slug = re.sub(r"-\d{3,}$", "", m.group(1))
    return " ".join(w.capitalize() for w in slug.replace("-", " ").split())

def extract_name(text_lines: list[str], url_hint: str = "") -> str:
    for l in text_lines[:150]:
        m = re.match(r"^([A-ZÁÉÍÓÚÂÊÔÃÕÄËÏÖÜ][\wÀ-ÿ'’´`\-]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÄËÏÖÜ][\wÀ-ÿ'’´`\-]+){1,3})\s+"
                     r"(?:Student|Developer|Engineer|Designer|Software|Estudante|Desenvolvedor|Engenheiro)\b", l, re.I)
        if m: return m.group(1)
    for l in text_lines[:300]:
        if NAME_LINE_RE.match(l) and not re.search(r"(developer|student|engineer|designer)", l, re.I):
            return l
    return name_from_url(url_hint)

def extract_age(text: str) -> str:
    m = re.search(r"\b(?:idade|age)\s*[:\-]?\s*(\d{1,2})\b", text, re.I)
    return m.group(1) if m else ""

# ---------------- core ----------------
def parse_pdf(path: str) -> dict:
    try:
        raw = extract_text(path)
    except Exception as e:
        raw = f"[PDF read error: {e}]"
    raw = raw.replace("\x00", " ")
    text = norm(raw)
    text_lines = lines(text)

    email = extract_email(text)
    phone = extract_phone(text)
    address = extract_address(text_lines, text)
    url = extract_linkedin_url(text)
    name = extract_name(text_lines, url_hint=url)
    if not name or name.lower().startswith("profile"):
        name = name_from_url(url) or name_from_email(email) or name or os.path.splitext(os.path.basename(path))[0]

    degree = extract_degree(text)
    years = extract_years(text)
    hard, soft = extract_skills(text)
    langs = extract_languages(text)
    langs_str = "; ".join(f"{k}: {v or 'unspecified'}" for k, v in sorted(langs.items()))

    age = extract_age(text)

    prof = strip_boilerplate(text)
    prof = prof[:5000]

    return {
        "name": name,
        "age": age,
        "phone": phone,
        "email": email,
        "address": address,
        "degree": degree,
        "years_experience": years,
        "skills": ", ".join(hard),
        "soft_skills": ", ".join(soft),
        "languages": langs_str,
        "profile_text": prof,
        "url": url or "",
    }

# -------------- IO --------------
def iter_pdf_paths(in_dir: str, pattern: str):
    pats = [pattern]
    if pattern.lower().endswith(".pdf"):
        pats.append(pattern[:-4] + ".PDF")
    for p in pats:
        for path in glob.glob(os.path.join(in_dir, p)):
            yield path

def run(in_dir: str, out_csv: str, pattern: str):
    rows = []
    count = 0
    for path in iter_pdf_paths(in_dir, pattern):
        count += 1
        rows.append(parse_pdf(path))
    df = pd.DataFrame(rows)
    cols = ["name","age","phone","email","address","degree","years_experience",
            "skills","soft_skills","languages","profile_text","url"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    df.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv} with {len(df)} rows from {count} files matched by pattern '{pattern}'")

# -------------- cli --------------
def main():
    ap = argparse.ArgumentParser(description="Ingest LinkedIn-like profile PDFs into CSV.")
    ap.add_argument("pdf_dir")
    ap.add_argument("out_csv")
    ap.add_argument("--pattern", default="*.pdf", help='e.g. "Profile*.pdf"')
    args = ap.parse_args()
    run(args.pdf_dir, args.out_csv, args.pattern)

if __name__ == "__main__":
    main()
