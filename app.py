import streamlit as st
import plotly.express as px
import pandas as pd
import os
import json
from streamlit_elements import elements, mui, html, editor, nivo, media, lazy, sync, dashboard
from utils.functions import processar_indicadores_financeiros, extract_accounts


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

# ======================
# FUNÇÃO DE FILTRO DE ANO
# ======================
def filtro_ano(df_plot):
    """
    Cria um seletor de ano no Streamlit e retorna o DataFrame filtrado.
    O campo 'mes' deve estar no formato 'YYYY-MM'.
    """
    # Extrair anos únicos ordenados
    anos = sorted({str(m)[:4] for m in df_plot["mes"]})

    # Caixa visual estilizada
    st.markdown("""
    <style>
        .year-filter-box {
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
            padding: 12px 20px;
            margin-bottom: 25px;
        }
        .year-filter-title {
            font-size: 15px;
            font-weight: 600;
            color: #333333;
            margin-bottom: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="year-filter-box">', unsafe_allow_html=True)

    # Filtro de ano (pode selecionar um ou vários)
    ano_selecionado = st.multiselect(
        "Selecione o(s) ano(s):",
        options=anos,
        default=anos[-1:],  # último ano por padrão
        label_visibility="collapsed"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Filtra o DataFrame conforme o(s) ano(s) escolhidos
    df_filtrado = df_plot[df_plot["mes"].str[:4].isin(ano_selecionado)]

    return df_filtrado, ano_selecionado    



indicadores_historicos = processar_indicadores_financeiros(df_hist)
ultimo_mes = indicadores_historicos.index.max() #extrai ultimo mês
indicadores_foto = indicadores_historicos.loc[indicadores_historicos.index == ultimo_mes] #filtra os indicadores do ultimo mês (visão foto)


# Dados de exemplo
indicadores = [
    {
        "titulo": "Endividamento Geral",
        "descricao": "Grau em que os Ativos Totais são financiados por recursos de terceiros.",
        "memoria": "Passivo circulante / Passivo circulante + Exigível Longo Prazo",
        "valor": round(indicadores_foto['Endividamento_Geral'].values[0], 2)
    },
    {
        "titulo": "Endividamento",
        "descricao": "Relacionamento entre a posição do Patrimônio Líquido em relação aos Empréstimos.",
        "memoria": "Passivo circulante + Exigível a Longo Prazo / Ativo Total",
        "valor": round(indicadores_foto['Endividamento'].values[0], 2)
    },
    {
        "titulo": "Liquidez Corrente",
        "descricao": "Capacidade de a empresa saldar suas dívidas a curto prazo, em até 360 dias.",
        "memoria": "Ativo Circulante / Passivo Circulante",
        "valor": round(indicadores_foto['Liquidez_Corrente'].values[0], 2)
    },
    {
        "titulo": "Solvência",
        "descricao": "Grau em que a empresa dispõe em Ativos Totais para o pagamento total de dívidas.",
        "memoria": "Ativo Total / Passivo Circulante + Exigível a Longo Prazo",
        "valor": round(indicadores_foto['Solvencia_Geral'].values[0], 2)
    },
    {
        "titulo": "Liquidez Geral",
        "descricao": "Situação financeira da empresa a longo prazo, incluindo dívidas acima de 360 dias.",
        "memoria": "(Ativo Circulante + Realizável a Longo Prazo) / (Passivo Circulante + Exigível a Longo Prazo)",
        "valor": round(indicadores_foto['Liquidez_Geral'].values[0], 2)
    },
    {
        "titulo": "Liquidez Imediata",
        "descricao": "Quanto a empresa possui de imediato no caixa, frente às obrigações exigíveis.",
        "memoria": "Disponível / Passivo Circulante",
        "valor": round(indicadores_foto['Liquidez_Imediata'].values[0], 2)
    }
]
# ======================== INIT ========================


receita_bruta = indicadores_foto['Receita_Bruta'].values[0]
receita_liquida = indicadores_foto['Receita_Líquida'].values[0]
lucro_bruito = indicadores_foto['Lucro_Bruto'].values[0]
lucro_liquido = indicadores_foto['Lucro_Líquido'].values[0]
disponibilidade_caixa = indicadores_foto['Disponibilidade_Caixa'].values[0]



# ======================
# CONFIGURAÇÕES GERAIS
# ======================
st.set_page_config(page_title="Dashboard Contábil", layout="wide")


# ======================
# SIDEBAR (MENU LATERAL)
# ======================
with st.sidebar:
    st.markdown("""
    <style>
        /* Sidebar geral */
        .sidebar .sidebar-content {
            background-color: #f5f5f5;  /* fundo cinza claro */
            padding-top: 20px;
        }
        /* Menu itens */
        .menu-item {
            display: flex;
            align-items: center;
            padding: 12px 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .menu-item:hover {
            background-color: #e0e0e0;
        }
        /* Ícone do menu */
        .menu-item img {
            width: 20px;
            height: 20px;
            margin-right: 12px;
        }
        /* Item ativo */
        .menu-item.active {
            background-color: #595959;
            color: white;
        }
        .menu-item.active img {
            filter: brightness(0) invert(1);
        }
    </style>
    
    
    <div class="menu-item active">
        <img src="https://img.icons8.com/?size=100&id=9zcV0gKAozhn&format=png&color=000000"/>
        Dashboard
    </div>
    <div class="menu-item">
        <img src="https://img.icons8.com/?size=100&id=11220&format=png&color=000000"/>
        Clientes
    </div>
    <div class="menu-item">
        <img src="https://img.icons8.com/?size=100&id=2969&format=png&color=000000"/>
        Configuração
    </div>
    """, unsafe_allow_html=True)

# ======================
# MENU DE ABAS
# ======================
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 2px solid #ddd;
}
.stTabs [data-baseweb="tab"] {
    color: #666;
    font-weight: 600;
    border-bottom: 2px solid transparent;
    padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
    color: #000000;
    border-bottom: 2px solid #000000;
}
</style>
""", unsafe_allow_html=True)
abas = st.tabs(["Gerencial", "Contábil", "Projeção", "Analítico"])




with abas[0]:  # Aba "Gerencial"
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 0 10px rgba(0,0,0,0.05);
        height: 250px; /* 🔹 altura fixa para todos os cards */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 25px; /* espaçamento entre linhas */
        overflow: hidden; /* evita quebra visual se texto for grande */
    }
    .metric-card h4 {
        margin-bottom: 10px;
        font-size: 16px;
        color: #222;
    }
    .metric-card p {
        margin-bottom: 10px;
        font-size: 14px;
        color: #555;
        text-align: justify;
    }
    .metric-card h2 {
        text-align: center;
        color: #000;
        margin-top: auto;
    }
    </style>
    """, unsafe_allow_html=True)

    cols_per_row = 3
    for i in range(0, len(indicadores), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, indicador in zip(cols, indicadores[i:i+cols_per_row]):
            col.markdown(f"""
            <div class="metric-card">
                <div>
                    <h4>{indicador['titulo']}</h4>
                    <p>{indicador['descricao']}</p>
                    <p style="font-size: 14px; color: #777;">
                        <b>Memória de Cálculo:</b> {indicador['memoria']}
                    </p>
                </div>
                <h2>{indicador['valor']}</h2>
            </div>
            """, unsafe_allow_html=True)




with abas[1]:  # Aba "Contábil"
    st.markdown("""
        <style>
            /* Container principal */
            .main {
                padding: 0rem 1rem 1rem 1rem !important;
            }

            /* Remover excesso de padding entre colunas */
            div[data-testid="column"] {
                padding-left: 0.4rem !important;
                padding-right: 0.4rem !important;
            }

            /* Painel contábil */
            .bignumber-card {
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0 3px 8px rgba(0, 0, 0, 0.07);
                border: 1px solid #f1f1f1;
                padding: 18px 10px;
                text-align: center;
                transition: all 0.2s ease-in-out;
                height: 90px;
            }
            .bignumber-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 12px rgba(0, 0, 0, 0.1);
            }

            /* Título da métrica */
            .metric-title {
                color: #3c3c3c;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 6px;
            }

            /* Valor da métrica */
            .metric-value {
                color: #3c3c3c;
                font-size: 18px;
                font-weight: 700;
                margin-top: 4px;
            }

            /* Linha separadora sutil entre seções */
            hr {
                margin-top: 1rem;
                margin-bottom: 1rem;
                border: none;
                border-top: 1px solid #eee;
            }
        </style>
        """, unsafe_allow_html=True)

    # ======================
    # MÉTRICAS SUPERIORES
    # ======================

    col1, col2, col3, col4, col5 = st.columns(5)
    metrics = [
        ("Receita Bruta", receita_bruta),
        ("Receita Líquida", receita_liquida),
        ("Lucro Bruto", lucro_bruito),
        ("Lucro Líquido", lucro_liquido),
        ("Disponibilidade de Caixa", disponibilidade_caixa),
    ]

    for col, (titulo, valor) in zip([col1, col2, col3, col4, col5], metrics):
        col.markdown(f"""
        <div class="bignumber-card" style="padding:10px; background-color:#f8f8f8; border-radius:8px; text-align:center;">
            <div class="metric-title" style="font-weight:bold; color:#333;">{titulo}</div>
            <div class="metric-value" style="font-size:20px; color:#595959;">R$ {valor:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    





    # ======================
    # GRÁFICOS DE INDICADORES TEMPORAIS
    # ======================

    # Converter índice para coluna e ordenar
    df_plot = indicadores_historicos.reset_index().sort_values("mes")
    df_plot["mes"] = df_plot["mes"].astype(str)
    df_plot, anos_escolhidos = filtro_ano(df_plot)

    df_plot["Banco"] = df_plot["Disponibilidade_Caixa"] * 0.5
    df_plot["Investimento"] = df_plot["Disponibilidade_Caixa"] * 0.3
    df_plot["Caixa"] = df_plot["Disponibilidade_Caixa"] * 0.2

    # Função para criar gráfico de barras por indicador

    col1, col2 = st.columns(2)

    # 1️⃣ Receita Líquida / Receita Bruta
    with col1:
        fig_receita = px.bar(
            df_plot,
            x="mes",
            y=["Receita_Bruta", "Receita_Líquida"],
            barmode="group",
            title="RECEITA LÍQUIDA / RECEITA BRUTA",
            labels={"value": "Valor", "variable": "Indicador", "mes": "Mês"},
            color_discrete_sequence=["#595959", "#B0B0B0"]
        )
        fig_receita.update_layout(
            title_x=0.3,
            plot_bgcolor="#fff",
            legend=dict(
                orientation="h",         # horizontal
                yanchor="top",
                y=-0.2,                  # move para baixo do gráfico
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig_receita, use_container_width=True)

    # 2️⃣ Disponibilidade de Caixa
    with col2:
        df_caixa_melt = df_plot.melt(
            id_vars=["mes"],
            value_vars=["Banco", "Investimento", "Caixa"],
            var_name="Composição",
            value_name="Valor"
        )
        fig_caixa = px.bar(
            df_caixa_melt,
            x="mes",
            y="Valor",
            color="Composição",
            barmode="stack",
            title="DISPONIBILIDADE DE CAIXA",
            labels={"mes": "Mês", "Valor": "Valor", "Composição": "Composição"},
            color_discrete_sequence=["#F1F1F1", "#B0B0B0", "#595959"]
        )
        fig_caixa.update_layout(
            title_x=0.3,
            plot_bgcolor="#fff",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig_caixa, use_container_width=True)

    # Segunda linha de gráficos
    col3, col4 = st.columns(2)

    # 3️⃣ Custo / Receita Líquida
    with col3:
        fig_custo = px.line(
            df_plot,
            x="mes",
            y="Custo_Total",
            title="CUSTO / RECEITA LÍQUIDA",
            labels={"mes": "Mês", "Custo Total": "Valor"}
        )
        fig_custo.update_traces(line=dict(color="#0052CC", width=3), name="Custo Total")
        fig_custo.add_scatter(
            x=df_plot["mes"],
            y=df_plot["Receita_Líquida"],
            mode="lines",
            name="Receita Líquida",
            line=dict(color="#DAA520", width=3)
        )
        fig_custo.update_layout(
            title_x=0.3,
            plot_bgcolor="#fff",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig_custo, use_container_width=True)

    # 4️⃣ Receita Líquida (barra simples)
    with col4:
        fig_liquida = px.bar(
            df_plot,
            x="mes",
            y="Receita_Líquida",
            title="RECEITA LÍQUIDA",
            text_auto=".2s",
            color_discrete_sequence=["#595959"]
        )
        fig_liquida.update_layout(
            title_x=0.3,
            plot_bgcolor="#fff",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.25,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig_liquida, use_container_width=True)


    
with abas[3]:  # Aba "Analítico"
    st.subheader("Métricas do Balancete")
    indicadores_historicos