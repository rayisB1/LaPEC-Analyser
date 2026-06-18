from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QComboBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QFrame, QTabWidget,
)
from PyQt6.QtCore import Qt
from src.filters import (
    appliquer_filtre_discontinuite,
    appliquer_filtre_seuils,
    compter_lignes_valides,
    DEFAUTS,
    COL_VE, COL_QR, COL_TITOT, COL_VT,
)


class PageFiltrage(QWidget):
    def __init__(self, fichiers: dict):
        super().__init__()
        self.fichiers = fichiers
        self._originaux: dict = {}
        self._compteurs: dict = {}
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

        form_disc.addRow(self._lbl(f"Seuil VE  ({COL_VE}) :"), self.spin_disc_VE)
        form_disc.addRow(self._lbl(f"Seuil Q.R.  ({COL_QR}) :"), self.spin_disc_TiTot)
        form_disc.addRow(self._lbl(f"Seuil Vt  ({COL_VT}) :"), self.spin_disc_Vt)
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
        style_cpt = "font-size: 13px; color: #2b2d3b; font-family: monospace;"
        for lbl in (self.lbl_avant, self.lbl_apres_disc, self.lbl_apres_seuils):
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
        layout.setSpacing(16)

        lbl = QLabel("Moyenne")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(lbl)

        placeholder = QLabel("Le calcul de moyennes sera disponible ici.")
        placeholder.setStyleSheet("font-size: 13px; color: #888;")
        layout.addWidget(placeholder)

        layout.addStretch()
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

        current = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        for nom in self.fichiers:
            self.combo.addItem(nom)
        idx = self.combo.findText(current)
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo.blockSignals(False)
        self._on_fichier_change()

    def _on_fichier_change(self):
        nom = self.combo.currentText()
        if nom:
            self._snapshot_si_nouveau(nom)
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
        self._compteurs[nom] = {"avant": avant, "apres_disc": None, "apres_seuils": None}
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
