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
    page_title="Simulador RLC com Exportação PDF",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador e Analisador de Circuitos RLC")
st.markdown(
    "Configure os parâmetros da fonte e a topologia do circuito para calcular a impedância equivalente, "
    "corrente, potências, diagramas fasoriais e exportar o relatório técnico em **PDF**, **TXT** ou **Markdown**."
)

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "componentes" not in st.session_state:
    st.session_state.componentes = [
        {"tipo": "Resistor", "valor": 100.0, "unidade": "Ω"},
        {"tipo": "Indutor", "valor": 312.0, "unidade": "mH"},
        {"tipo": "Capacitor", "valor": 30.01, "unidade": "µF"},
    ]

# --- BARRA LATERAL: CONFIGURAÇÕES E PARÂMETROS ---
st.sidebar.header("1. Parâmetros da Fonte CA")
V_rms = st.sidebar.number_input(
    "Tensão Eficaz V_rms (V)", value=100.0, step=1.0, min_value=0.1
)
f = st.sidebar.number_input(
    "Frequência f (Hz)", value=60.0, step=1.0, min_value=0.1
)
w = 2 * np.pi * f

st.sidebar.header("2. Topologia do Circuito")
arranjo = st.sidebar.selectbox(
    "Arranjo dos Componentes",
    [
        "Série Puro",
        "Paralelo Puro",
        "Misto (Resistor em Série + Bloco Paralelo)",
    ],
)

st.sidebar.header("3. Adicionar Componentes")
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

    submitted = st.form_submit_button("➕ Adicionar ao Circuito")
    if submitted:
        nome_tipo = tipo_comp.split(" ")[0]
        st.session_state.componentes.append(
            {"tipo": nome_tipo, "valor": float(val_comp), "unidade": unid}
        )
        st.rerun()

# --- MÓDULO VISUAL: DRAG & DROP ---
with st.expander(
    "🖐️ Bancada Interativa de Arraste (Drag & Drop)", expanded=False
):
    st.write(
        "Arraste os componentes pré-definidos para visualizar a alocação nos slots do circuito."
    )
    drag_drop_html = """
    <style>
        .container { display: flex; gap: 20px; font-family: sans-serif; }
        .box { background: #1e1e1e; color: white; padding: 15px; border-radius: 8px; flex: 1; }
        .comp { padding: 8px; margin: 5px 0; border-radius: 4px; font-weight: bold; cursor: grab; }
        .res { background: #d35400; } .ind { background: #2980b9; } .cap { background: #8e44ad; }
        .slot { height: 60px; border: 2px dashed #7f8c8d; margin: 8px 0; border-radius: 6px; display: flex; align-items: center; justify-content: center; }
    </style>
    <div class="container">
        <div class="box">
            <h4>📦 Componentes Disponíveis</h4>
            <div class="comp res" draggable="true" id="c1">R1 (100 Ω)</div>
            <div class="comp ind" draggable="true" id="c2">L1 (312 mH)</div>
            <div class="comp cap" draggable="true" id="c3">C1 (30.01 µF)</div>
        </div>
        <div class="box">
            <h4>🔌 Slots do Circuito</h4>
            <div class="slot" ondragover="event.preventDefault()" ondrop="this.appendChild(document.getElementById(event.dataTransfer.getData('text')))">Slot 1 (Entrada)</div>
            <div class="slot" ondragover="event.preventDefault()" ondrop="this.appendChild(document.getElementById(event.dataTransfer.getData('text')))">Slot 2 (Paralelo A)</div>
            <div class="slot" ondragover="event.preventDefault()" ondrop="this.appendChild(document.getElementById(event.dataTransfer.getData('text')))">Slot 3 (Paralelo B)</div>
        </div>
    </div>
    <script>
        document.querySelectorAll('.comp').forEach(c => {
            c.addEventListener('dragstart', e => e.dataTransfer.setData('text', e.target.id));
        });
    </script>
    """
    components.html(drag_drop_html, height=260)

# --- GERENCIADOR DE COMPONENTES ATIVOS ---
st.subheader("📋 Componentes no Circuito Ativo")
if not st.session_state.componentes:
    st.warning(
        "Nenhum componente adicionado. Utilize o menu lateral para adicionar elementos."
    )
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


# --- FUNÇÕES DE CÁLCULO ELETRÔNICO ---
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

# --- CÁLCULO DE GRANDEZA E POTÊNCIAS ---
abs_Z = abs(Z_eq)
angle_Z_rad = cmath.phase(Z_eq)
angle_Z_deg = np.degrees(angle_Z_rad)

I_rms = V_rms / abs_Z
angle_I_deg = -angle_Z_deg

S = V_rms * I_rms
P = S * np.cos(angle_Z_rad)
Q = S * np.sin(angle_Z_rad)
FP = np.cos(angle_Z_rad)


# --- DESENHO DO ESQUEMÁTICO DO CIRCUITO ---
def desenhar_esquematico(componentes, modo_arranjo, tensao):
    fig_esq, ax_esq = plt.subplots(figsize=(8, 2.8))
    ax_esq.set_aspect("equal")
    ax_esq.axis("off")

    ax_esq.add_patch(
        patches.Circle((-1, 2), 0.4, fill=False, color="red", lw=2)
    )
    ax_esq.text(
        -1,
        2,
        "~",
        fontsize=18,
        ha="center",
        va="center",
        color="red",
        weight="bold",
    )
    ax_esq.text(-1, 2.6, f"V = {tensao:.0f}V", fontsize=9, ha="center")

    ax_esq.plot([-1, -1, 0], [1.6, 0, 0], color="black", lw=2)
    ax_esq.plot([-1, -1, 0], [2.4, 4, 4], color="black", lw=2)

    n_comp = len(componentes)
    if modo_arranjo == "Série Puro":
        x_step = 6.0 / max(n_comp, 1)
        x_curr = 0.0
        for comp in componentes:
            x_next = x_curr + x_step
            ax_esq.plot([x_curr, x_next], [4, 4], color="black", lw=2)
            rect = patches.Rectangle(
                (x_curr + x_step * 0.15, 3.6),
                x_step * 0.7,
                0.8,
                facecolor="whitesmoke",
                edgecolor="navy",
                lw=2,
            )
            ax_esq.add_patch(rect)
            ax_esq.text(
                x_curr + x_step * 0.5,
                4,
                f"{comp['tipo'][0]}:{comp['valor']}{comp['unidade']}",
                fontsize=8,
                ha="center",
                va="center",
                weight="bold",
            )
            x_curr = x_next
        ax_esq.plot([x_curr, x_curr], [4, 0], color="black", lw=2)
        ax_esq.plot([0, x_curr], [0, 0], color="black", lw=2)
    elif modo_arranjo == "Paralelo Puro":
        x_step = 6.0 / max(n_comp, 1)
        ax_esq.plot([0, 6], [4, 4], color="black", lw=2)
        ax_esq.plot([0, 6], [0, 0], color="black", lw=2)
        for i, comp in enumerate(componentes):
            x_pos = (i + 0.5) * x_step
            ax_esq.plot([x_pos, x_pos], [4, 2.5], color="black", lw=2)
            ax_esq.plot([x_pos, x_pos], [1.5, 0], color="black", lw=2)
            rect = patches.Rectangle(
                (x_pos - 0.4, 1.5),
                0.8,
                1.0,
                facecolor="whitesmoke",
                edgecolor="darkgreen",
                lw=2,
            )
            ax_esq.add_patch(rect)
            ax_esq.text(
                x_pos,
                2.0,
                f"{comp['tipo'][0]}\n{comp['valor']}{comp['unidade']}",
                fontsize=8,
                ha="center",
                va="center",
                weight="bold",
            )
    elif modo_arranjo == "Misto (Resistor em Série + Bloco Paralelo)":
        res_list = [c for c in componentes if c["tipo"] == "Resistor"]
        reat_list = [c for c in componentes if c["tipo"] != "Resistor"]
        ax_esq.plot([0, 2], [4, 4], color="black", lw=2)
        rect_r = patches.Rectangle(
            (0.5, 3.6),
            1.0,
            0.8,
            facecolor="whitesmoke",
            edgecolor="darkorange",
            lw=2,
        )
        ax_esq.add_patch(rect_r)
        lbl_r = f"R:{res_list[0]['valor']}Ω" if res_list else "R_série"
        ax_esq.text(
            1.0,
            4.0,
            lbl_r,
            fontsize=8,
            ha="center",
            va="center",
            weight="bold",
        )
        ax_esq.plot([2, 6], [4, 4], color="black", lw=2)
        ax_esq.plot([0, 6], [0, 0], color="black", lw=2)
        n_r = len(reat_list) if reat_list else 1
        x_step = 4.0 / n_r
        for i, comp in enumerate(reat_list):
            x_pos = 2 + (i + 0.5) * x_step
            ax_esq.plot([x_pos, x_pos], [4, 2.5], color="black", lw=2)
            ax_esq.plot([x_pos, x_pos], [1.5, 0], color="black", lw=2)
            rect = patches.Rectangle(
                (x_pos - 0.4, 1.5),
                0.8,
                1.0,
                facecolor="whitesmoke",
                edgecolor="purple",
                lw=2,
            )
            ax_esq.add_patch(rect)
            ax_esq.text(
                x_pos,
                2.0,
                f"{comp['tipo'][0]}\n{comp['valor']}{comp['unidade']}",
                fontsize=8,
                ha="center",
                va="center",
                weight="bold",
            )
        ax_esq.plot([6, 6], [4, 0], color="black", lw=2)

    ax_esq.set_xlim(-2, 7)
    ax_esq.set_ylim(-0.5, 4.8)
    return fig_esq


st.markdown("---")
st.subheader("🔌 Esquemático do Circuito Montado")
st.pyplot(desenhar_esquematico(st.session_state.componentes, arranjo, V_rms))

# --- EXIBIÇÃO DOS RESULTADOS ---
st.subheader("📊 Resultados do Circuito")
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

# --- GRÁFICOS: DIAGRAMA FASORIAL E TRIÂNGULO DE POTÊNCIAS ---
st.markdown("---")
g1, g2 = st.columns(2)

with g1:
    st.subheader("Diagrama Fasorial (V e I)")
    fig_f, ax_f = plt.subplots(figsize=(5, 5))
    escala_I = 50.0

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
        color="blue",
        label=f"I = {I_rms:.2f}A ∠{angle_I_deg:.1f}° (x{escala_I:.0f})",
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
    fig_p, ax_p = plt.subplots(figsize=(5, 5))

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

# --- MÓDULO DE GERAÇÃO E DOWNLOAD DO RELATÓRIO TÉCNICO ---
st.markdown("---")
st.subheader("📄 Relatório Técnico da Simulação")


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
        # Substitui o caractere especial Ω por Ohm no texto do relatório para evitar o caractere ? no PDF
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

st.text_area("Pré-visualização do Relatório", relatorio_gerado, height=220)

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
