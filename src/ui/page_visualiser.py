import matplotlib
matplotlib.use("QtAgg")
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QSizePolicy,
    QScrollArea, QTableWidget, QTableWidgetItem, QMenu
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker


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

        btn = QPushButton("Actualiser")
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

        btn_reset1 = QPushButton("Vue initiale")
        btn_reset1.setFixedWidth(110)
        btn_reset1.setStyleSheet(self._style_btn_reset())
        btn_reset1.clicked.connect(lambda: (self.ax1.autoscale(), self.canvas1.draw_idle()))
        layout.addWidget(btn_reset1, alignment=Qt.AlignmentFlag.AlignRight)

        self.fig2 = Figure(figsize=(10, 2.5), facecolor="#f5f5f5")
        self.ax2 = self.fig2.add_subplot(111)
        self.canvas2 = FigureCanvas(self.fig2)
        self.canvas2.setFixedHeight(220)
        self.canvas2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.canvas2)

        btn_reset2 = QPushButton("Vue initiale")
        btn_reset2.setFixedWidth(110)
        btn_reset2.setStyleSheet(self._style_btn_reset())
        btn_reset2.clicked.connect(lambda: (self.ax2.autoscale(), self.canvas2.draw_idle()))
        layout.addWidget(btn_reset2, alignment=Qt.AlignmentFlag.AlignRight)

        self._annot1 = None
        self._annot2 = None
        self._x_lignes_data = []
        self._x_temps_data = []
        self._df_courant = None
        self.canvas1.mpl_connect("button_press_event", self._on_clic_fio2)
        self.canvas2.mpl_connect("button_press_event", self._on_clic_pet)
        self.canvas1.mpl_connect("scroll_event", self._on_scroll)
        self.canvas2.mpl_connect("scroll_event", self._on_scroll)

        # Tableau des données avec colonnes déplaçables
        lbl_table = QLabel("Données brutes")
        lbl_table.setStyleSheet("font-size: 14px; font-weight: bold; color: #2b2d3b;")
        layout.addWidget(lbl_table)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(500)
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
        header.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_contextuel)
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
        self._annot1 = None
        self._annot2 = None
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self._df_courant = df
        self._x_lignes_data = []
        self._x_temps_data = []

        if df is not None and not df.empty:
            x_lignes = list(range(len(df)))
            x_temps = self._temps_en_secondes(df) if "Temps" in df.columns else x_lignes
            self._x_lignes_data = x_lignes
            self._x_temps_data = x_temps

            fmt = ticker.FuncFormatter(lambda v, _: f"{int(v)//60:02d}:{int(v)%60:02d}")
            loc = ticker.MaxNLocator(nbins=10, integer=True)

            if "FiO2" in df.columns:
                self.ax1.plot(x_lignes, df["FiO2"], color="#e05c3a", linewidth=1.5)

            if "PetO2" in df.columns:
                self.ax2.plot(x_temps, df["PetO2"], color="#e05c3a", linewidth=1.5, label="PetO2")
            if "PetCO2" in df.columns:
                self.ax2.plot(x_temps, df["PetCO2"], color="#4f8ef7", linewidth=1.5, label="PetCO2")
            if "PetO2" in df.columns or "PetCO2" in df.columns:
                self.ax2.legend(fontsize=9)
                self.ax2.xaxis.set_major_formatter(fmt)
                self.ax2.xaxis.set_major_locator(loc)
                self.ax2.tick_params(axis="x", rotation=30, labelsize=8)

            # Remplir le tableau
            self.table.setRowCount(len(df))
            self.table.setColumnCount(len(df.columns))
            self.table.setHorizontalHeaderLabels(list(df.columns))
            for i, row in df.iterrows():
                for j, val in enumerate(row):
                    text = "" if pd.isna(val) else str(val)
                    self.table.setItem(i, j, QTableWidgetItem(text))

        self._style_axes()
        self.canvas1.draw()
        self.canvas2.draw()

    def _menu_contextuel(self, pos):
        lignes = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not lignes:
            return
        menu = QMenu(self)
        n = len(lignes)
        libelle = f"Vider {n} ligne{'s' if n > 1 else ''} sélectionnée{'s' if n > 1 else ''}"
        action = menu.addAction(libelle)
        action.triggered.connect(lambda: self._vider_lignes(lignes))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _vider_lignes(self, lignes):
        nom = self.combo.currentText()
        df = self.fichiers.get(nom)
        if df is None:
            return
        cols_a_vider = [c for c in df.columns if c != "Temps"]
        for r in lignes:
            df.loc[df.index[r], cols_a_vider] = None
        self.fichiers[nom] = df
        self._tracer()

    def _temps_en_secondes(self, df):
        result = []
        for v in df["Temps"]:
            try:
                m, s = str(v).split(":")
                result.append(int(m) * 60 + int(s))
            except Exception:
                result.append(None)
        return result

    def _style_btn_reset(self):
        return """
            QPushButton {
                background-color: #f0f0f0;
                color: #2b2d3b;
                border: 1px solid #ccc;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """

    def _on_scroll(self, event):
        ax = event.inaxes
        if ax not in (self.ax1, self.ax2) or event.xdata is None:
            return
        factor = 0.75 if event.button == "up" else 1.33
        for get, set_ in [(ax.get_xlim, ax.set_xlim), (ax.get_ylim, ax.set_ylim)]:
            lo, hi = get()
            pivot = event.xdata if get == ax.get_xlim else event.ydata
            set_([pivot + (v - pivot) * factor for v in (lo, hi)])
        canvas = self.canvas1 if ax == self.ax1 else self.canvas2
        canvas.draw_idle()

    def _on_clic_fio2(self, event):
        if event.dblclick and event.inaxes == self.ax1:
            self.ax1.autoscale()
            self.canvas1.draw_idle()
            return
        if event.inaxes != self.ax1 or not self._x_lignes_data:
            if self._annot1:
                self._annot1.set_visible(False)
                self.canvas1.draw_idle()
            return
        df = self._df_courant
        if df is None or df.empty or "FiO2" not in df.columns:
            return
        idx, _ = min(enumerate(self._x_lignes_data), key=lambda t: abs(t[1] - event.xdata))
        row = df.iloc[idx]
        val = row["FiO2"]
        if pd.isna(val):
            return
        temps = df["Temps"].iloc[idx] if "Temps" in df.columns else str(idx)
        text = f"Ligne : {idx}\nTemps : {temps}\nFiO2 : {val}"
        self._afficher_annot(self.ax1, self.canvas1, "_annot1",
                             self._x_lignes_data[idx], val, text)

    def _on_clic_pet(self, event):
        if event.dblclick and event.inaxes == self.ax2:
            self.ax2.autoscale()
            self.canvas2.draw_idle()
            return
        if event.inaxes != self.ax2 or not self._x_temps_data:
            if self._annot2:
                self._annot2.set_visible(False)
                self.canvas2.draw_idle()
            return
        df = self._df_courant
        if df is None or df.empty:
            return
        valid = [(i, x) for i, x in enumerate(self._x_temps_data) if x is not None]
        if not valid:
            return
        idx, x_pt = min(valid, key=lambda t: abs(t[1] - event.xdata))
        row = df.iloc[idx]
        temps = df["Temps"].iloc[idx] if "Temps" in df.columns else str(idx)
        lines = [f"Temps : {temps}"]
        y_pt = None
        for col in ["PetO2", "PetCO2"]:
            if col in df.columns:
                v = row[col]
                lines.append(f"{col} : {'' if pd.isna(v) else v}")
                if not pd.isna(v):
                    if y_pt is None or abs(v - event.ydata) < abs(y_pt - event.ydata):
                        y_pt = v
        if y_pt is None:
            return
        self._afficher_annot(self.ax2, self.canvas2, "_annot2",
                             x_pt, y_pt, "\n".join(lines))

    def _afficher_annot(self, ax, canvas, attr, x, y, text):
        annot = getattr(self, attr)
        if annot is None:
            annot = ax.annotate(
                text,
                xy=(x, y),
                xytext=(15, 15),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#888", alpha=0.93),
                arrowprops=dict(arrowstyle="->", color="#555", lw=1.2),
                fontsize=9,
                color="#2b2d3b",
            )
            setattr(self, attr, annot)
        else:
            annot.set_text(text)
            annot.xy = (x, y)
            annot.set_visible(True)
        canvas.draw_idle()

    def _style_axes(self):
        for ax, fig, titre, ylabel, xlabel in [
            (self.ax1, self.fig1, "FiO2", "FiO2", "Numéro de ligne"),
            (self.ax2, self.fig2, "PetO2 / PetCO2", "Pression (mmHg)", "Temps"),
        ]:
            ax.set_facecolor("white")
            ax.set_title(titre, fontsize=11, color="#2b2d3b", pad=8)
            ax.set_xlabel(xlabel, fontsize=9, color="#555555")
            ax.set_ylabel(ylabel, fontsize=9, color="#555555")
            ax.tick_params(colors="#555555", labelsize=8)
            ax.grid(True, alpha=0.3, linestyle="--")
            for spine in ax.spines.values():
                spine.set_edgecolor("#dddddd")
            fig.tight_layout()
