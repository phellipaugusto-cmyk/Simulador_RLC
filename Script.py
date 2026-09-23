import cmath
from datetime import datetime
import io
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import streamlit as st
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Análise Sincronizada",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Desenho e Cálculo Totalmente Sincronizados")
st.caption(
    "Edite os componentes e os nós de conexão na tabela abaixo. O circuito é desenhado e calculado automaticamente "
    "em tempo real com base nas conexões informadas."
)

# --- INICIALIZAÇÃO DA NETLIST (CIRCUITO DA SUA IMAGEM: 5 COMPONENTES EM PARALELO) ---
if "netlist_df" not in st.session_state:
    st.session_state.netlist_df = pd.DataFrame(
        [
            {"ID": 1, "Tipo": "Fonte CA", "Nó A": 0, "Nó B": 1, "Valor": 127.0, "Unidade": "V"},
            {"ID": 2, "Tipo": "Resistor", "Nó A": 1, "Nó B": 0, "Valor": 100.0, "Unidade": "Ω"},
            {"ID": 3, "Tipo": "Resistor", "Nó A": 1, "Nó B": 0, "Valor": 100.0, "Unidade": "Ω"},
            {"ID": 4, "Tipo": "Indutor", "Nó A": 1, "Nó B": 0, "Valor": 312.0, "Unidade": "mH"},
            {"ID": 5, "Tipo": "Capacitor", "Nó A": 1, "Nó B": 0, "Valor": 30.0, "Unidade": "µF"},
        ]
    )

# --- BARRA LATERAL: CONFIGURAÇÃO DE FREQUÊNCIA ---
st.sidebar.header("⚙️ Parâmetros Globais")
freq = st.sidebar.number_input("Frequência f (Hz)", value=60.0, min_value=0.1, step=1.0)
omega = 2 * np.pi * freq

# --- EDITOR DE CIRCUITO SINCRONIZADO ---
st.subheader("✏️ Editor de Componentes e Nós do Circuito")
st.caption("Altere os nós, tipos e valores diretamente na tabela. Você pode adicionar ou excluir linhas à vontade.")

edited_df = st.data_editor(
    st.session_state.netlist_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Tipo": st.column_config.SelectboxColumn(
            "Tipo de Elemento",
            options=["Fonte CA", "Resistor", "Indutor", "Capacitor", "Fio (Wire)"],
            required=True,
        ),
        "Nó A": st.column_config.NumberColumn("Nó Origem (A)", min_value=0, max_value=50, step=1),
        "Nó B": st.column_config.NumberColumn("Nó Destino (B)", min_value=0, max_value=50, step=1),
        "Valor": st.column_config.NumberColumn("Valor do Componente", min_value=0.0, step=1.0),
        "Unidade": st.column_config.TextColumn("Unidade", disabled=True),
    },
    key="editor_circuito",
)

# Atualiza session_state
st.session_state.netlist_df = edited_df

# Converte dataframe para lista de dicionários
netlist = edited_df.to_dict(orient="records")

if not netlist:
    st.warning("Adicione ao menos um componente na tabela acima para iniciar a simulação.")
    st.stop()


# --- FUNÇÃO DE DESENHO DO ESQUEMÁTICO DO CIRCUITO (VIA MATPLOTLIB / NETWORKX) ---
def renderizar_esquematico(netlist_data):
    G = nx.MultiGraph()
    for item in netlist_data:
        label = f"{item['Tipo'][0]}:{item['Valor']}{item['Unidade']}" if item["Tipo"] != "Fio (Wire)" else "Fio"
        G.add_edge(item["Nó A"], item["Nó B"], key=item["ID"], label=label, tipo=item["Tipo"])

    fig, ax = plt.subplots(figsize=(8, 3))
    pos = nx.spring_layout(G, seed=42)

    # Desenha nós
    nx.draw_networkx_nodes(G, pos, node_color="#007bff", node_size=600, ax=ax)
    nx.draw_networkx_labels(G, pos, font_color="white", font_weight="bold", font_size=9, ax=ax)

    # Desenha ramos/conexões
    nx.draw_networkx_edges(G, pos, width=2, edge_color="#222222", ax=ax)
    edge_labels = {(u, v): d["label"] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, ax=ax)

    ax.axis("off")
    plt.title("Esquema Elétrico Gerado dos Nós Conectados", fontsize=11, fontweight="bold")
    return fig


st.markdown("---")
st.subheader("🖥️ Circuito Esquemático Renderizado")
st.pyplot(renderizar_esquematico(netlist))


# --- MOTOR DE CÁLCULO NODAL (MNA / ANÁLISE DE GRAFOS) ---
def analisar_circuito(netlist_data, w):
    G = nx.MultiGraph()
    for item in netlist_data:
        G.add_edge(item["Nó A"], item["Nó B"], key=item["ID"], data=item)

    fontes = [i for i in netlist_data if i["Tipo"] == "Fonte CA"]
    if not fontes:
        return "Sem Fonte", complex(0, 0), 0.0, "Adicione uma fonte CA."

    fonte = fontes[0]
    n_src1, n_src2 = fonte["Nó A"], fonte["Nó B"]
    V_rms = fonte["Valor"]

    G_sem_fonte = G.copy()
    for u, v, k, d in list(G_sem_fonte.edges(keys=True, data=True)):
        if d["data"]["Tipo"] == "Fonte CA":
            G_sem_fonte.remove_edge(u, v, key=k)

    if not nx.has_path(G_sem_fonte, n_src1, n_src2):
        return "Circuito Aberto", complex(1e9, 0), V_rms, "Não há caminho fechado ligando os nós da fonte."

    def calc_z_elem(elem, frequency_w):
        t, v = elem["Tipo"], elem["Valor"]
        if t == "Resistor":
            return complex(v, 0)
        elif t == "Indutor":
            return complex(0, frequency_w * (v / 1000.0))
        elif t == "Capacitor":
            return complex(0, -1 / (frequency_w * (v / 1e6)))
        return complex(1e-6, 0)

    nos_unicos = sorted(list(G.nodes()))
    node_map = {node: i for i, node in enumerate(nos_unicos)}
    N = len(nos_unicos)

    ref_node = node_map[n_src2]
    src_node = node_map[n_src1]

    Y = np.zeros((N, N), dtype=complex)
    for item in netlist_data:
        if item["Tipo"] == "Fonte CA":
            continue
        z_item = calc_z_elem(item, w)
        y_item = 1.0 / z_item
        u, v = node_map[item["Nó A"]], node_map[item["Nó B"]]
        Y[u, u] += y_item
        Y[v, v] += y_item
        Y[u, v] -= y_item
        Y[v, u] -= y_item

    nos_ativos = [i for i in range(N) if i != ref_node]
    Y_red = Y[np.ix_(nos_ativos, nos_ativos)]

    I_vec = np.zeros(len(nos_ativos), dtype=complex)
    idx_src_red = nos_ativos.index(src_node)
    I_vec[idx_src_red] = 1.0

    try:
        V_potenciais = np.linalg.solve(Y_red, I_vec)
        Z_eq = V_potenciais[idx_src_red]
    except np.linalg.LinAlgError:
        Z_eq = complex(1e-6, 0)

    return "Circuito Conectado", Z_eq, V_rms, "Sucesso"


status_top, Z_eq, V_rms, msg = analisar_circuito(netlist, omega)

# --- RESULTADOS DAS GRANDEZAS ELÉTRICAS ---
abs_Z = abs(Z_eq)
angle_Z_rad = cmath.phase(Z_eq)
angle_Z_deg = np.degrees(angle_Z_rad)

I_rms = V_rms / abs_Z if abs_Z > 0 else 0.0
angle_I_deg = -angle_Z_deg

S = V_rms * I_rms
P = S * np.cos(angle_Z_rad)
Q = S * np.sin(angle_Z_rad)
FP = np.cos(angle_Z_rad)
carater = "Indutivo" if Q > 0.01 else "Capacitivo" if Q < -0.01 else "Resistivo Puro"

st.markdown("---")
st.subheader("⚙️ Configurações e Análise do Circuito Desenhado")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância Equivalent |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total RMS |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência (FP)", f"{FP:.4f}")

r1, r2 = st.columns(2)
with r1:
    st.write(f"**Ângulo da Impedância ($\theta_Z$):** {angle_Z_deg:.2f}°")
    st.write(f"**Potência Reativa (Q):** {Q:.2f} VAR")
with r2:
    st.write(f"**Potência Aparente (S):** {S:.2f} VA")
    st.write(f"**Comportamento Predominante:** {carater}")

# --- DIAGRAMAS FASORIAIS E TRIÂNGULO DE POTÊNCIA ---
st.markdown("---")
st.subheader("📐 Diagrama Fasorial e Triângulo de Potências")
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Diagrama Fasorial (V e I)**")
    fig_fasor, ax_f = plt.subplots(figsize=(4, 4))
    escala_I = (V_rms / I_rms) * 0.4 if I_rms > 0 else 1.0

    ax_f.quiver(
        0, 0, V_rms, 0,
        angles="xy", scale_units="xy", scale=1,
        color="red", label=f"V = {V_rms:.1f}V ∠0°"
    )
    u_I = (I_rms * escala_I) * np.cos(np.radians(angle_I_deg))
    v_I = (I_rms * escala_I) * np.sin(np.radians(angle_I_deg))
    ax_f.quiver(
        0, 0, u_I, v_I,
        angles="xy", scale_units="xy", scale=1,
        color="cyan", label=f"I = {I_rms:.2f}A ∠{angle_I_deg:.1f}°"
    )

    lim = max(V_rms, abs(I_rms * escala_I)) * 1.2
    ax_f.set_xlim(-lim, lim)
    ax_f.set_ylim(-lim, lim)
    ax_f.set_aspect("equal")
    ax_f.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax_f.axvline(0, color="gray", linestyle="--", linewidth=0.8)
    ax_f.grid(True, linestyle=":", alpha=0.6)
    ax_f.legend(loc="upper right", fontsize=8)
    st.pyplot(fig_fasor)

with g2:
    st.markdown("**Triângulo de Potências (P, Q, S)**")
    fig_pot, ax_p = plt.subplots(figsize=(4, 4))

    ax_p.quiver(
        0, 0, P, 0,
        angles="xy", scale_units="xy", scale=1,
        color="green", label=f"P = {P:.1f} W"
    )
    ax_p.quiver(
        P, 0, 0, Q,
        angles="xy", scale_units="xy", scale=1,
        color="orange", label=f"Q = {Q:.1f} VAR"
    )
    ax_p.quiver(
        0, 0, P, Q,
        angles="xy", scale_units="xy", scale=1,
        color="purple", label=f"S = {S:.1f} VA"
    )

    max_v = max(abs(P), abs(Q), abs(S)) * 1.2
    ax_p.set_xlim(-10, max_v if max_v > 0 else 10)
    ax_p.set_ylim(-max_v if Q < 0 else -10, max_v if Q >= 0 else 10)
    ax_p.grid(True, linestyle=":", alpha=0.6)
    ax_p.legend(loc="upper left", fontsize=8)
    st.pyplot(fig_pot)


# --- GERADOR DE RELATÓRIO PDF ---
def gerar_pdf(netlist_data, v_f, f_f, z_c, i_val, p_val, q_val, s_val, fp_val, car):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Relatorio Tecnico do Circuito RLC", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fonte CA: {v_f:.2f} V @ {f_f:.2f} Hz", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Componentes do Circuito:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for item in netlist_data:
        unid = "Ohm" if item["Unidade"] == "Ω" else item["Unidade"]
        pdf.cell(
            0,
            5,
            f"  Slot #{item['ID']}: {item['Tipo']} (No {item['Nó A']} -> No {item['Nó B']}) = {item['Valor']:.2f} {unid}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Resultados Calculados:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, f"  Impedancia Equivalente (|Z_eq|): {abs(z_c):.2f} Ohm", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Corrente Total RMS (|I_rms|): {i_val:.2f} A", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Potencia Ativa (P): {p_val:.2f} W", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Potencia Reativa (Q): {q_val:.2f} VAR", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Potencia Aparente (S): {s_val:.2f} VA", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Fator de Potencia (FP): {fp_val:.4f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Comportamento Predominante: {car}", new_x="LMARGIN", new_y="NEXT")

    out = pdf.output()
    return bytes(out) if isinstance(out, (bytes, bytearray)) else str(out).encode("latin-1")


st.markdown("---")
pdf_bytes = gerar_pdf(netlist, V_rms, freq, Z_eq, I_rms, P, Q, S, FP, carater)

st.download_button(
    label="📥 Baixar Relatório Técnico em PDF (.pdf)",
    data=pdf_bytes,
    file_name=f"relatorio_circuito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
