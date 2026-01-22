import streamlit as st
import pandas as pd
import io
import plotly.express as px
import numpy as np


# CONFIGURAÇÃO DA PÁGINA

st.set_page_config(
    page_title="Cargo Flow Pro",
    page_icon="recipiente (1).png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS CUSTOMIZADO (DESIGN SYSTEM)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* Reset e Definições Globais */
            
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    background: #1f2937;   /* COR DE FUNDO DO SITE */
    color: #e5e7eb;        /* COR DO TEXTO PRINCIPAL */
}

/* Seções e Cards */
.main-card {
    background: linear-gradient(145deg, rgba(55, 65, 81, 0.6), rgba(31, 41, 55, 0.3));
    border: 1px solid rgba(229, 231, 235, 0.1);
    border-radius: 24px;
    padding: 30px;
    margin-bottom: 25px;
    backdrop-filter: blur(12px);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

.sub-card {
    background: rgba(229, 231, 235, 0.05);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(229, 231, 235, 0.08);
}

/* Tipografia */
h1 {
    font-weight: 800;
    letter-spacing: -1.5px;
    background: linear-gradient(to right, #ffffff, #d1d5db);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

h3 {
    font-weight: 600;
    color: #d1d5db;
    margin-bottom: 20px;
}

/* Métricas Estilizadas */
.metric-box {
    background: linear-gradient(180deg, rgba(229, 231, 235, 0.08) 0%, rgba(229, 231, 235, 0) 100%);
    border: 1px solid rgba(229, 231, 235, 0.2);
    border-radius: 20px;
    padding: 25px;
    text-align: left;
    transition: transform 0.3s ease;
}

.metric-box:hover {
    transform: translateY(-5px);
    border-color: #2563eb;
}

.metric-label {
    font-size: 12px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.metric-value {
    font-size: 32px;
    font-weight: 800;
    color: #030507;
    margin-top: 5px;
}

/* Botões Modernos */
.stButton>button {
    background: #3b82f6;
    color: white;
    border-radius: 14px;
    height: 54px;
    font-weight: 700;
    font-size: 16px;
    border: none;
    box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3);
    width: 100%;
    transition: all 0.3s ease;
}

.stButton>button:hover {
    background: #2563eb;
    box-shadow: 0 15px 35px rgba(59, 130, 246, 0.5);
    transform: scale(1.02);
}

/* Sidebar Estilizada */
[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid rgba(229, 231, 235, 0.05);
}

.sidebar-logo {
    padding: 20px 0;
    text-align: center;
}

}
</style>
""", unsafe_allow_html=True)

# LÓGICA DE NEGÓCIO

CAP_TRUCK = 12
CARRETAS = [22, 26, 28]
MIN_APROVEITAMENTO = 1

def preview_situacao(df):
    rows = []
    for (cliente, bairro), g in df.groupby(["Cliente", "Bairro"]):
        total = g["Paletes"].sum()
        
        # Sugestão de melhor veículo baseado no volume atual
        sugestao = "Aguardar"
        if total >= 28 * MIN_APROVEITAMENTO: sugestao = "Carreta 28"
        elif total >= 26 * MIN_APROVEITAMENTO: sugestao = "Carreta 26"
        elif total >= 22 * MIN_APROVEITAMENTO: sugestao = "Carreta 22"
        elif total >= 12 * MIN_APROVEITAMENTO: sugestao = "Truck 12"

        rows.append({
            "Cliente": cliente,
            "Bairro": bairro,
            "Paletes Totais": round(total, 2),
            "Sugestão": sugestao,
            "Situação": "🟢 Possível Carga" if total >= CAP_TRUCK * MIN_APROVEITAMENTO else "🔴 Saldo"
        })
    return pd.DataFrame(rows)

def montar_cargas(df):
    linhas, resumo, saldos_detalhados = [], [], []
    carga_id = 1

    for (cliente, bairro), grupo in df.groupby(["Cliente", "Bairro"]):
        total = grupo["Paletes"].sum()
        tipo, capacidade = None, None

        # Lógica de seleção de veículo por capacidade
        for c in sorted(CARRETAS, reverse=True):
            if total >= c * MIN_APROVEITAMENTO:
                tipo, capacidade = f"Carreta {c}", c
                break

        if not tipo and total >= CAP_TRUCK * MIN_APROVEITAMENTO:
            tipo, capacidade = "Truck", CAP_TRUCK

        # Se não atingir o mínimo, vira saldo
        if not tipo:
            # Cálculo de gaps para todos os tipos de veículos
            faltante_truck = round(max(0, (CAP_TRUCK * MIN_APROVEITAMENTO) - total), 2)
            faltante_c22 = round(max(0, (22 * MIN_APROVEITAMENTO) - total), 2)
            faltante_c26 = round(max(0, (26 * MIN_APROVEITAMENTO) - total), 2)
            faltante_c28 = round(max(0, (28 * MIN_APROVEITAMENTO) - total), 2)
            
            saldos_detalhados.append({
                "Cliente": cliente,
                "Bairro": bairro,
                "Paletes Atuais": round(total, 2),
                "Falta p/ Truck (12)": faltante_truck,
                "Falta p/ C22": faltante_c22,
                "Falta p/ C26": faltante_c26,
                "Falta p/ C28": faltante_c28,
                "Status": "🔴 Aguardando Volume"
            })
            
            for _, r in grupo.iterrows():
                linhas.append({**r, "Carga": "", "Tipo Veiculo": "", "Status": "Saldo"})
            continue

        nome_carga = f"CARG-{cliente[:3].upper()}-{bairro[:2].upper()}-{carga_id:02d}"
        carga_id += 1
        restante = capacidade
        usados = 0

        for _, r in grupo.iterrows():
            pal = float(r["Paletes"])

            if restante <= 0:
                linhas.append({**r, "Carga": "", "Tipo Veiculo": "", "Status": "Saldo"})
                continue

            if pal <= restante:
                linhas.append({**r, "Carga": nome_carga, "Tipo Veiculo": tipo, "Status": "OK"})
                restante -= pal
                usados += pal
            else:
                linhas.append({**r, "Paletes": restante, "Carga": nome_carga, "Tipo Veiculo": tipo, "Status": "OK"})
                linhas.append({**r, "Paletes": round(pal - restante, 2), "Carga": "", "Tipo Veiculo": "", "Status": "Saldo"})
                usados += restante
                restante = 0

        resumo.append({
            "Manifesto": nome_carga,
            "Cliente": cliente,
            "Bairro": bairro,
            "Veículo": tipo,
            "Ocupação": round(usados, 2),
            "Capacidade": capacidade,
            "Aproveitamento (%)": int((usados / capacidade) * 100),
            "Situação": "🟢 Carga Montada"
        })

    return pd.DataFrame(linhas), pd.DataFrame(resumo), pd.DataFrame(saldos_detalhados)

# PAINEL PRINCIPAL

with st.sidebar:
    st.markdown('<div class="sidebar-logo"><h1>Montagem de Cargas</h1></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.info("💡 Carregue o arquivo para visualizar as sugestões de Carretas (22/26/28) e Truck (12).")

st.markdown("""
<div style="text-align: center; margin-bottom: 40px;">
    <h1 style="font-size: 50px;">🚚 Cargo Flow Pro</h1>
    <p style="color: #94a3af; font-size: 18px;">Montagem de Cargas Inteligentes</p>
</div>
""", unsafe_allow_html=True)

# Início do Fluxo
if 'df_base' not in st.session_state:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.markdown("### 📥 Importação de Pedidos")
    arquivo = st.file_uploader("📂 Upload do Excel de Pedidos", type=["xlsx"])
    
    if arquivo:
        st.session_state.df_base = pd.read_excel(arquivo)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    df = st.session_state.df_base
    
    st.markdown('<div class="main-card"><h3>📄 Pedidos em Carteira</h3>', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    if st.button("📂 Trocar Arquivo"):
        del st.session_state.df_base
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Diagnóstico Visual (Antes de montar)
    prev = preview_situacao(df)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="main-card"><h3>📦 Possíveis Cargas</h3>', unsafe_allow_html=True)
        st.dataframe(prev[prev["Situação"].str.contains("Possível")], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="main-card"><h3>⚠️ Saldos Identificados</h3>', unsafe_allow_html=True)
        st.dataframe(prev[prev["Situação"].str.contains("Saldo")], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. Execução
    if st.button("Montar Cargas"):
        pedidos, resumo, saldos = montar_cargas(df)

        # Métricas
        total_truck = resumo[resumo["Veículo"] == "Truck"].shape[0]
        total_carreta = resumo[resumo["Veículo"].str.contains("Carreta")].shape[0]
        total_veiculos = total_truck + total_carreta

        st.markdown("### 📊 Indicadores da Operação")
        m1, m2, m3, m4 = st.columns(4)
        
        m1.markdown(f'<div class="metric-box"><div class="metric-label">Total de Carros</div><div class="metric-value">{total_veiculos}</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-box"><div class="metric-label">Total Trucks</div><div class="metric-value">{total_truck}</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-box"><div class="metric-label">Total Carretas</div><div class="metric-value">{total_carreta}</div></div>', unsafe_allow_html=True)
        
        aprov_medio = int(resumo["Aproveitamento (%)"].mean()) if not resumo.empty else 0
        m4.markdown(f'<div class="metric-box"><div class="metric-label">Ocupação Média</div><div class="metric-value">{aprov_medio}%</div></div>', unsafe_allow_html=True)

        # Detalhes (Abas Atualizadas)
        
        tab1, tab2, tab3 = st.tabs(["📋 Itens Alocados", "📦 Cargas Montadas", "⚠️ Oportunidades (Saldos)"])
        with tab1:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.dataframe(pedidos, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with tab2:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.dataframe(resumo, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with tab3:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            if not saldos.empty:
                st.markdown("#### Inteligência de Saldos")
                st.info("Veja quanto falta para atingir 100% de ocupação em cada tipo de veículo:")
                st.dataframe(saldos, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Eficiência máxima: Todos os pedidos alocados em veículos!")
            st.markdown('</div>', unsafe_allow_html=True)

        # Exportação
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pedidos.to_excel(writer, sheet_name="Cargas_Detalhadas", index=False)
            resumo.to_excel(writer, sheet_name="Resumo_Frota", index=False)
            saldos.to_excel(writer, sheet_name="Saldos_Oportunidade", index=False)
        
        st.download_button(
            label="Fazer Download",
            data=output.getvalue(),
            file_name="CargoFlow_Frota.xlsx",
            mime="application/vnd.ms-excel"
        )
