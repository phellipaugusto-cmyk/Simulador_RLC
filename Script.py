import cmath
from datetime import datetime
import io
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import streamlit as st
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Construtor & Analisador Dinâmico",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Desenho e Cálculo Automático de Circuitos")
st.caption(
    "Monte seu circuito conectando componentes e fios entre os nós da grade visual. "
    "Os cálculos de impedância, corrente e potências são realizados em tempo real considerando a topologia desenhada."
)

# --- INICIALIZAÇÃO DO CIRCUITO (NETLIST) ---
# Inicializa com o circuito exato mostrado na sua imagem (Fonte, Resistor, Indutor e Capacitor em paralelo)
if "netlist" not in st.session_state:
    st.session_state.netlist = [
        {"id": 1, "tipo": "Fonte CA", "no_a": 0, "no_b": 1, "valor": 127.0, "unid": "V"},
        {"id": 2, "tipo": "Resistor", "no_a": 1, "no_b": 2, "valor": 100.0, "unid": "Ω"},
        {"id": 3, "tipo": "Indutor", "no_a": 2, "no_b": 3, "valor": 312.0, "unid": "mH"},
        {"id": 4, "tipo": "Capacitor", "no_a": 2, "no_b": 3, "valor": 30.01, "unid": "µF"},
        {"id": 5, "tipo": "Fio (Wire)", "no_a": 3, "no_b": 0, "valor": 0.0, "unid": ""},
    ]

# --- BARRA LATERAL: CONFIGURAÇÕES E FERRAMENTAS DE DESENHO ---
st.sidebar.header("⚙️ Parâmetros da Fonte")
freq = st.sidebar.number_input("Frequência f (Hz)", value=60.0, min_value=0.1, step=1.0)
omega = 2 * np.pi * freq

st.sidebar.markdown("---")
st.sidebar.header("✏️ Ferramentas de Conexão na Grade")

with st.sidebar.form("add_element_form", clear_on_submit=True):
    tipo_input = st.selectbox(
        "Componente", ["Resistor", "Indutor", "Capacitor", "Fonte CA", "Fio (Wire)"]
    )
    no_a_input = st.number_input("Nó Inicial (A)", min_value=0, max_value=20, value=0, step=1)
    no_b_input = st.number_input("Nó Final (B)", min_value=0, max_value=20, value=1, step=1)

    if tipo_input == "Resistor":
        v_default, u_default = 100.0, "Ω"
    elif tipo_input == "Indutor":
        v_default, u_default = 312.0, "mH"
    elif tipo_input == "Capacitor":
        v_default, u_default = 30.01, "µF"
    elif tipo_input == "Fonte CA":
        v_default, u_default = 127.0, "V"
    else:
        v_default, u_default = 0.0, ""

    val_input = st.number_input(f"Valor ({u_default})", value=v_default, min_value=0.0, step=1.0)

    if st.form_submit_button("➕ Desenhar / Conectar Ramo"):
        if no_a_input == no_b_input:
            st.error("Os nós de conexão devem ser diferentes!")
        else:
            novo_id = max([e["id"] for e in st.session_state.netlist], default=0) + 1
            st.session_state.netlist.append(
                {
                    "id": novo_id,
                    "tipo": tipo_input,
                    "no_a": int(no_a_input),
                    "no_b": int(no_b_input),
                    "valor": float(val_input),
                    "unid": u_default,
                }
            )
            st.rerun()

if st.sidebar.button("🗑️ Limpar Todo o Desenho"):
    st.session_state.netlist = []
    st.rerun()

# --- CANVAS VISUAL E PAINEL DE EDIÇÃO ---
st.subheader("🖥️ Circuito Desenhado e Tabela de Conexões de Nós")

if not st.session_state.netlist:
    st.warning("O circuito está vazio. Adicione componentes ou fios usando o menu lateral.")
    st.stop()

# Edição dinâmica dos componentes desenhados
cols = st.columns(min(len(st.session_state.netlist), 4))
for idx, item in enumerate(st.session_state.netlist):
    col_target = cols[idx % len(cols)]
    with col_target:
        st.markdown(f"**Slot #{item['id']}: {item['tipo']}**")
        item["no_a"] = st.number_input(f"Nó A (#{item['id']})", value=int(item["no_a"]), min_value=0, key=f"na_{idx}")
        item["no_b"] = st.number_input(f"Nó B (#{item['id']})", value=int(item["no_b"]), min_value=0, key=f"nb_{idx}")

        if item["tipo"] != "Fio (Wire)":
            item["valor"] = st.number_input(
                f"Valor ({item['unid']})",
                value=float(item["valor"]),
                min_value=0.01 if item["tipo"] != "Fonte CA" else 0.1,
                key=f"val_{idx}",
            )

        if st.button(f"❌ Rem. #{item['id']}", key=f"del_{idx}"):
            st.session_state.netlist.pop(idx)
            st.rerun()

# --- MOTOR DE CÁLCULO E RECONHECIMENTO DE TOPOLOGIA (MNA / ANÁLISE NODAL) ---
def analisar_circuito(netlist, w):
    G = nx.MultiGraph()
    for item in netlist:
        G.add_edge(item["no_a"], item["no_b"], key=item["id"], data=item)

    fontes = [i for i in netlist if i["tipo"] == "Fonte CA"]
    if not fontes:
        return "Sem Fonte", complex(0, 0), 0.0, "Adicione uma fonte CA para realizar os cálculos."

    fonte = fontes[0]
    n_src1, n_src2 = fonte["no_a"], fonte["no_b"]
    V_rms = fonte["valor"]

    G_sem_fonte = G.copy()
    for u, v, k, d in list(G_sem_fonte.edges(keys=True, data=True)):
        if d["data"]["tipo"] == "Fonte CA":
            G_sem_fonte.remove_edge(u, v, key=k)

    if not nx.has_path(G_sem_fonte, n_src1, n_src2):
        return "Circuito Aberto", complex(1e9, 0), V_rms, "Não há um caminho fechado ligando os terminais da fonte."

    caminhos = list(nx.all_simple_paths(G_sem_fonte, source=n_src1, target=n_src2))
    graus_internos = [deg for node, deg in G_sem_fonte.degree() if node not in [n_src1, n_src2]]

    if len(caminhos) == 1 and all(d <= 2 for d in graus_internos):
        topologia = "Série Puro"
    elif len(caminhos) > 1 and all(len(p) == 2 for p in caminhos):
        topologia = "Paralelo Puro"
    else:
        topologia = "Misto (Série-Paralelo)"

    def calc_z_elem(elem, frequency_w):
        t, v = elem["tipo"], elem["valor"]
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
    for item in netlist:
        if item["tipo"] == "Fonte CA":
            continue
        z_item = calc_z_elem(item, w)
        y_item = 1.0 / z_item
        u, v = node_map[item["no_a"]], node_map[item["no_b"]]
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

    return topologia, Z_eq, V_rms, "Sucesso"


topologia_detectada, Z_eq, V_rms, status = analisar_circuito(st.session_state.netlist, omega)

# --- DESENHO GRÁFICO DO ESQUEMÁTICO ---
def desenhar_esquematico_grafo(netlist):
    G_vis = nx.Graph()
    for item in netlist:
        lbl = f"{item['tipo'][0]}:{item['valor']}{item['unid']}" if item["tipo"] != "Fio (Wire)" else "Fio"
        G_vis.add_edge(item["no_a"], item["no_b"], label=lbl)

    fig_g, ax_g = plt.subplots(figsize=(8, 3))
    pos = nx.spring_layout(G_vis, seed=42)

    nx.draw_networkx_nodes(G_vis, pos, node_color="gold", node_size=700, ax=ax_g)
    nx.draw_networkx_labels(G_vis, pos, font_size=10, font_weight="bold", font_color="black", ax=ax_g)

    edge_labels = {(u, v): d["label"] for u, v, d in G_vis.edges(data=True)}
    nx.draw_networkx_edges(G_vis, pos, width=2, edge_color="navy", ax=ax_g)
    nx.draw_networkx_edge_labels(G_vis, pos, edge_labels=edge_labels, font_size=8, ax=ax_g)

    ax_g.axis("off")
    return fig_g


st.markdown("---")
st.subheader("🔌 Renderização Gráfica do Esquema Desenhado")
st.caption(f"Topologia Detectada: **{topologia_detectada}**")
st.pyplot(desenhar_esquematico_grafo(st.session_state.netlist))

# --- GRANDEZA ELÉTRICAS CALCULADAS A PARTIR DO DESENHO ---
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

st.subheader("⚙️ Resultados Calculados do Circuito Desenhado")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
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

# --- DIAGRAMAS FASORIAIS E POTÊNCIA ---
st.markdown("---")
st.subheader("📐 Diagramas Fasoriais e Triângulo de Potências")
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
def gerar_pdf(netlist, topologia, v_f, f_f, z_c, i_val, p_val, q_val, s_val, fp_val, car):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Relatorio Tecnico do Circuito RLC", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Topologia Detectada: {topologia}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fonte CA: {v_f:.2f} V @ {f_f:.2f} Hz", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Componentes do Circuito Desenhado:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for item in netlist:
        unid = "Ohm" if item["unid"] == "Ω" else item["unid"]
        pdf.cell(
            0,
            5,
            f"  Slot #{item['id']}: {item['tipo']} (No {item['no_a']} -> No {item['no_b']}) = {item['valor']:.2f} {unid}",
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
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1")


st.markdown("---")
pdf_bytes = gerar_pdf(
    st.session_state.netlist,
    topologia_detectada,
    V_rms,
    freq,
    Z_eq,
    I_rms,
    P,
    Q,
    S,
    FP,
    carater,
)

st.download_button(
    label="📥 Baixar Relatório Técnico em PDF (.pdf)",
    data=pdf_bytes,
    file_name=f"relatorio_circuito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
