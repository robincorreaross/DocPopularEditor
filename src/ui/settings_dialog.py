"""
SettingsDialog - Diálogo de configurações do DocPopularEditor.
Integra as funcionalidades do DocPopular (Armazenamento + Scanner)
com o layout premium do Ross PDF Editor.
"""

import os
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QFrame, QMessageBox,
    QLineEdit, QFileDialog, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QSize, Signal, QObject

from src.engine.scan_engine import ScannerEngine
from src.core.config import load_settings, save_settings


# ── Sinais para comunicação Thread → UI ─────────────────────────────────────

class _ScanTestSignals(QObject):
    finished = Signal(str, bool)  # mensagem, sucesso


# ── Estilos ─────────────────────────────────────────────────────────────────

_DIALOG_STYLE = """
QDialog { background-color: #0D1B2A; }
QLabel  { color: #E3F2FD; }
"""

_ENTRY_RO = """
QLineEdit {
    background-color: #1A2D40;
    color: #B0BEC5;
    border: 1px solid #2D4A6A;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}
"""

_COMBO = """
QComboBox {
    background-color: #1A2D40;
    color: #E3F2FD;
    border: 1px solid #2D4A6A;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
QComboBox:focus { border: 1px solid #4FC3F7; }
QComboBox QAbstractItemView {
    background-color: #0D2137;
    color: #E3F2FD;
    selection-background-color: #1565C0;
}
"""

_BTN_PRIMARY = """
QPushButton {
    background-color: #1565C0;
    color: white; border: none; border-radius: 8px;
    font-size: 13px; font-weight: bold; padding: 10px 24px;
}
QPushButton:hover { background-color: #1976D2; }
"""

_BTN_SECONDARY = """
QPushButton {
    background-color: #1E3A5F;
    color: white; border: none; border-radius: 8px;
    font-size: 12px; font-weight: bold; padding: 8px 16px;
}
QPushButton:hover { background-color: #1565C0; }
"""

_BTN_DARK = """
QPushButton {
    background-color: #37474F;
    color: white; border: none; border-radius: 8px;
    font-size: 12px; font-weight: bold; padding: 8px 16px;
}
QPushButton:hover { background-color: #455A64; }
"""

_BTN_GREEN = """
QPushButton {
    background-color: #2E7D32;
    color: white; border: none; border-radius: 8px;
    font-size: 13px; font-weight: bold; padding: 10px 24px;
}
QPushButton:hover { background-color: #388E3C; }
"""


class SettingsDialog(QDialog):
    """
    Diálogo de configurações do DocPopularEditor.
    Seções: Armazenamento (pasta de saída) e Scanner (seleção + teste).
    Usa config.py (load_settings / save_settings) como backend persistente.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scanner_engine = ScannerEngine()
        self._scan_signals = _ScanTestSignals()
        self._scan_signals.finished.connect(self._on_scan_test_done)

        self._settings = load_settings()
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("Configurações")
        self.setMinimumSize(520, 460)
        self.resize(560, 520)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Cabeçalho ──────────────────────────────────────────

        header = QWidget()
        header.setStyleSheet("background: transparent;")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(32, 28, 32, 16)
        h_lay.setSpacing(4)

        lbl_title = QLabel("⚙️  Configurações")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4FC3F7; background: transparent;")
        h_lay.addWidget(lbl_title)

        lbl_sub = QLabel("Gerencie as configurações de armazenamento e scanner.")
        lbl_sub.setStyleSheet("font-size: 13px; color: #78909C; background: transparent;")
        h_lay.addWidget(lbl_sub)

        root.addWidget(header)

        # Separador
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1E3450; border: none;")
        root.addWidget(sep)

        # ── Área scrollável ────────────────────────────────────

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #0D1B2A; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #2D4A6A; border-radius: 4px; min-height: 40px; }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(container)
        self._content_layout.setContentsMargins(32, 16, 32, 16)
        self._content_layout.setSpacing(16)

        self._build_storage_section()
        self._build_scanner_section()

        self._content_layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        # ── Botões de ação ─────────────────────────────────────

        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(32, 12, 32, 20)
        f_lay.setSpacing(12)

        f_lay.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet(_BTN_DARK)
        btn_cancel.setFixedHeight(42)
        btn_cancel.clicked.connect(self.reject)
        f_lay.addWidget(btn_cancel)

        btn_save = QPushButton("💾  Salvar Configurações")
        btn_save.setStyleSheet(_BTN_GREEN)
        btn_save.setFixedHeight(42)
        btn_save.clicked.connect(self._save_and_close)
        f_lay.addWidget(btn_save)

        root.addWidget(footer)

    # ── Seção Armazenamento ─────────────────────────────────────────────────

    def _build_storage_section(self):
        section = self._make_section("📂  Armazenamento")
        self._content_layout.addWidget(section)

        inner = section.findChild(QWidget, "section_inner")

        lbl = QLabel("Pasta de saída dos PDFs:")
        lbl.setStyleSheet("color: #90A4AE; font-size: 12px; background: transparent;")
        inner.layout().addWidget(lbl)

        # Linha: campo + botão alterar
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self.entry_folder = QLineEdit()
        self.entry_folder.setReadOnly(True)
        self.entry_folder.setStyleSheet(_ENTRY_RO)
        self.entry_folder.setFixedHeight(38)
        row_layout.addWidget(self.entry_folder, stretch=1)

        btn_change = QPushButton("📂  Alterar")
        btn_change.setStyleSheet(_BTN_SECONDARY)
        btn_change.setFixedWidth(110)
        btn_change.setFixedHeight(38)
        btn_change.clicked.connect(self._choose_folder)
        row_layout.addWidget(btn_change)

        inner.layout().addWidget(row)

        # Contagem de PDFs
        self.lbl_pdf_count = QLabel("")
        self.lbl_pdf_count.setStyleSheet("color: #546E7A; font-size: 11px; background: transparent;")
        inner.layout().addWidget(self.lbl_pdf_count)

    # ── Seção Scanner ──────────────────────────────────────────────────────

    def _build_scanner_section(self):
        section = self._make_section("🖨️  Scanner")
        self._content_layout.addWidget(section)

        inner = section.findChild(QWidget, "section_inner")

        lbl = QLabel("Scanner selecionado:")
        lbl.setStyleSheet("color: #90A4AE; font-size: 12px; background: transparent;")
        inner.layout().addWidget(lbl)

        # Linha: combo + atualizar + testar
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self.cb_scanners = QComboBox()
        self.cb_scanners.setStyleSheet(_COMBO)
        self.cb_scanners.setFixedHeight(38)
        row_layout.addWidget(self.cb_scanners, stretch=1)

        btn_refresh = QPushButton("🔄  Atualizar")
        btn_refresh.setStyleSheet(_BTN_SECONDARY)
        btn_refresh.setFixedWidth(110)
        btn_refresh.setFixedHeight(38)
        btn_refresh.clicked.connect(self._refresh_scanners)
        row_layout.addWidget(btn_refresh)

        self.btn_test = QPushButton("🧪  Testar")
        self.btn_test.setStyleSheet(_BTN_DARK)
        self.btn_test.setFixedWidth(90)
        self.btn_test.setFixedHeight(38)
        self.btn_test.clicked.connect(self._test_scanner)
        row_layout.addWidget(self.btn_test)

        inner.layout().addWidget(row)

        # Status do scanner
        self.lbl_scanner_status = QLabel(
            "ℹ️  Caso nenhum scanner seja detectado, o sistema usará importação de arquivo."
        )
        self.lbl_scanner_status.setStyleSheet("color: #546E7A; font-size: 11px; background: transparent;")
        self.lbl_scanner_status.setWordWrap(True)
        inner.layout().addWidget(self.lbl_scanner_status)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_section(self, title: str) -> QFrame:
        """Cria um card de seção com título e conteúdo interno."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame#section_card {
                background-color: #0D2137;
                border: 1px solid #1E3450;
                border-radius: 12px;
            }
        """)
        card.setObjectName("section_card")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4FC3F7; background: transparent; border:none;")
        card_layout.addWidget(lbl_title)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1E3450; border: none;")
        card_layout.addWidget(sep)

        inner = QWidget()
        inner.setObjectName("section_inner")
        inner.setStyleSheet("background: transparent;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 4, 0, 0)
        inner_layout.setSpacing(6)
        card_layout.addWidget(inner)

        return card

    def _load_data(self):
        """Popula os campos com as configurações carregadas."""
        # Armazenamento
        folder = self._settings.get("output_folder", "")
        self.entry_folder.setText(folder)
        self._update_pdf_count()

        # Scanner
        self._refresh_scanners()
        saved_scanner = self._settings.get("scanner_name", "")
        if saved_scanner:
            idx = self.cb_scanners.findText(saved_scanner)
            if idx >= 0:
                self.cb_scanners.setCurrentIndex(idx)

    def _choose_folder(self):
        """Abre diálogo para seleção da pasta de saída."""
        current = self.entry_folder.text() or str(Path.home())
        path = QFileDialog.getExistingDirectory(
            self, "Selecionar pasta de saída dos PDFs", current
        )
        if path:
            self.entry_folder.setText(path)
            self._settings["output_folder"] = path
            self._update_pdf_count()

    def _update_pdf_count(self):
        """Atualiza a contagem de PDFs na pasta configurada."""
        folder = self.entry_folder.text()
        if folder and Path(folder).exists():
            count = len(list(Path(folder).glob("*.pdf")))
            self.lbl_pdf_count.setText(f"📄  {count} arquivo(s) PDF salvos nesta pasta.")
        else:
            self.lbl_pdf_count.setText(
                "⚠️  Pasta não existe ainda (será criada ao salvar o primeiro PDF)."
            )

    def _refresh_scanners(self):
        """Busca scanners disponíveis e popula o combobox."""
        current = self.cb_scanners.currentText()
        self.cb_scanners.clear()

        try:
            scanners = self.scanner_engine.list_scanners()
        except Exception:
            scanners = []

        if not scanners:
            self.cb_scanners.addItem("(Nenhum scanner detectado)")
            self.cb_scanners.setEnabled(False)
            self.btn_test.setEnabled(False)
            self.lbl_scanner_status.setText("❌  Nenhum scanner encontrado.")
            self.lbl_scanner_status.setStyleSheet(
                "color: #EF5350; font-size: 11px; background: transparent;"
            )
        else:
            self.cb_scanners.addItems(scanners)
            self.cb_scanners.setEnabled(True)
            self.btn_test.setEnabled(True)
            idx = self.cb_scanners.findText(current)
            if idx >= 0:
                self.cb_scanners.setCurrentIndex(idx)
            self.lbl_scanner_status.setText(
                f"✅  {len(scanners)} scanner(s) detectado(s)."
            )
            self.lbl_scanner_status.setStyleSheet(
                "color: #66BB6A; font-size: 11px; background: transparent;"
            )

    def _test_scanner(self):
        """Executa um scan de teste em thread separada."""
        scanner_name = self.cb_scanners.currentText()
        if not scanner_name or "(Nenhum" in scanner_name:
            QMessageBox.warning(self, "Scanner", "Nenhum scanner selecionado.")
            return

        self.btn_test.setEnabled(False)
        self.lbl_scanner_status.setText("⌛  Realizando scan de teste...")
        self.lbl_scanner_status.setStyleSheet(
            "color: #FFB74D; font-size: 11px; background: transparent;"
        )

        def _run():
            try:
                img, err = self.scanner_engine.scan_page(scanner_name)
                if img:
                    msg = f"✅  Scan de teste bem-sucedido! ({img.size[0]}×{img.size[1]} px)"
                    self._scan_signals.finished.emit(msg, True)
                else:
                    err_msg = f"❌  Falha no scan: {err}" if err else "❌  Falha no scan de teste."
                    self._scan_signals.finished.emit(err_msg, False)
            except Exception as e:
                self._scan_signals.finished.emit(f"❌  Erro: {e}", False)

        threading.Thread(target=_run, daemon=True).start()

    def _on_scan_test_done(self, msg: str, success: bool):
        """Callback do teste de scanner (na thread principal)."""
        self.btn_test.setEnabled(True)
        self.lbl_scanner_status.setText(msg)
        color = "#66BB6A" if success else "#EF5350"
        self.lbl_scanner_status.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent;"
        )

    def _save_and_close(self):
        """Salva as configurações usando config.py e fecha o diálogo."""
        # Captura valores atuais
        self._settings["output_folder"] = self.entry_folder.text()

        scanner_val = self.cb_scanners.currentText()
        self._settings["scanner_name"] = scanner_val if "(Nenhum" not in scanner_val else ""

        try:
            save_settings(self._settings)
        except Exception as e:
            QMessageBox.critical(
                self, "Erro ao Salvar",
                f"Não foi possível salvar as configurações:\n{e}"
            )
            return

        self.accept()
