import matplotlib
matplotlib.use("QtAgg")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QSizePolicy,
    QScrollArea, QTableWidget, QTableWidgetItem
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PageVisualiser(QWidget):
    def __init__(self, fichiers: dict):
        super().__init__()
        self.fichiers = fichiers
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Visualiser les données")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(title)

        # Sélecteur de fichier
        row = QHBoxLayout()
        lbl = QLabel("Fichier :")
        lbl.setStyleSheet("font-size: 13px; color: #2b2d3b;")
        row.addWidget(lbl)

        self.combo = QComboBox()
        self.combo.setMinimumWidth(300)
        self.combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
                background: white;
            }
            QComboBox::drop-down { border: none; }
        """)
        self.combo.currentIndexChanged.connect(self._tracer)
        row.addWidget(self.combo)

        btn = QPushButton("⟳ Actualiser")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #4f8ef7;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3a7de0; }
        """)
        btn.clicked.connect(self._rafraichir_liste)
        row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)

        # Graphiques empilés verticalement
        self.fig1 = Figure(figsize=(10, 2.5), facecolor="#f5f5f5")
        self.ax1 = self.fig1.add_subplot(111)
        self.canvas1 = FigureCanvas(self.fig1)
        self.canvas1.setFixedHeight(220)
        self.canvas1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.canvas1)

        self.fig2 = Figure(figsize=(10, 2.5), facecolor="#f5f5f5")
        self.ax2 = self.fig2.add_subplot(111)
        self.canvas2 = FigureCanvas(self.fig2)
        self.canvas2.setFixedHeight(220)
        self.canvas2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.canvas2)

        # Tableau des données avec colonnes déplaçables
        lbl_table = QLabel("Données brutes")
        lbl_table.setStyleSheet("font-size: 14px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(lbl_table)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(220)
        header = self.table.horizontalHeader()
        header.setSectionsMovable(True)
        header.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #e8eaf0;
                color: #2b2d3b;
                padding: 6px 10px;
                border: none;
                border-right: 1px solid #ccc;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:hover {
                background-color: #d0d5e8;
                cursor: grab;
            }
        """)
        layout.addWidget(self.table)

        self._style_axes()

    def showEvent(self, event):
        super().showEvent(event)
        self._rafraichir_liste()

    def _rafraichir_liste(self):
        current = self.combo.currentText()
        self.combo.blockSignals(True)
        self.combo.clear()
        for nom in self.fichiers:
            self.combo.addItem(nom)
        idx = self.combo.findText(current)
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo.blockSignals(False)
        self._tracer()

    def _tracer(self):
        nom = self.combo.currentText()
        df = self.fichiers.get(nom)

        self.ax1.clear()
        self.ax2.clear()
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        if df is not None and not df.empty:
            x = range(len(df))

            if "FiO2" in df.columns:
                self.ax1.plot(x, df["FiO2"], color="#4f8ef7", linewidth=1.5)

            if "PetO2" in df.columns:
                self.ax2.plot(x, df["PetO2"], color="#4f8ef7", linewidth=1.5, label="PetO2")
            if "PetCO2" in df.columns:
                self.ax2.plot(x, df["PetCO2"], color="#e05c3a", linewidth=1.5, label="PetCO2")
            if "PetO2" in df.columns or "PetCO2" in df.columns:
                self.ax2.legend(fontsize=9)

            # Remplir le tableau
            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels(list(df.columns))
            for i, row in df.iterrows():
                for j, val in enumerate(row):
                    self.table.setItem(i, j, QTableWidgetItem(str(val)))

        self._style_axes()
        self.canvas1.draw()
        self.canvas2.draw()

    def _style_axes(self):
        for ax, fig, titre, ylabel in [
            (self.ax1, self.fig1, "FiO2 par ligne", "FiO2"),
            (self.ax2, self.fig2, "PetO2 / PetCO2 par ligne", "Pression (mmHg)"),
        ]:
            ax.set_facecolor("white")
            ax.set_title(titre, fontsize=11, color="#2b2d3b", pad=8)
            ax.set_xlabel("Numéro de ligne", fontsize=9, color="#555555")
            ax.set_ylabel(ylabel, fontsize=9, color="#555555")
            ax.tick_params(colors="#555555", labelsize=8)
            ax.grid(True, alpha=0.3, linestyle="--")
            for spine in ax.spines.values():
                spine.set_edgecolor("#dddddd")
            fig.tight_layout()
