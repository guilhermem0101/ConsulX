import streamlit as st
import plotly.express as px
import pandas as pd
import os
import json
from calcula_resultados import compute_indicators_from_files, extract_accounts
from streamlit_elements import elements, mui, html, editor, nivo, media, lazy, sync, dashboard
files = ["balancetes/balancete1.json"]
result = compute_indicators_from_files(files)
df_balancete = pd.json_normalize(
    result["per_file"]).drop(columns=["file", "n_leaves"])

# ======================== LÊ TODOS OS BALANCETES TEMPORAIS ========================
# Caminho da pasta
folder_path = "balancetes/industrial_nordeste"

all_rows = []

# Loop em todos os arquivos JSON da pasta
for filename in os.listdir(folder_path):
    if filename.endswith(".json"):
        file_path = os.path.join(folder_path, filename)

        # Extrai o mês do nome do arquivo (ex: Balancete.2023-01.normalized.json → 2023-01)
        mes = filename.split(".")[1]

        # Lê o JSON
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Percorre as seções e extrai as contas
        for section in data.values():
            if isinstance(section, dict) and "descricao" in section:
                contas = extract_accounts(section)
                # Adiciona o mês a cada conta extraída
                for conta in contas:
                    conta["mes"] = mes
                all_rows.extend(contas)

# Cria o DataFrame consolidado
df_hist = pd.DataFrame(all_rows)

# ======================== BIGNUMBERS ========================

receita_bruta = df_hist[(df_hist["nivel_1"] == "RECEITAS") & (
    df_hist["nivel_2"] == "Serviços Prestados a Prazo")]

# Impostos sobre receita (deduções) = "Simples Nacional sobre vendas e serviços"
impostos_sobre_receita = df_hist[(df_hist["nivel_1"] == "RECEITAS") & (
    df_hist["nivel_2"] == "Simples Nacional sobre vendas e serviços")]

# Custos e Despesas = todas as linhas em "CUSTOS E DESPESAS"
custos_despesas = df_hist[df_hist["nivel_1"] == "CUSTOS E DESPESAS"]

# Caixa e equivalentes = "ATIVO CIRCULANTE" e "DISPONIBILIDADES"
caixa = df_hist[(df_hist["nivel_2"] == "ATIVO CIRCULANTE") &
           (df_hist["nivel_3"] == "DISPONIBILIDADES")]

# Agregar valores por mês
receita_bruta_mensal = receita_bruta.groupby("mes")["saldo_atual"].sum()
impostos_mensal = impostos_sobre_receita.groupby("mes")["saldo_atual"].sum()
custos_mensal = custos_despesas.groupby("mes")["saldo_atual"].sum()
caixa_mensal = caixa.groupby("mes")["saldo_atual"].sum()

# Calcular os indicadores
df_indices = pd.DataFrame({
    "Receita Bruta": receita_bruta_mensal,
    "(-) Impostos sobre Receita": impostos_mensal,
    "Custo Total": custos_mensal,
    "Disponibilidade de Caixa": caixa_mensal
})

# Receita Líquida
df_indices["Receita Líquida"] = df_indices["Receita Bruta"] - \
    df_indices["(-) Impostos sobre Receita"]

# Lucro Bruto = Receita Líquida - Custo Total
df_indices["Lucro Bruto"] = df_indices["Receita Líquida"] - \
    df_indices["Custo Total"]

# Lucro Líquido (neste modelo simplificado consideramos que todos os custos/despesas já estão no grupo "CUSTOS E DESPESAS")
df_indices["Lucro Líquido"] = df_indices["Lucro Bruto"]


# ======================== INDICADDORES ========================

df_agrupado = df_hist.groupby(['nivel_2', 'mes'], as_index=False)[
    'saldo_atual'].sum()
filtro = df_agrupado.loc[
    df_agrupado['nivel_2'].isin(
        ['ATIVO CIRCULANTE', 'PASSIVO CIRCULANTE', 'ATIVO NÃO CIRCULANTE', 'PASSIVO NÃO CIRCULANTE'])
]
# Cria a tabela pivot
tabela_pivot = pd.pivot_table(
    filtro,
    values='saldo_atual',
    index='mes',
    columns='nivel_2',
    aggfunc='first'
)

print("Tabela original:")
# df_agrupado
print("\nTabela pivotada:")
# tabela_pivot

tabela_pivot = pd.merge(
    tabela_pivot, df_indices["Disponibilidade de Caixa"], on='mes', how='inner')
# Criar os cálculos
tabela_pivot['Ativo_Total'] = tabela_pivot['ATIVO CIRCULANTE'] + \
    tabela_pivot['ATIVO NÃO CIRCULANTE']
tabela_pivot['Passivo_Total'] = tabela_pivot['PASSIVO CIRCULANTE'] + \
    tabela_pivot['PASSIVO NÃO CIRCULANTE']

tabela_pivot['Liquidez_Corrente'] = tabela_pivot['ATIVO CIRCULANTE'] / \
    tabela_pivot['PASSIVO CIRCULANTE']
tabela_pivot['Liquidez_Imediata'] = tabela_pivot['Disponibilidade de Caixa'] / tabela_pivot['PASSIVO CIRCULANTE']
tabela_pivot['Liquidez_Geral'] = (tabela_pivot['ATIVO CIRCULANTE'] + tabela_pivot['ATIVO NÃO CIRCULANTE']) / \
    (tabela_pivot['PASSIVO CIRCULANTE'] +
     tabela_pivot['PASSIVO NÃO CIRCULANTE'])
tabela_pivot['Solvencia_Geral'] = tabela_pivot['Ativo_Total'] / \
    tabela_pivot['Passivo_Total']
tabela_pivot['Endividamento'] = tabela_pivot['Passivo_Total'] / \
    tabela_pivot['Ativo_Total']
tabela_pivot['Endividamento_Geral'] = (
    tabela_pivot['Passivo_Total']) / tabela_pivot['Ativo_Total']

ultima_data = tabela_pivot.index.max()
indices_max = tabela_pivot.loc[tabela_pivot.index == ultima_data]


# Dados de exemplo
indicadores = [
    {
        "titulo": "Endividamento Geral",
        "descricao": "Grau em que os Ativos Totais são financiados por recursos de terceiros.",
        "memoria": "Passivo Circulante + Exigível a Longo Prazo / Ativo Total",
        "valor": round(indices_max['Endividamento_Geral'].values[0], 2)
    },
    {
        "titulo": "Endividamento",
        "descricao": "Quanto a empresa possui de imediato no caixa, frente às obrigações exigíveis.",
        "memoria": "Disponível / Passivo Circulante",
        "valor": round(indices_max['Endividamento'].values[0], 2)
    },
    {
        "titulo": "Liquidez Corrente",
        "descricao": "Capacidade de a empresa saldar suas dívidas a curto prazo, em até 360 dias.",
        "memoria": "Ativo Circulante / Passivo Circulante",
        "valor": round(indices_max['Liquidez_Corrente'].values[0], 2)
    },
    {
        "titulo": "Solvência",
        "descricao": "Grau em que a empresa dispõe em Ativos Totais para o pagamento total de dívidas.",
        "memoria": "Ativo Total / Passivo Circulante + Exigível a Longo Prazo",
        "valor": round(indices_max['Solvencia_Geral'].values[0], 2)
    },
    {
        "titulo": "Liquidez Geral",
        "descricao": "Situação financeira da empresa a longo prazo, incluindo dívidas acima de 360 dias.",
        "memoria": "(Ativo Circulante + Realizável a Longo Prazo) / (Passivo Circulante + Exigível a Longo Prazo)",
        "valor": round(indices_max['Liquidez_Geral'].values[0], 2)
    },
    {
        "titulo": "Liquidez Imediata",
        "descricao": "Quanto a empresa possui de imediato no caixa, frente às obrigações exigíveis.",
        "memoria": "Disponível / Passivo Circulante",
        "valor": round(indices_max['Liquidez_Imediata'].values[0], 2)
    }
]
# ======================== INIT ========================

df_balancete.columns = df_balancete.columns.str.replace("indicators.", "")
receita_bruta = df_balancete.loc[0, "receita_bruta"]
receita_liquida = df_balancete.loc[0, "receita_liquida"]
lucro_bruito = df_balancete.loc[0, "lucro_bruto"]
lucro_liquido = df_balancete.loc[0, "lucro_liquido"]
disponibilidade_caixa = df_balancete.loc[0, "disponibilidade_caixa"]































# ======================
# CONFIGURAÇÕES GERAIS
# ======================
st.set_page_config(page_title="Dashboard Contábil", layout="wide")


# ======================
# SIDEBAR (MENU LATERAL)
# ======================
with st.sidebar:
    st.image("https://i.imgur.com/7KKstrd.jpeg", width=180)
    st.title("CONSULX")
    st.markdown("### 📊 Dashboard")
    st.markdown("### 👥 Clientes")
    st.markdown("### ⚙️ Configuração")

# ======================
# TOPO COM ABAS
# ======================
abas = st.tabs(["Gerencial", "Contábil", "Projeção", "Balancete"])

with abas[1]:  # Aba "Contábil"
    st.subheader("📑 Painel Contábil")

    # ======================
    # MÉTRICAS SUPERIORES
    # ======================
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Receita Bruta", f"R$ {receita_bruta:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))
    with col2:
        st.metric("Receita Líquida", f"R$ {receita_liquida:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))
    with col3:
        st.metric("Lucro Bruto", f"R$ {lucro_bruito:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))
    with col4:
        st.metric("Lucro Líquido", f"R$ {lucro_liquido:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))
    with col5:
        st.metric("Disponibilidade de Caixa", f"R$ {disponibilidade_caixa:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # ======================
    # GRÁFICOS DE INDICADORES TEMPORAIS (BARRAS INDIVIDUAIS)
    # ======================
    st.subheader("📊 Indicadores de Liquidez e Endividamento ao Longo do Tempo")

    # Converter índice para coluna e ordenar
    df_plot = tabela_pivot.reset_index().sort_values("mes")
    df_plot["mes"] = pd.to_datetime(df_plot["mes"], format="%Y-%m")

    # Função para criar gráfico de barras por indicador


    def plot_indicator_bar(df, indicador, titulo):
        fig = px.bar(
            df,
            x="mes",
            y=indicador,
            text_auto=".2f",
            labels={"mes": "Mês", indicador: "Índice"},
            title=titulo,
            color_discrete_sequence=["#3E4DD8"]
        )
        fig.update_traces(marker_line_width=0.5)
        fig.update_layout(
            xaxis_title="Período",
            yaxis_title="Valor",
            showlegend=False,
            title_x=0.3
        )
        return fig


   

    # Primeira linha
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_indicator_bar(df_plot, "Liquidez_Corrente",
                        "Liquidez Corrente"), use_container_width=True)
    with col2:
        st.plotly_chart(plot_indicator_bar(df_plot, "Solvencia_Geral",
                        "Solvência Geral"), use_container_width=True)

    # Segunda linha
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(plot_indicator_bar(df_plot, "Liquidez_Geral",
                        "Liquidez Geral"), use_container_width=True)
    with col4:
        st.plotly_chart(plot_indicator_bar(df_plot, "Liquidez_Imediata",
                        "Liquidez Imediata"), use_container_width=True)

    # Terceira linha
    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(plot_indicator_bar(df_plot, "Endividamento_Geral",
                        "Endividamento Geral"), use_container_width=True)
    with col6:
        st.plotly_chart(plot_indicator_bar(df_plot, "Endividamento",
                        "Endividamento"), use_container_width=True)

    


with abas[0]:  # Aba "Gerencial"
    st.subheader("📑 Painel Gerencial")

    #tabela_pivot
    #indices_max

    # Layout: 3 cards por linha
    cols_per_row = 3
    for i in range(0, len(indicadores), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, indicador in zip(cols, indicadores[i:i+cols_per_row]):
            col.markdown(f"""
            <div style="
                background-color: #f8f9fa;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 0 10px rgba(0,0,0,0.05);
                height: 250px;
            ">
                <h4 style="margin-bottom: 5px;">{indicador['titulo']}</h4>
                <p style="font-size: 13px; color: #555;">{indicador['descricao']}</p>
                <p style="font-size: 12px; color: #777;"><b>Memória de Cálculo:</b> {indicador['memoria']}</p>
                <h2 style="text-align:center; color:#000;">{indicador['valor']}</h2>
            </div>
            """, unsafe_allow_html=True)
