"""
balancete_to_json.py
Extrai texto de PDF/imagem/txt, identifica linhas de contas contábeis e converte para JSON hierárquico.
- Contas sintéticas viram nós com children.
- Valores são atribuídos apenas às contas analíticas (folhas).
- Aceita PDF, imagem (png/jpg) ou .txt com o texto extraído.

Dependências:
 pip install pdfplumber pytesseract pillow opencv-python
 E instalar o Tesseract OCR no sistema operacional.
"""

import re
import json
import pdfplumber
import pytesseract
from PIL import Image
import cv2
import numpy as np
import argparse
import logging
from collections import OrderedDict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --------------------------
# Helpers
# --------------------------
# matches numbers like 1.234,56 or 1234.56 or -1.234
NUM_RE = re.compile(r'-?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?')


def normalize_number(num_str):
    """Converte número em formato BR (1.234,56) ou EN (1,234.56) para float.
       Retorna None se não for numérico.
    """
    if num_str is None:
        return None
    s = num_str.strip()
    if not s:
        return None
    # remover pontos de milhares e trocar vírgula por ponto quando houver vírgula
    # detectar formato: se houver vírgula e separador de milhares '.', assume BR
    if s.count(',') == 1 and '.' in s and s.rfind('.') < s.rfind(','):
        s = s.replace('.', '').replace(',', '.')
    else:
        # tratar caso vírgula seja decimal ou apenas separador
        s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return None


def extract_text_from_pdf(path):
    logging.info(f"Extraindo texto do PDF: {path}")
    text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text)


def preprocess_image_for_ocr(img_path):
    # retorna imagem binarizada para OCR
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # aumente contraste / redimensione se necessário
    scale = 2.0
    gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale,
                      interpolation=cv2.INTER_CUBIC)
    # aplicação leve de blur e threshold
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th


def extract_text_from_image(path):
    logging.info(f"Extraindo texto da imagem (OCR): {path}")
    img = preprocess_image_for_ocr(path)
    pil_img = Image.fromarray(img)
    # ajustar idiomas conforme necessário
    text = pytesseract.image_to_string(pil_img, lang='por+eng')
    return text


# --------------------------
# Parsing
# --------------------------
# Regex para capturar código de conta no começo: ex "1.1.05.03.0001" ou "1.1.01"
CODE_RE = re.compile(r'^\s*(\d+(?:\.\d+)+)\s+(.+)$')


def parse_text_to_entries(text):
    """
    Converte texto em "entradas" com:
      - code (string) ex "1.1.05.03.0001"
      - desc (string)
      - valores (lista de até 4 números extraídos no final da linha)
    Heurística: a descrição é o trecho entre o código e o primeiro número da linha.
    """
    entries = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = CODE_RE.match(line)
        if not m:
            continue
        code = m.group(1).strip()
        tail = m.group(2).rstrip()
        # extrair todos os números da linha (últimos tokens)
        nums = NUM_RE.findall(tail)
        # retirar números da 'tail' para isolar descrição
        if nums:
            # pegar posição do primeiro número encontrado para separar desc
            first_num = nums[0]
            idx = tail.find(first_num)
            desc = tail[:idx].strip()
        else:
            desc = tail.strip()
        # converter números (mantendo ordem encontrada): pode ser saldo_anterior, debito, credito, saldo_atual
        nums_conv = [normalize_number(n) for n in nums]
        entries.append({
            "code": code,
            "desc": desc,
            "nums": nums_conv
        })
    return entries

# --------------------------
# Construção da árvore
# --------------------------


def insert_entry(tree_roots, code, desc, nums):
    """
    Insere entry na árvore, criando nós intermediários (sintéticos).
    Só coloca valores numéricos nas folhas (quando não houver 'children' adicionais).
    Estrutura de nó:
    {
       "conta": "1.1.05.03.0001",
       "descricao": "TERRENO...",
       "children": [...],   # opcional
       "saldo_anterior": ... , "debito": ..., "credito": ..., "saldo_atual": ...
    }
    """
    parts = code.split('.')
    # buscar (ou criar) root para primeiro part
    root_key = parts[0]
    # as raízes são armazenadas em lista; buscaremos/nos servimos de dict auxiliar
    cur_list = tree_roots
    cur_node = None
    prefix = []
    for i, p in enumerate(parts):
        prefix.append(p)
        cur_code = ".".join(prefix)
        # procurar node com conta == cur_code dentro cur_list
        found = None
        for n in cur_list:
            if n.get("conta") == cur_code:
                found = n
                break
        if not found:
            # criar novo nó sintético
            found = {"conta": cur_code, "descricao": None, "children": []}
            cur_list.append(found)
        # se for o último, atribuir descrição e valores (se houver)
        if i == len(parts) - 1:
            # atribuir descrição (substitui None se anterior)
            found["descricao"] = desc or found.get("descricao")
            # colocar valores apenas nas folhas
            if nums:
                # Mapear números: heurística comum: [saldo_anterior, debito, credito, saldo_atual]
                keys = ["saldo_anterior", "debito", "credito", "saldo_atual"]
                for k, v in zip(keys, nums):
                    if v is not None:
                        found[k] = v
            # se não houver números, mantém como nó sem valores
        else:
            # se not last, garantir que node tenha children e atualizar cur_list para children
            if "children" not in found:
                found["children"] = []
            cur_list = found["children"]


def tree_to_ordered_json(tree_roots):
    # opcional: pode ordenar children por 'conta' para previsibilidade
    def sort_children(node):
        if "children" in node:
            node["children"].sort(key=lambda x: list(
                map(int, x["conta"].split('.'))))
            for c in node["children"]:
                sort_children(c)
    for r in tree_roots:
        sort_children(r)
    return tree_roots

# --------------------------
# Pipeline principal
# --------------------------


def convert_file_to_json(input_path, output_path):
    # decidir forma de extração
    text = ""
    if input_path.lower().endswith(".pdf"):
        text = extract_text_from_pdf(input_path)
    elif input_path.lower().endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        text = extract_text_from_image(input_path)
    elif input_path.lower().endswith(".txt"):
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        raise ValueError(
            "Formato não suportado. Use PDF, imagem (png/jpg) ou txt.")
    logging.info("Texto extraído. Iniciando parsing de linhas com contas...")
    entries = parse_text_to_entries(text)
    logging.info(
        f"Linhas reconhecidas contendo código de conta: {len(entries)}")
    # construir árvore
    roots = []
    for e in entries:
        insert_entry(roots, e["code"], e["desc"], e["nums"])
    ordered = tree_to_ordered_json(roots)
    # salvar JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
    logging.info(f"Arquivo JSON salvo em: {output_path}")
    return ordered

# --------------------------
# CLI
# --------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Converte balancete (PDF/imagem/txt) em JSON hierárquico.")
    parser.add_argument("--input", "-i", required=True,
                        help="Balancete.pdf")
    parser.add_argument("--output", "-o", required=True,
                        help="Balancete.json")
    args = parser.parse_args()
    convert_file_to_json(args.input, args.output)


if __name__ == "__main__":
    main()
