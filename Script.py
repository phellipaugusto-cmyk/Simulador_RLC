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
    page_title="Simulador RLC Interativo & Topologia Dinâmica",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Simulador RLC: Construtor Dinâmico de Topologia")
st.markdown(
    "Monte a estrutura do seu circuito definindo livremente o arranjo de cada elemento (Série ou Bloco Paralelo). "
    "O motor do aplicativo identificará a topologia criada, calculará todas as grandezas elétricas e gerará o relatório técnico completo em **PDF**."
)

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "componentes" not in st.session_state:
    # Estrutura inicial: cada elemento possui tipo, valor, unidade e 'posicao' ('Série (Linha Principal)' ou 'Ramo Paralelo A', 'Ramo Paralelo B', etc.)
    st.session_state.componentes = [
        {
            "tipo": "Resistor",
            "valor": 100.0,
            "unidade": "Ω",
            "posicao": "Série (Linha Principal)",
        },
        {
            "tipo": "Indutor",
            "valor": 312.0,
            "unidade": "mH",
            "posicao": "Ramo Paralelo A",
        },
        {
            "tipo": "Capacitor",
            "valor": 30.01,
            "unidade": "µF",
            "posicao": "Ramo Paralelo B",
        },
    ]

# --- BARRA LATERAL: FONTE DE ALIMENTAÇÃO ---
st.sidebar.header("1. Fonte de Alimentação CA")
V_rms = st.sidebar.number_input(
    "Tensão Eficaz V_rms (V)", value=100.0, step=1.0, min_value=0.1
)
f = st.sidebar.number_input(
    "Frequência f (Hz)", value=60.0, step=1.0, min_value=0.1
)
w = 2 * np.pi * f

st.sidebar.header("2. Adicionar Novo Componente ao Circuito")
opcoes_posicao = [
    "Série (Linha Principal)",
    "Ramo Paralelo A",
    "Ramo Paralelo B",
    "Ramo Paralelo C",
]

with st.sidebar.form("add_comp_form", clear_on_submit=True):
    tipo_comp = st.selectbox(
        "Tipo de Elemento", ["Resistor (R)", "Indutor (L)", "Capacitor (C)"]
    )
    alocacao = st.selectbox("Alocação no Circuito", opcoes_posicao)

    if tipo_comp.startswith("Resistor"):
        val_default = 100.0
        unid = "Ω"
    elif tipo_comp.startswith("Indutor"):
        val_default = 312.0
        unid = "mH"
    else:
        val_default = 30.0
        unid = "µF"

    submitted = st.form_submit_button("➕ Inserir no Circuito")
    if submitted:
        nome_tipo = tipo_comp.split(" ")[0]
        st.session_state.componentes.append(
            {
                "tipo": nome_tipo,
                "valor": float(val_default),
                "unidade": unid,
                "posicao": alocacao,
            }
        )
        st.rerun()

# --- PAINEL DE CONSTRUÇÃO E AJUSTE DA TOPOLOGIA ---
st.subheader("🛠️ 1. Editor de Arranjo e Parâmetros dos Componentes")
st.caption(
    "Defina onde cada componente estará conectado no circuito e ajuste seus valores. O sistema reconhecerá automaticamente se o circuito é Série, Paralelo ou Misto."
)

if not st.session_state.componentes:
    st.warning(
        "O circuito está vazio. Adicione componentes através do menu lateral."
    )
    st.stop()

# Exibição dos componentes e edição interativa
cols = st.columns(min(len(st.session_state.componentes), 4))
for idx, comp in enumerate(st.session_state.componentes):
    col_idx = idx % len(cols)
    with cols[col_idx]:
        st.markdown(f"### Componente #{idx+1}")
        comp["tipo"] = st.selectbox(
            "Tipo",
            ["Resistor", "Indutor", "Capacitor"],
            index=["Resistor", "Indutor", "Capacitor"].index(comp["tipo"]),
            key=f"tipo_{idx}",
        )
        comp["posicao"] = st.selectbox(
            "Alocação",
            opcoes_posicao,
            index=opcoes_posicao.index(comp["posicao"])
            if comp["posicao"] in opcoes_posicao
            else 0,
            key=f"pos_{idx}",
        )

        if comp["tipo"] == "Resistor":
            comp["unidade"] = "Ω"
            comp["valor"] = st.number_input(
                "Resistência (Ω)",
                value=float(comp["valor"]),
                min_value=0.1,
                step=1.0,
                key=f"val_{idx}",
            )
        elif comp["tipo"] == "Indutor":
            comp["unidade"] = "mH"
            comp["valor"] = st.number_input(
                "Indutância (mH)",
                value=float(comp["valor"]),
                min_value=0.1,
                step=1.0,
                key=f"val_{idx}",
            )
        else:
            comp["unidade"] = "µF"
            comp["valor"] = st.number_input(
                "Capacitância (µF)",
                value=float(comp["valor"]),
                min_value=0.01,
                step=1.0,
                key=f"val_{idx}",
            )

        if st.button("🗑️ Remover", key=f"del_{idx}"):
            st.session_state.componentes.pop(idx)
            st.rerun()


# --- PROCESSAMENTO AUTOMÁTICO DA TOPOLOGIA E CÁLCULO DE IMPEDÂNCIA ---
def calcular_impedancia_elemento(comp, frequency_w):
    val = comp["valor"]
    if comp["tipo"] == "Resistor":
        return complex(val, 0)
    elif comp["tipo"] == "Indutor":
        L = val / 1000.0
        return complex(0, frequency_w * L)
    elif comp["tipo"] == "Capacitor":
        C = val / 1e6
        return complex(0, -1 / (frequency_w * C))


# Separação dos componentes por ramo de alocação
elementos_serie = [
    c
    for c in st.session_state.componentes
    if c["posicao"] == "Série (Linha Principal)"
]
ramos_paralelos = {}
for c in st.session_state.componentes:
    if c["posicao"] != "Série (Linha Principal)":
        nome_ramo = c["posicao"]
        if nome_ramo not in ramos_paralelos:
            ramos_paralelos[nome_ramo] = []
        ramos_paralelos[nome_ramo].append(c)

# Identificação da topologia equivalente
if elementos_serie and ramos_paralelos:
    topologia_detectada = (
        "Misto (Elementos em Série + Bloco em Paralelo Dividido)"
    )
elif elementos_serie and not ramos_paralelos:
    topologia_detectada = "Série Puro"
elif not elementos_serie and ramos_paralelos:
    topologia_detectada = "Paralelo Puro"
else:
    st.error("Adicione componentes para formar o circuito.")
    st.stop()

# Cálculo da Impedância Equivalente Dinâmica Z_eq
try:
    Z_serie_total = sum(
        calcular_impedancia_elemento(c, w) for c in elementos_serie
    )

    if ramos_paralelos:
        admitancia_paralela_total = complex(0, 0)
        for nome_ramo, comps_ramo in ramos_paralelos.items():
            Z_ramo = sum(
                calcular_impedancia_elemento(c, w) for c in comps_ramo
            )
            admitancia_paralela_total += 1 / Z_ramo
        Z_paralelo_total = 1 / admitancia_paralela_total
    else:
        Z_paralelo_total = complex(0, 0)

    Z_eq = Z_serie_total + Z_paralelo_total
except ZeroDivisionError:
    st.error("Erro de divisão por zero: verifique a combinação de reatâncias.")
    st.stop()

# --- CÁLCULO DAS GRANDEZAS ELÉTRICAS ---
abs_Z = abs(Z_eq)
angle_Z_rad = cmath.phase(Z_eq)
angle_Z_deg = np.degrees(angle_Z_rad)

I_rms = V_rms / abs_Z
angle_I_deg = -angle_Z_deg

S = V_rms * I_rms
P = S * np.cos(angle_Z_rad)
Q = S * np.sin(angle_Z_rad)
FP = np.cos(angle_Z_rad)
carater = (
    "Indutivo" if Q > 0.01 else "Capacitivo" if Q < -0.01 else "Resistivo Puro"
)


# --- DESENHO AUTOMÁTICO DO ESQUEMÁTICO DO CIRCUITO MONTADO ---
def desenhar_esquematico_dinamico(elem_s, ramos_p, tensao):
    fig_esq, ax_esq = plt.subplots(figsize=(8.5, 3.0))
    ax_esq.set_aspect("equal")
    ax_esq.axis("off")

    # Fonte de Tensão CA
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

    # Desenho dos elementos em série
    x_curr = 0.0
    if elem_s:
        x_step = 3.0 / len(elem_s)
        for comp in elem_s:
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
                4.0,
                f"{comp['tipo'][0]}:{comp['valor']}{comp['unidade']}",
                fontsize=8,
                ha="center",
                va="center",
                weight="bold",
            )
            x_curr = x_next
    else:
        ax_esq.plot([0, 3.0], [4, 4], color="black", lw=2)
        x_curr = 3.0

    # Desenho do bloco paralelo
    if ramos_p:
        ax_esq.plot([x_curr, x_curr + 4.0], [4, 4], color="black", lw=2)
        ax_esq.plot([0, x_curr + 4.0], [0, 0], color="black", lw=2)

        n_ramos = len(ramos_p)
        x_step_p = 4.0 / n_ramos
        for i, (nome_ramo, comps) in enumerate(ramos_p.items()):
            x_pos = x_curr + (i + 0.5) * x_step_p
            ax_esq.plot([x_pos, x_pos], [4, 2.5], color="black", lw=2)
            ax_esq.plot([x_pos, x_pos], [1.5, 0], color="black", lw=2)

            rect = patches.Rectangle(
                (x_pos - 0.5, 1.5),
                1.0,
                1.0,
                facecolor="whitesmoke",
                edgecolor="darkgreen",
                lw=2,
            )
            ax_esq.add_patch(rect)

            lbl = "\n".join([f"{c['tipo'][0]}:{c['valor']}" for c in comps])
            ax_esq.text(
                x_pos,
                2.0,
                lbl,
                fontsize=7,
                ha="center",
                va="center",
                weight="bold",
            )

        ax_esq.plot(
            [x_curr + 4.0, x_curr + 4.0], [4, 0], color="black", lw=2
        )
    else:
        ax_esq.plot([x_curr, x_curr], [4, 0], color="black", lw=2)
        ax_esq.plot([0, x_curr], [0, 0], color="black", lw=2)

    ax_esq.set_xlim(-2, x_curr + 5.0)
    ax_esq.set_ylim(-0.5, 4.8)
    return fig_esq


st.markdown("---")
st.subheader("🔌 Esquemático do Circuito Montado")
st.caption(f"Topologia Detectada: **{topologia_detectada}**")
fig_esquematico = desenhar_esquematico_dinamico(
    elementos_serie, ramos_paralelos, V_rms
)
st.pyplot(fig_esquematico)

# --- RESULTADOS NUMÉRICOS ---
st.subheader("📊 Resultados Numéricos")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência", f"{FP:.4f}")

r1, r2 = st.columns(2)
with r1:
    st.write(f"**Ângulo da Impedância ($\theta$):** {angle_Z_deg:.2f}°")
    st.write(f"**Potência Reativa (Q):** {Q:.2f} VAR")
with r2:
    st.write(f"**Potência Aparente (S):** {S:.2f} VA")
    st.write(f"**Comportamento Predominante:** {carater}")

# --- DIAGRAMAS FASORIAIS E DE POTÊNCIA ---
st.markdown("---")
st.subheader("📐 Diagramas Fasoriais e Triângulo de Potências")
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Diagrama Fasorial (V e I)**")
    fig_fasor, ax_f = plt.subplots(figsize=(4.5, 4.5))
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

# --- OSCILOSCÓPIO NO TEMPO E VARREDURA BODE ---
st.markdown("---")
st.subheader("📺 Osciloscópio Virtual e Varredura de Frequência")
col_w1, col_w2 = st.columns(2)

with col_w1:
    st.markdown("**Formas de Onda no Tempo: v(t) e i(t)**")
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

with col_w2:
    st.markdown("**Resposta em Frequência (|Z| e Fase)**")
    freq_array = np.logspace(1, 5, 200)
    z_sweep = []
    phase_sweep = []

    for f_i in freq_array:
        w_i = 2 * np.pi * f_i
        try:
            Z_s_i = sum(
                calcular_impedancia_elemento(c, w_i) for c in elementos_serie
            )
            if ramos_paralelos:
                Y_p_i = sum(
                    1 / sum(calcular_impedancia_elemento(c, w_i) for c in comps)
                    for comps in ramos_paralelos.values()
                )
                Z_p_i = 1 / Y_p_i
            else:
                Z_p_i = complex(0, 0)
            Z_tot_i = Z_s_i + Z_p_i
            z_sweep.append(abs(Z_tot_i))
            phase_sweep.append(np.degrees(cmath.phase(Z_tot_i)))
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

# --- EMISSÃO E DOWNLOAD DO RELATÓRIO PDF COMPLETO ---
st.markdown("---")
st.subheader("📄 Relatório Técnico para Exportação")


def gerar_relatorio_texto(
    componentes,
    topologia,
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
- Topologia Detectada: {topologia}
- Lista de Componentes Alocados:
"""
    for i, c in enumerate(componentes, 1):
        unidade_limpa = "Ohm" if c["unidade"] == "Ω" else c["unidade"]
        texto += f"   [{i}] {c['tipo']} ({c['posicao']}): {c['valor']:.2f} {unidade_limpa}\n"

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
Gerado automaticamente pelo Simulador RLC
{div_main}
"""
    return texto


def gerar_pdf_completo_bytes(
    texto, fig_esq, fig_fasor, fig_pot, fig_osc, fig_bode
):
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)

    # Página 1: Texto e Resultados
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

    buf_esq = io.BytesIO()
    fig_esq.savefig(buf_esq, format="png", dpi=130, bbox_inches="tight")
    buf_esq.seek(0)
    pdf.image(buf_esq, x=15, w=180)

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
    topologia_detectada,
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
        file_name=f"relatorio_rlc_dinamico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
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
