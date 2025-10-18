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

"""

from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import pandas as pd




# Extrator de balancete para dataframe
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


def processar_indicadores_financeiros(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa o DataFrame de dados financeiros e retorna uma tabela com indicadores
    financeiros calculados.
    
    Args:
        df (pd.DataFrame): DataFrame contendo os dados financeiros
        
    Returns:
        pd.DataFrame: Tabela com indicadores financeiros calculados
    """
    # Filtragem dos dados básicos
    receita_bruta = df[(df["nivel_1"] == "RECEITAS") &
                       (df["nivel_2"] == "Serviços Prestados a Prazo")]
    impostos_sobre_receita = df[(df["nivel_1"] == "RECEITAS") &
                                (df["nivel_2"] == "Simples Nacional sobre vendas e serviços")]
    custos_despesas = df[df["nivel_1"] == "CUSTOS E DESPESAS"]
    caixa = df[(df["nivel_2"] == "ATIVO CIRCULANTE") &
               (df["nivel_3"] == "DISPONIBILIDADES")]

    # Agregação mensal dos dados
    receita_bruta_mensal = receita_bruta.groupby("mes")["saldo_atual"].sum()
    impostos_mensal = impostos_sobre_receita.groupby("mes")[
        "saldo_atual"].sum()
    custos_mensal = custos_despesas.groupby("mes")["saldo_atual"].sum()
    caixa_mensal = caixa.groupby("mes")["saldo_atual"].sum()

    # Criação da tabela de indicadores
    df_indices = pd.DataFrame({
        "Receita_Bruta": receita_bruta_mensal,
        "Impostos_Receita": impostos_mensal,
        "Custo_Total": custos_mensal,
        "Disponibilidade_Caixa": caixa_mensal
    })

    # Cálculos de indicadores
    df_indices["Receita_Líquida"] = df_indices["Receita_Bruta"] - \
        df_indices["Impostos_Receita"]
    df_indices["Lucro_Bruto"] = df_indices["Receita_Líquida"] - \
        df_indices["Custo_Total"]
    df_indices["Lucro_Líquido"] = df_indices["Lucro_Bruto"]

    # Processamento adicional para tabela pivot
    df_agrupado = df.groupby(['nivel_2', 'mes'], as_index=False)[
        'saldo_atual'].sum()
    filtro = df_agrupado.loc[
        df_agrupado['nivel_2'].isin(
            ['ATIVO CIRCULANTE', 'PASSIVO CIRCULANTE',
             'ATIVO NÃO CIRCULANTE', 'PASSIVO NÃO CIRCULANTE'])
    ]

    # Criação da tabela pivot
    tabela_pivot = pd.pivot_table(
        filtro,
        values='saldo_atual',
        index='mes',
        columns='nivel_2',
        aggfunc='first'
    )

    # Mesclagem com indicadores
    tabela_pivot = pd.merge(
        tabela_pivot, df_indices, on='mes', how='inner'
    )

    # Cálculos finais
    tabela_pivot['Ativo_Total'] = tabela_pivot['ATIVO CIRCULANTE'] + \
        tabela_pivot['ATIVO NÃO CIRCULANTE']
    tabela_pivot['Passivo_Total'] = tabela_pivot['PASSIVO CIRCULANTE'] + \
        tabela_pivot['PASSIVO NÃO CIRCULANTE']

    # Indicadores de liquidez
    tabela_pivot['Liquidez_Corrente'] = tabela_pivot['ATIVO CIRCULANTE'] / \
        tabela_pivot['PASSIVO CIRCULANTE']
    tabela_pivot['Liquidez_Imediata'] = tabela_pivot['Disponibilidade_Caixa'] / \
        tabela_pivot['PASSIVO CIRCULANTE']
    tabela_pivot['Liquidez_Geral'] = (tabela_pivot['ATIVO CIRCULANTE'] +
                                      tabela_pivot['ATIVO NÃO CIRCULANTE']) / \
        (tabela_pivot['PASSIVO CIRCULANTE'] +
         tabela_pivot['PASSIVO NÃO CIRCULANTE'])

    # Indicadores de solvência
    tabela_pivot['Solvencia_Geral'] = tabela_pivot['Ativo_Total'] / \
        tabela_pivot['Passivo_Total']
    tabela_pivot['Endividamento'] = tabela_pivot['Passivo_Total'] / \
        tabela_pivot['Ativo_Total']
    tabela_pivot['Endividamento_Geral'] = tabela_pivot['Endividamento']
    
    tabela_pivot = tabela_pivot.rename(
        columns={"ATIVO CIRCULANTE": "Ativo_Circulante", "ATIVO NÃO CIRCULANTE": "Ativo_Nao_Circulante", "PASSIVO CIRCULANTE": "Passivo_Circulante", "PASSIVO NÃO CIRCULANTE": "Passivo_Nao_Circulante"})

    return tabela_pivot
