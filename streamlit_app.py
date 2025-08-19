\
import streamlit as st
import pandas as pd
from io import BytesIO
from typing import List, Dict, Any, Tuple
from rapidfuzz import fuzz, process
from PyPDF2 import PdfReader
from unidecode import unidecode

st.set_page_config(page_title="Recherche Concours Maître de Conférences", layout="wide")

st.title("🔎 Recherche Concours – Maître de Conférences / OFPPT")
st.write("Chargez les **résultats (PDF/CSV/XLSX/JSON)** puis recherchez par **Nom** ou **CIN**. "
         "L'appli effectue une recherche **approfondie** (exacte, partielle et floue) et affiche les **occurrences** avec **pages** et **extraits** pour les PDF.")

with st.expander("ℹ️ Conseils d'utilisation", expanded=False):
    st.markdown("""
    - **Étape 1** : Chargez les documents officiels (PDF des résultats, CSV/Excel publiés, exports JSON).
    - **Étape 2** : Saisissez le **Nom** (ex. *Mamouni Abdelaziz*) ou le **CIN** (ex. *AB123456*).
    - **Étape 3** : Ajustez la **sensibilité** (seuil de similarité floue) si nécessaire.
    - **Étape 4** : Consultez les **résultats** (tableaux filtrés + occurrences dans les PDF avec pages et contextes).
    """)

# --- Utils ---
def normalize(s: str) -> str:
    if s is None:
        return ""
    return unidecode(s).lower().strip()

def read_pdf(file) -> Dict[str, Any]:
    reader = PdfReader(file)
    pages_text = []
    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        pages_text.append(t)
    return {"n_pages": len(pages_text), "pages_text": pages_text}

def find_occurrences(text: str, query: str, window: int = 80) -> List[str]:
    out = []
    qn = normalize(query)
    tn = normalize(text)
    idx = 0
    while True:
        pos = tn.find(qn, idx)
        if pos == -1:
            break
        start = max(0, pos - window)
        end = min(len(text), pos + len(query) + window)
        snippet = text[start:end].replace("\n", " ")
        out.append(snippet)
        idx = pos + len(qn)
    return out

def load_tabular(file) -> pd.DataFrame:
    name = file.name.lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(file)
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(file)
        elif name.endswith(".json"):
            df = pd.read_json(file)
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()
    # Harmonize columns
    cols = {c.lower().strip(): c for c in df.columns}
    def first_match(cands):
        for c in cands:
            if c in cols:
                return cols[c]
        return None
    col_nom = first_match(["nom", "name", "full_name", "candidate", "candidat"])
    col_cin = first_match(["cin", "id", "numero_cin", "cnie"])
    col_uni = first_match(["universite", "université", "university", "etablissement", "établissement"])
    col_spec = first_match(["specialite", "spécialité", "specialty", "discipline"])
    col_res = first_match(["resultat", "résultat", "status", "etat", "issue"])
    # Build normalized frame
    out = pd.DataFrame({
        "nom": df[col_nom] if col_nom else None,
        "cin": df[col_cin] if col_cin else None,
        "universite": df[col_uni] if col_uni else None,
        "specialite": df[col_spec] if col_spec else None,
        "resultat": df[col_res] if col_res else None,
        "source": file.name
    })
    return out

# --- Sidebar inputs ---
with st.sidebar:
    st.header("Paramètres de recherche")
    name_query = st.text_input("Nom (ex. Mamouni Abdelaziz)")
    cin_query = st.text_input("CIN (ex. AB123456)")
    fuzzy_threshold = st.slider("Seuil de similarité floue (0-100)", min_value=60, max_value=100, value=85, step=1)
    st.caption("👉 Plus le seuil est élevé, plus la correspondance est stricte.")
    st.markdown("---")
    st.subheader("Importer les résultats")
    uploads = st.file_uploader(
        "Déposez les fichiers de résultats (PDF, CSV, XLSX, JSON)",
        type=["pdf", "csv", "xlsx", "xls", "json"],
        accept_multiple_files=True
    )

# Storage
pdf_docs = []
tables = []

if uploads:
    for up in uploads:
        if up.name.lower().endswith(".pdf"):
            with st.spinner(f"Lecture du PDF « {up.name} »..."):
                pdf_docs.append((up.name, read_pdf(up)))
        else:
            df = load_tabular(up)
            if not df.empty:
                tables.append(df.assign(source=up.name))

# Aggregate tabular data
tabular_df = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=["nom","cin","universite","specialite","resultat","source"])

# --- Search logic ---
def search_tabular(df: pd.DataFrame, name_q: str, cin_q: str, thr: int) -> pd.DataFrame:
    if df.empty:
        return df
    df2 = df.copy()
    df2["_nom_norm"] = df2["nom"].astype(str).map(normalize)
    df2["_cin_norm"] = df2["cin"].astype(str).map(normalize)
    matches = pd.Series([True]*len(df2))
    if name_q:
        nn = normalize(name_q)
        exact = df2["_nom_norm"] == nn
        contains = df2["_nom_norm"].str.contains(nn, na=False)
        fuzzy_scores = df2["_nom_norm"].map(lambda s: fuzz.partial_ratio(s, nn) if isinstance(s, str) else 0)
        fuzzy = fuzzy_scores >= thr
        name_match = exact | contains | fuzzy
        matches &= name_match
        df2["score_nom"] = fuzzy_scores
    if cin_q:
        cn = normalize(cin_q)
        cin_match = (df2["_cin_norm"] == cn) | (df2["_cin_norm"].str.contains(cn, na=False))
        matches &= cin_match
    out = df2.loc[matches, ["nom","cin","universite","specialite","resultat","source"] + (["score_nom"] if name_q else [])]
    return out.sort_values(by=["score_nom"] if "score_nom" in out.columns else out.columns.tolist(), ascending=False)

def search_pdfs(pdf_list: List[Tuple[str, Dict[str,Any]]], query: str) -> List[Dict[str, Any]]:
    results = []
    if not query:
        return results
    for fname, doc in pdf_list:
        for i, page_text in enumerate(doc["pages_text"], start=1):
            snippets = find_occurrences(page_text, query, window=90)
            for snip in snippets:
                results.append({
                    "fichier": fname,
                    "page": i,
                    "extrait": snip
                })
    return results

tab_hits = search_tabular(tabular_df, name_query, cin_query, fuzzy_threshold)
pdf_hits_name = search_pdfs(pdf_docs, name_query) if name_query else []
pdf_hits_cin = search_pdfs(pdf_docs, cin_query) if cin_query else []

# --- UI Results ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Résultats structurés (CSV/Excel/JSON)")
    st.caption("Correspondances trouvées dans les fichiers tabulaires importés.")
    st.dataframe(tab_hits, use_container_width=True, hide_index=True)

    if not tab_hits.empty:
        csv = tab_hits.to_csv(index=False).encode("utf-8")
        st.download_button("Télécharger les résultats (CSV)", data=csv, file_name="resultats_recherche.csv", mime="text/csv")

with col2:
    st.subheader("🧭 Occurrences dans les PDF")
    if name_query:
        st.markdown("**Correspondances par _Nom_ dans les PDF**")
        if pdf_hits_name:
            st.write(pd.DataFrame(pdf_hits_name))
        else:
            st.info("Aucune occurrence trouvée pour le **nom** dans les PDF.")
    if cin_query:
        st.markdown("**Correspondances par _CIN_ dans les PDF**")
        if pdf_hits_cin:
            st.write(pd.DataFrame(pdf_hits_cin))
        else:
            st.info("Aucune occurrence trouvée pour le **CIN** dans les PDF.")

# Footer
st.markdown("---")
st.caption("💡 Astuce : pour améliorer la détection, assurez-vous que les PDF contiennent bien du texte (et non des images scannées).")

