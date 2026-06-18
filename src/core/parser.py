import pandas as pd
from pathlib import Path
import pdfplumber
import re
import json

CONFIG_PATH = Path("config.json")


def _clean_text(txt: str) -> str:
    """Même nettoyage que CleanText() du VBA : supprime chr(160) et 'Â'."""
    return txt.replace("Â", "").replace("\xa0", "").strip()

COLONNES_DEFAUT = [
    'Temps', 'V.E.', 'VO2', 'VCO2', 'Q.R.', 'Eq O2',
    'VE/VCO2', 'PetO2', 'PetCO2', 'F.R.', 'Vt', 'Rés Ven',
    'Ti', 'Ttot', 'Ti/Ttot', 'Vt/Ti', 'FiO2', 'FiCO2', 'Réf VO2'
]

FORMAT_DEFAUT = {
    "nom": "COSMED K5",
    "delimiteur": "¦",
    "marqueur_header": "temps",
    "marqueur_debut": "examen complet",
    "regex_premiere_colonne": r"^\d{2}:\d{2}$"
}


def charger_ordre() -> list:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
            return data.get('ordre_colonnes', COLONNES_DEFAUT)
        except Exception:
            pass
    return COLONNES_DEFAUT.copy()


def charger_formats() -> list:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
            formats = data.get('formats', [])
            if formats:
                return formats
        except Exception:
            pass
    return [FORMAT_DEFAUT.copy()]


def parse_vo2_file(filepath: str) -> pd.DataFrame:
    ext = Path(filepath).suffix.lower()
    if ext == '.pdf':
        lines = _read_pdf(filepath)
    else:
        lines = Path(filepath).read_text(encoding='utf-8', errors='replace').splitlines()

    formats = charger_formats()
    last_error = None
    for fmt in formats:
        try:
            return _parse_lines(lines, fmt)
        except ValueError as e:
            last_error = e
            continue

    raise ValueError(f"Aucun format compatible trouvé. Dernier essai : {last_error}")


def _read_pdf(filepath: str) -> list:
    lines = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(text.splitlines())
    return lines


def _parse_lines(lines: list, fmt: dict) -> pd.DataFrame:
    delimiteur = fmt.get("delimiteur", "¦")
    marqueur_header = fmt.get("marqueur_header", "temps").lower()
    marqueur_debut = fmt.get("marqueur_debut", "examen complet").lower()
    regex_col0 = fmt.get("regex_premiere_colonne", r"^\d{2}:\d{2}$")

    # Trouver la ligne des headers
    header_line = None
    for line in lines:
        if marqueur_header in line.lower() and delimiteur in line:
            header_line = line
            break

    if header_line is None:
        raise ValueError(f"Impossible de trouver l'en-tête (marqueur='{marqueur_header}', délimiteur='{delimiteur}')")

    headers = [_clean_text(h) for h in header_line.split(delimiteur) if _clean_text(h)]

    # Trouver le début des données
    start_index = None
    for i, line in enumerate(lines):
        if marqueur_debut in line.lower():
            start_index = i + 1
            break

    if start_index is None:
        raise ValueError(f"Impossible de trouver le début des données (marqueur='{marqueur_debut}')")

    # Parser les lignes de données
    rows = []
    for line in lines[start_index:]:
        if not line.strip():
            continue
        if delimiteur not in line:
            continue
        parts = [p.strip() for p in line.split(delimiteur)]
        parts_clean = [p for p in parts if p != '']
        if not parts_clean:
            continue
        if not re.match(regex_col0, parts_clean[0]):
            continue
        while len(parts_clean) < len(headers):
            parts_clean.append('')
        rows.append(parts_clean[:len(headers)])

    if not rows:
        raise ValueError("Aucune ligne de données trouvée avec ce format")

    df = pd.DataFrame(rows, columns=headers)

    # Convertir les colonnes numériques
    for col in df.columns:
        serie = df[col].astype(str).str.strip()
        serie = serie.str.replace(',', '.', regex=False)
        converted = pd.to_numeric(serie, errors='coerce')
        if converted.notna().mean() > 0.5:
            df[col] = converted

    # Réordonner selon la config sauvegardée
    ordre = charger_ordre()
    colonnes_ordonnees = [c for c in ordre if c in df.columns]
    colonnes_extra = [c for c in df.columns if c not in ordre]
    df = df[colonnes_ordonnees + colonnes_extra]

    return df
