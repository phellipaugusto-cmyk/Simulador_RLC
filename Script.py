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
    page_title="Simulador RLC - Canvas Interativo",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC com Canvas Interativo Bidirecional")
st.caption(
    "Desenhe as conexões na grade abaixo com o mouse. O aplicativo lê os objetos desenhados "
    "e envia as coordenadas diretamente para o backend em Python para realizar a análise elétrica em tempo real."
)

# --- BARRA LATERAL: FERRAMENTAS E PARÂMETROS ---
st.sidebar.header("⚙️ Parâmetros do Circuito")
freq = st.sidebar.number_input("Frequência f (Hz)", value=60.0, min_value=0.1, step=1.0)
omega = 2 * np.pi * freq

V_fonte_val = st.sidebar.number_input("Tensão da Fonte CA (V_rms)", value=127.0, min_value=0.1)

st.sidebar.markdown("---")
st.sidebar.header("✏️ Modos de Desenho")
drawing_mode = st.sidebar.selectbox("Ferramenta de Desenho", ["line", "transform"])
stroke_color = st.sidebar.color_picker("Cor da Conexão", "#007bff")

# --- CANVAS INTERATIVO ---
st.subheader("🖥️ Quadro de Desenho do Circuito")
st.caption("Clique e arraste para conectar os nós da grade. Utilize a barra de ferramentas para alterar os parâmetros.")

canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",
    stroke_width=3,
    stroke_color=stroke_color,
    background_color="#ffffff",
    height=400,
    width=800,
    drawing_mode=drawing_mode,
    key="canvas_rlc",
)

# --- CONVERSÃO DOS OBJETOS DO CANVAS PARA COMPONENTES ELÉTRICOS ---
netlist_processada = []

if canvas_result.json_data is not None:
    objects = canvas_result.json_data["objects"]
    grid_size = 30  # Tamanho do grid para arredondar nós

    for idx, obj in enumerate(objects):
        if obj["type"] == "line":
            x1 = round(obj["x1"] / grid_size) * grid_size
            y1 = round(obj["y1"] / grid_size) * grid_size
            x2 = round(obj["x2"] / grid_size) * grid_size
            y2 = round(obj["y2"] / grid_size) * grid_size

            no_a = f"N_{int(x1//grid_size)}_{int(y1//grid_size)}"
            no_b = f"N_{int(x2//grid_size)}_{int(y2//grid_size)}"

            # Atribuição dos tipos com base na ordem de criação ou lista
            netlist_processada.append({
                "id": idx + 1,
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "no_a": no_a, "no_b": no_b,
            })

# --- CONFIGURAÇÃO MANUAL DE VALORES DOS COMPONENTES DESENHADOS ---
st.markdown("---")
st.subheader("⚙️ Configurações dos Ramos Desenhados no Canvas")

if not netlist_processada:
    st.info("💡 Desenhe linhas no quadro acima para conectar a fonte e os componentes.")
    st.stop()

netlist_final = []
cols = st.columns(min(len(netlist_processada), 4))

for idx, item in enumerate(netlist_processada):
    col_t = cols[idx % len(cols)]
    with col_t:
        st.markdown(f"**Conexão #{item['id']}** ({item['no_a']} ➔ {item['no_b']})")
        tipo = st.selectbox(
            f"Tipo #{item['id']}",
            ["Fio (Wire)", "Resistor (R)", "Indutor (L)", "Capacitor (C)", "Fonte CA (V)"],
            key=f"tipo_{idx}"
        )

        val = 0.0
        unid = ""
        if tipo == "Resistor (R)":
            val = st.number_input(f"Resistência (Ω)", value=100.0, key=f"v_{idx}")
            unid = "Ω"
        elif tipo == "Indutor (L)":
            val = st.number_input(f"Indutância (mH)", value=312.0, key=f"v_{idx}")
            unid = "mH"
        elif tipo == "Capacitor (C)":
            val = st.number_input(f"Capacitância (µF)", value=30.01, key=f"v_{idx}")
            unid = "µF"
        elif tipo == "Fonte CA (V)":
            val = V_fonte_val
            unid = "V"

        netlist_final.append({
            "id": item["id"],
            "tipo": tipo,
            "no_a": item["no_a"],
            "no_b": item["no_b"],
            "valor": val,
            "unid": unid
        })

# --- MOTOR DE CÁLCULO E ANÁLISE NODAL (MNA / GRAFOS) ---
def analisar_circuito(netlist, w):
    G = nx.MultiGraph()
    for item in netlist:
        G.add_edge(item["no_a"], item["no_b"], key=item["id"], data=item)

    fontes = [i for i in netlist if "Fonte CA" in i["tipo"]]
    if not fontes:
        return "Sem Fonte", complex(0, 0), V_fonte_val, "Adicione uma fonte CA."

    fonte = fontes[0]
    n_src1, n_src2 = fonte["no_a"], fonte["no_b"]
    V_rms = fonte["valor"]

    G_sem_fonte = G.copy()
    for u, v, k, d in list(G_sem_fonte.edges(keys=True, data=True)):
        if "Fonte CA" in d["data"]["tipo"]:
            G_sem_fonte.remove_edge(u, v, key=k)

    if not nx.has_path(G_sem_fonte, n_src1, n_src2):
        return "Circuito Aberto", complex(1e9, 0), V_rms, "Caminho aberto."

    def calc_z(elem, frequency_w):
        t, v = elem["tipo"], elem["valor"]
        if "Resistor" in t:
            return complex(v, 0)
        elif "Indutor" in t:
            return complex(0, frequency_w * (v / 1000.0))
        elif "Capacitor" in t:
            return complex(0, -1 / (frequency_w * (v / 1e6)))
        return complex(1e-6, 0)

    nos_unicos = sorted(list(G.nodes()))
    node_map = {node: i for i, node in enumerate(nos_unicos)}
    N = len(nos_unicos)

    ref_node = node_map[n_src2]
    src_node = node_map[n_src1]

    Y = np.zeros((N, N), dtype=complex)
    for item in netlist:
        if "Fonte CA" in item["tipo"]:
            continue
        z_item = calc_z(item, w)
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

    return "Circuito Calculado", Z_eq, V_rms, "Sucesso"


topologia_detectada, Z_eq, V_rms, status = analisar_circuito(netlist_final, omega)

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

st.markdown("---")
st.subheader("📊 Resultados Calculados do Circuito Desenhado")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I_rms|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência", f"{FP:.4f}")

# --- DIAGRAMA FASORIAL ---
st.markdown("---")
st.subheader("📐 Diagrama Fasorial e Triângulo de Potências")
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Diagrama Fasorial (V e I)**")
    fig_fasor, ax_f = plt.subplots(figsize=(4, 4))
    escala_I = (V_rms / I_rms) * 0.4 if I_rms > 0 else 1.0

    ax_f.quiver(0, 0, V_rms, 0, angles="xy", scale_units="xy", scale=1, color="red", label=f"V = {V_rms:.1f}V ∠0°")
    u_I = (I_rms * escala_I) * np.cos(np.radians(angle_I_deg))
    v_I = (I_rms * escala_I) * np.sin(np.radians(angle_I_deg))
    ax_f.quiver(0, 0, u_I, v_I, angles="xy", scale_units="xy", scale=1, color="cyan", label=f"I = {I_rms:.2f}A ∠{angle_I_deg:.1f}°")

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

    ax_p.quiver(0, 0, P, 0, angles="xy", scale_units="xy", scale=1, color="green", label=f"P = {P:.1f} W")
    ax_p.quiver(P, 0, 0, Q, angles="xy", scale_units="xy", scale=1, color="orange", label=f"Q = {Q:.1f} VAR")
    ax_p.quiver(0, 0, P, Q, angles="xy", scale_units="xy", scale=1, color="purple", label=f"S = {S:.1f} VA")

    max_v = max(abs(P), abs(Q), abs(S)) * 1.2
    ax_p.set_xlim(-10, max_v if max_v > 0 else 10)
    ax_p.set_ylim(-max_v if Q < 0 else -10, max_v if Q >= 0 else 10)
    ax_p.grid(True, linestyle=":", alpha=0.6)
    ax_p.legend(loc="upper left", fontsize=8)
    st.pyplot(fig_pot)

# --- RELATÓRIO PDF ---
def gerar_pdf(netlist, v_f, f_f, z_c, i_val, p_val, q_val, s_val, fp_val, car):
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
    pdf.cell(0, 6, "Componentes Desenhados no Canvas:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for item in netlist:
        unid = "Ohm" if item["unid"] == "Ω" else item["unid"]
        pdf.cell(0, 5, f"  Conexao #{item['id']}: {item['tipo']} ({item['no_a']} -> {item['no_b']}) = {item['valor']:.2f} {unid}", new_x="LMARGIN", new_y="NEXT")

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
pdf_bytes = gerar_pdf(netlist_final, V_rms, freq, Z_eq, I_rms, P, Q, S, FP, carater)

st.download_button(
    label="📥 Baixar Relatório Técnico em PDF (.pdf)",
    data=pdf_bytes,
    file_name=f"relatorio_circuito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
