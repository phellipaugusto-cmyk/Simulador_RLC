import cmath
from datetime import datetime
import io
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Desenho no Quadro e Símbolos Normais",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Desenho no Quadro e Análise Automática")
st.caption(
    "Selecione a ferramenta no menu lateral, clique e arraste no quadro ligando os pontos cinzas (nós) de cada componente. "
    "O aplicativo identifica os traços, desenha o esquema com símbolos elétricos normais e calcula os resultados em tempo real."
)

# --- CONFIGURAÇÕES DA GRADE E CANVAS ---
GRID_SIZE = 50  # Distância em pixels entre os nós da grade
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 400


def gerar_imagem_grade(width, height, grid_step):
    """Gera o fundo do quadro com pontos cinzas destacados em cada nó da grade."""
    img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    for x in range(grid_step, width, grid_step):
        for y in range(grid_step, height, grid_step):
            draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(100, 100, 100, 255))
    return img


bg_grid = gerar_imagem_grade(CANVAS_WIDTH, CANVAS_HEIGHT, GRID_SIZE)

# --- PALETA DE FERRAMENTAS DE DESENHO ---
FERRAMENTAS = {
    "🔴 Fonte CA (V)": {"cor": "#dc3545", "tipo": "Fonte CA", "val_def": 127.0, "unid": "V"},
    "⚡ Resistor (R)": {"cor": "#007bff", "tipo": "Resistor", "val_def": 100.0, "unid": "Ω"},
    "🌀 Indutor (L)": {"cor": "#6f42c1", "tipo": "Indutor", "val_def": 312.0, "unid": "mH"},
    "🔋 Capacitor (C)": {"cor": "#fd7e14", "tipo": "Capacitor", "val_def": 30.01, "unid": "µF"},
    "✏️ Fio (Conexão)": {"cor": "#28a745", "tipo": "Fio (Wire)", "val_def": 0.0, "unid": ""},
}

# --- BARRA LATERAL: FERRAMENTAS E FREQUÊNCIA ---
st.sidebar.header("🎨 Ferramentas de Desenho")
ferramenta_sel = st.sidebar.radio("Selecione o Componente:", list(FERRAMENTAS.keys()))
tool_info = FERRAMENTAS[ferramenta_sel]

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Parâmetros Globais")
freq = st.sidebar.number_input("Frequência f (Hz)", value=60.0, min_value=0.1, step=1.0)
omega = 2 * np.pi * freq

# --- QUADRO INTERATIVO DE DESENHO ---
st.subheader("🖥️ Quadro de Desenho (Ligue os Pontos da Grade)")
st.caption(
    f"Ferramenta ativa: **{ferramenta_sel}** | "
    "Clique em um ponto cinza e arraste até outro ponto para criar a conexão do componente."
)

canvas_result = st_canvas(
    fill_color="rgba(0,0,0,0)",
    stroke_width=4,
    stroke_color=tool_info["cor"],
    background_image=bg_grid,
    height=CANVAS_HEIGHT,
    width=CANVAS_WIDTH,
    drawing_mode="line",
    key="canvas_rlc_interactive",
)

# --- MAPEAMENTO DOS DESENHOS PARA NÓS E COMPONENTES ---
netlist = []

if canvas_result.json_data is not None:
    objects = canvas_result.json_data.get("objects", [])

    for idx, obj in enumerate(objects):
        if obj.get("type") == "line":
            # Snapping magnético aos pontos da grade
            x1_snap = round(obj["x1"] / GRID_SIZE) * GRID_SIZE
            y1_snap = round(obj["y1"] / GRID_SIZE) * GRID_SIZE
            x2_snap = round(obj["x2"] / GRID_SIZE) * GRID_SIZE
            y2_snap = round(obj["y2"] / GRID_SIZE) * GRID_SIZE

            # Ignora pontos isolados ou sem comprimento
            if x1_snap == x2_snap and y1_snap == y2_snap:
                continue

            no_a = f"N({int(x1_snap // GRID_SIZE)},{int(y1_snap // GRID_SIZE)})"
            no_b = f"N({int(x2_snap // GRID_SIZE)},{int(y2_snap // GRID_SIZE)})"

            stroke_color = str(obj.get("stroke")).lower()
            tipo_componente = "Fio (Wire)"
            val_def = 0.0
            unid_def = ""

            for key, info in FERRAMENTAS.items():
                if info["cor"].lower() == stroke_color:
                    tipo_componente = info["tipo"]
                    val_def = info["val_def"]
                    unid_def = info["unid"]
                    break

            netlist.append({
                "id": idx + 1,
                "tipo": tipo_componente,
                "no_a": no_a,
                "no_b": no_b,
                "valor": val_def,
                "unid": unid_def,
                "p1": (x1_snap, y1_snap),
                "p2": (x2_snap, y2_snap),
            })

st.markdown("---")
st.subheader("⚙️ Configurações e Componentes Detectados no Quadro")

if not netlist:
    st.info("💡 Desenhe as conexões no quadro acima unindo os pontos cinzas com a Fonte CA, componentes e Fios.")
    st.stop()

# --- FORMULÁRIO DE VALORES DOS COMPONENTES ---
st.markdown("**Valores dos Componentes Desenhados:**")
cols = st.columns(min(len(netlist), 4))

for idx, item in enumerate(netlist):
    col_t = cols[idx % len(cols)]
    with col_t:
        st.markdown(f"**Slot #{item['id']}: {item['tipo']}**")
        st.caption(f"De `{item['no_a']}` a `{item['no_b']}`")
        if item["tipo"] != "Fio (Wire)":
            item["valor"] = st.number_input(
                f"Valor ({item['unid']})",
                value=float(item["valor"]),
                min_value=0.01 if item["tipo"] != "Fonte CA" else 0.1,
                key=f"val_canvas_slot_{idx}",
            )

# --- RENDERIZAÇÃO DO ESQUEMA ELÉTRICO COM SÍMBOLOS NORMAIS ---
def desenhar_simbolo_norma(ax, p1, p2, tipo, rotulo):
    """Desenha os símbolos gráficos elétricos padronizados (R, L, C, Fonte CA)."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    dist = np.hypot(dx, dy)
    if dist == 0:
        return

    angle = np.arctan2(dy, dx)
    cos_a, sin_a = np.cos(angle), np.sin(angle)

    def to_glob(lx, ly):
        return (x1 + lx * cos_a - ly * sin_a, y1 + lx * sin_a + ly * cos_a)

    ax.plot([x1, x2], [y1, y2], color="black", lw=1.5, zorder=1)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

    if tipo == "Resistor":
        w_res, h_res = min(0.35 * dist, 0.4), 0.12
        cx_l = (dist - w_res) / 2
        pts = [
            (0, 0), (cx_l, 0),
            (cx_l + w_res * 0.125, h_res),
            (cx_l + w_res * 0.375, -h_res),
            (cx_l + w_res * 0.625, h_res),
            (cx_l + w_res * 0.875, -h_res),
            (cx_l + w_res, 0), (dist, 0)
        ]
        gx, gy = zip(*[to_glob(lx, ly) for lx, ly in pts])
        ax.plot(gx, gy, color="black", lw=2, zorder=3)

    elif tipo == "Capacitor":
        gap, h_cap, c_mid = 0.08, 0.2, dist / 2
        p1_a, p1_b = to_glob(c_mid - gap, h_cap), to_glob(c_mid - gap, -h_cap)
        p2_a, p2_b = to_glob(c_mid + gap, h_cap), to_glob(c_mid + gap, -h_cap)
        ax.plot([p1_a[0], p1_b[0]], [p1_a[1], p1_b[1]], color="black", lw=2.5, zorder=3)
        ax.plot([p2_a[0], p2_b[0]], [p2_a[1], p2_b[1]], color="black", lw=2.5, zorder=3)

    elif tipo == "Indutor":
        w_ind = min(0.4 * dist, 0.5)
        c_start, n_loops = (dist - w_ind) / 2, 4
        r_loop = w_ind / (2 * n_loops)
        t = np.linspace(0, np.pi, 30)
        for i in range(n_loops):
            x_off = c_start + i * (2 * r_loop) + r_loop
            lx, ly = x_off - r_loop * np.cos(t), r_loop * np.sin(t)
            gx, gy = zip(*[to_glob(x, y) for x, y in zip(lx, ly)])
            ax.plot(gx, gy, color="black", lw=2, zorder=3)

    elif tipo == "Fonte CA":
        r_src = 0.18
        circle = patches.Circle((cx, cy), r_src, facecolor="white", edgecolor="black", lw=2, zorder=3)
        ax.add_patch(circle)
        t_s = np.linspace(-np.pi, np.pi, 25)
        lx_s = (t_s / np.pi) * (r_src * 0.6) + (dist / 2)
        ly_s = np.sin(t_s) * (r_src * 0.4)
        gx_s, gy_s = zip(*[to_glob(x, y) for x, y in zip(lx_s, ly_s)])
        ax.plot(gx_s, gy_s, color="black", lw=1.8, zorder=4)

    if tipo != "Fio (Wire)":
        lbl_x, lbl_y = to_glob(dist / 2, 0.25)
        ax.text(
            lbl_x, lbl_y, rotulo,
            fontsize=9, fontweight="bold", ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="gray", alpha=0.9),
            zorder=5,
        )


def renderizar_esquematico(netlist_data):
    G = nx.MultiGraph()
    for item in netlist_data:
        G.add_edge(item["no_a"], item["no_b"], key=item["id"], data=item)

    fig, ax = plt.subplots(figsize=(8, 4))
    pos = nx.spring_layout(G, seed=42, k=1.2)

    for node, (nx_x, ny_y) in pos.items():
        ax.scatter(nx_x, ny_y, s=350, color="#007bff", zorder=6, edgecolors="black")
        ax.text(nx_x, ny_y, str(node), color="white", fontweight="bold", ha="center", va="center", fontsize=8, zorder=7)

    for u, v, k, d in G.edges(keys=True, data=True):
        elem = d["data"]
        unid = elem.get("unid", "")
        rotulo = f"{elem['tipo']}\n{elem['valor']}{unid}" if elem["tipo"] != "Fio (Wire)" else "Fio"
        desenhar_simbolo_norma(ax, pos[u], pos[v], elem["tipo"], rotulo)

    ax.axis("off")
    plt.title("Esquema Elétrico com Símbolos Normais (Calculado do Quadro)", fontsize=11, fontweight="bold")
    return fig


st.markdown("---")
st.subheader("🖥️ Esquema Elétrico Renderizado com Símbolos Padrão")
st.pyplot(renderizar_esquematico(netlist))

# --- CÁLCULO ELÉTRICO E ANÁLISE NODAL (MNA) ---
def analisar_circuito(netlist_data, w):
    G = nx.MultiGraph()
    for item in netlist_data:
        G.add_edge(item["no_a"], item["no_b"], key=item["id"], data=item)

    fontes = [i for i in netlist_data if i["tipo"] == "Fonte CA"]
    if not fontes:
        return "Sem Fonte", complex(0, 0), 0.0, "Adicione uma fonte CA no quadro."

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

    return "Sucesso", Z_eq, V_rms, "Calculado"


status, Z_eq, V_rms, msg = analisar_circuito(netlist, omega)

if status != "Sucesso":
    st.warning(f"⚠️ {msg}")
    st.stop()

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
st.subheader("📊 Resultados Numéricos Calculados")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I_rms|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência (FP)", f"{FP:.4f}")

r1, r2 = st.columns(2)
with r1:
    st.write(f"**Ângulo da Impedância ($\theta_Z$):** {angle_Z_deg:.2f}°")
    st.write(f"**Potência Reativa (Q):** {Q:.2f} VAR")
with r2:
    st.write(f"**Potência Aparente (S):** {S:.2f} VA")
    st.write(f"**Comportamento Predominante:** {carater}")

# --- DIAGRAMAS FASORIAIS ---
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
    ax_f.quiver(0, 0, u_I, v_I, angles="xy", scale_units="xy", scale=1, color="blue", label=f"I = {I_rms:.2f}A ∠{angle_I_deg:.1f}°")

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
        unid = "Ohm" if item.get("unid") == "Ω" else item.get("unid", "")
        pdf.cell(0, 5, f"  Slot #{item['id']}: {item['tipo']} ({item['no_a']} -> {item['no_b']}) = {item['valor']:.2f} {unid}", new_x="LMARGIN", new_y="NEXT")

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
