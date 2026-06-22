import pandas as pd
import numpy as np

COLS_MOYENNE = [
    'V.E.', 'VO2', 'VCO2', 'Q.R.', 'Eq O2', 'VE/VCO2',
    'PetO2', 'PetCO2', 'F.R.', 'Vt', 'Rés Ven', 'Ti', 'Ttot', 'Ti/Ttot', 'Vt/Ti',
]


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
