from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget,
    QListWidgetItem, QAbstractItemView,
    QMessageBox, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QScrollArea,
    QFrame
)
from PyQt6.QtCore import Qt
import json
from pathlib import Path

CONFIG_PATH = Path("config.json")

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


def charger_config() -> list:
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


def sauvegarder_config(ordre: list):
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception:
            pass
    data['ordre_colonnes'] = ordre
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def sauvegarder_formats(formats: list):
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception:
            pass
    data['formats'] = formats
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


class DialogueFormat(QDialog):
    """Dialogue pour créer ou éditer un profil de format."""

    def __init__(self, parent=None, format_existant: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Profil de format" if format_existant else "Nouveau format")
        self.setMinimumWidth(420)
        self._build_ui(format_existant or {})

    def _build_ui(self, fmt: dict):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.champ_nom = QLineEdit(fmt.get("nom", ""))
        self.champ_nom.setPlaceholderText("ex : COSMED K5")

        self.champ_delimiteur = QLineEdit(fmt.get("delimiteur", "¦"))
        self.champ_delimiteur.setPlaceholderText("ex : ¦  ou  ;  ou  ,")

        self.champ_header = QLineEdit(fmt.get("marqueur_header", ""))
        self.champ_header.setPlaceholderText("ex : temps")

        self.champ_debut = QLineEdit(fmt.get("marqueur_debut", ""))
        self.champ_debut.setPlaceholderText("ex : examen complet")

        self.champ_regex = QLineEdit(fmt.get("regex_premiere_colonne", r"^\d{2}:\d{2}$"))
        self.champ_regex.setPlaceholderText(r"ex : ^\d{2}:\d{2}$")

        champ_style = "padding: 6px; border: 1px solid #ddd; border-radius: 4px;"
        for champ in [self.champ_nom, self.champ_delimiteur, self.champ_header,
                      self.champ_debut, self.champ_regex]:
            champ.setStyleSheet(champ_style)

        form.addRow("Nom du profil :", self.champ_nom)
        form.addRow("Délimiteur :", self.champ_delimiteur)
        form.addRow("Mot-clé en-tête :", self.champ_header)
        form.addRow("Mot-clé début données :", self.champ_debut)
        form.addRow("Regex 1ère colonne :", self.champ_regex)

        aide = QLabel(
            "Le mot-clé en-tête doit apparaître dans la ligne qui contient les noms de colonnes.\n"
            "Le mot-clé début données marque la ligne avant les premières mesures."
        )
        aide.setStyleSheet("color: #888; font-size: 11px;")
        aide.setWordWrap(True)

        layout.addLayout(form)
        layout.addWidget(aide)

        boutons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        boutons.accepted.connect(self._valider)
        boutons.rejected.connect(self.reject)
        layout.addWidget(boutons)

    def _valider(self):
        if not self.champ_nom.text().strip():
            QMessageBox.warning(self, "Erreur", "Le nom du profil est obligatoire.")
            return
        if not self.champ_delimiteur.text():
            QMessageBox.warning(self, "Erreur", "Le délimiteur est obligatoire.")
            return
        self.accept()

    def get_format(self) -> dict:
        return {
            "nom": self.champ_nom.text().strip(),
            "delimiteur": self.champ_delimiteur.text(),
            "marqueur_header": self.champ_header.text().strip().lower(),
            "marqueur_debut": self.champ_debut.text().strip().lower(),
            "regex_premiere_colonne": self.champ_regex.text().strip()
        }


class PageParametres(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        title = QLabel("⚙️ Paramètres")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(title)

        layout.addWidget(self._section_colonnes())
        layout.addWidget(self._separateur())
        layout.addWidget(self._section_formats())
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _separateur(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #e0e0e0;")
        return sep

    # ── Section ordre des colonnes ──────────────────────────────────────────

    def _section_colonnes(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        section = QLabel("Ordre des colonnes")
        section.setStyleSheet("font-size: 15px; font-weight: bold; color: #4f8ef7;")
        layout.addWidget(section)

        info = QLabel("Glisse les colonnes pour changer leur ordre. Cet ordre sera appliqué à chaque import.")
        info.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(info)

        content = QHBoxLayout()

        left = QVBoxLayout()
        self.liste = QListWidget()
        self.liste.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.liste.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.liste.setFixedHeight(280)
        self.liste.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #2b2d3b;
            }
        """)
        self._charger_liste()
        left.addWidget(self.liste)
        content.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(8)
        right.addStretch()

        btn_haut = QPushButton("▲ Monter")
        btn_haut.clicked.connect(self._monter)
        btn_haut.setStyleSheet("padding: 8px 16px;")
        right.addWidget(btn_haut)

        btn_bas = QPushButton("▼ Descendre")
        btn_bas.clicked.connect(self._descendre)
        btn_bas.setStyleSheet("padding: 8px 16px;")
        right.addWidget(btn_bas)

        right.addSpacing(20)

        btn_reset = QPushButton("↺ Réinitialiser")
        btn_reset.clicked.connect(self._reset)
        btn_reset.setStyleSheet("padding: 8px 16px; color: #e74c3c;")
        right.addWidget(btn_reset)

        right.addStretch()
        content.addLayout(right)
        layout.addLayout(content)

        btn_save = QPushButton("Sauvegarder l'ordre")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4f8ef7;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3a7de0; }
        """)
        btn_save.clicked.connect(self._sauvegarder)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignLeft)

        return w

    # ── Section formats de fichiers ─────────────────────────────────────────

    def _section_formats(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        section = QLabel("Formats de fichiers")
        section.setStyleSheet("font-size: 15px; font-weight: bold; color: #4f8ef7;")
        layout.addWidget(section)

        info = QLabel(
            "Définissez les profils de format pour lire différents types de fichiers PDF. "
            "Le parser essaie chaque profil dans l'ordre jusqu'à en trouver un compatible."
        )
        info.setStyleSheet("color: #666; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        content = QHBoxLayout()
        content.setSpacing(12)

        # Liste des profils
        left = QVBoxLayout()
        self.liste_formats = QListWidget()
        self.liste_formats.setFixedHeight(160)
        self.liste_formats.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #2b2d3b;
            }
        """)
        left.addWidget(self.liste_formats)
        content.addLayout(left, stretch=1)

        # Détail du profil sélectionné (lecture seule)
        right = QVBoxLayout()
        right.setSpacing(4)
        self.detail_format = QLabel("")
        self.detail_format.setStyleSheet(
            "background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px; "
            "padding: 10px; font-size: 12px; color: #444;"
        )
        self.detail_format.setWordWrap(True)
        self.detail_format.setFixedHeight(160)
        self.detail_format.setAlignment(Qt.AlignmentFlag.AlignTop)
        right.addWidget(self.detail_format)
        content.addLayout(right, stretch=1)

        self.liste_formats.currentRowChanged.connect(self._afficher_detail_format)
        self._charger_liste_formats()

        layout.addLayout(content)

        # Boutons d'action
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_ajouter = QPushButton("+ Ajouter")
        btn_ajouter.clicked.connect(self._ajouter_format)
        btn_ajouter.setStyleSheet("""
            QPushButton {
                background-color: #4f8ef7; color: white;
                border: none; padding: 8px 16px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #3a7de0; }
        """)

        btn_modifier = QPushButton("✎ Modifier")
        btn_modifier.clicked.connect(self._modifier_format)
        btn_modifier.setStyleSheet("padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px;")

        btn_monter_fmt = QPushButton("▲")
        btn_monter_fmt.setFixedWidth(36)
        btn_monter_fmt.clicked.connect(self._monter_format)
        btn_monter_fmt.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 6px;")

        btn_descendre_fmt = QPushButton("▼")
        btn_descendre_fmt.setFixedWidth(36)
        btn_descendre_fmt.clicked.connect(self._descendre_format)
        btn_descendre_fmt.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 6px;")

        btn_supprimer = QPushButton("✕ Supprimer")
        btn_supprimer.clicked.connect(self._supprimer_format)
        btn_supprimer.setStyleSheet("padding: 8px 16px; color: #e74c3c; border: 1px solid #ddd; border-radius: 6px;")

        btn_row.addWidget(btn_ajouter)
        btn_row.addWidget(btn_modifier)
        btn_row.addWidget(btn_monter_fmt)
        btn_row.addWidget(btn_descendre_fmt)
        btn_row.addStretch()
        btn_row.addWidget(btn_supprimer)

        layout.addLayout(btn_row)
        return w

    def _charger_liste_formats(self):
        self.liste_formats.clear()
        self._formats = charger_formats()
        for i, fmt in enumerate(self._formats):
            label = fmt.get("nom", f"Format {i+1}")
            if i == 0:
                label += "  (prioritaire)"
            self.liste_formats.addItem(label)
        if self._formats:
            self.liste_formats.setCurrentRow(0)

    def _afficher_detail_format(self, row: int):
        if row < 0 or row >= len(self._formats):
            self.detail_format.setText("")
            return
        fmt = self._formats[row]
        texte = (
            f"<b>Délimiteur :</b> {fmt.get('delimiteur', '')}<br>"
            f"<b>Mot-clé en-tête :</b> {fmt.get('marqueur_header', '')}<br>"
            f"<b>Mot-clé début données :</b> {fmt.get('marqueur_debut', '')}<br>"
            f"<b>Regex 1ère colonne :</b> {fmt.get('regex_premiere_colonne', '')}"
        )
        self.detail_format.setText(texte)

    def _ajouter_format(self):
        dlg = DialogueFormat(self)
        if dlg.exec():
            self._formats.append(dlg.get_format())
            sauvegarder_formats(self._formats)
            self._charger_liste_formats()
            self.liste_formats.setCurrentRow(len(self._formats) - 1)

    def _modifier_format(self):
        row = self.liste_formats.currentRow()
        if row < 0:
            return
        dlg = DialogueFormat(self, format_existant=self._formats[row])
        if dlg.exec():
            self._formats[row] = dlg.get_format()
            sauvegarder_formats(self._formats)
            self._charger_liste_formats()
            self.liste_formats.setCurrentRow(row)

    def _supprimer_format(self):
        row = self.liste_formats.currentRow()
        if row < 0:
            return
        if len(self._formats) == 1:
            QMessageBox.warning(self, "Impossible", "Il doit rester au moins un format.")
            return
        nom = self._formats[row].get("nom", "ce format")
        reply = QMessageBox.question(
            self, "Supprimer", f"Supprimer le profil « {nom} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._formats.pop(row)
            sauvegarder_formats(self._formats)
            self._charger_liste_formats()

    def _monter_format(self):
        row = self.liste_formats.currentRow()
        if row > 0:
            self._formats.insert(row - 1, self._formats.pop(row))
            sauvegarder_formats(self._formats)
            self._charger_liste_formats()
            self.liste_formats.setCurrentRow(row - 1)

    def _descendre_format(self):
        row = self.liste_formats.currentRow()
        if row < len(self._formats) - 1:
            self._formats.insert(row + 1, self._formats.pop(row))
            sauvegarder_formats(self._formats)
            self._charger_liste_formats()
            self.liste_formats.setCurrentRow(row + 1)

    # ── Colonnes ────────────────────────────────────────────────────────────

    def _charger_liste(self):
        self.liste.clear()
        for col in charger_config():
            self.liste.addItem(col)

    def _monter(self):
        row = self.liste.currentRow()
        if row > 0:
            item = self.liste.takeItem(row)
            self.liste.insertItem(row - 1, item)
            self.liste.setCurrentRow(row - 1)

    def _descendre(self):
        row = self.liste.currentRow()
        if row < self.liste.count() - 1:
            item = self.liste.takeItem(row)
            self.liste.insertItem(row + 1, item)
            self.liste.setCurrentRow(row + 1)

    def _reset(self):
        reply = QMessageBox.question(
            self, "Réinitialiser",
            "Remettre l'ordre par défaut ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            sauvegarder_config(COLONNES_DEFAUT.copy())
            self._charger_liste()

    def _sauvegarder(self):
        ordre = [self.liste.item(i).text() for i in range(self.liste.count())]
        sauvegarder_config(ordre)
        QMessageBox.information(self, "Sauvegardé", "L'ordre des colonnes a été sauvegardé.")

    def get_ordre(self) -> list:
        return [self.liste.item(i).text() for i in range(self.liste.count())]
