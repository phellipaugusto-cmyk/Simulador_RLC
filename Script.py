import cmath
from datetime import datetime
import io
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Quadro de Desenho Interativo",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Desenho no Quadro e Cálculo Automático")
st.caption(
    "Selecione o componente no menu lateral, clique e arraste o mouse no quadro para desenhar as conexões. "
    "O Python lê os traços da tela em tempo real para realizar a análise nodal e os cálculos elétricos."
)

# --- MAPA DE FERRAMENTAS E CORES ---
FERRAMENTAS = {
    "✏️ Fio (Conexão)": {"cor": "#28a745", "tipo": "Fio (Wire)", "val_def": 0.0, "unid": ""},
    "⚡ Resistor (R)": {"cor": "#007bff", "tipo": "Resistor", "val_def": 100.0, "unid": "Ω"},
    "🌀 Indutor (L)": {"cor": "#6f42c1", "tipo": "Indutor", "val_def": 312.0, "unid": "mH"},
    "🔋 Capacitor (C)": {"cor": "#fd7e14", "tipo": "Capacitor", "val_def": 30.01, "unid": "µF"},
    "🔴 Fonte CA (V)": {"cor": "#dc3545", "tipo": "Fonte CA", "val_def": 127.0, "unid": "V"},
}

# --- BARRA LATERAL: SELEÇÃO DE FERRAMENTAS E PARÂMETROS ---
st.sidebar.header("🎨 Ferramentas de Desenho")
ferramenta_sel = st.sidebar.radio("Escolha o Componente para Desenhar:", list(FERRAMENTAS.keys()))
info_tool = FERRAMENTAS[ferramenta_sel]

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Parâmetros Globais")
freq = st.sidebar.number_input("Frequência f (Hz)", value=60.0, min_value=0.1, step=1.0)
omega = 2 * np.pi * freq

# --- QUADRO DE DESENHO INTERATIVO (CANVAS) ---
st.subheader("🖥️ Quadro Interativo de Desenho")
st.caption(
    f"Ferramenta Ativa: **{ferramenta_sel}** (Cor da linha: `{info_tool['cor']}`). "
    "Conecte os pontos da grade para formar o circuito."
)

canvas_result = st_canvas(
    fill_color="rgba(0, 0, 0, 0)",
    stroke_width=3,
    stroke_color=info_tool["cor"],
    background_color="#f8f9fa",
    height=400,
    width=800,
    drawing_mode="line",
    key="quadro_rlc",
)

# --- RECONHECIMENTO AUTOMÁTICO DOS COMPONENTES DESENHADOS ---
netlist = []
grid_size = 30  # Tamanho do grid em pixels para atração dos nós

if canvas_result.json_data is not None:
    objects = canvas_result.json_data.get("objects", [])

    for idx, obj in enumerate(objects):
        if obj.get("type") == "line":
            x1 = round(obj["x1"] / grid_size) * grid_size
            y1 = round(obj["y1"] / grid_size) * grid_size
            x2 = round(obj["x2"] / grid_size) * grid_size
            y2 = round(obj["y2"] / grid_size) * grid_size

            # Identificação dos nós por coordenadas snapped na grade
            no_a = f"N_{int(x1//grid_size)}_{int(y1//grid_size)}"
            no_b = f"N_{int(x2//grid_size)}_{int(y2//grid_size)}"

            # Corresponde a cor da linha ao tipo do componente
            cor_linha = obj.get("stroke")
            tipo_detectado = "Fio (Wire)"
            val_def = 0.0
            unid_def = ""

            for key, val in FERRAMENTAS.items():
                if val["cor"].lower() == str(cor_linha).lower():
                    tipo_detectado = val["tipo"]
                    val_def = val["val_def"]
                    unid_def = val["unid"]
                    break

            netlist.append({
                "id": idx + 1,
                "tipo": tipo_detectado,
                "no_a": no_a,
                "no_b": no_b,
                "valor": val_def,
                "unid": unid_def,
            })

st.markdown("---")
st.subheader("⚙️ Configurações e Análise do Circuito Desenhado")

if not netlist:
    st.info("💡 Desenhe o circuito no quadro acima (incluindo uma Fonte CA, componentes e Fios) para realizar os cálculos.")
    st.stop()

# --- AJUSTE DE VALORES DOS COMPONENTES DESENHADOS ---
st.markdown("**Componentes Detectados no Quadro:**")
cols = st.columns(min(len(netlist), 4))

for idx, item in enumerate(netlist):
    col_target = cols[idx % len(cols)]
    with col_target:
        st.markdown(f"**Slot #{item['id']}: {item['tipo']}**")
        st.caption(f"Conectado entre `{item['no_a']}` e `{item['no_b']}`")
        if item["tipo"] != "Fio (Wire)":
            item["valor"] = st.number_input(
                f"Valor ({item['unid']})",
                value=float(item["valor"]),
                min_value=0.01 if item["tipo"] != "Fonte CA" else 0.1,
                key=f"val_canvas_{idx}"
            )


# --- MOTOR DE CÁLCULO NODAL (MNA / ANÁLISE DE GRAFOS) ---
def analisar_circuito_desenhado(netlist_data, w):
    G = nx.MultiGraph()
    for item in netlist_data:
        G.add_edge(item["no_a"], item["no_b"], key=item["id"], data=item)

    fontes = [i for i in netlist_data if i["tipo"] == "Fonte CA"]
    if not fontes:
        return "Sem Fonte", complex(0, 0), 127.0, "Adicione uma fonte CA."

    fonte = fontes[0]
    n_src1, n_src2 = fonte["no_a"], fonte["no_b"]
    V_rms = fonte["valor"]

    G_sem_fonte = G.copy()
    for u, v, k, d in list(G_sem_fonte.edges(keys=True, data=True)):
        if d["data"]["tipo"] == "Fonte CA":
            G_sem_fonte.remove_edge(u, v, key=k)

    if not nx.has_path(G_sem_fonte, n_src1, n_src2):
        return "Circuito Aberto", complex(1e9, 0), V_rms, "Não há caminho fechado ligando a fonte."

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
    for item in netlist_data:
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

    return "Circuito Conectado", Z_eq, V_rms, "Sucesso"


status_top, Z_eq, V_rms, msg = analisar_circuito_desenhado(netlist, omega)

# --- RESULTADOS DAS GRANDEZA ELÉTRICAS ---
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

m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total RMS |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência (FP)", f"{FP:.4f}")

# --- DIAGRAMA FASORIAL E TRIÂNGULO DE POTÊNCIA ---
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
    pdf.cell(0, 6, "Componentes Desenhados no Quadro:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for item in netlist_data:
        unid = "Ohm" if item["unid"] == "Ω" else item["unid"]
        pdf.cell(
            0,
            5,
            f"  Slot #{item['id']}: {item['tipo']} ({item['no_a']} -> {item['no_b']}) = {item['valor']:.2f} {unid}",
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
