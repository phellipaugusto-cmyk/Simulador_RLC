import cmath
from datetime import datetime
import io
import json
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Canvas Interativo",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Desenho e Análise de Circuitos")
st.caption(
    "Desenhe seu circuito na grade abaixo: selecione a ferramenta, clique e arraste entre os pontos para conectar componentes e fios."
)

# --- CANVAS INTERATIVO HTML5 / JAVASCRIPT (RENDERIZADO DIRETO EM MEMÓRIA) ---
html_canvas_code = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }
  #toolbar { display: flex; gap: 8px; padding: 10px; background: #ffffff; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
  .btn { padding: 8px 14px; font-weight: bold; border: 1px solid #ccc; background: #fff; cursor: pointer; border-radius: 4px; }
  .btn.active { background: #007bff; color: white; border-color: #0056b3; }
  .btn-danger { background: #dc3545; color: white; border: none; }
  #canvas-container { text-align: center; margin: 10px auto; }
  canvas { background: #ffffff; border: 1px solid #ccc; box-shadow: 0 2px 5px rgba(0,0,0,0.1); cursor: crosshair; }
</style>
</head>
<body>

<div id="toolbar">
  <button class="btn active" onclick="setTool('wire', event)">✏️ Fio (Conexão)</button>
  <button class="btn" onclick="setTool('R', event)">⚡ Resistor (R)</button>
  <button class="btn" onclick="setTool('L', event)">🌀 Indutor (L)</button>
  <button class="btn" onclick="setTool('C', event)">🔋 Capacitor (C)</button>
  <button class="btn" onclick="setTool('V', event)">🔴 Fonte CA (V)</button>
  <button class="btn btn-danger" onclick="clearCanvas()">🗑️ Limpar Tela</button>
</div>

<div id="canvas-container">
  <canvas id="circuitCanvas" width="800" height="400"></canvas>
</div>

<script>
const canvas = document.getElementById('circuitCanvas');
const ctx = canvas.getContext('2d');
const gridSize = 30;

let currentTool = 'wire';
let elements = [];
let isDrawing = false;
let startX = 0, startY = 0;
let currentX = 0, currentY = 0;

function setTool(tool, evt) {
  currentTool = tool;
  document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
  evt.target.classList.add('active');
}

function snapToGrid(val) {
  return Math.round(val / gridSize) * gridSize;
}

canvas.addEventListener('mousedown', (e) => {
  const rect = canvas.getBoundingClientRect();
  startX = snapToGrid(e.clientX - rect.left);
  startY = snapToGrid(e.clientY - rect.top);
  isDrawing = true;
});

canvas.addEventListener('mousemove', (e) => {
  if (!isDrawing) return;
  const rect = canvas.getBoundingClientRect();
  currentX = snapToGrid(e.clientX - rect.left);
  currentY = snapToGrid(e.clientY - rect.top);
  draw();

  ctx.strokeStyle = '#007bff';
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(startX, startY);
  ctx.lineTo(currentX, currentY);
  ctx.stroke();
  ctx.setLineDash([]);
});

canvas.addEventListener('mouseup', (e) => {
  if (!isDrawing) return;
  isDrawing = false;
  const rect = canvas.getBoundingClientRect();
  currentX = snapToGrid(e.clientX - rect.left);
  currentY = snapToGrid(e.clientY - rect.top);

  if (startX !== currentX || startY !== currentY) {
    let val = 100;
    let unid = 'Ω';
    if (currentTool === 'L') { val = 312; unid = 'mH'; }
    if (currentTool === 'C') { val = 30; unid = 'µF'; }
    if (currentTool === 'V') { val = 127; unid = 'V'; }
    if (currentTool === 'wire') { val = 0; unid = ''; }

    elements.push({
      id: elements.length + 1,
      type: currentTool,
      x1: startX, y1: startY,
      x2: currentX, y2: currentY,
      val: val, unid: unid
    });
  }
  draw();
});

function clearCanvas() {
  elements = [];
  draw();
}

function drawGrid() {
  ctx.fillStyle = '#ccc';
  for (let x = 0; x < canvas.width; x += gridSize) {
    for (let y = 0; y < canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawGrid();

  elements.forEach((el) => {
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#222';

    if (el.type === 'wire') {
      ctx.strokeStyle = '#28a745';
      ctx.beginPath();
      ctx.moveTo(el.x1, el.y1);
      ctx.lineTo(el.x2, el.y2);
      ctx.stroke();
    } else {
      const midX = (el.x1 + el.x2) / 2;
      const midY = (el.y1 + el.y2) / 2;

      ctx.beginPath();
      ctx.moveTo(el.x1, el.y1);
      ctx.lineTo(el.x2, el.y2);
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#000080';
      ctx.fillRect(midX - 25, midY - 15, 50, 30);
      ctx.strokeRect(midX - 25, midY - 15, 50, 30);

      ctx.fillStyle = '#000';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${el.type}:${el.val}${el.unid}`, midX, midY + 4);
    }

    ctx.fillStyle = '#007bff';
    ctx.beginPath();
    ctx.arc(el.x1, el.y1, 4, 0, 2 * Math.PI);
    ctx.arc(el.x2, el.y2, 4, 0, 2 * Math.PI);
    ctx.fill();
  });
}

drawGrid();
</script>
</body>
</html>
"""

# Renderiza o Canvas garantindo altura de 510px na tela
components.html(html_canvas_code, height=510)

# --- INICIALIZAÇÃO E GERENCIAMENTO DOS COMPONENTES ---
if "netlist" not in st.session_state:
    st.session_state.netlist = [
        {
            "id": 1,
            "tipo": "Fonte CA",
            "no_a": 0,
            "no_b": 1,
            "valor": 127.0,
            "unid": "V",
        },
        {
            "id": 2,
            "tipo": "Resistor",
            "no_a": 1,
            "no_b": 2,
            "valor": 100.0,
            "unid": "Ω",
        },
        {
            "id": 3,
            "tipo": "Indutor",
            "no_a": 2,
            "no_b": 3,
            "valor": 312.0,
            "unid": "mH",
        },
        {
            "id": 4,
            "tipo": "Capacitor",
            "no_a": 2,
            "no_b": 3,
            "valor": 30.01,
            "unid": "µF",
        },
        {
            "id": 5,
            "tipo": "Fio (Wire)",
            "no_a": 3,
            "no_b": 0,
            "valor": 0.0,
            "unid": "",
        },
    ]

st.markdown("---")
st.subheader("⚙️ Configurações e Análise do Circuito Desenhado")

# --- BARRA LATERAL: PARÂMETROS ---
st.sidebar.header("⚙️ Parâmetros Globais")
freq = st.sidebar.number_input(
    "Frequência da Fonte (Hz)", value=60.0, min_value=0.1, step=1.0
)
omega = 2 * np.pi * freq

st.sidebar.markdown("---")
st.sidebar.header("➕ Adicionar/Ajustar Ramo")
with st.sidebar.form("add_elem_form", clear_on_submit=True):
    t_input = st.selectbox(
        "Componente",
        ["Resistor", "Indutor", "Capacitor", "Fonte CA", "Fio (Wire)"],
    )
    na_input = st.number_input(
        "Nó Origem (A)", min_value=0, max_value=20, value=0
    )
    nb_input = st.number_input(
        "Nó Destino (B)", min_value=0, max_value=20, value=1
    )

    u_def = (
        "Ω"
        if t_input == "Resistor"
        else (
            "mH"
            if t_input == "Indutor"
            else "µF" if t_input == "Capacitor" else "V"
        )
    )
    v_def = (
        100.0
        if t_input == "Resistor"
        else (
            312.0
            if t_input == "Indutor"
            else 30.01 if t_input == "Capacitor" else 127.0
        )
    )

    val_input = st.number_input(f"Valor ({u_def})", value=float(v_def))

    if st.form_submit_button("➕ Adicionar ao Circuito"):
        if na_input == nb_input:
            st.error("Os nós inicial e final devem ser diferentes.")
        else:
            nid = (
                max([e["id"] for e in st.session_state.netlist], default=0) + 1
            )
            st.session_state.netlist.append(
                {
                    "id": nid,
                    "tipo": t_input,
                    "no_a": int(na_input),
                    "no_b": int(nb_input),
                    "valor": float(val_input),
                    "unid": u_def,
                }
            )
            st.rerun()

if st.sidebar.button("🗑️ Limpar Todos os Componentes"):
    st.session_state.netlist = []
    st.rerun()

# --- TABELA DE COMPONENTES ---
cols = st.columns(min(len(st.session_state.netlist), 4))
for idx, item in enumerate(st.session_state.netlist):
    col_t = cols[idx % len(cols)]
    with col_t:
        st.markdown(f"**Slot #{item['id']}: {item['tipo']}**")
        item["no_a"] = st.number_input(
            f"Nó A (#{item['id']})",
            value=int(item["no_a"]),
            min_value=0,
            key=f"na_{idx}",
        )
        item["no_b"] = st.number_input(
            f"Nó B (#{item['id']})",
            value=int(item["no_b"]),
            min_value=0,
            key=f"nb_{idx}",
        )
        if item["tipo"] != "Fio (Wire)":
            item["valor"] = st.number_input(
                f"Valor ({item['unid']})",
                value=float(item["valor"]),
                min_value=0.01,
                key=f"v_{idx}",
            )
        if st.button(f"❌ Excluir #{item['id']}", key=f"d_{idx}"):
            st.session_state.netlist.pop(idx)
            st.rerun()


# --- MOTOR DE CÁLCULO E ANÁLISE NODAL (MNA / GRAFOS) ---
def analisar_topologia_e_impedancia(netlist, w):
    G = nx.MultiGraph()
    for item in netlist:
        G.add_edge(item["no_a"], item["no_b"], key=item["id"], data=item)

    fontes = [i for i in netlist if i["tipo"] in ["Fonte CA", "V"]]
    if not fontes:
        return (
            "Sem Fonte",
            complex(0, 0),
            127.0,
            "Adicione uma Fonte CA ao circuito.",
        )

    fonte = fontes[0]
    n_src1, n_src2 = fonte["no_a"], fonte["no_b"]
    V_rms = fonte["valor"]

    G_sem_fonte = G.copy()
    for u, v, k, d in list(G_sem_fonte.edges(keys=True, data=True)):
        if d["data"]["tipo"] in ["Fonte CA", "V"]:
            G_sem_fonte.remove_edge(u, v, key=k)

    if not nx.has_path(G_sem_fonte, n_src1, n_src2):
        return (
            "Circuito Aberto",
            complex(1e9, 0),
            V_rms,
            "Não há caminho fechado ligando os terminais da fonte.",
        )

    caminhos = list(
        nx.all_simple_paths(G_sem_fonte, source=n_src1, target=n_src2)
    )
    graus_internos = [
        deg for node, deg in G_sem_fonte.degree() if node not in [n_src1, n_src2]
    ]

    if len(caminhos) == 1 and all(d <= 2 for d in graus_internos):
        topologia = "Série Puro"
    elif len(caminhos) > 1 and all(len(p) == 2 for p in caminhos):
        topologia = "Paralelo Puro"
    else:
        topologia = "Misto (Série-Paralelo)"

    def calc_z(elem, frequency_w):
        t, v = elem["tipo"], elem["valor"]
        if t in ["Resistor", "R"]:
            return complex(v, 0)
        elif t in ["Indutor", "L"]:
            return complex(0, frequency_w * (v / 1000.0))
        elif t in ["Capacitor", "C"]:
            return complex(0, -1 / (frequency_w * (v / 1e6)))
        return complex(1e-6, 0)

    nos_unicos = sorted(list(G.nodes()))
    node_map = {node: i for i, node in enumerate(nos_unicos)}
    N = len(nos_unicos)

    ref_node = node_map[n_src2]
    src_node = node_map[n_src1]

    Y = np.zeros((N, N), dtype=complex)
    for item in netlist:
        if item["tipo"] in ["Fonte CA", "V"]:
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

    return topologia, Z_eq, V_rms, "Sucesso"


topologia_detectada, Z_eq, V_rms, status = analisar_topologia_e_impedancia(
    st.session_state.netlist, omega
)

# --- GRANDEZA ELÉTRICAS ---
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

st.caption(f"Topologia Detectada: **{topologia_detectada}**")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência", f"{FP:.4f}")

# --- DIAGRAMAS FASORIAIS E TRIÂNGULO DE POTÊNCIA ---
st.markdown("---")
st.subheader("📐 Diagrama Fasorial e Triângulo de Potências")
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Diagrama Fasorial (V e I)**")
    fig_fasor, ax_f = plt.subplots(figsize=(4, 4))
    escala_I = (V_rms / I_rms) * 0.4 if I_rms > 0 else 1.0

    ax_f.quiver(
        0,
        0,
        V_rms,
        0,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="red",
        label=f"V = {V_rms:.1f}V ∠0°",
    )
    u_I = (I_rms * escala_I) * np.cos(np.radians(angle_I_deg))
    v_I = (I_rms * escala_I) * np.sin(np.radians(angle_I_deg))
    ax_f.quiver(
        0,
        0,
        u_I,
        v_I,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="cyan",
        label=f"I = {I_rms:.2f}A ∠{angle_I_deg:.1f}°",
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
        0,
        0,
        P,
        0,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="green",
        label=f"P = {P:.1f} W",
    )
    ax_p.quiver(
        P,
        0,
        0,
        Q,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="orange",
        label=f"Q = {Q:.1f} VAR",
    )
    ax_p.quiver(
        0,
        0,
        P,
        Q,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="purple",
        label=f"S = {S:.1f} VA",
    )

    max_v = max(abs(P), abs(Q), abs(S)) * 1.2
    ax_p.set_xlim(-10, max_v if max_v > 0 else 10)
    ax_p.set_ylim(-max_v if Q < 0 else -10, max_v if Q >= 0 else 10)
    ax_p.grid(True, linestyle=":", alpha=0.6)
    ax_p.legend(loc="upper left", fontsize=8)
    st.pyplot(fig_pot)


# --- GERADOR DE RELATÓRIO PDF ---
def gerar_pdf(
    netlist, topologia, v_f, f_f, z_c, i_val, p_val, q_val, s_val, fp_val, car
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(
        0,
        10,
        "Relatorio Tecnico do Circuito RLC",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(
        0,
        6,
        f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0, 6, f"Topologia Detectada: {topologia}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.cell(
        0, 6, f"Fonte CA: {v_f:.2f} V @ {f_f:.2f} Hz", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Lista de Componentes:", new_x="LMARGIN", new_y="NEXT")
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
    pdf.cell(
        0,
        5,
        f"  Impedancia Equivalente (|Z_eq|): {abs(z_c):.2f} Ohm",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  Corrente Total RMS (|I_rms|): {i_val:.2f} A",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  Potencia Ativa (P): {p_val:.2f} W",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  Potencia Reativa (Q): {q_val:.2f} VAR",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  Potencia Aparente (S): {s_val:.2f} VA",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  Fator de Potencia (FP): {fp_val:.4f}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  Comportamento Predominante: {car}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

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
