"""
sidebar.py - Barra lateral de navegação do DocPopularEditor (PySide6).
Estilo inspirado no DocPopular, com botões de navegação e rodapé com versão.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QSpacerItem
)

from version import APP_VERSION


class SidebarButton(QPushButton):
    """Botão customizado para a sidebar com estilo hover."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(42)
        self.setStyleSheet(self._default_style())
        self._active = False

    def _default_style(self) -> str:
        return """
            QPushButton {
                background-color: transparent;
                color: #B0BEC5;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                text-align: left;
                padding-left: 16px;
            }
            QPushButton:hover {
                background-color: #1E3A5F;
                color: #E3F2FD;
            }
        """

    def _active_style(self) -> str:
        return """
            QPushButton {
                background-color: #1E3A5F;
                color: #E3F2FD;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                text-align: left;
                padding-left: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #264d73;
            }
        """

    def set_active(self, active: bool):
        self._active = active
        self.setStyleSheet(self._active_style() if active else self._default_style())


class Sidebar(QFrame):
    """
    Barra lateral permanente do DocPopularEditor.
    Contém: Logo, Nova Transação, Buscar Documento, Configurações, Ajuda.
    """

    # Sinais emitidos quando o usuário clica nos botões
    nova_transacao_clicked = Signal()
    buscar_documento_clicked = Signal()
    configuracoes_clicked = Signal()
    ajuda_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._setup_style()
        self._build()

    def _setup_style(self):
        self.setStyleSheet("""
            QFrame#sidebar {
                background-color: #0D1B2A;
                border-right: 1px solid #1E3450;
            }
        """)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo ──
        logo_frame = QFrame()
        logo_frame.setStyleSheet("background: transparent; border: none;")
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 24, 16, 8)
        logo_layout.setSpacing(2)

        icon_label = QLabel("📄")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px; border: none; background: transparent;")
        logo_layout.addWidget(icon_label)

        app_name = QLabel("DocPopularEditor")
        app_name.setAlignment(Qt.AlignCenter)
        app_name.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #4FC3F7; "
            "border: none; background: transparent;"
        )
        logo_layout.addWidget(app_name)

        app_sub = QLabel("Editor & Auditor PFPB")
        app_sub.setAlignment(Qt.AlignCenter)
        app_sub.setStyleSheet(
            "font-size: 10px; color: #78909C; "
            "border: none; background: transparent;"
        )
        logo_layout.addWidget(app_sub)

        layout.addWidget(logo_frame)

        # ── Separador ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1E3450; border: none;")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # ── Botões de Navegação ──
        nav_frame = QFrame()
        nav_frame.setStyleSheet("background: transparent; border: none;")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(12, 0, 12, 0)
        nav_layout.setSpacing(4)

        self.btn_nova_transacao = SidebarButton("  📋  Nova Transação")
        self.btn_nova_transacao.clicked.connect(self._on_nova_transacao)
        nav_layout.addWidget(self.btn_nova_transacao)

        self.btn_buscar = SidebarButton("  🔍  Procurar Documento")
        self.btn_buscar.clicked.connect(self._on_buscar)
        nav_layout.addWidget(self.btn_buscar)

        nav_layout.addSpacing(8)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background-color: #1E3450; border: none;")
        nav_layout.addWidget(sep2)

        nav_layout.addSpacing(8)

        self.btn_configuracoes = SidebarButton("  ⚙️  Configurações")
        self.btn_configuracoes.clicked.connect(self._on_configuracoes)
        nav_layout.addWidget(self.btn_configuracoes)

        self.btn_ajuda = SidebarButton("  ❓  Ajuda e Suporte")
        self.btn_ajuda.clicked.connect(self._on_ajuda)
        nav_layout.addWidget(self.btn_ajuda)

        layout.addWidget(nav_frame)

        # ── Espaçador ──
        layout.addStretch(1)

        # ── Rodapé com versão ──
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setAlignment(Qt.AlignLeft)
        version_label.setStyleSheet(
            "font-size: 10px; color: #546E7A; "
            "border: none; background: transparent; padding: 12px 16px;"
        )
        layout.addWidget(version_label)

        # Lista de botões para controlar o estado ativo
        self._nav_buttons = [
            self.btn_nova_transacao,
            self.btn_buscar,
            self.btn_configuracoes,
            self.btn_ajuda,
        ]

    def _set_active(self, active_btn: SidebarButton):
        """Marca apenas o botão clicado como ativo."""
        for btn in self._nav_buttons:
            btn.set_active(btn is active_btn)

    def clear_active(self):
        """Remove o estado ativo de todos os botões."""
        for btn in self._nav_buttons:
            btn.set_active(False)

    def set_active(self, name: str):
        """Ativa um botão por nome: 'nova_transacao', 'buscar', 'configuracoes', 'ajuda'."""
        mapping = {
            "nova_transacao": self.btn_nova_transacao,
            "buscar": self.btn_buscar,
            "configuracoes": self.btn_configuracoes,
            "ajuda": self.btn_ajuda,
        }
        target = mapping.get(name)
        if target:
            self._set_active(target)

    def _on_nova_transacao(self):
        self._set_active(self.btn_nova_transacao)
        self.nova_transacao_clicked.emit()

    def _on_buscar(self):
        self._set_active(self.btn_buscar)
        self.buscar_documento_clicked.emit()

    def _on_configuracoes(self):
        self._set_active(self.btn_configuracoes)
        self.configuracoes_clicked.emit()

    def _on_ajuda(self):
        self._set_active(self.btn_ajuda)
        self.ajuda_clicked.emit()
