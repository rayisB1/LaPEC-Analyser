import pandas as pd

DEFAUTS = {
    "disc_VE": 5.0,
    "disc_TiTot": 0.25,
    "disc_Vt": 0.25,
    "seuil_VE_min": 3.0,
    "seuil_VE_max": 15.0,
    "seuil_TiTot_min": 0.2,
    "seuil_TiTot_max": 0.8,
}

COL_VE = "V.E."
COL_TITOT = "Ti/Ttot"
COL_VT = "Vt"
COL_TEMPS = "Temps"


def _cols_a_vider(df: pd.DataFrame) -> list:
    return [c for c in df.columns if c != COL_TEMPS]


def appliquer_filtre_discontinuite(
    df: pd.DataFrame,
    disc_VE: float = DEFAUTS["disc_VE"],
    disc_TiTot: float = DEFAUTS["disc_TiTot"],
    disc_Vt: float = DEFAUTS["disc_Vt"],
) -> pd.DataFrame:
    """
    Retourne un nouveau DataFrame.
    Vide la ligne i si |val[i] - val[i-1]| > seuil sur au moins un critère.
    Ne compare que des valeurs numériques (NaN ignorées).
    """
    result = df.copy()
    a_vider = _cols_a_vider(result)

    criterions = []
    if COL_VE in result.columns:
        criterions.append((COL_VE, disc_VE))
    if COL_TITOT in result.columns:
        criterions.append((COL_TITOT, disc_TiTot))
    if COL_VT in result.columns:
        criterions.append((COL_VT, disc_Vt))

    mask = pd.Series(False, index=result.index)
    for col, seuil in criterions:
        serie = pd.to_numeric(result[col], errors="coerce")
        diff = serie.diff().abs()
        # diff[i] = |val[i] - val[i-1]|; NaN diff → False (row not emptied)
        mask = mask | (diff > seuil)

    # Never empty the first row (diff is always NaN at index 0)
    if len(result) > 0:
        mask.iloc[0] = False

    result.loc[mask, a_vider] = None
    return result


def appliquer_filtre_seuils(
    df: pd.DataFrame,
    min_VE: float = DEFAUTS["seuil_VE_min"],
    max_VE: float = DEFAUTS["seuil_VE_max"],
    min_TiTot: float = DEFAUTS["seuil_TiTot_min"],
    max_TiTot: float = DEFAUTS["seuil_TiTot_max"],
) -> pd.DataFrame:
    """
    Retourne un nouveau DataFrame.
    Vide les lignes dont V.E. ou Ti/Ttot sont hors [min, max] ou non numériques.
    """
    result = df.copy()
    a_vider = _cols_a_vider(result)

    mask = pd.Series(False, index=result.index)

    if COL_VE in result.columns:
        ve = pd.to_numeric(result[COL_VE], errors="coerce")
        mask = mask | ve.isna() | (ve < min_VE) | (ve > max_VE)

    if COL_TITOT in result.columns:
        titot = pd.to_numeric(result[COL_TITOT], errors="coerce")
        mask = mask | titot.isna() | (titot < min_TiTot) | (titot > max_TiTot)

    result.loc[mask, a_vider] = None
    return result


def appliquer_filtres_additionnels(df: pd.DataFrame, filtres: list) -> pd.DataFrame:
    """
    Applique une liste de filtres personnalisés définis par l'utilisateur.
    Chaque élément de `filtres` est un dict :
      {'type': 'disc',  'col': str, 'seuil': float}
      {'type': 'seuil', 'col': str, 'min': float, 'max': float}
    Une ligne qui échoue à n'importe quel filtre a toutes ses colonnes (hors Temps) vidées.
    """
    if not filtres:
        return df.copy()
    result = df.copy()
    a_vider = _cols_a_vider(result)

    for f in filtres:
        col = f.get('col', '')
        if not col or col not in result.columns:
            continue
        serie = pd.to_numeric(result[col], errors='coerce')

        if f.get('type') == 'disc':
            diff = serie.diff().abs()
            mask = diff > f.get('seuil', 0.0)
            if len(result) > 0:
                mask.iloc[0] = False
            result.loc[mask, a_vider] = None

        elif f.get('type') == 'seuil':
            mask = pd.Series(False, index=result.index)
            if f.get('min') is not None:
                mask |= serie < f['min']
            if f.get('max') is not None:
                mask |= serie > f['max']
            result.loc[mask, a_vider] = None

    return result


def compter_lignes_valides(df: pd.DataFrame) -> int:
    """
    Compte les lignes non-vidées : au moins une valeur non-nulle
    parmi V.E., Ti/Ttot, Vt.
    """
    cols = [c for c in (COL_VE, COL_TITOT, COL_VT) if c in df.columns]
    if not cols:
        return len(df)
    return int(df[cols].notna().any(axis=1).sum())
