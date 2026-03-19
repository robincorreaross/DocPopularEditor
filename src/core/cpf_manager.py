"""
cpf_manager.py - Gerenciador de documentos salvos por CPF.
Portado do DocPopular para o DocPopularEditor.
"""

from __future__ import annotations

import glob
from pathlib import Path
from typing import List, Optional

from PIL import Image


def validate_cpf(cpf: str) -> bool:
    """Valida um CPF usando o algoritmo do Módulo 11."""
    nums = [int(digit) for digit in cpf if digit.isdigit()]

    if len(nums) != 11:
        return False

    if len(set(nums)) == 1:
        return False

    soma_1 = sum(nums[i] * (10 - i) for i in range(9))
    resto_1 = soma_1 % 11
    digito_1 = 0 if resto_1 < 2 else 11 - resto_1

    if nums[9] != digito_1:
        return False

    soma_2 = sum(nums[i] * (11 - i) for i in range(10))
    resto_2 = soma_2 % 11
    digito_2 = 0 if resto_2 < 2 else 11 - resto_2

    if nums[10] != digito_2:
        return False

    return True


def get_cpfs_dir(settings: dict) -> Path:
    """Retorna o caminho do diretório 'CPFs', criando-o se necessário."""
    base_folder_str = settings.get("output_folder", str(Path.home() / "Documents" / "DocPopularEditor"))
    base_folder = Path(base_folder_str)
    cpfs_folder = base_folder / "CPFs"
    cpfs_folder.mkdir(parents=True, exist_ok=True)
    return cpfs_folder


def find_all_documents_by_cpf(cpf: str, settings: dict) -> List[Path]:
    """Procura todos os documentos salvos com o CPF especificado."""
    if not cpf:
        return []

    cpfs_dir = get_cpfs_dir(settings)
    pattern = str(cpfs_dir / f"{cpf}_pag*.jpg")
    files = glob.glob(pattern)

    legacy_file = cpfs_dir / f"{cpf}.jpg"
    if legacy_file.exists():
        files.append(str(legacy_file))

    if not files:
        return []

    files.sort()
    return [Path(f) for f in files]


def find_document_by_cpf(cpf: str, settings: dict) -> Optional[Path]:
    """Retorna a primeira página do documento de um CPF."""
    all_docs = find_all_documents_by_cpf(cpf, settings)
    if all_docs:
        return all_docs[0]
    return None


def save_cpf_documents(cpf: str, images: List[Image.Image], settings: dict) -> List[Path]:
    """Salva uma lista de imagens na pasta de CPFs."""
    cpfs_dir = get_cpfs_dir(settings)

    old_files = find_all_documents_by_cpf(cpf, settings)
    for f in old_files:
        try:
            f.unlink()
        except Exception:
            pass

    saved_paths = []
    for i, img in enumerate(images, 1):
        file_path = cpfs_dir / f"{cpf}_pag{i}.jpg"
        img.save(str(file_path), format="JPEG", quality=90)
        saved_paths.append(file_path)

    return saved_paths


def save_cpf_document(cpf: str, image: Image.Image, settings: dict) -> Path:
    """Legacy helper para salvar apenas uma imagem."""
    paths = save_cpf_documents(cpf, [image], settings)
    return paths[0]
