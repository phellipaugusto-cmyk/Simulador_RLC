from datetime import datetime
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC - Desenho Gráfico no Canvas",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Desenho Interativo na Grade")
st.caption(
    "Desenhe o circuito diretamente na tela: selecione uma ferramenta abaixo, clique e arraste entre os pontos da grade para conectar fios e componentes."
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
  #results { margin: 15px; padding: 15px; background: #fff; border: 1px solid #ddd; border-radius: 5px; }
</style>
</head>
<body>

<div id="toolbar">
  <button class="btn active" onclick="setTool('wire')">✏️ Fio (Conexão)</button>
  <button class="btn" onclick="setTool('R')">⚡ Resistor (R)</button>
  <button class="btn" onclick="setTool('L')">🌀 Indutor (L)</button>
  <button class="btn" onclick="setTool('C')">🔋 Capacitor (C)</button>
  <button class="btn" onclick="setTool('V')">🔴 Fonte CA (V)</button>
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

function setTool(tool) {
  currentTool = tool;
  document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
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
  // Linha temporária ao arrastar
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

  elements.forEach((el, idx) => {
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#222';
    ctx.fillStyle = '#222';

    if (el.type === 'wire') {
      ctx.strokeStyle = '#28a745';
      ctx.beginPath();
      ctx.moveTo(el.x1, el.y1);
      ctx.lineTo(el.x2, el.y2);
      ctx.stroke();
    } else {
      // Linhas de conexão
      const midX = (el.x1 + el.x2) / 2;
      const midY = (el.y1 + el.y2) / 2;

      ctx.beginPath();
      ctx.moveTo(el.x1, el.y1);
      ctx.lineTo(el.x2, el.y2);
      ctx.stroke();

      // Caixa do componente
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#000080';
      ctx.fillRect(midX - 25, midY - 15, 50, 30);
      ctx.strokeRect(midX - 25, midY - 15, 50, 30);

      ctx.fillStyle = '#000';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${el.type}:${el.val}${el.unid}`, midX, midY + 4);
    }

    // Terminal/Nó
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
st.subheader("⚙️ Configurações e Análise da Rede Desenhada")

col_a, col_b = st.columns(2)
with col_a:
    V_rms = st.number_input("Tensão da Fonte (V_rms)", value=127.0, step=1.0)
    freq = st.number_input("Frequência (Hz)", value=60.0, step=1.0)
    omega = 2 * np.pi * freq

with col_b:
    R_val = st.number_input("Resistência Equivalente do Esquema (Ω)", value=100.0, step=1.0)
    L_val = st.number_input("Indutância Equivalente do Esquema (mH)", value=312.0, step=1.0)
    C_val = st.number_input("Capacitância Equivalente do Esquema (µF)", value=30.01, step=1.0)

# Cálculo de Impedância RLC
XL = omega * (L_val / 1000.0)
XC = 1.0 / (omega * (C_val / 1e6))
X_net = XL - XC
Z_complex = complex(R_val, X_net)

abs_Z = abs(Z_complex)
phase_Z_rad = np.angle(Z_complex)
phase_Z_deg = np.degrees(phase_Z_rad)

I_rms = V_rms / abs_Z if abs_Z > 0 else 0.0
S = V_rms * I_rms
P = S * np.cos(phase_Z_rad)
Q = S * np.sin(phase_Z_rad)
FP = np.cos(phase_Z_rad)

# Exibição dos resultados
st.subheader("📊 Grandezas Elétricas do Circuito")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência", f"{FP:.4f}")

# --- GERADOR DE RELATÓRIO PDF ---
def gerar_pdf(v, f, z, i, p, q, s, fp):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Relatorio Tecnico do Circuito RLC", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Data de Emissao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True)
    pdf.cell(0, 6, f"Fonte CA: {v:.2f} V @ {f:.2f} Hz", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "Resultados Calculados:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, f"  Impedancia Equivalente (|Z|): {abs(z):.2f} Ohm", ln=True)
    pdf.cell(0, 5, f"  Corrente Total RMS (|I|): {i:.2f} A", ln=True)
    pdf.cell(0, 5, f"  Potencia Ativa (P): {p:.2f} W", ln=True)
    pdf.cell(0, 5, f"  Potencia Reativa (Q): {q:.2f} VAR", ln=True)
    pdf.cell(0, 5, f"  Potencia Aparente (S): {s:.2f} VA", ln=True)
    pdf.cell(0, 5, f"  Fator de Potencia (FP): {fp:.4f}", ln=True)

    return bytes(pdf.output())

st.markdown("---")
pdf_bytes = gerar_pdf(V_rms, freq, Z_complex, I_rms, P, Q, S, FP)
st.download_button(
    label="📥 Baixar Relatório PDF Completo",
    data=pdf_bytes,
    file_name=f"relatorio_circuito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
