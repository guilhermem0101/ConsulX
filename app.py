import streamlit as st
import plotly.express as px
import pandas as pd
import json
from calcula_resultados import compute_indicators_from_files, extract_accounts

files = ["balancetes/balancete1.json"]
result = compute_indicators_from_files(files)
df_balancete = pd.json_normalize(
    result["per_file"]).drop(columns=["file", "n_leaves"])


    
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
abas = st.tabs(["Gerencial", "Contábil", "Folha", "Balancete"])

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
    # GRÁFICOS
    # ======================

    col1, col2 = st.columns([1, 2])

    # Pizza
    with col1:
        pie_data = pd.DataFrame({
            "Categoria": ["A", "B", "C", "D", "E"],
            "Valor": [50, 13, 20, 10, 7]
        })
        fig_pie = px.pie(pie_data, values="Valor", names="Categoria", hole=0.5)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Barras horizontais
    with col2:
        bar_data = pd.DataFrame({
            "Fonte": ["Organic search", "Direct", "Referral", "Paid search", "Social"],
            "Percentual": [27, 20, 18, 12, 9]
        })
        fig_bar = px.bar(bar_data, x="Percentual", y="Fonte", orientation="h")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Linha/Barras comparando vendas
    st.subheader("Comparação de Vendas")
    vendas_data = pd.DataFrame({
        "Mês": pd.date_range("2023-01-01", periods=12, freq="M"),
        "Carol": [1.5, 2, 1.8, 2.2, 2, 2.5, 2.8, 2.4, 2.6, 2.9, 3.0, 3.2],
        "João": [1.2, 1.6, 1.4, 1.8, 1.5, 2.0, 2.2, 1.9, 2.1, 2.3, 2.5, 2.7],
    })
    fig_comp = px.bar(vendas_data, x="Mês", y=[
                      "Carol", "João"], barmode="group")
    st.plotly_chart(fig_comp, use_container_width=True)
