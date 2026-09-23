import cmath
from datetime import datetime
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC & Editor Livre (Estilo Falstad)",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC Avançado com Editor Esquematizado Livre")
st.markdown(
    "Construa e posicione componentes livremente na bancada interativa abaixo (estilo **Falstad/Multisim**), "
    "analise formas de onda em tempo real e gere relatórios técnicos em **PDF**, **TXT** e **Markdown**."
)

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "componentes" not in st.session_state:
    st.session_state.componentes = [
        {"tipo": "Resistor", "valor": 100.0, "unidade": "Ω"},
        {"tipo": "Indutor", "valor": 312.0, "unidade": "mH"},
        {"tipo": "Capacitor", "valor": 30.01, "unidade": "µF"},
    ]

# --- BARRA LATERAL: FONTE, TOPOLOGIA E PARÂMETROS ---
st.sidebar.header("1. Fonte de Alimentação CA")
V_rms = st.sidebar.number_input(
    "Tensão Eficaz V_rms (V)", value=100.0, step=1.0, min_value=0.1
)
f = st.sidebar.number_input(
    "Frequência f (Hz)", value=60.0, step=1.0, min_value=0.1
)
w = 2 * np.pi * f

st.sidebar.header("2. Topologia para Análise Exata")
arranjo = st.sidebar.selectbox(
    "Arranjo dos Componentes Ativos",
    [
        "Série Puro",
        "Paralelo Puro",
        "Misto (Resistor em Série + Bloco Paralelo)",
    ],
)

st.sidebar.header("3. Inserir Elemento na Lista")
with st.sidebar.form("add_comp_form", clear_on_submit=True):
    tipo_comp = st.selectbox(
        "Tipo de Elemento", ["Resistor (R)", "Indutor (L)", "Capacitor (C)"]
    )
    val_comp = st.number_input("Valor", value=10.0, min_value=0.001)

    if tipo_comp.startswith("Resistor"):
        unid = "Ω"
    elif tipo_comp.startswith("Indutor"):
        unid = "mH"
    else:
        unid = "µF"

    submitted = st.form_submit_button("➕ Adicionar à Lista Ativa")
    if submitted:
        nome_tipo = tipo_comp.split(" ")[0]
        st.session_state.componentes.append(
            {"tipo": nome_tipo, "valor": float(val_comp), "unidade": unid}
        )
        st.rerun()

# --- MÓDULO 1: BANCADA DE DESENHO E ALOCAÇÃO LIVRE (ESTILO FALSTAD) ---
st.subheader("🛠️ Editor de Circuitos Esquematizado Livre (Canvas 2D)")
st.caption(
    "Selecione uma ferramenta abaixo e clique/arraste no grid para desenhar fios, conectar componentes e definir a trajetória do circuito."
)

falstad_canvas_html = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: sans-serif; background: #121212; color: #ffffff; margin: 0; padding: 10px; }
    #toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; background: #1e1e1e; padding: 10px; border-radius: 8px; }
    button { background: #2c3e50; color: white; border: 1px solid #455a64; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-weight: bold; }
    button.active { background: #27ae60; border-color: #2ecc71; }
    button:hover { background: #34495e; }
    #canvas-container { position: relative; width: 100%; overflow: hidden; border: 2px solid #333; border-radius: 8px; background-color: #0d1117; }
    canvas { display: block; cursor: crosshair; }
</style>
</head>
<body>

<div id="toolbar">
    <button id="btn-wire" class="active" onclick="setTool('wire')">✏️ Fio (Wire)</button>
    <button id="btn-res" onclick="setTool('res')">🟧 Resistor (R)</button>
    <button id="btn-ind" onclick="setTool('ind')">🟦 Indutor (L)</button>
    <button id="btn-cap" onclick="setTool('cap')">🟪 Capacitor (C)</button>
    <button id="btn-source" onclick="setTool('source')">🔴 Fonte CA</button>
    <button id="btn-gnd" onclick="setTool('gnd')">⏚ Terra (GND)</button>
    <button id="btn-clear" onclick="clearCanvas()" style="background:#c0392b;">🗑️ Limpar Tela</button>
</div>

<div id="canvas-container">
    <canvas id="circuitCanvas" width="900" height="320"></canvas>
</div>

<script>
    const canvas = document.getElementById('circuitCanvas');
    const ctx = canvas.getContext('2d');
    const gridSize = 20;
    
    let currentTool = 'wire';
    let elements = [];
    let isDrawing = false;
    let startX = 0, startY = 0;
    let currentX = 0, currentY = 0;

    function snap(val) {
        return Math.round(val / gridSize) * gridSize;
    }

    function setTool(tool) {
        currentTool = tool;
        document.querySelectorAll('#toolbar button').forEach(b => b.classList.remove('active'));
        const btn = document.getElementById('btn-' + tool);
        if(btn) btn.classList.add('active');
    }

    function clearCanvas() {
        elements = [];
        drawGrid();
    }

    function drawGrid() {
        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        ctx.fillStyle = '#30363d';
        for(let x = 0; x < canvas.width; x += gridSize) {
            for(let y = 0; y < canvas.height; y += gridSize) {
                ctx.fillRect(x - 1, y - 1, 2, 2);
            }
        }

        // Desenha todos os elementos gravados
        elements.forEach(el => drawElement(el));

        // Desenha a prévia do elemento durante o arrasto
        if(isDrawing) {
            ctx.strokeStyle = '#f1c40f';
            ctx.lineWidth = 2;
            drawElement({ tool: currentTool, x1: startX, y1: startY, x2: currentX, y2: currentY, preview: true });
        }
    }

    function drawElement(el) {
        ctx.beginPath();
        ctx.strokeStyle = el.preview ? '#f39c12' : '#2ecc71';
        ctx.lineWidth = 2.5;

        if (el.tool === 'wire') {
            ctx.moveTo(el.x1, el.y1);
            ctx.lineTo(el.x2, el.y2);
            ctx.stroke();
        } else if (['res', 'ind', 'cap', 'source'].includes(el.tool)) {
            // Desenha fio guia até o componente
            let midX = (el.x1 + el.x2) / 2;
            let midY = (el.y1 + el.y2) / 2;
            ctx.moveTo(el.x1, el.y1);
            ctx.lineTo(el.x2, el.y2);
            ctx.stroke();

            // Símbolo do componente no centro
            ctx.fillStyle = el.tool === 'res' ? '#e67e22' : el.tool === 'ind' ? '#3498db' : el.tool === 'cap' ? '#9b59b6' : '#e74c3c';
            ctx.beginPath();
            ctx.arc(midX, midY, 12, 0, 2 * Math.PI);
            ctx.fill();
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 10px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            let label = el.tool === 'res' ? 'R' : el.tool === 'ind' ? 'L' : el.tool === 'cap' ? 'C' : 'AC';
            ctx.fillText(label, midX, midY);
        } else if (el.tool === 'gnd') {
            ctx.moveTo(el.x1, el.y1);
            ctx.lineTo(el.x1, el.y1 + 15);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(el.x1 - 10, el.y1 + 15);
            ctx.lineTo(el.x1 + 10, el.y1 + 15);
            ctx.stroke();
        }
    }

    canvas.addEventListener('mousedown', e => {
        const rect = canvas.getBoundingClientRect();
        startX = snap(e.clientX - rect.left);
        startY = snap(e.clientY - rect.top);
        isDrawing = true;
    });

    canvas.addEventListener('mousemove', e => {
        if (!isDrawing) return;
        const rect = canvas.getBoundingClientRect();
        currentX = snap(e.clientX - rect.left);
        currentY = snap(e.clientY - rect.top);
        drawGrid();
    });

    canvas.addEventListener('mouseup', e => {
        if (!isDrawing) return;
        isDrawing = false;
        const rect = canvas.getBoundingClientRect();
        currentX = snap(e.clientX - rect.left);
        currentY = snap(e.clientY - rect.top);

        if (startX !== currentX || startY !== currentY || currentTool === 'gnd') {
            elements.push({ tool: currentTool, x1: startX, y1: startY, x2: currentX, y2: currentY });
        }
        drawGrid();
    });

    drawGrid();
</script>

</body>
</html>
"""
components.html(falstad_canvas_html, height=390)

# --- GERENCIADOR DE COMPONENTES DA LISTA ---
st.subheader("📋 Componentes no Circuito Ativo (Calculadora)")
if not st.session_state.componentes:
    st.warning("Nenhum componente cadastrado para análise numérica.")
    st.stop()

cols = st.columns(min(len(st.session_state.componentes), 6))
for idx, comp in enumerate(st.session_state.componentes):
    col_idx = idx % len(cols)
    with cols[col_idx]:
        st.metric(
            f"{idx+1}. {comp['tipo']}", f"{comp['valor']} {comp['unidade']}"
        )
        if st.button("🗑️ Remover", key=f"del_{idx}"):
            st.session_state.componentes.pop(idx)
            st.rerun()


# --- MOTOR DE CÁLCULO ELETRÔNICO ---
def calcular_impedancia_item(comp, frequency_w):
    val = comp["valor"]
    if comp["tipo"] == "Resistor":
        return complex(val, 0)
    elif comp["tipo"] == "Indutor":
        L = val / 1000.0
        return complex(0, frequency_w * L)
    elif comp["tipo"] == "Capacitor":
        C = val / 1e6
        return complex(0, -1 / (frequency_w * C))


try:
    if arranjo == "Série Puro":
        Z_eq = sum(
            calcular_impedancia_item(c, w)
            for c in st.session_state.componentes
        )
    elif arranjo == "Paralelo Puro":
        Y_total = sum(
            1 / calcular_impedancia_item(c, w)
            for c in st.session_state.componentes
        )
        Z_eq = 1 / Y_total
    elif arranjo == "Misto (Resistor em Série + Bloco Paralelo)":
        res_list = [
            c for c in st.session_state.componentes if c["tipo"] == "Resistor"
        ]
        reat_list = [
            c for c in st.session_state.componentes if c["tipo"] != "Resistor"
        ]
        if not res_list or not reat_list:
            st.error(
                "Para o arranjo Misto, adicione pelo menos 1 Resistor e 1 elemento reativo (L ou C)."
            )
            st.stop()
        Z_s = sum(calcular_impedancia_item(r, w) for r in res_list)
        Y_p = sum(1 / calcular_impedancia_item(c, w) for c in reat_list)
        Z_eq = Z_s + (1 / Y_p)
except ZeroDivisionError:
    st.error("Erro de divisão por zero na combinação do circuito.")
    st.stop()

# --- RESULTADOS DAS GRANDEZAS ELÉTRICAS ---
abs_Z = abs(Z_eq)
angle_Z_rad = cmath.phase(Z_eq)
angle_Z_deg = np.degrees(angle_Z_rad)

I_rms = V_rms / abs_Z
angle_I_deg = -angle_Z_deg

S = V_rms * I_rms
P = S * np.cos(angle_Z_rad)
Q = S * np.sin(angle_Z_rad)
FP = np.cos(angle_Z_rad)

st.markdown("---")
st.subheader("📊 Resultados Numéricos do Circuito")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência", f"{FP:.4f}")

r1, r2 = st.columns(2)
carater = (
    "Indutivo" if Q > 0.01 else "Capacitivo" if Q < -0.01 else "Resistivo Puro"
)
with r1:
    st.write(f"**Ângulo da Impedância ($\theta$):** {angle_Z_deg:.2f}°")
    st.write(f"**Potência Reativa (Q):** {Q:.2f} VAR")
with r2:
    st.write(f"**Potência Aparente (S):** {S:.2f} VA")
    st.write(f"**Comportamento Predominante:** {carater}")

# --- MÓDULO 2: OSCILOSCÓPIO VIRTUAL NO DOMÍNIO DO TEMPO (v(t) e i(t)) ---
st.markdown("---")
st.subheader("📺 Osciloscópio Virtual: Formas de Onda no Tempo v(t) e i(t)")

t = np.linspace(0, 2 / f, 500)
V_pico = V_rms * np.sqrt(2)
I_pico = I_rms * np.sqrt(2)

v_t = V_pico * np.sin(w * t)
i_t = I_pico * np.sin(w * t + np.radians(angle_I_deg))

fig_osc, ax_osc = plt.subplots(figsize=(9, 3.2))
ax_osc.plot(
    t * 1000,
    v_t,
    color="red",
    linewidth=2,
    label=f"v(t) - Pico: {V_pico:.1f} V",
)
ax_osc_i = ax_osc.twinx()
ax_osc_i.plot(
    t * 1000,
    i_t,
    color="cyan",
    linewidth=2,
    linestyle="--",
    label=f"i(t) - Pico: {I_pico:.2f} A",
)

ax_osc.set_xlabel("Tempo (ms)")
ax_osc.set_ylabel("Tensão (V)", color="red")
ax_osc_i.set_ylabel("Corrente (A)", color="cyan")
ax_osc.grid(True, linestyle=":", alpha=0.6)

# União de legendas dos dois eixos
lines_1, labels_1 = ax_osc.get_legend_handles_labels()
lines_2, labels_2 = ax_osc_i.get_legend_handles_labels()
ax_osc.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right")

st.pyplot(fig_osc)

# --- MÓDULO 3: DIAGRAMA FASORIAL E TRIÂNGULO DE POTÊNCIAS ---
st.markdown("---")
g1, g2 = st.columns(2)

with g1:
    st.subheader("Diagrama Fasorial (V e I)")
    fig_f, ax_f = plt.subplots(figsize=(4.5, 4.5))
    escala_I = (V_rms / I_rms) * 0.5 if I_rms > 0 else 1.0

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
    st.pyplot(fig_f)

with g2:
    st.subheader("Triângulo de Potências (P, Q, S)")
    fig_p, ax_p = plt.subplots(figsize=(4.5, 4.5))

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
    ax_p.set_xlim(-10, max_v)
    ax_p.set_ylim(-max_v if Q < 0 else -10, max_v if Q >= 0 else 10)
    ax_p.grid(True, linestyle=":", alpha=0.6)
    ax_p.legend(loc="upper left", fontsize=8)
    st.pyplot(fig_p)

# --- MÓDULO 4: VARREDURA DE FREQUÊNCIA (RESPOSTA EM FREQUÊNCIA - BODE) ---
st.markdown("---")
st.subheader("📈 Varredura de Frequência (|Z| e Fase vs. Frequência)")

freq_array = np.logspace(1, 5, 200)  # 10 Hz até 100 kHz
z_sweep = []
phase_sweep = []

for f_i in freq_array:
    w_i = 2 * np.pi * f_i
    try:
        if arranjo == "Série Puro":
            Z_i = sum(
                calcular_impedancia_item(c, w_i)
                for c in st.session_state.componentes
            )
        elif arranjo == "Paralelo Puro":
            Y_i = sum(
                1 / calcular_impedancia_item(c, w_i)
                for c in st.session_state.componentes
            )
            Z_i = 1 / Y_i
        else:
            res_l = [
                c
                for c in st.session_state.componentes
                if c["tipo"] == "Resistor"
            ]
            reat_l = [
                c
                for c in st.session_state.componentes
                if c["tipo"] != "Resistor"
            ]
            Z_s = sum(calcular_impedancia_item(r, w_i) for r in res_l)
            Y_p = sum(1 / calcular_impedancia_item(c, w_i) for c in reat_l)
            Z_i = Z_s + (1 / Y_p)
        z_sweep.append(abs(Z_i))
        phase_sweep.append(np.degrees(cmath.phase(Z_i)))
    except ZeroDivisionError:
        z_sweep.append(0)
        phase_sweep.append(0)

fig_bode, (ax_mag, ax_pha) = plt.subplots(1, 2, figsize=(10, 3.2))

ax_mag.semilogx(freq_array, z_sweep, color="blue", linewidth=2)
ax_mag.set_title("Módulo da Impedância |Z(f)|")
ax_mag.set_xlabel("Frequência (Hz)")
ax_mag.set_ylabel("|Z| (Ω)")
ax_mag.grid(True, which="both", linestyle=":", alpha=0.6)

ax_pha.semilogx(freq_array, phase_sweep, color="purple", linewidth=2)
ax_pha.set_title("Ângulo de Fase θ(f)")
ax_pha.set_xlabel("Frequência (Hz)")
ax_pha.set_ylabel("Fase (°)")
ax_pha.grid(True, which="both", linestyle=":", alpha=0.6)

st.pyplot(fig_bode)

# --- MÓDULO 5: GERAÇÃO E EXPORTAÇÃO DE RELATÓRIOS ---
st.markdown("---")
st.subheader("📄 Exportação do Relatório Técnico")


def gerar_relatorio_texto(
    componentes,
    modo_arranjo,
    tensao,
    freq,
    z_complex,
    i_val,
    p_val,
    q_val,
    s_val,
    fp_val,
    natureza,
):
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    z_mag = abs(z_complex)
    z_deg = np.degrees(cmath.phase(z_complex))

    div_main = "=" * 45
    div_sub = "-" * 45

    texto = f"""{div_main}
RELATORIO TECNICO DE ANALISE DE CIRCUITO RLC
Data de Geracao: {agora}
{div_main}

1. PARAMETROS DA FONTE DE ALIMENTACAO
{div_sub}
- Tensao Eficaz (V_rms): {tensao:.2f} V
- Frequencia (f): {freq:.2f} Hz
- Frequencia Angular (w): {2 * np.pi * freq:.2f} rad/s

2. TOPOLOGIA E COMPONENTES DO CIRCUITO
{div_sub}
- Topologia Selecionada: {modo_arranjo}
- Lista de Componentes do Circuito:
"""
    for i, c in enumerate(componentes, 1):
        unidade_limpa = "Ohm" if c["unidade"] == "Ω" else c["unidade"]
        texto += f"   [{i}] {c['tipo']}: {c['valor']} {unidade_limpa}\n"

    texto += f"""
3. RESULTADOS DOS CALCULOS ELETRONICOS
{div_sub}
- Impedancia Equivalente (|Z_eq|): {z_mag:.2f} Ohm
- Angulo da Impedancia (theta_Z): {z_deg:.2f} deg
- Formato Complexo de Z_eq: {z_complex.real:.2f} + j({z_complex.imag:.2f}) Ohm
- Corrente Total RMS (|I_rms|): {i_val:.2f} A
- Angulo da Corrente (theta_I): {-z_deg:.2f} deg
- Potencia Ativa (P): {p_val:.2f} W
- Potencia Reativa (Q): {q_val:.2f} VAR
- Potencia Aparente (S): {s_val:.2f} VA
- Fator de Potencia (FP): {fp_val:.4f}
- Comportamento Predominante: {natureza}

{div_main}
Gerado automaticamente pelo Simulador de Circuitos RLC
{div_main}
"""
    return texto


def gerar_pdf_bytes(texto):
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Courier", size=9)

    for line in texto.split("\n"):
        clean_line = line.encode("latin-1", "replace").decode("latin-1")
        pdf.set_x(15)
        if not clean_line.strip():
            pdf.ln(3)
        else:
            pdf.multi_cell(
                w=0, h=5, text=clean_line, new_x="LMARGIN", new_y="NEXT"
            )

    return bytes(pdf.output())


relatorio_gerado = gerar_relatorio_texto(
    st.session_state.componentes,
    arranjo,
    V_rms,
    f,
    Z_eq,
    I_rms,
    P,
    Q,
    S,
    FP,
    carater,
)

st.text_area("Pré-visualização do Relatório", relatorio_gerado, height=200)

col_dl1, col_dl2, col_dl3 = st.columns(3)

with col_dl1:
    st.download_button(
        label="📥 Baixar PDF (.pdf)",
        data=gerar_pdf_bytes(relatorio_gerado),
        file_name=f"relatorio_rlc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
    )

with col_dl2:
    st.download_button(
        label="📥 Baixar Texto (.txt)",
        data=relatorio_gerado,
        file_name=f"relatorio_rlc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
    )

with col_dl3:
    relatorio_md = (
        f"# Relatório Técnico RLC\n```text\n{relatorio_gerado}\n```"
    )
    st.download_button(
        label="📥 Baixar Markdown (.md)",
        data=relatorio_md,
        file_name=f"relatorio_rlc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="text/markdown",
    )
