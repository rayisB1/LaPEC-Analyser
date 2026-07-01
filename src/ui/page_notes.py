from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class PageNotes(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # En-tête
        header = QWidget()
        header.setStyleSheet("background-color: #f5f5f5;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(32, 28, 32, 16)

        row = QHBoxLayout()
        title = QLabel("Notes")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2b2d3b;")
        row.addWidget(title)
        row.addStretch()

        self.btn_effacer = QPushButton("Effacer")
        self.btn_effacer.setStyleSheet(self._style_secondaire())
        self.btn_effacer.clicked.connect(self._effacer)
        row.addWidget(self.btn_effacer)

        self.btn_exporter = QPushButton("Exporter en .txt")
        self.btn_exporter.setStyleSheet(self._style_primaire())
        self.btn_exporter.clicked.connect(self._exporter)
        row.addWidget(self.btn_exporter)

        header_layout.addLayout(row)
        outer.addWidget(header)

        # Zone de texte
        self.editeur = QPlainTextEdit()
        self.editeur.setPlaceholderText("Écrivez vos notes et remarques ici…")
        self.editeur.setFont(QFont("Consolas", 12))
        self.editeur.setStyleSheet("""
            QPlainTextEdit {
                background-color: white;
                color: #2b2d3b;
                border: none;
                padding: 24px 32px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        outer.addWidget(self.editeur)

    # ── Actions ────────────────────────────────────────────────────────────────

    def _effacer(self):
        if self.editeur.toPlainText().strip() == "":
            return
        rep = QMessageBox.question(
            self, "Effacer les notes",
            "Effacer tout le contenu des notes ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if rep == QMessageBox.StandardButton.Yes:
            self.editeur.clear()

    def _exporter(self):
        texte = self.editeur.toPlainText()
        if not texte.strip():
            QMessageBox.information(self, "Export", "Les notes sont vides.")
            return

        chemin, _ = QFileDialog.getSaveFileName(
            self, "Exporter les notes", "notes_lapec.txt",
            "Fichier texte (*.txt)"
        )
        if not chemin:
            return

        try:
            with open(chemin, "w", encoding="utf-8") as f:
                f.write(texte)
            QMessageBox.information(self, "Export réussi", f"Notes enregistrées :\n{chemin}")
        except Exception as exc:
            QMessageBox.critical(self, "Erreur d'export", str(exc))

    # ── Styles ─────────────────────────────────────────────────────────────────

    def _style_primaire(self):
        return """
            QPushButton {
                background-color: #4f8ef7; color: white; border: none;
                padding: 8px 18px; border-radius: 4px; font-size: 13px;
            }
            QPushButton:hover { background-color: #3a7de0; }
            QPushButton:pressed { background-color: #2d6bc7; }
        """

    def _style_secondaire(self):
        return """
            QPushButton {
                background-color: #f0f0f0; color: #2b2d3b;
                border: 1px solid #ccc;
                padding: 8px 18px; border-radius: 4px; font-size: 13px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """
