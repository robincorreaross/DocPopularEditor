"""
search_dialog.py - Diálogo de busca de documentos por CPF.
Portado do DocPopular para PySide6.
"""

import os
from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QWidget, QFileDialog, QMessageBox
)

from src.core.cpf_manager import find_all_documents_by_cpf, validate_cpf


def _aplicar_mascara_cpf(entry: QLineEdit, text: str) -> str:
    apenas_nums = "".join(filter(str.isdigit, text))[:11]
    novo = ""
    for i, d in enumerate(apenas_nums):
        if i in (3, 6):
            novo += "."
        elif i == 9:
            novo += "-"
        novo += d
    if text != novo:
        pos = entry.cursorPosition()
        entry.blockSignals(True)
        entry.setText(novo)
        entry.blockSignals(False)
        entry.setCursorPosition(min(pos, len(novo)))
    return novo


_ENTRY_STYLE = """
QLineEdit {
    background-color: #1A2D40;
    color: #E3F2FD;
    border: 1px solid #2D4A6A;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 15px;
}
QLineEdit:focus { border: 1px solid #4FC3F7; }
"""

_BTN_BLUE = """
QPushButton {
    background-color: #1565C0;
    color: white; border: none; border-radius: 8px;
    font-size: 13px; font-weight: bold; padding: 10px 20px;
}
QPushButton:hover { background-color: #1976D2; }
QPushButton:disabled { background-color: #1A2D40; color: #445566; }
"""

_BTN_GREEN = """
QPushButton {
    background-color: #2E7D32;
    color: white; border: none; border-radius: 8px;
    font-size: 12px; font-weight: bold; padding: 8px 16px;
}
QPushButton:hover { background-color: #388E3C; }
"""

_BTN_GRAY = """
QPushButton {
    background-color: #37474F;
    color: white; border: none; border-radius: 8px;
    font-size: 12px; font-weight: bold; padding: 8px 16px;
}
QPushButton:hover { background-color: #455A64; }
"""


class SearchDialog(QDialog):
    """
    Diálogo de busca de documentos por CPF.
    O usuário digita o CPF e vê todos os documentos salvos associados.
    """

    def __init__(self, parent, settings: dict):
        super().__init__(parent)
        self.settings = settings
        self._paths: List[str] = []

        self.setWindowTitle("Procurar Documento por CPF")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.resize(680, 560)
        self.setStyleSheet("QDialog { background-color: #0D1B2A; } QLabel { color: #E3F2FD; }")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(16)

        # Título
        lbl_title = QLabel("🔍  Procurar Documento por CPF")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4FC3F7; background: transparent;")
        root.addWidget(lbl_title)

        lbl_sub = QLabel("Digite o CPF do paciente para localizar documentos salvos.")
        lbl_sub.setStyleSheet("font-size: 13px; color: #78909C; background: transparent;")
        root.addWidget(lbl_sub)

        # Campo CPF + botão buscar
        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(12)

        self.entry_cpf = QLineEdit()
        self.entry_cpf.setPlaceholderText("000.000.000-00")
        self.entry_cpf.setStyleSheet(_ENTRY_STYLE)
        self.entry_cpf.setFixedHeight(44)
        self.entry_cpf.textChanged.connect(self._on_cpf_changed)
        self.entry_cpf.returnPressed.connect(self._do_search)
        search_layout.addWidget(self.entry_cpf, stretch=1)

        self.btn_search = QPushButton("🔍  Buscar")
        self.btn_search.setStyleSheet(_BTN_BLUE)
        self.btn_search.setFixedHeight(44)
        self.btn_search.setEnabled(False)
        self.btn_search.clicked.connect(self._do_search)
        search_layout.addWidget(self.btn_search)

        root.addWidget(search_row)

        # Label de erro CPF
        self.lbl_cpf_error = QLabel("")
        self.lbl_cpf_error.setStyleSheet("color: #FF5252; font-size: 12px; background: transparent;")
        self.lbl_cpf_error.hide()
        root.addWidget(self.lbl_cpf_error)

        # Separador
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1E3450; border: none;")
        root.addWidget(sep)

        # Área de resultados
        self.lbl_result_title = QLabel("Resultados")
        self.lbl_result_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #90A4AE; background: transparent;")
        root.addWidget(self.lbl_result_title)

        # Scroll para as previews
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: #0D1B2A; width: 8px; border-radius: 4px; }
            QScrollBar::handle:vertical { background: #2D4A6A; border-radius: 4px; min-height: 40px; }
        """)
        self.result_container = QWidget()
        self.result_container.setStyleSheet("background: transparent;")
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(4, 4, 4, 4)
        self.result_layout.setSpacing(8)
        self.result_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.result_container)
        root.addWidget(self.scroll, stretch=1)

        # Placeholder inicial
        self._mostrar_placeholder("Digite um CPF e clique em Buscar.")

        # Botão fechar
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setStyleSheet(_BTN_GRAY)
        btn_fechar.setFixedHeight(40)
        btn_fechar.clicked.connect(self.accept)
        root.addWidget(btn_fechar, alignment=Qt.AlignRight)

    def _on_cpf_changed(self, text: str):
        novo = _aplicar_mascara_cpf(self.entry_cpf, text)
        is_completo = len(novo) == 14
        is_valido = validate_cpf(novo)

        if is_completo and not is_valido:
            self.lbl_cpf_error.setText("⚠️ CPF inválido")
            self.lbl_cpf_error.show()
        else:
            self.lbl_cpf_error.hide()

        self.btn_search.setEnabled(is_completo and is_valido)

    def _do_search(self):
        cpf_formatado = self.entry_cpf.text()
        # Limpa o CPF para buscar no sistema de arquivos (apenas números)
        cpf_clean = "".join(filter(str.isdigit, cpf_formatado))
        try:
            paths = find_all_documents_by_cpf(cpf_clean, self.settings)
        except Exception as e:
            paths = []
            QMessageBox.warning(self, "Erro na Busca", f"Não foi possível buscar documentos:\n{e}")

        self._paths = paths
        self._render_results(cpf_clean, paths)

    def _render_results(self, cpf: str, paths: list):
        # Limpa os resultados anteriores
        for i in reversed(range(self.result_layout.count())):
            w = self.result_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        if not paths:
            self._mostrar_placeholder(f"Nenhum documento encontrado para o CPF {cpf}.")
            self.lbl_result_title.setText("Resultados — 0 documento(s)")
            return

        self.lbl_result_title.setText(f"Resultados — {len(paths)} documento(s) encontrado(s) para {cpf}")

        for path in paths:
            card = self._criar_card_documento(path)
            self.result_layout.addWidget(card)

    def _criar_card_documento(self, path: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0D2137;
                border: 1px solid #1E3450;
                border-radius: 10px;
            }
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(16)

        # Preview da imagem
        lbl_img = QLabel()
        lbl_img.setFixedSize(80, 100)
        lbl_img.setAlignment(Qt.AlignCenter)
        lbl_img.setStyleSheet("background-color: #1A2D40; border-radius: 6px; border: none;")
        try:
            pix = QPixmap(path)
            if not pix.isNull():
                lbl_img.setPixmap(
                    pix.scaled(80, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                lbl_img.setText("📄")
                lbl_img.setStyleSheet("font-size: 28px; background-color: #1A2D40; border-radius: 6px; border: none;")
        except Exception:
            lbl_img.setText("📄")
        card_layout.addWidget(lbl_img)

        # Informações do arquivo
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        nome = os.path.basename(path)
        lbl_nome = QLabel(str(nome))
        lbl_nome.setStyleSheet("color: #E3F2FD; font-size: 13px; font-weight: bold; background: transparent;")
        lbl_nome.setWordWrap(True)
        info_layout.addWidget(lbl_nome)

        try:
            tamanho = os.path.getsize(str(path)) / 1024
            lbl_info = QLabel(f"Tamanho: {tamanho:.1f} KB")
        except Exception:
            lbl_info = QLabel("Arquivo localizado")
        lbl_info.setStyleSheet("color: #78909C; font-size: 11px; background: transparent;")
        info_layout.addWidget(lbl_info)

        lbl_path = QLabel(str(path))
        lbl_path.setStyleSheet("color: #546E7A; font-size: 10px; background: transparent;")
        lbl_path.setWordWrap(True)
        info_layout.addWidget(lbl_path)

        info_layout.addStretch()
        card_layout.addLayout(info_layout, stretch=1)

        # Botões de ação
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        btn_abrir = QPushButton("📂  Abrir")
        btn_abrir.setStyleSheet(_BTN_GREEN)
        btn_abrir.setFixedWidth(110)
        btn_abrir.clicked.connect(lambda: self._abrir_arquivo(path))
        btn_layout.addWidget(btn_abrir)

        btn_pasta = QPushButton("📁  Ver Pasta")
        btn_pasta.setStyleSheet(_BTN_GRAY)
        btn_pasta.setFixedWidth(110)
        btn_pasta.clicked.connect(lambda: self._abrir_pasta(path))
        btn_layout.addWidget(btn_pasta)

        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)

        return card

    def _abrir_arquivo(self, path: str):
        """Abre o arquivo com o programa padrão do sistema."""
        try:
            os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível abrir o arquivo:\n{e}")

    def _abrir_pasta(self, path: str):
        """Abre o explorador na pasta do arquivo."""
        try:
            pasta = os.path.dirname(path)
            os.startfile(pasta)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível abrir a pasta:\n{e}")

    def _mostrar_placeholder(self, msg: str):
        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #37474F; font-size: 13px; background: transparent; padding: 40px;")
        self.result_layout.addWidget(lbl)
