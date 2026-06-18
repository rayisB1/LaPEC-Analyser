from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget,
    QFileDialog, QTableWidget,
    QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from src.core.parser import parse_vo2_file

class PageImport(QWidget):
    def __init__(self):
        super().__init__()
        self.fichiers = {}  # nom -> DataFrame
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Titre
        title = QLabel("Importer des fichiers")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(title)

        # Bouton import
        btn_import = QPushButton("+ Ajouter des fichiers PDF")
        btn_import.setStyleSheet("""
            QPushButton {
                background-color: #4f8ef7;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3a7de0; }
        """)
        btn_import.clicked.connect(self._importer)
        layout.addWidget(btn_import, alignment=Qt.AlignmentFlag.AlignLeft)

        # Zone principale : liste + aperçu
        content = QHBoxLayout()

        # Liste des fichiers
        left = QVBoxLayout()
        left.addWidget(QLabel("Fichiers chargés :"))
        self.liste = QListWidget()
        self.liste.setFixedWidth(250)
        self.liste.currentItemChanged.connect(self._afficher_apercu)
        left.addWidget(self.liste)

        btn_suppr = QPushButton("Supprimer le fichier")
        btn_suppr.setStyleSheet("""
            QPushButton {
                background-color: #e05c3a;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #c44e30; }
        """)
        btn_suppr.clicked.connect(self._supprimer)
        left.addWidget(btn_suppr)

        content.addLayout(left)

        # Aperçu tableau
        right = QVBoxLayout()
        self.label_apercu = QLabel("Sélectionne un fichier pour voir un aperçu")
        right.addWidget(self.label_apercu)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { color: #2b2d3b; background-color: white; }
            QTableWidget::item:selected { background-color: #c8d8f8; color: #2b2d3b; }
            QHeaderView::section {
                background-color: #e8eaf0;
                color: #2b2d3b;
                padding: 6px 10px;
                border: none;
                border-right: 1px solid #ccc;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:hover { background-color: #d0d5e8; }
        """)
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        right.addWidget(self.table)
        content.addLayout(right)

        layout.addLayout(content)

    def _importer(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Ouvrir fichiers VO2", "", "Fichiers PDF (*.pdf);;Tous (*.*)"
        )
        for path in paths:
            try:
                df = parse_vo2_file(path)
                nom = path.split('/')[-1].split('\\')[-1]
                self.fichiers[nom] = df
                if not self.liste.findItems(nom, Qt.MatchFlag.MatchExactly):
                    self.liste.addItem(nom)
            except Exception as e:
                import traceback
                QMessageBox.warning(self, "Erreur", traceback.format_exc())

    def _supprimer(self):
        item = self.liste.currentItem()
        if item:
            del self.fichiers[item.text()]
            self.liste.takeItem(self.liste.row(item))
            self.table.clear()
            self.label_apercu.setText("Sélectionne un fichier pour voir un aperçu")

    def _afficher_apercu(self, item):
        if item is None:
            return
        df = self.fichiers.get(item.text())
        if df is None:
            return

        self.label_apercu.setText(
            f"{item.text()} — {len(df)} lignes, {len(df.columns)} colonnes"
        )

        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(list(df.columns))

        for i, row in df.iterrows():
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))
