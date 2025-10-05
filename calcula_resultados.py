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
from typing import List, Dict, Any 
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


# -------------------- CLI opcional --------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Compute indicators from balancete JSONs")
    parser.add_argument("--files", "-f", nargs="+",
                        required=True, help="JSON files")
    parser.add_argument(
        "--out", "-o", default="resultados_indicadores.json", help="output file")
    args = parser.parse_args()
    res = compute_indicators_from_files(args.files)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("Saved:", args.out)


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
