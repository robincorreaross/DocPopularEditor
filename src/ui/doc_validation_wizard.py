"""
doc_validation_wizard.py - Wizard de validação do documento de identidade.
Guia o operador por 5 passos de verificação via checklist manual.
Portado do DocPopular (CustomTkinter → PySide6).
"""

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QLineEdit, QWidget, QSizePolicy
)


def _verificar_validade_documento(data_emissao: date, max_anos: int = 10) -> bool:
    """Verifica se o documento ainda está dentro do prazo de validade."""
    hoje = date.today()
    anos_passados = hoje.year - data_emissao.year
    if (hoje.month, hoje.day) < (data_emissao.month, data_emissao.day):
        anos_passados -= 1
    return anos_passados <= max_anos


def _calcular_idade(data_nasc: date) -> int:
    """Calcula a idade em anos completos."""
    hoje = date.today()
    idade = hoje.year - data_nasc.year
    if (hoje.month, hoje.day) < (data_nasc.month, data_nasc.day):
        idade -= 1
    return idade


def _aplicar_mascara_data(entry: QLineEdit):
    """Aplica máscara DD/MM/AAAA em um QLineEdit."""
    text = entry.text()
    apenas_nums = "".join(filter(str.isdigit, text))[:8]
    novo = ""
    for i, d in enumerate(apenas_nums):
        if i in (2, 4):
            novo += "/"
        novo += d
    if text != novo:
        pos = entry.cursorPosition()
        entry.blockSignals(True)
        entry.setText(novo)
        entry.blockSignals(False)
        entry.setCursorPosition(min(pos, len(novo)))


# ─── Estilos ──────────────────────────────────────────────────────────────────

_DIALOG_STYLE = """
QDialog {
    background-color: #0D1B2A;
}
QLabel {
    color: #E3F2FD;
}
"""

_BTN_GREEN = """
QPushButton {
    background-color: #2E7D32;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: bold;
    padding: 10px 20px;
}
QPushButton:hover { background-color: #388E3C; }
QPushButton:disabled { background-color: #1B3A1D; color: #555; }
"""

_BTN_RED = """
QPushButton {
    background-color: #B71C1C;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: bold;
    padding: 10px 20px;
}
QPushButton:hover { background-color: #C62828; }
"""

_BTN_BLUE = """
QPushButton {
    background-color: #1565C0;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: bold;
    padding: 10px 20px;
}
QPushButton:hover { background-color: #1976D2; }
"""

_ENTRY_STYLE = """
QLineEdit {
    background-color: #1A2D40;
    color: #E3F2FD;
    border: 1px solid #2D4A6A;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 14px;
}
QLineEdit:focus { border: 1px solid #1E88E5; }
"""

_CARD_STYLE = "background-color: #0D1B2A; border: 1px solid #1E3450; border-radius: 10px;"


class DocValidationWizard(QDialog):
    """
    Janela modal que valida o documento de identidade em 5 passos.
    Checklist manual — o operador informa e confirma tudo.
    """

    TOTAL_PASSOS = 5

    def __init__(self, parent, cpf_digitado: str):
        super().__init__(parent)
        self.cpf_digitado = cpf_digitado

        # Resultado final
        self.resultado: Optional[str] = None  # "aprovado", "refazer", "cancelar"
        self.motivos_reprovacao: list = []
        self.dados_validacao: dict = {}
        self._passo_atual = 0

        self.setWindowTitle("Validação do Documento")
        self.setModal(True)
        self.setFixedSize(580, 520)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Layout principal
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(0)

        # ── Cabeçalho ─────────────────────────────────────────
        self.lbl_titulo = QLabel("")
        self.lbl_titulo.setStyleSheet("color: #E3F2FD; font-size: 20px; font-weight: bold;")
        root.addWidget(self.lbl_titulo)

        self.lbl_passo = QLabel("")
        self.lbl_passo.setStyleSheet("color: #546E7A; font-size: 11px;")
        root.addWidget(self.lbl_passo)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #1E3A5F; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #1E88E5; border-radius: 3px; }
        """)
        root.addSpacing(8)
        root.addWidget(self.progress)
        root.addSpacing(12)

        # ── Área de conteúdo (mutável) ─────────────────────────
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        root.addWidget(self.content_widget, stretch=1)

        # ── Rodapé com botões ──────────────────────────────────
        self.footer_widget = QWidget()
        self.footer_layout = QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(0, 0, 0, 0)
        self.footer_layout.setSpacing(12)
        self.footer_layout.addStretch()
        root.addSpacing(12)
        root.addWidget(self.footer_widget)

        self._mostrar_passo(0)

    # ═══════════════════════════════════════════════════════════
    # Helpers UI
    # ═══════════════════════════════════════════════════════════

    def _limpar_conteudo(self):
        for i in reversed(range(self.content_layout.count())):
            w = self.content_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

    def _limpar_footer(self):
        for i in reversed(range(self.footer_layout.count())):
            item = self.footer_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        self.footer_layout.addStretch()

    def _add_label(self, text, color="#90A4AE", size=13, bold=False, wrap=True) -> QLabel:
        lbl = QLabel(text)
        weight = "bold" if bold else "normal"
        lbl.setStyleSheet(f"color: {color}; font-size: {size}px; font-weight: {weight}; background: transparent;")
        if wrap:
            lbl.setWordWrap(True)
        self.content_layout.addWidget(lbl)
        return lbl

    def _add_card(self, items: list, item_color="#A5D6A7") -> QFrame:
        card = QFrame()
        card.setStyleSheet(_CARD_STYLE)
        vlayout = QVBoxLayout(card)
        vlayout.setContentsMargins(16, 12, 16, 12)
        vlayout.setSpacing(4)
        for txt in items:
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color: {item_color}; font-size: 13px; background: transparent;")
            lbl.setWordWrap(True)
            vlayout.addWidget(lbl)
        self.content_layout.addWidget(card)
        return card

    def _botoes_sim_nao(self, on_sim, on_nao):
        self._limpar_footer()
        btn_nao = QPushButton("❌   Não")
        btn_nao.setStyleSheet(_BTN_RED)
        btn_nao.setFixedHeight(42)
        btn_nao.setMinimumWidth(200)
        btn_nao.clicked.connect(on_nao)

        btn_sim = QPushButton("✅   Sim")
        btn_sim.setStyleSheet(_BTN_GREEN)
        btn_sim.setFixedHeight(42)
        btn_sim.setMinimumWidth(200)
        btn_sim.clicked.connect(on_sim)

        self.footer_layout.addStretch()
        self.footer_layout.addWidget(btn_nao)
        self.footer_layout.addWidget(btn_sim)

    def _botao_confirmar(self, on_click, texto="Confirmar  ✔"):
        self._limpar_footer()
        btn = QPushButton(texto)
        btn.setStyleSheet(_BTN_GREEN)
        btn.setFixedHeight(42)
        btn.setMinimumWidth(240)
        btn.clicked.connect(on_click)
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(btn)

    # ═══════════════════════════════════════════════════════════
    # Renderização dos Passos
    # ═══════════════════════════════════════════════════════════

    def _mostrar_passo(self, passo: int):
        self._passo_atual = passo
        self._limpar_conteudo()
        self._limpar_footer()
        prog_val = int((passo + 1) / self.TOTAL_PASSOS * 100)
        self.progress.setValue(prog_val)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #1E3A5F; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #1E88E5; border-radius: 3px; }
        """)
        self.lbl_passo.setText(f"Passo {passo + 1} de {self.TOTAL_PASSOS}")

        renderers = [
            self._passo_legibilidade,
            self._passo_data_emissao,
            self._passo_cpf,
            self._passo_idade,
            self._passo_assinatura,
        ]
        renderers[passo]()

    # ── Passo 1: Legibilidade e Foto ──────────────────────────

    def _passo_legibilidade(self):
        self.lbl_titulo.setText("📋  Legibilidade e Foto")
        self._add_label("Verifique o documento digitalizado:", "#E3F2FD", 14, bold=True)
        self._add_card([
            "✔  O documento está legível (texto e dados visíveis)",
            "✔  O documento possui foto do paciente",
            "✔  A imagem não está cortada ou desfocada",
        ])
        self._add_label("\nO documento atende a todos os critérios acima?", "#90A4AE", 13)
        self._botoes_sim_nao(
            on_sim=lambda: self._mostrar_passo(1),
            on_nao=lambda: self._reprovar("Documento ilegível ou sem foto"),
        )

    # ── Passo 2: Data de Emissão ───────────────────────────────

    def _passo_data_emissao(self):
        self.lbl_titulo.setText("📅  Data de Emissão")
        self._add_label("O documento deve ter no máximo 10 anos desde a emissão.", "#90A4AE", 13)
        self._add_label("Digite a data de emissão que consta no documento (DD/MM/AAAA):", "#E3F2FD", 12, bold=True)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        self._entry_emissao = QLineEdit()
        self._entry_emissao.setPlaceholderText("DD/MM/AAAA")
        self._entry_emissao.setFixedSize(160, 36)
        self._entry_emissao.setStyleSheet(_ENTRY_STYLE)
        self._entry_emissao.textChanged.connect(lambda: _aplicar_mascara_data(self._entry_emissao))
        row_layout.addWidget(self._entry_emissao)

        self._lbl_emissao_erro = QLabel("")
        self._lbl_emissao_erro.setStyleSheet("color: #FF5252; font-size: 12px; background: transparent;")
        row_layout.addWidget(self._lbl_emissao_erro)
        row_layout.addStretch()

        self.content_layout.addWidget(row)
        self.content_layout.addStretch()
        self._entry_emissao.setFocus()
        self._botao_confirmar(on_click=self._validar_data_emissao)

    def _validar_data_emissao(self):
        texto = self._entry_emissao.text().strip()
        try:
            parts = texto.replace("-", "/").replace(".", "/").split("/")
            dia, mes, ano = int(parts[0]), int(parts[1]), int(parts[2])
            data = date(ano, mes, dia)
        except (ValueError, IndexError):
            self._lbl_emissao_erro.setText("❌ Data inválida. Use DD/MM/AAAA")
            return

        if data > date.today():
            self._lbl_emissao_erro.setText("❌ Data no futuro")
            return

        valido = _verificar_validade_documento(data)
        self.dados_validacao["data_emissao"] = data.isoformat()
        self.dados_validacao["doc_valido"] = valido

        if valido:
            self._mostrar_passo(2)
        else:
            anos = date.today().year - data.year
            self._reprovar(f"Documento vencido — emitido há {anos} anos (limite: 10 anos)")

    # ── Passo 3: CPF no Documento ──────────────────────────────

    def _passo_cpf(self):
        self.lbl_titulo.setText("🔢  Conferência do CPF")
        self._add_label("O CPF no documento deve conferir com o CPF digitado.", "#90A4AE", 13)

        card = QFrame()
        card.setStyleSheet(_CARD_STYLE)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        lbl_desc = QLabel("CPF digitado pelo operador:")
        lbl_desc.setStyleSheet("color: #78909C; font-size: 12px; background: transparent;")
        card_layout.addWidget(lbl_desc)
        lbl_cpf = QLabel(self.cpf_digitado)
        lbl_cpf.setStyleSheet("color: #4FC3F7; font-size: 22px; font-weight: bold; background: transparent;")
        card_layout.addWidget(lbl_cpf)
        self.content_layout.addWidget(card)

        self._add_label("\nO CPF no documento confere com o CPF acima?", "#E3F2FD", 14, bold=True)
        self.content_layout.addStretch()
        self._botoes_sim_nao(
            on_sim=lambda: (self.dados_validacao.update({"cpf_confere": True}), self._mostrar_passo(3)),
            on_nao=lambda: self._reprovar("CPF no documento não confere com o CPF digitado"),
        )

    # ── Passo 4: Idade do Paciente ─────────────────────────────

    def _passo_idade(self):
        self.lbl_titulo.setText("🎂  Idade do Paciente")
        self._add_label("Verificação da idade do paciente a partir da data de nascimento.", "#90A4AE", 13)
        self._add_label("Digite a data de nascimento que consta no documento (DD/MM/AAAA):", "#E3F2FD", 12, bold=True)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        self._entry_nasc = QLineEdit()
        self._entry_nasc.setPlaceholderText("DD/MM/AAAA")
        self._entry_nasc.setFixedSize(160, 36)
        self._entry_nasc.setStyleSheet(_ENTRY_STYLE)
        self._entry_nasc.textChanged.connect(lambda: _aplicar_mascara_data(self._entry_nasc))
        row_layout.addWidget(self._entry_nasc)

        self._lbl_nasc_erro = QLabel("")
        self._lbl_nasc_erro.setStyleSheet("color: #FF5252; font-size: 12px; background: transparent;")
        row_layout.addWidget(self._lbl_nasc_erro)
        row_layout.addStretch()

        self.content_layout.addWidget(row)
        self.content_layout.addStretch()
        self._entry_nasc.setFocus()
        self._botao_confirmar(on_click=self._validar_idade)

    def _validar_idade(self):
        texto = self._entry_nasc.text().strip()
        try:
            parts = texto.replace("-", "/").replace(".", "/").split("/")
            dia, mes, ano = int(parts[0]), int(parts[1]), int(parts[2])
            data_nasc = date(ano, mes, dia)
        except (ValueError, IndexError):
            self._lbl_nasc_erro.setText("❌ Data inválida. Use DD/MM/AAAA")
            return

        if data_nasc > date.today():
            self._lbl_nasc_erro.setText("❌ Data no futuro")
            return

        idade = _calcular_idade(data_nasc)
        self.dados_validacao["data_nascimento"] = data_nasc.isoformat()
        self.dados_validacao["idade"] = idade
        self.dados_validacao["is_menor"] = idade < 18
        self.dados_validacao["is_idoso"] = idade >= 60

        # Mostra resultado da idade
        self._limpar_conteudo()
        self.lbl_titulo.setText("🎂  Resultado — Idade")

        card = QFrame()
        card.setStyleSheet(_CARD_STYLE)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(4)

        lbl_idade = QLabel(f"Idade calculada: {idade} anos")
        lbl_idade.setStyleSheet("color: #E3F2FD; font-size: 20px; font-weight: bold; background: transparent;")
        card_layout.addWidget(lbl_idade)

        lbl_nasc = QLabel(f"Data de Nascimento: {data_nasc.strftime('%d/%m/%Y')}")
        lbl_nasc.setStyleSheet("color: #78909C; font-size: 13px; background: transparent;")
        card_layout.addWidget(lbl_nasc)

        if idade < 18:
            categoria = "👶  MENOR DE IDADE"
            cor = "#FFB74D"
            desc = "A etapa de assinatura/polegar será pulada.\nUma etapa adicional será necessária para o documento do responsável legal."
            on_click_next = self._aprovar
        elif idade >= 60:
            categoria = "👴  IDOSO (≥ 60 anos)"
            cor = "#4FC3F7"
            desc = "Paciente classificado como idoso."
            on_click_next = lambda: self._mostrar_passo(4)
        else:
            categoria = "👤  ADULTO (18–59 anos)"
            cor = "#A5D6A7"
            desc = "Faixa etária padrão."
            on_click_next = lambda: self._mostrar_passo(4)

        lbl_cat = QLabel(categoria)
        lbl_cat.setStyleSheet(f"color: {cor}; font-size: 16px; font-weight: bold; background: transparent;")
        card_layout.addWidget(lbl_cat)

        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("color: #90A4AE; font-size: 12px; background: transparent;")
        lbl_desc.setWordWrap(True)
        card_layout.addWidget(lbl_desc)

        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
        self._botao_confirmar(on_click=on_click_next, texto="Prosseguir  ▶")

    # ── Passo 5: Assinatura ────────────────────────────────────

    def _passo_assinatura(self):
        self.lbl_titulo.setText("✍️  Assinatura do Documento")
        self._add_label("Verifique se o documento possui assinatura do titular.", "#90A4AE", 13)
        self._add_label(
            "Caso não possua assinatura, pode indicar alguma incapacidade,\n"
            "e nesse caso verificaremos a impressão do dedo polegar.",
            "#78909C", 12
        )
        self._add_label("O documento possui assinatura?", "#E3F2FD", 14, bold=True)
        self.content_layout.addStretch()
        self._botoes_sim_nao(
            on_sim=lambda: self._finalizar_assinatura(True, False),
            on_nao=self._perguntar_polegar,
        )

    def _perguntar_polegar(self):
        self._limpar_conteudo()
        self._limpar_footer()
        self.lbl_titulo.setText("👆  Impressão do Polegar")
        self._add_label("O documento não possui assinatura.", "#FFB74D", 13)
        self._add_label(
            "Quando não há assinatura, é necessário verificar\n"
            "se existe impressão do dedo polegar como alternativa.",
            "#90A4AE", 13
        )
        self._add_label("O documento possui impressão do dedo polegar?", "#E3F2FD", 14, bold=True)
        self.content_layout.addStretch()
        self._botoes_sim_nao(
            on_sim=lambda: self._finalizar_assinatura(False, True),
            on_nao=lambda: self._reprovar("Documento sem assinatura e sem impressão do polegar"),
        )

    def _finalizar_assinatura(self, tem_assinatura: bool, tem_polegar: bool):
        self.dados_validacao["tem_assinatura"] = tem_assinatura
        self.dados_validacao["tem_polegar"] = tem_polegar
        self._aprovar()

    # ═══════════════════════════════════════════════════════════
    # Resultados Finais
    # ═══════════════════════════════════════════════════════════

    def _aprovar(self):
        self.resultado = "aprovado"
        self.accept()

    def _reprovar(self, motivo: str):
        self.motivos_reprovacao.append(motivo)
        self._limpar_conteudo()
        self._limpar_footer()

        self.lbl_titulo.setText("❌  Documento Reprovado")
        self.lbl_passo.setText("Validação não aprovada")
        self.progress.setValue(100)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #1E3A5F; border-radius: 3px; border: none; }
            QProgressBar::chunk { background-color: #C62828; border-radius: 3px; }
        """)

        motivo_frame = QFrame()
        motivo_frame.setStyleSheet("background-color: #2A0D0D; border: 1px solid #5C1C1C; border-radius: 10px;")
        motivo_layout = QVBoxLayout(motivo_frame)
        motivo_layout.setContentsMargins(16, 12, 16, 12)
        motivo_layout.setSpacing(4)

        lbl_mot_title = QLabel("Motivo da reprovação:")
        lbl_mot_title.setStyleSheet("color: #FF8A80; font-size: 13px; font-weight: bold; background: transparent;")
        motivo_layout.addWidget(lbl_mot_title)

        for m in self.motivos_reprovacao:
            lbl_m = QLabel(f"  ⛔  {m}")
            lbl_m.setStyleSheet("color: #FFCDD2; font-size: 13px; background: transparent;")
            lbl_m.setWordWrap(True)
            motivo_layout.addWidget(lbl_m)

        self.content_layout.addWidget(motivo_frame)
        self._add_label("O que deseja fazer?", "#E3F2FD", 14, bold=True)
        self.content_layout.addStretch()

        # Botões de reprovação
        self._limpar_footer()
        btn_refazer = QPushButton("🔄  Refazer Digitalização")
        btn_refazer.setStyleSheet(_BTN_BLUE)
        btn_refazer.setFixedHeight(42)
        btn_refazer.setMinimumWidth(220)
        btn_refazer.clicked.connect(self._refazer)

        btn_cancelar = QPushButton("🚫  Cancelar Transação")
        btn_cancelar.setStyleSheet(_BTN_RED)
        btn_cancelar.setFixedHeight(42)
        btn_cancelar.setMinimumWidth(220)
        btn_cancelar.clicked.connect(self._cancelar)

        self.footer_layout.addStretch()
        self.footer_layout.addWidget(btn_refazer)
        self.footer_layout.addWidget(btn_cancelar)

    def _refazer(self):
        self.resultado = "refazer"
        self.reject()

    def _cancelar(self):
        self.resultado = "cancelar"
        self.reject()

    def closeEvent(self, event):
        if self.resultado is None:
            self.resultado = "cancelar"
        super().closeEvent(event)
