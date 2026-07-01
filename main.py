import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget
)
from PyQt6.QtCore import Qt
from src.ui.page_import import PageImport
from src.ui.page_filtrage import PageFiltrage
from src.ui.page_parametres import PageParametres
from src.ui.page_visualiser import PageVisualiser
from src.ui.page_resume import PageResume
from src.ui.page_notes import PageNotes

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAPEC Analyzer")
        self.setMinimumSize(1200, 700)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #2b2d3b;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        title = QLabel("LAPEC\nAnalyzer")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; padding: 24px 0;")
        sidebar_layout.addWidget(title)

        self.nav_buttons = []
        nav_items = [
            ("Importer", 0),
            ("Visualiser", 1),
            ("Filtrage et Moyenne", 2),
            ("Résumé", 3),
            ("Notes", 4),
            ("Paramètres", 5),
        ]

        for label, index in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    color: #aaaaaa;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding: 14px 20px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #3a3d50;
                    color: white;
                }
                QPushButton:checked {
                    background-color: #3a3d50;
                    color: white;
                    border-left: 3px solid #4f8ef7;
                }
            """)
            btn.clicked.connect(lambda checked, i=index: self._navigate(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()
        root.addWidget(sidebar)

        # Pages
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f5f5f5; color: #2b2d3b;")

        self.resume_data = {}  # nom -> résultat calculer_moyennes

        self.page_import = PageImport()
        self.stack.addWidget(self.page_import)
        self.stack.addWidget(PageVisualiser(self.page_import.fichiers))
        self.stack.addWidget(PageFiltrage(self.page_import.fichiers, self.resume_data))
        self.stack.addWidget(PageResume(self.resume_data))
        self.stack.addWidget(PageNotes())
        self.stack.addWidget(PageParametres())

        root.addWidget(self.stack)
        self._navigate(0)

    def _navigate(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _make_page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        label = QLabel(title)
        label.setStyleSheet("font-size: 22px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(label)
        layout.addStretch()
        return page


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())