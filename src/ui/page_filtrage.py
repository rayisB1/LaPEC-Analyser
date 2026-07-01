import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QComboBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QFrame, QTabWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from src.moyennes import calculer_moyennes, COLS_MOYENNE
from src.filters import (
    appliquer_filtre_discontinuite,
    appliquer_filtre_seuils,
    appliquer_filtres_additionnels,
    compter_lignes_valides,
    DEFAUTS,
    COL_VE, COL_TITOT, COL_VT, COL_TEMPS,
)


class FiltreLigneWidget(QWidget):
    """Un filtre personnalisé : colonne + type (disc ou seuil) + paramètres."""

    def __init__(self, colonnes: list, on_remove, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(6)

        self.combo_col = QComboBox()
        self.combo_col.addItems(colonnes)
        self.combo_col.setMinimumWidth(110)
        row.addWidget(self.combo_col)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["Valeur", "Seuils min/max"])
        self.combo_type.setFixedWidth(120)
        self.combo_type.currentIndexChanged.connect(self._toggle_params)
        row.addWidget(self.combo_type)

        # Params discontinuité
        self.lbl_seuil = QLabel("valeur :")
        self.spin_seuil = self._spin(0.0, 9999.0, 2, 1.0)
        row.addWidget(self.lbl_seuil)
        row.addWidget(self.spin_seuil)

        # Params seuils
        self.lbl_min = QLabel("min :")
        self.spin_min = self._spin(-9999.0, 9999.0, 2, 0.0)
        self.lbl_max = QLabel("max :")
        self.spin_max = self._spin(-9999.0, 9999.0, 2, 100.0)
        for w in (self.lbl_min, self.spin_min, self.lbl_max, self.spin_max):
            row.addWidget(w)

        for lbl in (self.lbl_seuil, self.lbl_min, self.lbl_max):
            lbl.setStyleSheet("font-size: 12px; color: #2b2d3b;")

        btn_rm = QPushButton("×")
        btn_rm.setFixedSize(26, 26)
        btn_rm.setStyleSheet(
            "QPushButton{background:#e05c3a;color:white;border:none;border-radius:4px;font-size:13px;}"
            "QPushButton:hover{background:#c44e30;}"
        )
        btn_rm.clicked.connect(lambda: on_remove(self))
        row.addWidget(btn_rm)
        row.addStretch()

        self._toggle_params()

    def _spin(self, min_, max_, dec, default) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setMinimum(min_)
        sb.setMaximum(max_)
        sb.setDecimals(dec)
        sb.setValue(default)
        sb.setFixedWidth(88)
        sb.setStyleSheet(
            "QDoubleSpinBox{padding:3px 6px;border:1px solid #ccc;"
            "border-radius:4px;font-size:12px;background:white;color:#2b2d3b;}"
        )
        return sb

    def _toggle_params(self):
        disc = self.combo_type.currentIndex() == 0
        self.lbl_seuil.setVisible(disc)
        self.spin_seuil.setVisible(disc)
        self.lbl_min.setVisible(not disc)
        self.spin_min.setVisible(not disc)
        self.lbl_max.setVisible(not disc)
        self.spin_max.setVisible(not disc)

    def config(self) -> dict:
        col = self.combo_col.currentText()
        if self.combo_type.currentIndex() == 0:
            return {'type': 'disc', 'col': col, 'seuil': self.spin_seuil.value()}
        return {'type': 'seuil', 'col': col,
                'min': self.spin_min.value(), 'max': self.spin_max.value()}

    def actualiser_colonnes(self, colonnes: list):
        cur = self.combo_col.currentText()
        self.combo_col.blockSignals(True)
        self.combo_col.clear()
        self.combo_col.addItems(colonnes)
        idx = self.combo_col.findText(cur)
        self.combo_col.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_col.blockSignals(False)


class PageFiltrage(QWidget):
    def __init__(self, fichiers: dict, resume_data: dict):
        super().__init__()
        self.fichiers = fichiers
        self.resume_data = resume_data
        self._originaux: dict = {}
        self._compteurs: dict = {}
        self._filtres_lignes: list = []
        self._build_ui()

    # ── Construction UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Titre au-dessus des onglets
        header = QWidget()
        header.setStyleSheet("background-color: #f5f5f5;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(32, 28, 32, 0)

        title = QLabel("Filtrage et Moyenne")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2b2d3b;")
        header_layout.addWidget(title)
        outer.addWidget(header)

        # Onglets
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._style_tabs())
        self.tabs.addTab(self._build_tab_filtrage(), "Filtrage")
        self.tabs.addTab(self._build_tab_moyenne(), "Moyenne")
        self.tabs.currentChanged.connect(self._on_tab_change)
        outer.addWidget(self.tabs)

    def _build_tab_filtrage(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(20)

        # Sélecteur de fichier + bouton recharger
        row_fichier = QHBoxLayout()
        row_fichier.addWidget(self._lbl("Fichier :"))

        self.combo = QComboBox()
        self.combo.setMinimumWidth(300)
        self.combo.setStyleSheet(self._style_combo())
        self.combo.currentIndexChanged.connect(self._on_fichier_change)
        row_fichier.addWidget(self.combo)

        self.btn_reload = QPushButton("Recharger données originales")
        self.btn_reload.setStyleSheet(self._style_btn_secondary())
        self.btn_reload.clicked.connect(self._recharger_originaux)
        row_fichier.addWidget(self.btn_reload)
        row_fichier.addStretch()
        layout.addLayout(row_fichier)

        # ── Paramètres discontinuité ──────────────────────────────────────────
        grp_disc = QGroupBox("Filtre de discontinuité  —  seuils d'écart max entre lignes consécutives")
        grp_disc.setStyleSheet(self._style_groupbox())
        form_disc = QFormLayout(grp_disc)
        form_disc.setSpacing(10)
        form_disc.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spin_disc_VE = self._spinbox(DEFAUTS["disc_VE"], 0.0, 999.0, 2)
        self.spin_disc_TiTot = self._spinbox(DEFAUTS["disc_TiTot"], 0.0, 99.0, 3)
        self.spin_disc_Vt = self._spinbox(DEFAUTS["disc_Vt"], 0.0, 99.0, 3)

        form_disc.addRow(self._lbl(f"VE  ({COL_VE}) :"), self.spin_disc_VE)
        form_disc.addRow(self._lbl(f"Ti/Ttot  ({COL_TITOT}) :"), self.spin_disc_TiTot)
        form_disc.addRow(self._lbl(f"Vt  ({COL_VT}) :"), self.spin_disc_Vt)
        layout.addWidget(grp_disc)

        # ── Paramètres seuils ─────────────────────────────────────────────────
        grp_seuils = QGroupBox("Filtre de seuils  —  bornes min/max valides par ligne")
        grp_seuils.setStyleSheet(self._style_groupbox())
        form_seuils = QFormLayout(grp_seuils)
        form_seuils.setSpacing(10)
        form_seuils.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spin_ve_min = self._spinbox(DEFAUTS["seuil_VE_min"], -999.0, 999.0, 2)
        self.spin_ve_max = self._spinbox(DEFAUTS["seuil_VE_max"], -999.0, 999.0, 2)
        self.spin_titot_min = self._spinbox(DEFAUTS["seuil_TiTot_min"], -99.0, 99.0, 3)
        self.spin_titot_max = self._spinbox(DEFAUTS["seuil_TiTot_max"], -99.0, 99.0, 3)

        form_seuils.addRow(
            self._lbl(f"VE  ({COL_VE}) :"),
            self._minmax_widget(self.spin_ve_min, self.spin_ve_max),
        )
        form_seuils.addRow(
            self._lbl(f"TiTot  ({COL_TITOT}) :"),
            self._minmax_widget(self.spin_titot_min, self.spin_titot_max),
        )
        layout.addWidget(grp_seuils)

        # Bouton réinitialiser seuils
        btn_defaults = QPushButton("Réinitialiser les seuils par défaut")
        btn_defaults.setStyleSheet(self._style_btn_secondary())
        btn_defaults.setFixedWidth(270)
        btn_defaults.clicked.connect(self._reset_defauts)
        layout.addWidget(btn_defaults)

        # ── Filtres additionnels ───────────────────────────────────────────────
        grp_add = QGroupBox("Filtres additionnels  —  sur n'importe quelle colonne")
        grp_add.setStyleSheet(self._style_groupbox())
        vbox_add = QVBoxLayout(grp_add)
        vbox_add.setSpacing(4)

        self._filtres_layout = QVBoxLayout()
        self._filtres_layout.setSpacing(4)
        vbox_add.addLayout(self._filtres_layout)

        btn_ajouter = QPushButton("+ Ajouter un filtre")
        btn_ajouter.setStyleSheet(self._style_btn_secondary())
        btn_ajouter.setFixedWidth(180)
        btn_ajouter.clicked.connect(self._ajouter_filtre_additionnel)
        vbox_add.addWidget(btn_ajouter)
        layout.addWidget(grp_add)

        layout.addWidget(self._separateur())

        # ── Boutons d'action ──────────────────────────────────────────────────
        lbl_actions = QLabel("Actions")
        lbl_actions.setStyleSheet("font-size: 15px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(lbl_actions)

        self.btn_disc = QPushButton("Appliquer filtre discontinuité")
        self.btn_disc.setStyleSheet(self._style_btn_primary())
        self.btn_disc.setFixedWidth(290)
        self.btn_disc.clicked.connect(self._appliquer_disc)
        layout.addWidget(self.btn_disc)

        self.btn_seuils = QPushButton("Appliquer filtre seuils")
        self.btn_seuils.setStyleSheet(self._style_btn_primary())
        self.btn_seuils.setFixedWidth(290)
        self.btn_seuils.clicked.connect(self._appliquer_seuils)
        layout.addWidget(self.btn_seuils)

        self.btn_additionnels = QPushButton("Appliquer filtres additionnels")
        self.btn_additionnels.setStyleSheet(self._style_btn_primary())
        self.btn_additionnels.setFixedWidth(290)
        self.btn_additionnels.clicked.connect(self._appliquer_filtres_additionnels)
        layout.addWidget(self.btn_additionnels)

        layout.addWidget(self._separateur())

        # ── Compteurs de suivi ────────────────────────────────────────────────
        lbl_suivi = QLabel("Suivi de la perte de données")
        lbl_suivi.setStyleSheet("font-size: 15px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(lbl_suivi)

        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background: white; border: 1px solid #ddd; border-radius: 6px; }"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 12, 16, 12)
        panel_layout.setSpacing(8)

        self.lbl_avant = QLabel()
        self.lbl_apres_disc = QLabel()
        self.lbl_apres_seuils = QLabel()
        self.lbl_apres_additionnel = QLabel()
        style_cpt = "font-size: 13px; color: #2b2d3b; font-family: monospace;"
        for lbl in (self.lbl_avant, self.lbl_apres_disc,
                    self.lbl_apres_seuils, self.lbl_apres_additionnel):
            lbl.setStyleSheet(style_cpt)
            panel_layout.addWidget(lbl)

        layout.addWidget(panel)
        layout.addStretch()

        self._update_compteurs_labels(None)
        return scroll

    def _build_tab_moyenne(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 32)
        layout.setSpacing(12)

        # Sélecteur de fichier
        row_fichier = QHBoxLayout()
        row_fichier.addWidget(self._lbl("Fichier :"))
        self.combo_moy = QComboBox()
        self.combo_moy.setMinimumWidth(300)
        self.combo_moy.setStyleSheet(self._style_combo())
        self.combo_moy.currentIndexChanged.connect(self._tracer_moyenne)
        row_fichier.addWidget(self.combo_moy)
        row_fichier.addStretch()
        layout.addLayout(row_fichier)

        # Figure matplotlib (hauteur fixe pour laisser place au tableau)
        self.fig_moy = Figure(figsize=(10, 4.5), facecolor="#f5f5f5")
        self.ax_vo2 = self.fig_moy.add_subplot(111)
        self.ax_qr = self.ax_vo2.twinx()
        self.canvas_moy = FigureCanvas(self.fig_moy)
        self.canvas_moy.setFixedHeight(400)
        self.canvas_moy.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.canvas_moy)

        btn_reset = QPushButton("Vue initiale")
        btn_reset.setFixedWidth(110)
        btn_reset.setStyleSheet(self._style_btn_secondary())
        btn_reset.clicked.connect(self._reset_vue_moyenne)
        layout.addWidget(btn_reset, alignment=Qt.AlignmentFlag.AlignRight)

        self.canvas_moy.mpl_connect("scroll_event", self._on_scroll_moy)

        layout.addWidget(self._separateur())

        # Titre section moyennes
        lbl_moy = QLabel("Moyennes par période")
        lbl_moy.setStyleSheet("font-size: 15px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(lbl_moy)

        # Info : FR, nb cycles, plages
        self.lbl_moy_info = QLabel("—")
        self.lbl_moy_info.setStyleSheet(
            "font-size: 12px; color: #555; font-family: monospace; padding: 4px 0;"
        )
        self.lbl_moy_info.setWordWrap(True)
        layout.addWidget(self.lbl_moy_info)

        # Tableau des résultats
        self.table_moy = QTableWidget()
        self.table_moy.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_moy.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_moy.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_moy.setMinimumHeight(110)
        self.table_moy.setMaximumHeight(160)
        self.table_moy.setStyleSheet("""
            QTableWidget { color: #2b2d3b; background-color: white;
                           border: 1px solid #ddd; border-radius: 4px; }
            QTableWidget::item:selected { background-color: #c8d8f8; color: #2b2d3b; }
            QHeaderView::section {
                background-color: #e8eaf0; color: #2b2d3b;
                padding: 4px 8px; border: none;
                border-right: 1px solid #ccc; font-weight: bold; font-size: 11px;
            }
        """)
        layout.addWidget(self.table_moy)

        # Envoi vers le résumé
        row_resume = QHBoxLayout()
        self.btn_resume = QPushButton("Résumé")
        self.btn_resume.setStyleSheet(self._style_btn_primary())
        self.btn_resume.setFixedWidth(160)
        self.btn_resume.clicked.connect(self._envoyer_resume)
        row_resume.addWidget(self.btn_resume)

        self.lbl_resume_statut = QLabel("")
        self.lbl_resume_statut.setStyleSheet("font-size: 12px; color: #27ae60;")
        row_resume.addWidget(self.lbl_resume_statut)
        row_resume.addStretch()
        layout.addLayout(row_resume)

        layout.addStretch()

        self._style_axes_moyenne()
        return scroll

    # ── Événements ─────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._rafraichir_liste()

    def _rafraichir_liste(self):
        for nom in list(self._originaux):
            if nom not in self.fichiers:
                del self._originaux[nom]
                self._compteurs.pop(nom, None)

        for combo, signal in [(self.combo, self._on_fichier_change),
                               (self.combo_moy, self._tracer_moyenne)]:
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            for nom in self.fichiers:
                combo.addItem(nom)
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

        self._on_fichier_change()
        if self.tabs.currentIndex() == 1:
            self._tracer_moyenne()

    def _on_fichier_change(self):
        nom = self.combo.currentText()
        if nom:
            self._snapshot_si_nouveau(nom)
        self._actualiser_colonnes_filtres()
        self._update_compteurs_labels(nom)

    # ── Logique de filtrage ────────────────────────────────────────────────────

    def _snapshot_si_nouveau(self, nom: str):
        df = self.fichiers.get(nom)
        if df is not None and nom not in self._originaux:
            self._originaux[nom] = df.copy()
            self._compteurs[nom] = {
                "avant": compter_lignes_valides(df),
                "apres_disc": None,
                "apres_seuils": None,
                "apres_additionnel": None,
            }

    def _appliquer_disc(self):
        nom = self.combo.currentText()
        df = self.fichiers.get(nom)
        if df is None:
            return
        self._snapshot_si_nouveau(nom)
        df_filtre = appliquer_filtre_discontinuite(
            df,
            disc_VE=self.spin_disc_VE.value(),
            disc_TiTot=self.spin_disc_TiTot.value(),
            disc_Vt=self.spin_disc_Vt.value(),
        )
        self.fichiers[nom] = df_filtre
        self._compteurs[nom]["apres_disc"] = compter_lignes_valides(df_filtre)
        self._update_compteurs_labels(nom)

    def _appliquer_seuils(self):
        nom = self.combo.currentText()
        df = self.fichiers.get(nom)
        if df is None:
            return
        self._snapshot_si_nouveau(nom)
        df_filtre = appliquer_filtre_seuils(
            df,
            min_VE=self.spin_ve_min.value(),
            max_VE=self.spin_ve_max.value(),
            min_TiTot=self.spin_titot_min.value(),
            max_TiTot=self.spin_titot_max.value(),
        )
        self.fichiers[nom] = df_filtre
        self._compteurs[nom]["apres_seuils"] = compter_lignes_valides(df_filtre)
        self._update_compteurs_labels(nom)

    def _recharger_originaux(self):
        nom = self.combo.currentText()
        original = self._originaux.get(nom)
        if original is None:
            return
        self.fichiers[nom] = original.copy()
        avant = self._compteurs.get(nom, {}).get("avant")
        self._compteurs[nom] = {
            "avant": avant,
            "apres_disc": None,
            "apres_seuils": None,
            "apres_additionnel": None,
        }
        self._update_compteurs_labels(nom)

    def _reset_defauts(self):
        self.spin_disc_VE.setValue(DEFAUTS["disc_VE"])
        self.spin_disc_TiTot.setValue(DEFAUTS["disc_TiTot"])
        self.spin_disc_Vt.setValue(DEFAUTS["disc_Vt"])
        self.spin_ve_min.setValue(DEFAUTS["seuil_VE_min"])
        self.spin_ve_max.setValue(DEFAUTS["seuil_VE_max"])
        self.spin_titot_min.setValue(DEFAUTS["seuil_TiTot_min"])
        self.spin_titot_max.setValue(DEFAUTS["seuil_TiTot_max"])

    # ── Affichage des compteurs ────────────────────────────────────────────────

    def _update_compteurs_labels(self, nom):
        cpt = self._compteurs.get(nom, {}) if nom else {}
        avant = cpt.get("avant")
        apres_disc = cpt.get("apres_disc")
        apres_seuils = cpt.get("apres_seuils")
        df_courant = self.fichiers.get(nom) if nom else None
        n_total = len(df_courant) if df_courant is not None else 0

        if avant is not None:
            self.lbl_avant.setText(
                f"Avant filtrage              :  {avant} lignes valides  "
                f"(sur {n_total} lignes au total)"
            )
        else:
            self.lbl_avant.setText("Avant filtrage              :  —")

        if apres_disc is not None and avant:
            pct = 100.0 * apres_disc / avant
            self.lbl_apres_disc.setText(
                f"Après filtre discontinuité  :  {apres_disc} lignes valides  "
                f"(−{avant - apres_disc}  soit {100 - pct:.1f}% perdues)"
            )
        else:
            self.lbl_apres_disc.setText("Après filtre discontinuité  :  —  (non appliqué)")

        if apres_seuils is not None and avant:
            pct = 100.0 * apres_seuils / avant
            self.lbl_apres_seuils.setText(
                f"Après filtre seuils         :  {apres_seuils} lignes valides  "
                f"(−{avant - apres_seuils}  soit {100 - pct:.1f}% perdues vs. initial)"
            )
        else:
            self.lbl_apres_seuils.setText("Après filtre seuils         :  —  (non appliqué)")

        apres_add = cpt.get("apres_additionnel")
        if apres_add is not None and avant:
            pct = 100.0 * apres_add / avant
            self.lbl_apres_additionnel.setText(
                f"Après filtres additionnels  :  {apres_add} lignes valides  "
                f"(−{avant - apres_add}  soit {100 - pct:.1f}% perdues vs. initial)"
            )
        else:
            self.lbl_apres_additionnel.setText(
                "Après filtres additionnels  :  —  (non appliqué)"
            )

    # ── Filtres additionnels ───────────────────────────────────────────────────

    def _colonnes_disponibles(self) -> list:
        nom = self.combo.currentText()
        df = self.fichiers.get(nom)
        if df is None:
            return []
        return [c for c in df.columns if c != COL_TEMPS]

    def _actualiser_colonnes_filtres(self):
        cols = self._colonnes_disponibles()
        for widget in self._filtres_lignes:
            widget.actualiser_colonnes(cols)

    def _ajouter_filtre_additionnel(self):
        cols = self._colonnes_disponibles()
        widget = FiltreLigneWidget(cols, self._supprimer_filtre_additionnel)
        self._filtres_lignes.append(widget)
        self._filtres_layout.addWidget(widget)

    def _supprimer_filtre_additionnel(self, widget: FiltreLigneWidget):
        if widget in self._filtres_lignes:
            self._filtres_lignes.remove(widget)
            self._filtres_layout.removeWidget(widget)
            widget.deleteLater()

    def _appliquer_filtres_additionnels(self):
        nom = self.combo.currentText()
        df = self.fichiers.get(nom)
        if df is None or not self._filtres_lignes:
            return
        self._snapshot_si_nouveau(nom)
        filtres = [w.config() for w in self._filtres_lignes]
        df_filtre = appliquer_filtres_additionnels(df, filtres)
        self.fichiers[nom] = df_filtre
        self._compteurs[nom]["apres_additionnel"] = compter_lignes_valides(df_filtre)
        self._update_compteurs_labels(nom)

    # ── Graphique Moyenne ──────────────────────────────────────────────────────

    def _on_tab_change(self, index: int):
        if index == 1:
            self._tracer_moyenne()

    def _tracer_moyenne(self):
        nom = self.combo_moy.currentText()
        df = self.fichiers.get(nom)

        self.ax_vo2.clear()
        self.ax_qr.clear()

        res = None
        if df is not None and not df.empty:
            x = self._temps_en_secondes_moy(df)
            res = calculer_moyennes(df)

            def _fmt_t(v, _):
                v = int(v)
                h, rem = divmod(v, 3600)
                m, s = divmod(rem, 60)
                return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

            def _x_at(idx):
                idx = max(0, min(idx, len(x) - 1))
                if x[idx] is not None:
                    return x[idx]
                for d in range(1, 10):
                    for i in (idx + d, idx - d):
                        if 0 <= i < len(x) and x[i] is not None:
                            return x[i]
                return None

            # Zones colorées des périodes (tracées en fond, zorder=0)
            if res:
                SPANS = [
                    ("Dernières 4'",  res['last4'],         '#4f8ef7'),
                    ("Stable VO2",    res.get('stable_vo2'),   '#27ae60'),
                    ("Stable PetO2",  res.get('stable_peto2'), '#f39c12'),
                    ("VO2 mini 4'",   res.get('vo2_min'),      '#9b59b6'),
                ]
                for label, periode, color in SPANS:
                    if periode is None:
                        continue
                    x1 = _x_at(periode['debut'])
                    x2 = _x_at(periode['fin'] - 1)
                    if x1 is not None and x2 is not None and x2 > x1:
                        self.ax_vo2.axvspan(x1, x2, alpha=0.13, color=color,
                                            label=label, zorder=0)

            # Courbes
            if "VO2" in df.columns:
                vo2 = pd.to_numeric(df["VO2"], errors="coerce")
                vo2_lisse = vo2.rolling(window=11, center=True, min_periods=1).mean()
                if len(vo2_lisse) > 10:
                    vo2_lisse.iloc[:5] = float("nan")
                    vo2_lisse.iloc[-5:] = float("nan")
                vo2_lisse = vo2_lisse.round(2)
                self.ax_vo2.plot(x, vo2,
                                 color=(180/255, 50/255, 50/255),
                                 linewidth=1, label="VO2 (L)", zorder=2)
                self.ax_vo2.plot(x, vo2_lisse,
                                 color=(180/255, 55/255, 55/255),
                                 linewidth=2, label="VO2 (L) lissé", zorder=2)

            if "Q.R." in df.columns:
                qr = pd.to_numeric(df["Q.R."], errors="coerce")
                self.ax_qr.plot(x, qr,
                                color=(255/255, 90/255, 172/255),
                                linewidth=1, label="QR", zorder=2)

            self.ax_vo2.xaxis.set_major_formatter(ticker.FuncFormatter(_fmt_t))
            self.ax_vo2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10, integer=True))
            self.ax_vo2.tick_params(axis="x", rotation=30, labelsize=8)

            lines1, labels1 = self.ax_vo2.get_legend_handles_labels()
            lines2, labels2 = self.ax_qr.get_legend_handles_labels()
            self.ax_vo2.legend(lines1 + lines2, labels1 + labels2,
                               fontsize=9, loc="upper center",
                               bbox_to_anchor=(0.5, -0.22), ncol=3,
                               framealpha=0.9, edgecolor="#dddddd")

        self._style_axes_moyenne()
        self.canvas_moy.draw()
        self._mettre_a_jour_tableau_moyennes(res)

    def _envoyer_resume(self):
        nom = self.combo_moy.currentText()
        df = self.fichiers.get(nom)
        if df is None or df.empty:
            return
        res = calculer_moyennes(df)
        if res is None:
            self.lbl_resume_statut.setStyleSheet("font-size: 12px; color: #e05c3a;")
            self.lbl_resume_statut.setText("Impossible d'envoyer (colonne F.R. manquante).")
            QTimer.singleShot(4000, lambda: self.lbl_resume_statut.setText(""))
            return
        self.resume_data[nom] = res
        self.lbl_resume_statut.setStyleSheet("font-size: 12px; color: #27ae60;")
        self.lbl_resume_statut.setText(f"✓ « {nom} » envoyé au résumé.")
        QTimer.singleShot(4000, lambda: self.lbl_resume_statut.setText(""))

    def _mettre_a_jour_tableau_moyennes(self, res=None):
        nom = self.combo_moy.currentText()
        df = self.fichiers.get(nom)

        self.table_moy.clear()
        self.table_moy.setRowCount(0)

        if df is None or df.empty:
            self.lbl_moy_info.setText("—")
            return

        if res is None:
            res = calculer_moyennes(df)
        if res is None:
            self.lbl_moy_info.setText("Impossible de calculer (colonne F.R. manquante).")
            return

        # Info textuelle
        def _temps(idx):
            try:
                return str(df["Temps"].iloc[idx]) if "Temps" in df.columns else str(idx)
            except Exception:
                return str(idx)

        info_lines = [
            f"FR moy : {res['freq_moy']} cycles/min  |  4 min ≈ {res['nb_lignes']} cycles  |  tampon 1 min ≈ {res['nb_lignes_1min']} cycles",
            f"Dernières 4'  : lignes {res['last4']['debut']}–{res['last4']['fin']}  "
            f"({_temps(res['last4']['debut'])} → {_temps(res['last4']['fin'] - 1)})",
        ]
        if res['stable_vo2']:
            sv = res['stable_vo2']
            info_lines.append(
                f"Stable VO2    : lignes {sv['debut']}–{sv['fin']}  "
                f"({_temps(sv['debut'])} → {_temps(sv['fin'] - 1)})"
            )
        if res['stable_peto2']:
            sp = res['stable_peto2']
            info_lines.append(
                f"Stable PetO2  : lignes {sp['debut']}–{sp['fin']}  "
                f"({_temps(sp['debut'])} → {_temps(sp['fin'] - 1)})"
            )
        if res.get('vo2_min'):
            vm = res['vo2_min']
            info_lines.append(
                f"VO2 mini 4'   : lignes {vm['debut']}–{vm['fin']}  "
                f"({_temps(vm['debut'])} → {_temps(vm['fin'] - 1)})"
            )
        self.lbl_moy_info.setText("\n".join(info_lines))

        # Construction du tableau
        col_headers = COLS_MOYENNE + ["CV VO2", "CV PetO2"]
        periodes = [
            ("Dernières 4'", res['last4']),
            ("Stable VO2",   res['stable_vo2']),
            ("Stable PetO2", res['stable_peto2']),
            ("VO2 mini 4'",  res.get('vo2_min')),
        ]
        periodes = [(lbl, p) for lbl, p in periodes if p is not None]

        self.table_moy.setColumnCount(len(col_headers))
        self.table_moy.setRowCount(len(periodes))
        self.table_moy.setHorizontalHeaderLabels(col_headers)
        self.table_moy.setVerticalHeaderLabels([lbl for lbl, _ in periodes])

        for row_idx, (_, periode) in enumerate(periodes):
            stats = periode['stats']
            for col_idx, col in enumerate(COLS_MOYENNE):
                val = stats.get(col)
                txt = f"{val:.2f}" if val is not None else "—"
                self.table_moy.setItem(row_idx, col_idx, QTableWidgetItem(txt))
            # CV VO2
            cv_vo2 = stats.get('cv_vo2')
            self.table_moy.setItem(
                row_idx, len(COLS_MOYENNE),
                QTableWidgetItem(f"{cv_vo2:.4f}" if cv_vo2 is not None else "—")
            )
            # CV PetO2
            cv_pet = stats.get('cv_peto2')
            self.table_moy.setItem(
                row_idx, len(COLS_MOYENNE) + 1,
                QTableWidgetItem(f"{cv_pet:.4f}" if cv_pet is not None else "—")
            )

    def _style_axes_moyenne(self):
        self.ax_vo2.set_facecolor("white")
        self.ax_vo2.set_title("VO2 et QR", fontsize=12, color="#2b2d3b", pad=8)
        self.ax_vo2.set_xlabel("Temps", fontsize=9, color="#555555")
        self.ax_vo2.set_ylabel("VO2 (L)", fontsize=9, color=(180/255, 50/255, 50/255))
        self.ax_vo2.set_ylim(0, 0.6)
        self.ax_vo2.tick_params(colors="#555555", labelsize=8)
        self.ax_vo2.grid(True, alpha=0.3, linestyle="--")
        self.ax_qr.set_ylabel("QR", fontsize=9, color=(255/255, 90/255, 172/255))
        self.ax_qr.yaxis.set_label_position("right")
        self.ax_qr.set_ylim(0, 1.2)
        self.ax_qr.tick_params(axis="y", colors=(255/255, 90/255, 172/255), labelsize=8)
        for spine in self.ax_vo2.spines.values():
            spine.set_edgecolor("#dddddd")
        self.fig_moy.tight_layout(rect=[0, 0.12, 1, 1.0])

    def _reset_vue_moyenne(self):
        self.ax_vo2.autoscale(axis="x")
        self.ax_vo2.set_ylim(0, 0.6)
        self.ax_qr.set_ylim(0, 1.2)
        self.canvas_moy.draw_idle()

    def _on_scroll_moy(self, event):
        ax = event.inaxes
        if ax not in (self.ax_vo2, self.ax_qr) or event.xdata is None:
            return
        factor = 0.75 if event.button == "up" else 1.33
        lo, hi = self.ax_vo2.get_xlim()
        pivot = event.xdata
        self.ax_vo2.set_xlim([pivot + (v - pivot) * factor for v in (lo, hi)])
        self.canvas_moy.draw_idle()

    def _temps_en_secondes_moy(self, df) -> list:
        result = []
        for v in df["Temps"]:
            try:
                parts = str(v).split(":")
                if len(parts) == 3:
                    h, m, s = parts
                    result.append(int(h) * 3600 + int(m) * 60 + int(s))
                else:
                    m, s = parts
                    result.append(int(m) * 60 + int(s))
            except Exception:
                result.append(None)
        return result

    # ── Helpers UI ─────────────────────────────────────────────────────────────

    def _spinbox(self, default, minimum, maximum, decimals) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setMinimum(minimum)
        sb.setMaximum(maximum)
        sb.setDecimals(decimals)
        sb.setValue(default)
        sb.setFixedWidth(110)
        sb.setStyleSheet("""
            QDoubleSpinBox {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
                background: white;
                color: #2b2d3b;
            }
        """)
        return sb

    def _minmax_widget(self, spin_min: QDoubleSpinBox, spin_max: QDoubleSpinBox) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._lbl("min"))
        row.addWidget(spin_min)
        row.addSpacing(12)
        row.addWidget(self._lbl("max"))
        row.addWidget(spin_max)
        row.addStretch()
        return w

    def _lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 13px; color: #2b2d3b;")
        return lbl

    def _separateur(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd; margin: 4px 0;")
        return sep

    # ── Styles ─────────────────────────────────────────────────────────────────

    def _style_tabs(self):
        return """
            QTabWidget::pane {
                border: none;
                background: #f5f5f5;
            }
            QTabBar::tab {
                background: #e8eaf0;
                color: #666;
                padding: 8px 28px;
                font-size: 13px;
                border: none;
                border-bottom: 3px solid transparent;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #f5f5f5;
                color: #2b2d3b;
                font-weight: bold;
                border-bottom: 3px solid #4f8ef7;
            }
            QTabBar::tab:hover:!selected {
                background: #d8dae8;
                color: #2b2d3b;
            }
        """

    def _style_combo(self):
        return """
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
                background: white;
                color: #2b2d3b;
            }
            QComboBox::drop-down { border: none; }
        """

    def _style_groupbox(self):
        return """
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #2b2d3b;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #2b2d3b;
            }
        """

    def _style_btn_primary(self):
        return """
            QPushButton {
                background-color: #4f8ef7;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3a7de0; }
            QPushButton:pressed { background-color: #2d6bc7; }
        """

    def _style_btn_secondary(self):
        return """
            QPushButton {
                background-color: #f0f0f0;
                color: #2b2d3b;
                border: 1px solid #ccc;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """
