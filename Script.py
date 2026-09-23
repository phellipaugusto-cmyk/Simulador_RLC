import cmath
from datetime import datetime
import io
import os
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Canvas Bidirecional",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC com Canvas Interativo Bidirecional")
st.caption(
    "Desenhe o circuito com o mouse na grade. A cada conexão feita, os dados do Canvas são enviados em tempo real "
    "para o backend em Python, que reconhece os nós, a topologia e calcula todas as grandezas elétricas."
)

# --- CRIAÇÃO DINÂMICA DO COMPONENTE HTML5/JS BIDIRECIONAL ---
COMPONENT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "frontend_component"
)
os.makedirs(COMPONENT_DIR, exist_ok=True)

html_frontend_code = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/streamlit-component-lib@1.4.0/dist/streamlit-component-lib.js"></script>
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

function sendDataToStreamlit() {
  Streamlit.setComponentValue(elements);
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

    sendDataToStreamlit();
  }
  draw();
});

function clearCanvas() {
  elements = [];
  draw();
  sendDataToStreamlit();
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

function onRender(event) {
  Streamlit.setFrameHeight(500);
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.init();
drawGrid();
</script>
</body>
</html>
"""

with open(
    os.path.join(COMPONENT_DIR, "index.html"), "w", encoding="utf-8"
) as f:
    f.write(html_frontend_code)

circuit_canvas = components.declare_component(
    "circuit_canvas", path=COMPONENT_DIR
)

# --- EXECUÇÃO DO CANVAS BIDIRECIONAL ---
canvas_elements = circuit_canvas(key="rlc_canvas", default=[])

# --- BARRA LATERAL: PARÂMETROS DA FONTE ---
st.sidebar.header("⚙️ ParâmetrosGlobais da Simulação")
freq = st.sidebar.number_input(
    "Frequência da Fonte (Hz)", value=60.0, min_value=0.1, step=1.0
)
omega = 2 * np.pi * freq


# --- PARSER DE COORDENADAS DO CANVAS PARA NÓS DO CIRCUITO ---
def coords_to_node(x, y, grid_size=30):
    return f"N_{int(x // grid_size)}_{int(y // grid_size)}"


netlist_processada = []
if canvas_elements:
    for item in canvas_elements:
        no_a = coords_to_node(item["x1"], item["y1"])
        no_b = coords_to_node(item["x2"], item["y2"])
        netlist_processada.append(
            {
                "id": item["id"],
                "tipo": item["type"],
                "no_a": no_a,
                "no_b": no_b,
                "valor": float(item["val"]),
                "unid": item["unid"],
            }
        )

st.markdown("---")
st.subheader("⚙️ Configurações e Análise do Circuito Desenhado")

if not netlist_processada:
    st.info(
        "💡 Desenhe um circuito fechado no quadro acima (incluindo uma Fonte V, componentes e Fios) para iniciar os cálculos."
    )
    st.stop()


# --- MOTOR DE RECONHECIMENTO DE TOPOLOGIA E ANÁLISE NODAL (MNA) ---
def analisar_circuito_desenhado(netlist, w):
    G = nx.MultiGraph()
    for item in netlist:
        G.add_edge(item["no_a"], item["no_b"], key=item["id"], data=item)

    fontes = [i for i in netlist if i["tipo"] == "V"]
    if not fontes:
        return (
            "Sem Fonte",
            complex(0, 0),
            0.0,
            "Adicione uma Fonte CA (V) ao circuito.",
        )

    fonte = fontes[0]
    n_src1, n_src2 = fonte["no_a"], fonte["no_b"]
    V_rms = fonte["valor"]

    G_sem_fonte = G.copy()
    for u, v, k, d in list(G_sem_fonte.edges(keys=True, data=True)):
        if d["data"]["tipo"] == "V":
            G_sem_fonte.remove_edge(u, v, key=k)

    if not nx.has_path(G_sem_fonte, n_src1, n_src2):
        return (
            "Circuito Aberto",
            complex(1e9, 0),
            V_rms,
            "Conecte os fios para fechar o loop com a fonte.",
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

    def calc_z_elem(elem, frequency_w):
        t, v = elem["tipo"], elem["valor"]
        if t == "R":
            return complex(v, 0)
        elif t == "L":
            return complex(0, frequency_w * (v / 1000.0))
        elif t == "C":
            return complex(0, -1 / (frequency_w * (v / 1e6)))
        return complex(1e-6, 0)

    nos_unicos = sorted(list(G.nodes()))
    node_map = {node: i for i, node in enumerate(nos_unicos)}
    N = len(nos_unicos)

    ref_node = node_map[n_src2]
    src_node = node_map[n_src1]

    Y = np.zeros((N, N), dtype=complex)
    for item in netlist:
        if item["tipo"] == "V":
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


topologia_detectada, Z_eq, V_rms, status = analisar_circuito_desenhado(
    netlist_processada, omega
)

# --- GRANDEZA ELÉTRICAS CALCULADAS A PARTIR DO CANVASES ---
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

st.caption(f"Topologia Detectada Automaticamente: **{topologia_detectada}**")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total RMS |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência (FP)", f"{FP:.4f}")

# --- DIAGRAMAS FASORIAIS E POTÊNCIA ---
st.markdown("---")
st.subheader("📐 Diagramas Fasoriais e Triângulo de Potências")
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
    pdf.cell(
        0, 6, "Componentes Desenhados na Grade:", new_x="LMARGIN", new_y="NEXT"
    )
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
    netlist_processada,
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
