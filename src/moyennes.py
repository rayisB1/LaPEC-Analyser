import pandas as pd
import numpy as np

COLS_MOYENNE = [
    'V.E.', 'VO2', 'VCO2', 'Q.R.', 'Eq O2', 'VE/VCO2',
    'PetO2', 'PetCO2', 'F.R.', 'Vt', 'Rés Ven', 'Ti', 'Ttot', 'Ti/Ttot', 'Vt/Ti',
]

# Colonnes calculées en plus des moyennes (clé stats -> libellé affiché)
COLS_CV = [('cv_vo2', 'CV VO2'), ('cv_peto2', 'CV PetO2')]

# Blocs de méthode pour le résumé : (clé dans calculer_moyennes, préfixe colonne)
BLOCS_RESUME = [
    ('last4', 'last4'),
    ('stable_vo2', 'stabV'),
    ('stable_peto2', 'stabPet'),
    ('vo2_min', 'vo2Min'),
]

RMR_LABELS = {
    'last4': 'last4 RMR',
    'stable_vo2': 'stabV RMR',
    'stable_peto2': 'stabP RMR',
    'vo2_min': 'vo2Min RMR',
}


def calculer_moyennes(df: pd.DataFrame) -> dict | None:
    """
    Reproduit Sub MoyennageVO2 : calcule les 3 périodes de référence.
    Retourne None si les données sont insuffisantes.
    """
    if 'F.R.' not in df.columns:
        return None

    fr = pd.to_numeric(df['F.R.'], errors='coerce').dropna()
    if fr.empty:
        return None

    freq_moy = fr.mean()
    nb_lignes = max(10, round(freq_moy * 4))
    nb_lignes_1min = max(5, round(freq_moy * 1))
    n = len(df)

    # Dernières 4 minutes : exclut la dernière 1 min tampon
    ligne_fin = n - nb_lignes_1min
    ligne_debut = max(0, ligne_fin - nb_lignes)

    # Fenêtres stables
    best_i_vo2, best_j_vo2 = _find_stable_window(df, 'VO2', nb_lignes)
    best_i_pet, best_j_pet = _find_stable_window(df, 'PetO2', nb_lignes)

    # Fenêtre des 4 minutes les plus basses (VO2 minimal)
    best_i_vo2_min, best_j_vo2_min = _find_min_mean_window(df, 'VO2', nb_lignes)

    return {
        'freq_moy': round(float(freq_moy), 2),
        'nb_lignes': nb_lignes,
        'nb_lignes_1min': nb_lignes_1min,
        'last4': {
            'debut': ligne_debut,
            'fin': ligne_fin,
            'stats': _periode_stats(df, ligne_debut, ligne_fin),
        },
        'stable_vo2': None if best_i_vo2 is None else {
            'debut': best_i_vo2,
            'fin': best_j_vo2,
            'stats': _periode_stats(df, best_i_vo2, best_j_vo2),
        },
        'stable_peto2': None if best_i_pet is None else {
            'debut': best_i_pet,
            'fin': best_j_pet,
            'stats': _periode_stats(df, best_i_pet, best_j_pet),
        },
        'vo2_min': None if best_i_vo2_min is None else {
            'debut': best_i_vo2_min,
            'fin': best_j_vo2_min,
            'stats': _periode_stats(df, best_i_vo2_min, best_j_vo2_min),
        },
    }


def _periode_stats(df: pd.DataFrame, debut: int, fin: int) -> dict:
    """Moyennes et CV pour une plage de lignes."""
    sl = df.iloc[debut:fin]
    stats = {}
    for col in COLS_MOYENNE:
        vals = pd.to_numeric(sl.get(col, pd.Series(dtype=float)), errors='coerce').dropna()
        stats[col] = round(float(vals.mean()), 2) if len(vals) > 0 else None

    for col, key in [('VO2', 'cv_vo2'), ('PetO2', 'cv_peto2')]:
        vals = pd.to_numeric(sl.get(col, pd.Series(dtype=float)), errors='coerce').dropna()
        mean = vals.mean() if len(vals) > 0 else 0
        if len(vals) > 1 and mean != 0:
            stats[key] = round(float(vals.std() / mean), 4)
        else:
            stats[key] = None
    return stats


def _find_stable_window(df: pd.DataFrame, col: str, window: int):
    """
    Fenêtre de `window` lignes consécutives qui minimise le CV de `col`.
    Retourne (debut, fin) en indices df, ou (None, None).
    """
    if col not in df.columns or window <= 0:
        return None, None

    vals = pd.to_numeric(df[col], errors='coerce').to_numpy(dtype=float)
    n = len(vals)
    if n < window:
        return None, None

    best_cv = float('inf')
    best_i = None

    for i in range(n - window + 1):
        chunk = vals[i:i + window]
        valid = chunk[~np.isnan(chunk)]
        if len(valid) == 0:
            continue
        mean = valid.mean()
        if mean == 0:
            continue
        cv = valid.std() / mean
        if cv < best_cv:
            best_cv = cv
            best_i = i

    if best_i is None:
        return None, None
    return best_i, best_i + window


def deduire_visite(nom: str) -> int | None:
    """Déduit le numéro de visite à partir du nom de l'examen (-V1/-V2)."""
    if '-V2' in nom:
        return 2
    if '-V1' in nom:
        return 1
    return None


def calculer_rmr(stats: dict) -> float | None:
    """
    RMR (kcal/jour) via l'équation de Weir abrégée :
    RMR = (3.941 * VO2 + 1.106 * VCO2) * 1440, avec VO2/VCO2 en L/min.
    """
    vo2 = stats.get('VO2')
    vco2 = stats.get('VCO2')
    if vo2 is None or vco2 is None:
        return None
    return round((3.941 * vo2 + 1.106 * vco2) * 1440, 2)


def _find_min_mean_window(df: pd.DataFrame, col: str, window: int):
    """
    Fenêtre de `window` lignes consécutives qui minimise la moyenne de `col`.
    Retourne (debut, fin) en indices df, ou (None, None).
    """
    if col not in df.columns or window <= 0:
        return None, None

    vals = pd.to_numeric(df[col], errors='coerce').to_numpy(dtype=float)
    n = len(vals)
    if n < window:
        return None, None

    best_mean = float('inf')
    best_i = None

    for i in range(n - window + 1):
        chunk = vals[i:i + window]
        valid = chunk[~np.isnan(chunk)]
        if len(valid) == 0:
            continue
        mean = valid.mean()
        if mean < best_mean:
            best_mean = mean
            best_i = i

    if best_i is None:
        return None, None
    return best_i, best_i + window
