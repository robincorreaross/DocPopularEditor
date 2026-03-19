"""
auditor_wizard.py - Tela de digitalização por etapas do DocPopularEditor.

Substitui o scan_screen.py do DocPopular (CustomTkinter → PySide6).
Integrado com a MainWindow via QWidget.
"""

import io
import threading
from typing import Optional, List

from PIL import Image
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QMessageBox, QProgressBar,
    QSizePolicy, QApplication
)

from src.core.transaction import Transaction
from src.core.cpf_manager import find_all_documents_by_cpf, save_cpf_documents, validate_cpf


THUMB_W = 120
THUMB_H = 140

# ─── Estilos ──────────────────────────────────────────────────────────────────

_BTN_STYLE = lambda bg, hover: f"""
QPushButton {{
    background-color: {bg};
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 13px;
    font-weight: bold;
    padding: 10px 0px;
}}
QPushButton:hover {{ background-color: {hover}; }}
QPushButton:disabled {{ background-color: #1A2D40; color: #445566; }}
"""

_ENTRY_STYLE = """
QLineEdit {
    background-color: #1A2D40;
    color: #E3F2FD;
    border: 1px solid #2D4A6A;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 14px;
}
QLineEdit:focus { border: 1px solid #1E88E5; }
"""

_THUMB_CARD_STYLE = """
QFrame#thumb_card {
    background-color: #0D2137;
    border: 1px solid #1E3450;
    border-radius: 8px;
}
"""


# ─── Thumb Card ───────────────────────────────────────────────────────────────

class _ThumbCard(QFrame):
    """Miniatura de uma imagem digitalizada com botão de remover."""
    delete_requested = Signal(int)

    def __init__(self, index: int, pil_image: Image.Image, parent=None):
        super().__init__(parent)
        self.index = index
        self.setObjectName("thumb_card")
        self.setStyleSheet(_THUMB_CARD_STYLE)
        self.setFixedWidth(THUMB_W + 24)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Imagem
        self.lbl_img = QLabel()
        self.lbl_img.setAlignment(Qt.AlignCenter)
        self.lbl_img.setFixedSize(THUMB_W, THUMB_H)
        self._set_image(pil_image)
        layout.addWidget(self.lbl_img, alignment=Qt.AlignCenter)

        # Número
        lbl_num = QLabel(f"Pág. {index + 1}")
        lbl_num.setAlignment(Qt.AlignCenter)
        lbl_num.setStyleSheet("color: #546E7A; font-size: 10px; background: transparent;")
        layout.addWidget(lbl_num)

        # Botão remover (posicionado absolutamente)
        self.btn_del = QPushButton("✕", self)
        self.btn_del.setFixedSize(26, 26)
        self.btn_del.setStyleSheet("""
            QPushButton {
                background-color: #B71C1C;
                color: white;
                border: none;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FF5252; }
        """)
        self.btn_del.clicked.connect(lambda: self.delete_requested.emit(self.index))
        self.btn_del.move(self.width() - 30, 4)
        self.btn_del.raise_()

    def _set_image(self, pil_image: Image.Image):
        img_copy = pil_image.copy()
        img_copy.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
        if img_copy.mode != "RGB":
            img_copy = img_copy.convert("RGB")
        buf = io.BytesIO()
        img_copy.save(buf, format="PNG")
        qimg = QImage()
        qimg.loadFromData(buf.getvalue())
        pixmap = QPixmap.fromImage(qimg).scaled(
            THUMB_W, THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.lbl_img.setPixmap(pixmap)

    def resizeEvent(self, event):
        self.btn_del.move(self.width() - 30, 4)
        super().resizeEvent(event)


# ─── Diálogo "Mais Páginas?" ──────────────────────────────────────────────────

class _MorePagesDialog(QMessageBox):
    def __init__(self, parent, etapa_titulo: str):
        super().__init__(parent)
        self.setWindowTitle("Mais páginas?")
        self.setText("Mais páginas?")
        self.setInformativeText(f"Existem mais páginas para «{etapa_titulo}»?")
        self.setStyleSheet("""
            QMessageBox { background-color: #0D1B2A; color: #E3F2FD; }
            QLabel { color: #E3F2FD; }
            QPushButton {
                background-color: #1E3A5F; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-size: 12px;
            }
            QPushButton:hover { background-color: #1565C0; }
        """)
        self.btn_sim = self.addButton("✔  Sim, há mais", QMessageBox.YesRole)
        self.btn_nao = self.addButton("▶  Não, próxima etapa", QMessageBox.NoRole)
        self.setDefaultButton(self.btn_nao)

    @property
    def result(self) -> str:
        clicked = self.clickedButton()
        if clicked == self.btn_nao:
            return "next"
        return "more"


# ─── Diálogo "Documento Encontrado" ───────────────────────────────────────────

class _FoundDocumentDialog(QMessageBox):
    def __init__(self, parent, cpf: str, image_path: Optional[str]):
        super().__init__(parent)
        self.setWindowTitle("Documento Encontrado")
        self.setText("Documento Já Existe")
        self.setInformativeText(
            f"Foi encontrado um documento de identificação\n"
            f"salvo para o CPF {cpf}.\n\nO que deseja fazer?"
        )
        self.setStyleSheet("""
            QMessageBox { background-color: #0D1B2A; color: #E3F2FD; }
            QLabel { color: #E3F2FD; }
            QPushButton {
                background-color: #1E3A5F; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-size: 12px;
            }
            QPushButton:hover { background-color: #1565C0; }
        """)
        if image_path:
            try:
                pix = QPixmap(image_path)
                if not pix.isNull():
                    self.setIconPixmap(
                        pix.scaled(90, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
            except Exception:
                pass

        self.btn_usar = self.addButton("📄  Usar Recente Salvo", QMessageBox.YesRole)
        self.btn_novo = self.addButton("📸  Fazer Nova e Substituir", QMessageBox.NoRole)

    @property
    def result(self) -> str:
        return "use" if self.clickedButton() == self.btn_usar else "new"


# ─── AuditorWizard ────────────────────────────────────────────────────────────

class AuditorWizard(QWidget):
    """
    Widget principal da digitalização por etapas.
    Exibido na área de conteúdo central da MainWindow no modo Transação.
    Emite 'concluido' quando todas as etapas forem finalizadas.
    """

    concluido = Signal(object)  # emite a Transaction finalizada
    cancelado = Signal()        # usuário cancelou a transação

    def __init__(self, transaction: Transaction, settings: dict, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        self.settings = settings
        self._last_cpf_check = ""
        self._thumb_cards: List[_ThumbCard] = []

        self.setStyleSheet("QWidget { background-color: #101E2B; }")
        self._build()
        self._refresh()

        # Pré-preenche CPF se a etapa já tiver
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf and etapa.cpf:
            self.entry_cpf.blockSignals(True)
            self.entry_cpf.setText(etapa.cpf)
            self.entry_cpf.blockSignals(False)

    # ── Construção da UI ───────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 28, 40, 16)
        root.setSpacing(0)

        # ── Cabeçalho ─────────────────────────────────────────
        header = QWidget()
        hdr_layout = QVBoxLayout(header)
        hdr_layout.setContentsMargins(0, 0, 0, 0)
        hdr_layout.setSpacing(2)

        self.lbl_tipo = QLabel()
        self.lbl_tipo.setStyleSheet("color: #4FC3F7; font-size: 12px; background: transparent;")
        hdr_layout.addWidget(self.lbl_tipo)

        self.lbl_titulo = QLabel()
        self.lbl_titulo.setStyleSheet("color: #E3F2FD; font-size: 24px; font-weight: bold; background: transparent;")
        hdr_layout.addWidget(self.lbl_titulo)

        self.lbl_desc = QLabel()
        self.lbl_desc.setStyleSheet("color: #78909C; font-size: 13px; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        hdr_layout.addWidget(self.lbl_desc)

        # ── Campo CPF (oculto por padrão) ─────────────────────
        self.cpf_frame = QWidget()
        cpf_layout = QHBoxLayout(self.cpf_frame)
        cpf_layout.setContentsMargins(0, 12, 0, 0)
        cpf_layout.setSpacing(10)

        lbl_cpf_label = QLabel("Digite o CPF para continuar:")
        lbl_cpf_label.setStyleSheet("color: #A5D6A7; font-size: 12px; font-weight: bold; background: transparent;")
        cpf_layout.addWidget(lbl_cpf_label)

        self.entry_cpf = QLineEdit()
        self.entry_cpf.setPlaceholderText("000.000.000-00")
        self.entry_cpf.setFixedSize(160, 32)
        self.entry_cpf.setStyleSheet(_ENTRY_STYLE)
        self.entry_cpf.textChanged.connect(self._aplicar_mascara_cpf)
        cpf_layout.addWidget(self.entry_cpf)

        self.lbl_cpf_error = QLabel("⚠️ CPF Inválido")
        self.lbl_cpf_error.setStyleSheet("color: #FF5252; font-size: 12px; font-weight: bold; background: transparent;")
        self.lbl_cpf_error.hide()
        cpf_layout.addWidget(self.lbl_cpf_error)

        cpf_layout.addStretch()
        self.cpf_frame.hide()
        hdr_layout.addWidget(self.cpf_frame)

        root.addWidget(header)
        root.addSpacing(12)

        # ── Barra de Progresso ────────────────────────────────
        prog_frame = QWidget()
        prog_layout = QVBoxLayout(prog_frame)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        prog_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #1E3A5F; border-radius: 4px; border: none; }
            QProgressBar::chunk { background-color: #1E88E5; border-radius: 4px; }
        """)
        prog_layout.addWidget(self.progress_bar)

        self.lbl_progress = QLabel()
        self.lbl_progress.setAlignment(Qt.AlignRight)
        self.lbl_progress.setStyleSheet("color: #546E7A; font-size: 11px; background: transparent;")
        prog_layout.addWidget(self.lbl_progress)

        root.addWidget(prog_frame)
        root.addSpacing(8)

        # ── Área de Thumbs ────────────────────────────────────
        thumb_container = QFrame()
        thumb_container.setStyleSheet("""
            QFrame {
                background-color: #0D1B2A;
                border: 1px solid #1E3450;
                border-radius: 12px;
            }
        """)
        thumb_v = QVBoxLayout(thumb_container)
        thumb_v.setContentsMargins(16, 12, 16, 12)
        thumb_v.setSpacing(8)

        lbl_pages = QLabel("Páginas digitalizadas:")
        lbl_pages.setStyleSheet("color: #90A4AE; font-size: 12px; font-weight: bold; background: transparent;")
        thumb_v.addWidget(lbl_pages)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(THUMB_H + 50)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal {
                background: #0D1B2A; height: 8px; border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #2D4A6A; border-radius: 4px; min-width: 40px;
            }
        """)

        self.thumb_inner = QWidget()
        self.thumb_inner.setStyleSheet("background: transparent;")
        self.thumb_row = QHBoxLayout(self.thumb_inner)
        self.thumb_row.setContentsMargins(4, 4, 4, 4)
        self.thumb_row.setSpacing(8)
        self.thumb_row.setAlignment(Qt.AlignLeft)

        self.lbl_empty = QLabel("Nenhuma página digitalizada ainda.")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet("color: #37474F; font-size: 12px; background: transparent;")
        self.thumb_row.addWidget(self.lbl_empty, alignment=Qt.AlignCenter)

        self.scroll_area.setWidget(self.thumb_inner)
        thumb_v.addWidget(self.scroll_area)

        root.addWidget(thumb_container, stretch=1)
        root.addSpacing(12)

        # ── Status Scanner ─────────────────────────────────────
        self.lbl_scan_status = QLabel("")
        self.lbl_scan_status.setAlignment(Qt.AlignCenter)
        self.lbl_scan_status.setStyleSheet("color: #546E7A; font-size: 11px; background: transparent;")
        self.lbl_scan_status.hide()
        root.addWidget(self.lbl_scan_status)

        # ── Botões ────────────────────────────────────────────
        controls = QWidget()
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(12)

        self.btn_prev = QPushButton("◀   Etapa Anterior")
        self.btn_prev.setStyleSheet(_BTN_STYLE("#37474F", "#455A64"))
        self.btn_prev.setFixedHeight(44)
        self.btn_prev.clicked.connect(self._voltar_etapa)
        ctrl_layout.addWidget(self.btn_prev, stretch=1)

        self.btn_scan = QPushButton("📷   Escanear Página")
        self.btn_scan.setStyleSheet(_BTN_STYLE("#1565C0", "#1976D2"))
        self.btn_scan.setFixedHeight(44)
        self.btn_scan.clicked.connect(self._do_scan)
        ctrl_layout.addWidget(self.btn_scan, stretch=1)

        self.btn_import = QPushButton("📁   Importar Arquivo")
        self.btn_import.setStyleSheet(_BTN_STYLE("#1E3A5F", "#263F6A"))
        self.btn_import.setFixedHeight(44)
        self.btn_import.clicked.connect(self._do_import)
        ctrl_layout.addWidget(self.btn_import, stretch=1)

        self.btn_next = QPushButton("Próxima Etapa  ▶")
        self.btn_next.setStyleSheet(_BTN_STYLE("#2E7D32", "#388E3C"))
        self.btn_next.setFixedHeight(44)
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._pergunta_mais_paginas)
        ctrl_layout.addWidget(self.btn_next, stretch=1)

        root.addWidget(controls)

    # ── Atualização de Estado ──────────────────────────────────────────────────

    def _refresh(self):
        """Atualiza toda a UI com o estado atual da etapa."""
        t = self.transaction
        etapa = t.etapa_atual

        self.lbl_tipo.setText(f"🏥  {t.nome_tipo}  •  Etapa {t.etapa_atual_index + 1} de {t.total_etapas}")
        self.lbl_titulo.setText(f"{etapa.icone}  {etapa.titulo}")
        self.lbl_desc.setText(etapa.descricao)

        progresso = int((t.etapa_atual_index / t.total_etapas) * 100)
        self.progress_bar.setValue(progresso)
        self.lbl_progress.setText(f"Etapa {t.etapa_atual_index + 1} / {t.total_etapas}")

        # Campo CPF
        if etapa.require_cpf:
            self.cpf_frame.show()
            cpf_atual = self.entry_cpf.text()
            if etapa.cpf and not cpf_atual:
                self.entry_cpf.blockSignals(True)
                self.entry_cpf.setText(etapa.cpf)
                self.entry_cpf.blockSignals(False)
        else:
            self.cpf_frame.hide()

        self._render_thumbs(etapa.imagens)
        self._valida_estado_botoes()

    def _valida_estado_botoes(self):
        etapa = self.transaction.etapa_atual
        cpf_valido = True
        mostra_erro = False

        if etapa.require_cpf:
            cpf_texto = self.entry_cpf.text()
            is_completo = len(cpf_texto) == 14
            is_ok = validate_cpf(cpf_texto)
            cpf_valido = is_completo and is_ok
            if is_completo and not is_ok:
                mostra_erro = True

        self.lbl_cpf_error.setVisible(mostra_erro)
        self.btn_prev.setEnabled(self.transaction.etapa_atual_index > 0)

        if cpf_valido:
            self.btn_scan.setEnabled(True)
            self.btn_import.setEnabled(True)
            self.btn_next.setEnabled(etapa.tem_imagens)
        else:
            self.btn_scan.setEnabled(False)
            self.btn_import.setEnabled(False)
            self.btn_next.setEnabled(False)

    def _render_thumbs(self, imagens: list):
        """Renderiza as miniaturas dos scans."""
        # Remove cards anteriores sem destruir o layout
        for card in self._thumb_cards:
            card.setParent(None)
        self._thumb_cards.clear()

        if not imagens:
            self.lbl_empty.show()
            return

        self.lbl_empty.hide()
        for i, img in enumerate(imagens):
            card = _ThumbCard(i, img, self.thumb_inner)
            card.delete_requested.connect(self._remover_imagem)
            self.thumb_row.insertWidget(i, card)
            self._thumb_cards.append(card)
            card.show()

    # ── Ações do Scanner ───────────────────────────────────────────────────────

    def _do_scan(self):
        from src.engine.scan_engine import ScannerEngine
        engine = ScannerEngine()

        scanner_name = self.settings.get("scanner_name", "") if self.settings else ""

        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("⌛  Escaneando...")
        self.lbl_scan_status.show()
        self.lbl_scan_status.setText("Iniciando scanner...")

        def _status(msg: str):
            QTimer.singleShot(0, lambda: self.lbl_scan_status.setText(msg))

        def _callback(png_bytes: Optional[bytes], error: Optional[str]):
            QTimer.singleShot(0, lambda: self._on_scan_done(png_bytes, error))

        engine.scan_with_dialog(_callback, _status, device_name=scanner_name or None)

    def _on_scan_done(self, png_bytes: Optional[bytes], error: Optional[str]):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("📷   Escanear Página")
        self.lbl_scan_status.hide()

        if error:
            QMessageBox.warning(self, "Erro no Scanner", error)
            return

        if png_bytes:
            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            self._on_image_captured(img)

    def _do_import(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Importar Arquivo",
            "",
            "Imagens e PDF (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.pdf);;Todos os arquivos (*)"
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGB")
            self._on_image_captured(img)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Importar", f"Não foi possível abrir o arquivo:\n{e}")

    def _on_image_captured(self, img: Image.Image):
        if img:
            self.transaction.etapa_atual.adicionar_imagem(img)
            self._valida_estado_botoes()
            self._refresh()

    def _remover_imagem(self, index: int):
        self.transaction.etapa_atual.remover_imagem(index)
        self._last_cpf_check = ""
        self._valida_estado_botoes()
        self._refresh()

    # ── Navegação entre etapas ─────────────────────────────────────────────────

    def _pergunta_mais_paginas(self):
        etapa = self.transaction.etapa_atual

        # Salva CPF e documentos se necessário
        if etapa.require_cpf:
            cpf_salvo = self.entry_cpf.text()
            etapa.cpf = cpf_salvo
            try:
                if etapa.tem_imagens:
                    save_cpf_documents(cpf_salvo, etapa.imagens, self.settings)
            except Exception as e:
                print(f"[AuditorWizard] Falha ao salvar doc na pasta CPFs: {e}")

        dlg = _MorePagesDialog(self, etapa.titulo)
        dlg.exec()

        if dlg.result == "next":
            if etapa.require_cpf:
                self._abrir_wizard_validacao()
            else:
                self._avancar_etapa()

    def _abrir_wizard_validacao(self):
        from src.ui.doc_validation_wizard import DocValidationWizard
        etapa = self.transaction.etapa_atual
        wizard = DocValidationWizard(self, etapa.cpf)
        wizard.exec()

        if wizard.resultado == "aprovado":
            etapa.validacao_doc = wizard.dados_validacao

            # Menor de idade → insere etapa do responsável legal
            if etapa.id == "id_paciente" and wizard.dados_validacao.get("is_menor", False):
                from src.core.transaction import criar_etapa_responsavel_legal
                self.transaction.is_menor_idade = True
                self.transaction.idade_paciente = wizard.dados_validacao.get("idade", 0)
                if not self.transaction.ja_tem_etapa("id_responsavel"):
                    self.transaction.inserir_etapa_apos_atual(criar_etapa_responsavel_legal())

            # Idoso
            if wizard.dados_validacao.get("is_idoso", False):
                self.transaction.is_idoso = True
                self.transaction.idade_paciente = wizard.dados_validacao.get("idade", 0)

            self._avancar_etapa()

        elif wizard.resultado == "refazer":
            etapa.imagens.clear()
            etapa.validacao_doc = {}
            self._refresh()
            QMessageBox.information(
                self,
                "Refazer Digitalização",
                "As imagens foram removidas. Digitalize o documento novamente."
            )

        elif wizard.resultado == "cancelar":
            resp = QMessageBox.question(
                self,
                "Cancelar Transação",
                "Tem certeza que deseja cancelar toda a transação?\n"
                "Todas as imagens digitalizadas serão perdidas.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if resp == QMessageBox.Yes:
                self.cancelado.emit()

    def _avancar_etapa(self):
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf:
            etapa.cpf = self.entry_cpf.text()
        self._last_cpf_check = ""
        self.entry_cpf.blockSignals(True)
        self.entry_cpf.clear()
        self.entry_cpf.blockSignals(False)

        tem_proxima = self.transaction.avancar_etapa()
        if tem_proxima:
            self._refresh()
        else:
            # Todas as etapas concluídas → emite sinal para a MainWindow
            self.concluido.emit(self.transaction)

    def _voltar_etapa(self):
        etapa = self.transaction.etapa_atual
        if etapa.require_cpf:
            cpf_atual = self.entry_cpf.text()
            if cpf_atual and validate_cpf(cpf_atual):
                etapa.cpf = cpf_atual

        self.entry_cpf.blockSignals(True)
        self.entry_cpf.clear()
        self.entry_cpf.blockSignals(False)

        if self.transaction.voltar_etapa():
            etapa_destino = self.transaction.etapa_atual
            self._last_cpf_check = etapa_destino.cpf if etapa_destino.cpf else ""
            self._refresh()

    # ── Máscara de CPF ─────────────────────────────────────────────────────────

    def _aplicar_mascara_cpf(self, text: str):
        apenas_nums = "".join(filter(str.isdigit, text))[:11]
        novo = ""
        for i, d in enumerate(apenas_nums):
            if i in (3, 6):
                novo += "."
            elif i == 9:
                novo += "-"
            novo += d

        if text != novo:
            self.entry_cpf.blockSignals(True)
            pos = self.entry_cpf.cursorPosition()
            self.entry_cpf.setText(novo)
            self.entry_cpf.setCursorPosition(min(pos, len(novo)))
            self.entry_cpf.blockSignals(False)

        self._valida_estado_botoes()

        if len(novo) < 14:
            self._last_cpf_check = ""

        # Verifica CPF existente ao completar 14 dígitos
        if (len(novo) == 14 and validate_cpf(novo)
                and self._last_cpf_check != novo):
            self._last_cpf_check = novo
            self._verificar_documento_existente(novo)

    def _verificar_documento_existente(self, cpf_formatado: str):
        # Limpa para buscar no sistema de arquivos
        cpf_clean = "".join(filter(str.isdigit, cpf_formatado))
        try:
            paths = find_all_documents_by_cpf(cpf_clean, self.settings)
        except Exception:
            paths = []

        if paths:
            dlg = _FoundDocumentDialog(self, cpf, str(paths[0]))
            dlg.exec()
            if dlg.result == "use":
                try:
                    for p in paths:
                        img = Image.open(p).convert("RGB")
                        self.transaction.etapa_atual.adicionar_imagem(img.copy())
                    self._valida_estado_botoes()
                    self._refresh()
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Não foi possível carregar o arquivo:\n{e}")
