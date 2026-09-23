import cmath
from datetime import datetime
import io
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador RLC Profissional", page_icon="⚡", layout="wide"
)

st.title("⚡ Simulador e Analisador de Circuitos RLC")
st.markdown(
    "Defina a estrutura do circuito, ajuste os valores dos componentes interativamente e analise os diagramas, "
    "formas de onda e relatórios exportáveis com gráficos integrados em **PDF**, **TXT** e **Markdown**."
)

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "componentes" not in st.session_state:
    st.session_state.componentes = [
        {"tipo": "Resistor", "valor": 100.0, "unidade": "Ω"},
        {"tipo": "Indutor", "valor": 312.0, "unidade": "mH"},
        {"tipo": "Capacitor", "valor": 30.01, "unidade": "µF"},
    ]

# --- BARRA LATERAL: FONTE E TOPOLOGIA ---
st.sidebar.header("1. Fonte de Alimentação CA")
V_rms = st.sidebar.number_input(
    "Tensão Eficaz V_rms (V)", value=100.0, step=1.0, min_value=0.1
)
f = st.sidebar.number_input(
    "Frequência f (Hz)", value=60.0, step=1.0, min_value=0.1
)
w = 2 * np.pi * f

st.sidebar.header("2. Topologia do Circuito")
arranjo = st.sidebar.selectbox(
    "Arranjo Estrutural",
    [
        "Série Puro",
        "Paralelo Puro",
        "Misto (Resistor em Série + Bloco Paralelo)",
    ],
)

st.sidebar.header("3. Adicionar Elementos ao Circuito")
with st.sidebar.form("add_comp_form", clear_on_submit=True):
    tipo_comp = st.selectbox(
        "Selecione o Tipo de Elemento",
        ["Resistor (R)", "Indutor (L)", "Capacitor (C)"],
    )

    if tipo_comp.startswith("Resistor"):
        val_default = 100.0
        unid = "Ω"
    elif tipo_comp.startswith("Indutor"):
        val_default = 100.0
        unid = "mH"
    else:
        val_default = 10.0
        unid = "µF"

    submitted = st.form_submit_button("➕ Inserir Slot no Circuito")
    if submitted:
        nome_tipo = tipo_comp.split(" ")[0]
        st.session_state.componentes.append(
            {"tipo": nome_tipo, "valor": float(val_default), "unidade": unid}
        )
        st.rerun()

# --- ETAPA 1: MONTAGEM E AJUSTE DINÂMICO DE VALORES ---
st.subheader("🛠️ 1. Estrutura e Valores dos Componentes no Circuito")
st.caption(
    "Aloque os slots de componentes no circuito e utilize os controles interativos abaixo para ajustar os parâmetros em tempo real."
)

if not st.session_state.componentes:
    st.warning("Nenhum componente alocado. Adicione elementos pela barra lateral.")
    st.stop()

# Ajuste individual por slot de componente
cols = st.columns(min(len(st.session_state.componentes), 4))
for idx, comp in enumerate(st.session_state.componentes):
    col_idx = idx % len(cols)
    with cols[col_idx]:
        st.markdown(f"**Slot {idx+1}: {comp['tipo']}**")
        if comp["tipo"] == "Resistor":
            novo_val = st.slider(
                f"Resistência (Ω) #{idx+1}",
                min_value=1.0,
                max_value=1000.0,
                value=float(comp["valor"]),
                step=1.0,
                key=f"slider_{idx}",
            )
            comp["valor"] = novo_val
        elif comp["tipo"] == "Indutor":
            novo_val = st.slider(
                f"Indutância (mH) #{idx+1}",
                min_value=1.0,
                max_value=1000.0,
                value=float(comp["valor"]),
                step=1.0,
                key=f"slider_{idx}",
            )
            comp["valor"] = novo_val
        elif comp["tipo"] == "Capacitor":
            novo_val = st.slider(
                f"Capacitância (µF) #{idx+1}",
                min_value=0.1,
                max_value=500.0,
                value=float(comp["valor"]),
                step=0.1,
                key=f"slider_{idx}",
            )
            comp["valor"] = novo_val

        if st.button("🗑️ Remover Slot", key=f"del_{idx}"):
            st.session_state.componentes.pop(idx)
            st.rerun()


# --- FUNÇÃO DE DESENHO NORMALIZADO DO CIRCUITO (ESQUEMÁTICO MATPLOTLIB) ---
def desenhar_esquematico(componentes, modo_arranjo, tensao):
    fig_esq, ax_esq = plt.subplots(figsize=(8, 2.6))
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
            lbl = "Ω" if comp["unidade"] == "Ω" else comp["unidade"]
            ax_esq.text(
                x_curr + x_step * 0.5,
                4,
                f"{comp['tipo'][0]}:{comp['valor']:.1f}{lbl}",
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
            lbl = "Ω" if comp["unidade"] == "Ω" else comp["unidade"]
            ax_esq.text(
                x_pos,
                2.0,
                f"{comp['tipo'][0]}\n{comp['valor']:.1f}{lbl}",
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
        lbl_r = f"R:{res_list[0]['valor']:.1f}Ω" if res_list else "R_série"
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
            lbl = "Ω" if comp["unidade"] == "Ω" else comp["unidade"]
            ax_esq.text(
                x_pos,
                2.0,
                f"{comp['tipo'][0]}\n{comp['valor']:.1f}{lbl}",
                fontsize=8,
                ha="center",
                va="center",
                weight="bold",
            )
        ax_esq.plot([6, 6], [4, 0], color="black", lw=2)

    ax_esq.set_xlim(-2, 7)
    ax_esq.set_ylim(-0.5, 4.8)
    return fig_esq


fig_esquematico = desenhar_esquematico(
    st.session_state.componentes, arranjo, V_rms
)
st.pyplot(fig_esquematico)


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

# --- CÁLCULO DE GRANDEZAS E POTÊNCIAS ---
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
st.subheader("📊 2. Resultados Numéricos do Circuito")
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

# --- ETAPA 2: DIAGRAMA FASORIAL E TRIÂNGULO DE POTÊNCIAS (VETORES QUIVER) ---
st.markdown("---")
st.subheader("📐 3. Diagramas Vectoriais (Fasores e Potências)")
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Diagrama Fasorial (V e I)**")
    fig_fasor, ax_f = plt.subplots(figsize=(4.5, 4.5))
    escala_I = (V_rms / I_rms) * 0.4 if I_rms > 0 else 1.0

    # VETOR TENSÃO
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
    # VETOR CORRENTE
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
    ax_f.set_xlabel("Re")
    ax_f.set_ylabel("Im")
    ax_f.grid(True, linestyle=":", alpha=0.6)
    ax_f.legend(loc="upper right", fontsize=8)
    st.pyplot(fig_fasor)

with g2:
    st.markdown("**Triângulo de Potências (P, Q, S)**")
    fig_pot, ax_p = plt.subplots(figsize=(4.5, 4.5))

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
    ax_p.set_xlabel("Ativa (W)")
    ax_p.set_ylabel("Reativa (VAR)")
    ax_p.grid(True, linestyle=":", alpha=0.6)
    ax_p.legend(loc="upper left", fontsize=8)
    st.pyplot(fig_pot)

# --- FORMAS DE ONDA NO TEMPO E VARREDURA DE FREQUÊNCIA ---
st.markdown("---")
st.subheader("📺 4. Análise Temporal e Frequencial")

col_wave1, col_wave2 = st.columns(2)

with col_wave1:
    st.markdown("**Osciloscópio Virtual: v(t) e i(t)**")
    t = np.linspace(0, 2 / f, 500)
    V_pico = V_rms * np.sqrt(2)
    I_pico = I_rms * np.sqrt(2)

    v_t = V_pico * np.sin(w * t)
    i_t = I_pico * np.sin(w * t + np.radians(angle_I_deg))

    fig_osc, ax_osc = plt.subplots(figsize=(5, 3.5))
    ax_osc.plot(
        t * 1000,
        v_t,
        color="red",
        linewidth=1.8,
        label=f"v(t) - Pico: {V_pico:.1f}V",
    )
    ax_osc_i = ax_osc.twinx()
    ax_osc_i.plot(
        t * 1000,
        i_t,
        color="cyan",
        linewidth=1.8,
        linestyle="--",
        label=f"i(t) - Pico: {I_pico:.2f}A",
    )

    ax_osc.set_xlabel("Tempo (ms)")
    ax_osc.set_ylabel("Tensão (V)", color="red")
    ax_osc_i.set_ylabel("Corrente (A)", color="cyan")
    ax_osc.grid(True, linestyle=":", alpha=0.6)

    lines_1, labels_1 = ax_osc.get_legend_handles_labels()
    lines_2, labels_2 = ax_osc_i.get_legend_handles_labels()
    ax_osc.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right")
    st.pyplot(fig_osc)

with col_wave2:
    st.markdown("**Resposta em Frequência (Bode)**")
    freq_array = np.logspace(1, 5, 200)
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

    fig_bode, (ax_mag, ax_pha) = plt.subplots(2, 1, figsize=(5, 3.5))

    ax_mag.semilogx(freq_array, z_sweep, color="blue", linewidth=1.5)
    ax_mag.set_ylabel("|Z| (Ω)")
    ax_mag.grid(True, which="both", linestyle=":", alpha=0.6)

    ax_pha.semilogx(freq_array, phase_sweep, color="purple", linewidth=1.5)
    ax_pha.set_xlabel("Frequência (Hz)")
    ax_pha.set_ylabel("Fase (°)")
    ax_pha.grid(True, which="both", linestyle=":", alpha=0.6)

    st.pyplot(fig_bode)

# --- ETAPA 3: GERAÇÃO DO RELATÓRIO PDF COM GRÁFICOS EMBUTIDOS ---
st.markdown("---")
st.subheader("📄 5. Emissão e Exportação do Relatório Técnico")


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
        texto += f"   [{i}] {c['tipo']}: {c['valor']:.2f} {unidade_limpa}\n"

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


def gerar_pdf_completo_bytes(
    texto, fig_esq, fig_fasor, fig_pot, fig_osc, fig_bode
):
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    # Página 1: Dados e Cálculos
    pdf.add_page()
    pdf.set_font("Courier", size=9)
    for line in texto.split("\n"):
        clean_line = line.encode("latin-1", "replace").decode("latin-1")
        pdf.set_x(15)
        if not clean_line.strip():
            pdf.ln(3)
        else:
            pdf.multi_cell(
                w=0, h=4.5, text=clean_line, new_x="LMARGIN", new_y="NEXT"
            )

    # Página 2: Anexo de Gráficos e Diagramas
    pdf.add_page()
    pdf.set_font("Courier", style="B", size=11)
    pdf.cell(0, 8, "ANEXO: DIAGRAMAS E GRAFICOS", new_x="LMARGIN", new_y="NEXT")

    # Inserção do Esquemático
    buf_esq = io.BytesIO()
    fig_esq.savefig(buf_esq, format="png", dpi=130, bbox_inches="tight")
    buf_esq.seek(0)
    pdf.image(buf_esq, x=15, w=180)

    # Inserção Fasor e Potência
    buf_fasor = io.BytesIO()
    fig_fasor.savefig(buf_fasor, format="png", dpi=130, bbox_inches="tight")
    buf_fasor.seek(0)

    buf_pot = io.BytesIO()
    fig_pot.savefig(buf_pot, format="png", dpi=130, bbox_inches="tight")
    buf_pot.seek(0)

    pdf.ln(2)
    y_pos = pdf.get_y()
    pdf.image(buf_fasor, x=15, y=y_pos, w=85)
    pdf.image(buf_pot, x=105, y=y_pos, w=85)

    # Inserção Osciloscópio e Bode
    buf_osc = io.BytesIO()
    fig_osc.savefig(buf_osc, format="png", dpi=130, bbox_inches="tight")
    buf_osc.seek(0)

    buf_bode = io.BytesIO()
    fig_bode.savefig(buf_bode, format="png", dpi=130, bbox_inches="tight")
    buf_bode.seek(0)

    pdf.add_page()
    pdf.image(buf_osc, x=15, w=180)
    pdf.ln(2)
    pdf.image(buf_bode, x=15, w=180)

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

st.text_area("Pré-visualização do Relatório", relatorio_gerado, height=180)

col_dl1, col_dl2, col_dl3 = st.columns(3)

with col_dl1:
    pdf_bytes = gerar_pdf_completo_bytes(
        relatorio_gerado,
        fig_esquematico,
        fig_fasor,
        fig_pot,
        fig_osc,
        fig_bode,
    )
    st.download_button(
        label="📥 Baixar PDF com Gráficos (.pdf)",
        data=pdf_bytes,
        file_name=f"relatorio_rlc_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
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
