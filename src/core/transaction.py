"""
transaction.py - Define os tipos de transação e suas etapas de digitalização.
Portado do DocPopular para o DocPopularEditor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from PIL import Image


@dataclass
class ScanStep:
    """Representa uma etapa de digitalização dentro de um fluxo de transação."""
    id: str
    titulo: str
    descricao: str
    icone: str = "📄"
    imagens: List[Image.Image] = field(default_factory=list)
    require_cpf: bool = False
    cpf: str = ""
    validacao_doc: dict = field(default_factory=dict)

    def adicionar_imagem(self, imagem: Image.Image) -> None:
        self.imagens.append(imagem)

    def remover_imagem(self, index: int) -> None:
        if 0 <= index < len(self.imagens):
            self.imagens.pop(index)

    @property
    def tem_imagens(self) -> bool:
        return len(self.imagens) > 0

    @property
    def total_imagens(self) -> int:
        return len(self.imagens)


@dataclass
class Transaction:
    """Representa uma transação completa com tipo e etapas."""
    tipo: int
    nome_tipo: str
    etapas: List[ScanStep]
    etapa_atual_index: int = 0
    is_menor_idade: bool = False
    is_idoso: bool = False
    idade_paciente: int = 0

    @property
    def etapa_atual(self) -> ScanStep:
        return self.etapas[self.etapa_atual_index]

    @property
    def total_etapas(self) -> int:
        return len(self.etapas)

    @property
    def progresso(self) -> float:
        return self.etapa_atual_index / self.total_etapas

    @property
    def concluida(self) -> bool:
        return self.etapa_atual_index >= self.total_etapas

    def avancar_etapa(self) -> bool:
        if self.etapa_atual_index < self.total_etapas - 1:
            self.etapa_atual_index += 1
            return True
        self.etapa_atual_index = self.total_etapas
        return False

    def voltar_etapa(self) -> bool:
        if self.etapa_atual_index > 0:
            if self.etapa_atual_index >= self.total_etapas:
                self.etapa_atual_index = self.total_etapas - 1
            else:
                self.etapa_atual_index -= 1
            return True
        return False

    def todas_imagens(self) -> List[Image.Image]:
        todas: List[Image.Image] = []
        for etapa in self.etapas:
            todas.extend(etapa.imagens)
        return todas

    def resumo_etapas(self) -> List[dict]:
        return [
            {
                "titulo": e.titulo,
                "imagens": e.total_imagens,
                "concluida": e.total_imagens > 0,
            }
            for e in self.etapas
        ]

    def inserir_etapa_apos_atual(self, etapa: ScanStep) -> None:
        self.etapas.insert(self.etapa_atual_index + 1, etapa)

    def ja_tem_etapa(self, etapa_id: str) -> bool:
        return any(e.id == etapa_id for e in self.etapas)


# ─── Fábrica de Transação (Fluxo Único Inteligente) ─────────────────────────

def criar_transacao_unica() -> Transaction:
    """
    Cria uma transação com fluxo único inteligente.
    Começa com o documento de identificação do paciente.
    As etapas seguintes são inseridas dinamicamente conforme a validação avança.
    """
    return Transaction(
        tipo=0,
        nome_tipo="Fluxo Único",
        etapas=[
            ScanStep(
                id="id_paciente",
                titulo="Documento de Identificação do Paciente",
                descricao=(
                    "Digitalize o documento de identificação com foto do paciente.\n"
                    "O documento deve conter o número do CPF."
                ),
                icone="🪪",
                require_cpf=True,
            ),
            ScanStep(
                id="receita",
                titulo="Receita Médica e/ou Laudo Médico",
                descricao=(
                    "Digitalize a Receita Médica e/ou o Laudo Médico.\n"
                    "Verifique se contém assinatura, carimbo e CRM do médico."
                ),
                icone="📋",
            ),
            ScanStep(
                id="cupom",
                titulo="Cupom Fiscal + Cupom Vinculado",
                descricao=(
                    "Digitalize o Cupom Fiscal e o Cupom Vinculado do programa.\n"
                    "O Cupom Vinculado deve conter o endereço do beneficiário e estar assinado."
                ),
                icone="🧾",
            ),
        ],
    )


# ─── Etapas Dinâmicas ────────────────────────────────────────────────────────

def criar_etapa_responsavel_legal() -> ScanStep:
    """Cria etapa para documento do responsável legal (menor de idade)."""
    return ScanStep(
        id="id_responsavel",
        titulo="Documento de Identificação do Responsável Legal",
        descricao=(
            "Paciente menor de 18 anos detectado.\n"
            "Digitalize o documento de identificação do responsável legal (pai, mãe ou tutor).\n"
            "O documento deve conter o número do CPF."
        ),
        icone="🪪",
        require_cpf=True,
    )
