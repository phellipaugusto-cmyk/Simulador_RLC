import cmath
from datetime import datetime
import io
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Construtor Gráfico Interativo",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Desenho Interativo no Canvas")
st.caption(
    "Desenhe o circuito diretamente na tela: selecione uma ferramenta na barra superior do quadro, "
    "clique e arraste sobre os pontos da grade para conectar componentes e fios."
)

# --- CANVAS INTERATIVO EM HTML5/JAVASCRIPT ---
html_canvas_code = """
<!DOCTYPE html>
<html>
<head>
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

components.html(html_canvas_code, height=520)

# --- PAINEL DE PARÂMETROS E CÁLCULO ELETRÔNICO ---
st.markdown("---")
st.subheader("⚙️ Configurações e Análise do Circuito Desenhado")

col_a, col_b = st.columns(2)
with col_a:
    V_rms = st.number_input("Tensão da Fonte (V_rms)", value=127.0, step=1.0, min_value=0.1)
    freq = st.number_input("Frequência (Hz)", value=60.0, step=1.0, min_value=0.1)
    omega = 2 * np.pi * freq

with col_b:
    R_val = st.number_input("Resistência Equivalente (Ω)", value=100.0, step=1.0, min_value=0.1)
    L_val = st.number_input("Indutância Equivalente (mH)", value=312.0, step=1.0, min_value=0.1)
    C_val = st.number_input("Capacitância Equivalente (µF)", value=30.01, step=1.0, min_value=0.01)

# Cálculo da Impedância e Grandezas RLC
XL = omega * (L_val / 1000.0)
XC = 1.0 / (omega * (C_val / 1e6))
X_net = XL - XC
Z_complex = complex(R_val, X_net)

abs_Z = abs(Z_complex)
phase_Z_rad = cmath.phase(Z_complex)
phase_Z_deg = np.degrees(phase_Z_rad)

I_rms = V_rms / abs_Z if abs_Z > 0 else 0.0
phase_I_deg = -phase_Z_deg

S = V_rms * I_rms
P = S * np.cos(phase_Z_rad)
Q = S * np.sin(phase_Z_rad)
FP = np.cos(phase_Z_rad)
carater = "Indutivo" if Q > 0.01 else "Capacitivo" if Q < -0.01 else "Resistivo Puro"

st.subheader("📊 Grandezas Elétricas Resultantes")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência", f"{FP:.4f}")

# --- DIAGRAMAS FASORIAIS E POTÊNCIA ---
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
    u_I = (I_rms * escala_I) * np.cos(np.radians(phase_I_deg))
    v_I = (I_rms * escala_I) * np.sin(np.radians(phase_I_deg))
    ax_f.quiver(
        0, 0, u_I, v_I,
        angles="xy", scale_units="xy", scale=1,
        color="cyan", label=f"I = {I_rms:.2f}A ∠{phase_I_deg:.1f}°"
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

# --- GERADOR DE RELATÓRIO PDF COMPATÍVEL ---
def gerar_pdf(v, f, z, i, p, q, s, fp, car):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Relatorio Tecnico do Circuito RLC", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Fonte CA: {v:.2f} V @ {f:.2f} Hz", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Resultados Calculados:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, f"  Impedancia Equivalente (|Z|): {abs(z):.2f} Ohm", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Corrente Total RMS (|I|): {i:.2f} A", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Potencia Ativa (P): {p:.2f} W", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Potencia Reativa (Q): {q:.2f} VAR", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Potencia Aparente (S): {s:.2f} VA", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Fator de Potencia (FP): {fp:.4f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  Comportamento: {car}", new_x="LMARGIN", new_y="NEXT")

    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return str(out).encode("latin-1")

st.markdown("---")
pdf_bytes = gerar_pdf(V_rms, freq, Z_complex, I_rms, P, Q, S, FP, carater)
st.download_button(
    label="📥 Baixar Relatório PDF Completo",
    data=pdf_bytes,
    file_name=f"relatorio_circuito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
