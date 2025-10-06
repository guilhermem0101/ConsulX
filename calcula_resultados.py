#!/usr/bin/env python3
"""
calcula_resultados.py

Lê um ou mais arquivos JSON de balancete (hierárquico, contas sintéticas com children),
extrai folhas (contas analíticas) e calcula indicadores financeiros:
- Receita Bruta
- Receita Líquida (Receita Bruta - impostos sobre vendas)
- Lucro Bruto (Receita Líquida - custos)
- Lucro Líquido (Lucro Bruto - despesas)
- Disponibilidade de Caixa (caixa + bancos + aplicações)

Atenção: o script usa heurísticas por palavras-chave. Ajuste `keywords` conforme seu chart of accounts.
"""
import json
import os
import re
from typing import List, Dict, Any 
from pathlib import Path
from datetime import datetime
import pandas as pd
# --- heurísticas simples (ajuste se necessário) ---
REVENUE_KEYWORDS = ["receita", "receitas", "venda",
                    "vendas", "serviço", "serviços", "faturamento"]
TAX_ON_SALES_KEYWORDS = ["iss", "icms", "pis", "cofins",
                         "simples", "irrf", "imposto", "impostos", "retido"]
COST_KEYWORDS = ["custo", "custos", "cmv", "estoque", "mercadoria"]
EXPENSE_KEYWORDS = ["despesa", "despesas", "juros", "multas",
                    "salário", "salários", "frete", "serviços de terceiros", "deprecia"]
CASH_KEYWORDS = ["caixa", "banco", "conta", "aplica",
                 "aplicação", "disponibilidades", "equivalente"]

REVENUE_CODE_PREFIXES = {"3", "03"}
COST_CODE_PREFIXES = {"4", "04"}
EXPENSE_CODE_PREFIXES = {"4", "04"}

# -------------------- utilitários --------------------


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_leaf(node: Dict[str, Any]) -> bool:
    return not node.get("children")


def to_float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def get_number_from_node(node: Dict[str, Any]) -> float:
    if "saldo_atual" in node:
        return to_float(node.get("saldo_atual", 0.0))
    if any(k in node for k in ("saldo_anterior", "debito", "credito")):
        sa = to_float(node.get("saldo_anterior", 0.0))
        deb = to_float(node.get("debito", 0.0))
        cred = to_float(node.get("credito", 0.0))
        return sa + deb - cred
    return 0.0


def flatten_leaves(node: Dict[str, Any], parent_code: str = "") -> List[Dict[str, Any]]:
    leaves = []
    if is_leaf(node):
        leaves.append({
            "code": node.get("conta") or parent_code,
            "descricao": (node.get("descricao") or "").strip(),
            "balance": get_number_from_node(node),
        })
    else:
        for c in node.get("children", []):
            leaves.extend(flatten_leaves(c, parent_code=node.get("conta", "")))
    return leaves


def walk_roots(data: Any) -> List[Dict[str, Any]]:
    leaves = []
    if isinstance(data, dict):
        # if top-level includes named sections (balancete, passivo, etc.)
        for v in data.values():
            if isinstance(v, dict) and "conta" in v:
                leaves.extend(flatten_leaves(v))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and "conta" in item:
                        leaves.extend(flatten_leaves(item))
            elif isinstance(v, dict):
                # defensive: try flatten
                try:
                    leaves.extend(flatten_leaves(v))
                except Exception:
                    pass
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                leaves.extend(flatten_leaves(item))
    return leaves


def matches_keywords(text: str, keywords: List[str]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


def code_prefix_matches(code: str, prefixes: set) -> bool:
    if not code:
        return False
    first = code.split('.')[0]
    return first in prefixes

# -------------------- cálculo --------------------


def compute_indicators_from_leaves(leaves: List[Dict[str, Any]]) -> Dict[str, float]:
    receita_bruta = impostos_vendas = custos = despesas = disponibilidade_caixa = 0.0

    for leaf in leaves:
        desc = (leaf.get("descricao") or "").lower()
        code = leaf.get("code") or ""
        bal = float(leaf.get("balance") or 0.0)

        if matches_keywords(desc, CASH_KEYWORDS):
            disponibilidade_caixa += bal

        if matches_keywords(desc, REVENUE_KEYWORDS) or code_prefix_matches(code, REVENUE_CODE_PREFIXES):
            receita_bruta += bal

        if matches_keywords(desc, TAX_ON_SALES_KEYWORDS):
            impostos_vendas += bal

        if matches_keywords(desc, COST_KEYWORDS) or code_prefix_matches(code, COST_CODE_PREFIXES):
            custos += bal

        if matches_keywords(desc, EXPENSE_KEYWORDS) or code_prefix_matches(code, EXPENSE_CODE_PREFIXES):
            despesas += bal

    receita_liquida = receita_bruta - impostos_vendas
    lucro_bruto = receita_liquida - custos
    lucro_liquido = lucro_bruto - despesas

    return {
        "receita_bruta": round(receita_bruta, 2),
        "impostos_vendas": round(impostos_vendas, 2),
        "receita_liquida": round(receita_liquida, 2),
        "custos": round(custos, 2),
        "lucro_bruto": round(lucro_bruto, 2),
        "despesas": round(despesas, 2),
        "lucro_liquido": round(lucro_liquido, 2),
        "disponibilidade_caixa": round(disponibilidade_caixa, 2)
    }

# -------------------- API pública mínima --------------------


def compute_indicators_from_files(file_paths: List[str]) -> Dict[str, Any]:
    """
    Retorna dict:
    {
      "per_file": [ { "file": path, "indicators": {...} }, ... ],
      "combined_totals": {...}
    }
    """
    per_file = []
    totals = {
        "receita_bruta": 0.0,
        "impostos_vendas": 0.0,
        "receita_liquida": 0.0,
        "custos": 0.0,
        "lucro_bruto": 0.0,
        "despesas": 0.0,
        "lucro_liquido": 0.0,
        "disponibilidade_caixa": 0.0
    }

    for fp in file_paths:
        if not os.path.exists(fp):
            raise FileNotFoundError(fp)
        data = load_json(fp)
        leaves = walk_roots(data)
        inds = compute_indicators_from_leaves(leaves)
        per_file.append(
            {"file": fp, "indicators": inds, "n_leaves": len(leaves)})
        for k in totals:
            totals[k] += inds.get(k, 0.0)

    combined = {"per_file": per_file, "combined_totals": {
        k: round(v, 2) for k, v in totals.items()}}
    return combined

# -----------------------------------------------------------------------------------------------------
# -----------------------
# Helpers para conversão
# -----------------------
_br_num_re = re.compile(r'^\s*([+-]?[0-9\.\,]+)\s*([DC])?\s*$', re.IGNORECASE)


def br_str_to_float_and_sinal(s: str):
    """
    Converte strings brasileiras '1.234,56D' -> (1234.56, 'D').
    Retorna (None, '') se não for possível parsear.
    """
    if not isinstance(s, str):
        return None, ""
    m = _br_num_re.match(s.strip())
    if not m:
        return None, ""
    num_str = m.group(1)
    suf = (m.group(2) or "").upper()
    num_str = num_str.replace(".", "").replace(",", ".")
    try:
        val = float(num_str)
    except:
        return None, suf
    return val, suf


def parse_value_field(value):
    """
    Aceita:
      - dict {"valor": float, "sinal": "D"}
      - string "1.234,56D"
      - numeric
    Retorna (valor_float_or_None, sinal_str_or_empty)
    """
    if value is None:
        return None, ""
    if isinstance(value, dict):
        val = value.get("valor")
        sinal = (value.get("sinal") or "").upper()
        # ensure float
        try:
            valf = float(val) if val is not None else None
        except:
            valf = None
        return valf, sinal
    if isinstance(value, (int, float)):
        return float(value), ""
    if isinstance(value, str):
        return br_str_to_float_and_sinal(value)
    return None, ""


def periodo_to_mes_ref(periodo_str: str, fallback_filename: str = None):
    """
    Converte '01/02/2023 - 28/02/2023' -> '2023-02'.
    Se falhar, tenta extrair do filename: 'Balancete.2023-02.json' -> '2023-02'
    """
    if isinstance(periodo_str, str) and "-" in periodo_str:
        parts = periodo_str.split("-")
        # pegar a data da direita (fim do periodo) e extrair mês/ano
        right = parts[-1].strip()
        try:
            dt = datetime.strptime(right, "%d/%m/%Y")
            return f"{dt.year:04d}-{dt.month:02d}"
        except:
            pass
    # fallback usando filename
    if fallback_filename:
        m = re.search(r'(\d{4})-(\d{2})', fallback_filename)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
    return None

# -----------------------
# Flatten recursion
# -----------------------


def _flatten_account_node(node: dict, rows: list, periodo: str, level: int = 0, parent_code: str = None):
    """
    Percorre recursivamente 'node' (uma conta / grupo) e adiciona linhas em `rows`.
    Cada linha contém dados do saldo_atual, saldo_anterior, debito, credito (valor + sinal).
    """
    if not isinstance(node, dict):
        return

    codigo = node.get("codigo")
    descricao = node.get("descricao") or node.get("conta") or ""
    # montar um identificador (se existir apenas codigo)
    identificador = f"{codigo} - {descricao}" if codigo else descricao

    # extrair campos relevantes e parsear
    sa_val, sa_sinal = parse_value_field(node.get("saldo_atual"))
    san_val, san_sinal = parse_value_field(node.get("saldo_anterior"))
    deb_val, deb_sinal = parse_value_field(node.get("debito"))
    cred_val, cred_sinal = parse_value_field(node.get("credito"))

    # criar linha (uma única linha por conta/periodo)
    row = {
        "mes_ref": periodo,
        # texto original do periodo (pode sobrescrever depois)
        "periodo_text": periodo,
        "codigo": codigo,
        "conta": descricao,
        "identificador": identificador,
        "nivel": level,
        "saldo_atual_valor": sa_val,
        "saldo_atual_sinal": sa_sinal,
        "saldo_anterior_valor": san_val,
        "saldo_anterior_sinal": san_sinal,
        "debito_valor": deb_val,
        "debito_sinal": deb_sinal,
        "credito_valor": cred_val,
        "credito_sinal": cred_sinal,
        "parent_codigo": parent_code
    }
    # signed saldo (útil para plot): tratamos D => positivo, C => negativo
    if sa_val is not None:
        if sa_sinal == "C":
            row["saldo_atual_signed"] = -abs(sa_val)
        else:
            # D or '' -> positivo
            row["saldo_atual_signed"] = abs(sa_val)
    else:
        row["saldo_atual_signed"] = None

    rows.append(row)

    # processar filhos se existirem
    children = node.get("children") or node.get("filhos") or []
    if isinstance(children, list):
        for child in children:
            _flatten_account_node(child, rows, periodo,
                                  level=level + 1, parent_code=codigo)

# -----------------------
# Função pública
# -----------------------


def load_balancetes_to_df(folder: str = "balancetes", pattern: str = "*.json"):
    """
    Lê todos os arquivos JSON na pasta `folder` (por padrão ./balancetes),
    achata a estrutura hierárquica e retorna um pandas.DataFrame com colunas:
      ['mes_ref', 'periodo_text', 'codigo', 'conta', 'identificador', 'nivel',
       'saldo_atual_valor', 'saldo_atual_sinal', 'saldo_atual_signed', ...]
    Além disso, preenche saldos de contas sintéticas (quando NaN) somando os saldos
    das contas descendentes.
    """
    p = Path(folder)
    if not p.exists():
        raise FileNotFoundError(f"Pasta '{folder}' não encontrada")

    files = sorted(p.glob(pattern))
    all_rows = []

    for f in files:
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            # tentar pular arquivo que não seja JSON válido
            print(f"AVISO: falha ao ler {f.name}: {e}")
            continue

        # obter periodo do metadata (se existir)
        meta = raw.get("metadata") if isinstance(raw, dict) else {}
        periodo_text = meta.get("periodo") if meta else None
        mes_ref = periodo_to_mes_ref(periodo_text, fallback_filename=f.name)
        # se não veio periodo_text, tentar metadado com outro nome
        if not periodo_text and isinstance(raw, dict):
            periodo_text = raw.get("periodo") or raw.get("meta_periodo")

        # localizar raiz do balancete: 'balancete' ou 'balancetes'
        bal = raw.get("balancete") or raw.get(
            "balancetes") or raw.get("Balancete") or []
        if isinstance(bal, dict):
            # algumas estruturas podem ter um dict com top-level accounts
            # transformar em lista
            bal = [bal]

        # caso não venha balancete no topo, tentar encontrar lista em qualquer chave
        if not bal:
            for k, v in (raw.items() if isinstance(raw, dict) else []):
                if isinstance(v, list):
                    # heurística: lista de dicts com 'descricao' ou 'codigo'
                    if v and isinstance(v[0], dict) and ("descricao" in v[0] or "codigo" in v[0]):
                        bal = v
                        break

        # para cada top-level account, achatar recursivamente
        for top in (bal or []):
            _flatten_account_node(
                top, all_rows, mes_ref or periodo_text or f.name, level=0, parent_code=None)

    # transformar em DataFrame
    df = pd.DataFrame(all_rows)

    # preencher saldos sintéticos com soma dos descendentes (quando saldo_atual_valor for NaN)
    if not df.empty:
        # garantir que saldo_atual_signed seja numérico (float) para somas
        df["saldo_atual_signed"] = pd.to_numeric(
            df["saldo_atual_signed"], errors="coerce")

        # lista de códigos não-nulos ordenada por comprimento decrescente (filhos primeiro)
        codes = df["codigo"].fillna("").unique().tolist()
        codes = [c for c in codes if c]  # remover strings vazias
        codes_sorted = sorted(codes, key=lambda x: len(x), reverse=True)

        for code in codes_sorted:
            # máscara para todos os descendentes diretos/indiretos (prefixo "code.")
            prefix = f"{code}."
            # somar saldo_atual_signed de todas as linhas cuja 'codigo' começa com prefix
            mask_desc = df["codigo"].fillna("").str.startswith(prefix)
            if not mask_desc.any():
                continue
            descendant_sum = df.loc[mask_desc,
                                    "saldo_atual_signed"].dropna().sum()
            # se a conta 'code' tem saldo_atual_valor faltando, preenchemos com a soma
            mask_self = (df["codigo"] == code)
            if mask_self.any():
                # apenas preencher onde saldo_atual_valor está ausente (NaN)
                mask_need = mask_self & df["saldo_atual_valor"].isna()
                if mask_need.any():
                    df.loc[mask_need, "saldo_atual_signed"] = descendant_sum
                    df.loc[mask_need, "saldo_atual_valor"] = abs(
                        descendant_sum) if pd.notna(descendant_sum) else None
                    df.loc[mask_need,
                           "saldo_atual_sinal"] = "C" if descendant_sum < 0 else "D"

        # converter mes_ref em periodo datetime (1o dia do mês)
        try:
            df["mes_ref_dt"] = pd.to_datetime(
                df["mes_ref"] + "-01", errors="coerce")
        except:
            df["mes_ref_dt"] = pd.NaT

        # ordenar por data / codigo
        df = df.sort_values(["mes_ref_dt", "codigo"],
                            na_position="last").reset_index(drop=True)

    return df

# --------------------------------------------------------------------------------------
# Load the JSON data from the file
with open("balancetes/balancete1.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Recursive function to traverse the hierarchical structure and collect data


def extract_accounts(node, hierarchy=None):
    if hierarchy is None:
        hierarchy = []

    current_hierarchy = hierarchy + [node["descricao"]]
    rows = []

    if "children" in node:
        for child in node["children"]:
            rows.extend(extract_accounts(child, current_hierarchy))
    else:
        row = {f"nivel_{i+1}": level for i,
               level in enumerate(current_hierarchy)}
        row["conta"] = node["conta"]
        row["descricao"] = node["descricao"]
        row["saldo_atual"] = node.get("saldo_atual", 0.0)
        rows.append(row)

    return rows


# Extract all top-level sections (ativo, passivo, receitas, etc.)
all_rows = []
for section in data.values():
    if isinstance(section, dict) and "descricao" in section:
        all_rows.extend(extract_accounts(section))

# Create a DataFrame
df = pd.DataFrame(all_rows)

# Display the resulting DataFrame
df
