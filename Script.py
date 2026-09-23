import cmath
from datetime import datetime
import io
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA (OTIMIZADA PARA MOBILE) ---
st.set_page_config(
    page_title="Simulador RLC - Construtor Mobile", page_icon="⚡", layout="wide"
)

st.title("⚡ Construtor e Analisador de Circuitos RLC")
st.caption(
    "Fluxo Mobile: Adicione os componentes e conexões ao circuito primeiro e configure os valores individualmente na etapa seguinte."
)

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if "circuito" not in st.session_state:
    # Estrutura inicial padrão de componentes sem exigir valores imediatos
    st.session_state.circuito = [
        {"id": 1, "tipo": "Fonte CA", "valor": 100.0, "unid": "V"},
        {"id": 2, "tipo": "Resistor", "valor": 100.0, "unid": "Ω"},
        {"id": 3, "tipo": "Indutor", "valor": 312.0, "unid": "mH"},
        {"id": 4, "tipo": "Capacitor", "valor": 30.01, "unid": "µF"},
        {"id": 5, "tipo": "Terra (GND)", "valor": 0.0, "unid": ""},
    ]

# --- BARRA LATERAL: PARÂMETROS GERAIS ---
st.sidebar.header("⚙️ Configurações Gerais")
freq_fonte = st.sidebar.number_input(
    "Frequência da Fonte (Hz)", value=60.0, min_value=0.1, step=1.0
)
omega = 2 * np.pi * freq_fonte

modo_arranjo = st.sidebar.selectbox(
    "Topologia do Circuito",
    [
        "Série Puro",
        "Paralelo Puro",
        "Misto (Resistor Série + Bloco Paralelo)",
    ],
)

# --- ETAPA 1: INSERÇÃO RÁPIDA DE COMPONENTES (BOTÕES TOUCH) ---
st.subheader("🧩 Etapa 1: Adicionar Componentes ao Circuito")
st.write("Toque nos botões abaixo para inserir os slots dos elementos no seu circuito:")

c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    if st.button("➕ Resistor", use_container_width=True):
        novo_id = len(st.session_state.circuito) + 1
        st.session_state.circuito.append(
            {"id": novo_id, "tipo": "Resistor", "valor": 100.0, "unid": "Ω"}
        )
        st.rerun()

with c2:
    if st.button("➕ Indutor", use_container_width=True):
        novo_id = len(st.session_state.circuito) + 1
        st.session_state.circuito.append(
            {"id": novo_id, "tipo": "Indutor", "valor": 100.0, "unid": "mH"}
        )
        st.rerun()

with c3:
    if st.button("➕ Capacitor", use_container_width=True):
        novo_id = len(st.session_state.circuito) + 1
        st.session_state.circuito.append(
            {"id": novo_id, "tipo": "Capacitor", "valor": 10.0, "unid": "µF"}
        )
        st.rerun()

with c4:
    if st.button("➕ Fonte CA", use_container_width=True):
        novo_id = len(st.session_state.circuito) + 1
        st.session_state.circuito.append(
            {"id": novo_id, "tipo": "Fonte CA", "valor": 127.0, "unid": "V"}
        )
        st.rerun()

with c5:
    if st.button("➕ Fio (Wire)", use_container_width=True):
        novo_id = len(st.session_state.circuito) + 1
        st.session_state.circuito.append(
            {"id": novo_id, "tipo": "Fio (Wire)", "valor": 0.0, "unid": ""}
        )
        st.rerun()

with c6:
    if st.button("➕ Terra (GND)", use_container_width=True):
        novo_id = len(st.session_state.circuito) + 1
        st.session_state.circuito.append(
            {"id": novo_id, "tipo": "Terra (GND)", "valor": 0.0, "unid": ""}
        )
        st.rerun()

if st.button("🗑️ Limpar Todo o Circuito", type="secondary"):
    st.session_state.circuito = []
    st.rerun()

# --- ETAPA 2: DEFINIÇÃO DE VALORES DOS COMPONENTES INSERIDOS ---
st.markdown("---")
st.subheader("⚙️ Etapa 2: Definir Valores dos Componentes no Circuito")

if not st.session_state.circuito:
    st.warning("O circuito está vazio. Adicione componentes na Etapa 1 acima.")
    st.stop()

# Layout em grade responsiva para mobile
grid_cols = st.columns(min(len(st.session_state.circuito), 4))

for idx, comp in enumerate(st.session_state.circuito):
    col_target = grid_cols[idx % len(grid_cols)]
    with col_target:
        st.markdown(f"**Slot #{idx+1}: {comp['tipo']}**")

        if comp["tipo"] == "Resistor":
            comp["valor"] = st.number_input(
                f"R #{idx+1} (Ω)",
                value=float(comp["valor"]),
                min_value=0.1,
                step=1.0,
                key=f"val_{idx}",
            )
        elif comp["tipo"] == "Indutor":
            comp["valor"] = st.number_input(
                f"L #{idx+1} (mH)",
                value=float(comp["valor"]),
                min_value=0.1,
                step=1.0,
                key=f"val_{idx}",
            )
        elif comp["tipo"] == "Capacitor":
            comp["valor"] = st.number_input(
                f"C #{idx+1} (µF)",
                value=float(comp["valor"]),
                min_value=0.01,
                step=1.0,
                key=f"val_{idx}",
            )
        elif comp["tipo"] == "Fonte CA":
            comp["valor"] = st.number_input(
                f"V_rms #{idx+1} (V)",
                value=float(comp["valor"]),
                min_value=0.1,
                step=1.0,
                key=f"val_{idx}",
            )
        elif comp["tipo"] in ["Fio (Wire)", "Terra (GND)"]:
            st.caption("Conexão direta (sem valor atribuído)")

        if st.button(f"❌ Remover #{idx+1}", key=f"del_{idx}"):
            st.session_state.circuito.pop(idx)
            st.rerun()


# --- DESENHO AUTOMÁTICO DO ESQUEMÁTICO ---
def renderizar_esquematico(lista_comps, arranjo):
    fig_esq, ax_esq = plt.subplots(figsize=(8, 2.5))
    ax_esq.set_aspect("equal")
    ax_esq.axis("off")

    x_pos = 0.0
    ax_esq.plot([-1, 0], [2, 2], color="black", lw=2)

    for i, item in enumerate(lista_comps):
        tipo = item["tipo"]
        val = item["valor"]
        unid = item["unid"]

        if tipo == "Fonte CA":
            ax_esq.add_patch(
                patches.Circle((x_pos, 2), 0.4, fill=False, color="red", lw=2)
            )
            ax_esq.text(
                x_pos,
                2,
                "~",
                fontsize=16,
                ha="center",
                va="center",
                color="red",
                weight="bold",
            )
            ax_esq.text(
                x_pos, 2.6, f"{val:.0f}{unid}", fontsize=8, ha="center"
            )
        elif tipo in ["Resistor", "Indutor", "Capacitor"]:
            rect = patches.Rectangle(
                (x_pos - 0.4, 1.6),
                0.8,
                0.8,
                facecolor="whitesmoke",
                edgecolor="navy",
                lw=2,
            )
            ax_esq.add_patch(rect)
            ax_esq.text(
                x_pos,
                2.0,
                f"{tipo[0]}:{val:.1f}{unid}",
                fontsize=7,
                ha="center",
                va="center",
                weight="bold",
            )
        elif tipo == "Fio (Wire)":
            ax_esq.plot(
                [x_pos - 0.4, x_pos + 0.4], [2, 2], color="green", lw=3
            )
            ax_esq.text(
                x_pos,
                2.3,
                "Fio",
                fontsize=7,
                ha="center",
                color="green",
            )
        elif tipo == "Terra (GND)":
            ax_esq.plot(
                [x_pos, x_pos], [2, 1.2], color="black", lw=2
            )
            ax_esq.plot(
                [x_pos - 0.3, x_pos + 0.3], [1.2, 1.2], color="black", lw=3
            )
            ax_esq.plot(
                [x_pos - 0.2, x_pos + 0.2], [1.0, 1.0], color="black", lw=2
            )
            ax_esq.plot(
                [x_pos - 0.1, x_pos + 0.1], [0.8, 0.8], color="black", lw=1
            )

        if i < len(lista_comps) - 1:
            ax_esq.plot(
                [x_pos + 0.4, x_pos + 1.1], [2, 2], color="black", lw=2
            )
        x_pos += 1.5

    ax_esq.set_xlim(-1.5, x_pos + 0.5)
    ax_esq.set_ylim(-0.2, 3.2)
    return fig_esq


st.markdown("---")
st.subheader("🔌 Esquemático do Circuito Montado")
fig_esquematico = renderizar_esquematico(
    st.session_state.circuito, modo_arranjo
)
st.pyplot(fig_esquematico)


# --- MOTOR DE CÁLCULO ELÉTRICO ---
def calc_z(item, w):
    t = item["tipo"]
    v = item["valor"]
    if t == "Resistor":
        return complex(v, 0)
    elif t == "Indutor":
        return complex(0, w * (v / 1000.0))
    elif t == "Capacitor":
        return complex(0, -1 / (w * (v / 1e6)))
    return complex(0, 0)


# Filtra fontes e elementos reativos/resistivos
fontes = [c for c in st.session_state.circuito if c["tipo"] == "Fonte CA"]
elementos_passivos = [
    c
    for c in st.session_state.circuito
    if c["tipo"] in ["Resistor", "Indutor", "Capacitor"]
]

V_fonte = fontes[0]["valor"] if fontes else 100.0

if not elementos_passivos:
    st.info("Adicione pelo menos um Resistor, Indutor ou Capacitor para calcular a impedância.")
    st.stop()

try:
    if modo_arranjo == "Série Puro":
        Z_eq = sum(calc_z(c, omega) for c in elementos_passivos)
    elif modo_arranjo == "Paralelo Puro":
        Y_tot = sum(1 / calc_z(c, omega) for c in elementos_passivos)
        Z_eq = 1 / Y_tot
    else:
        res = [c for c in elementos_passivos if c["tipo"] == "Resistor"]
        reat = [c for c in elementos_passivos if c["tipo"] != "Resistor"]
        if not res or not reat:
            Z_eq = sum(calc_z(c, omega) for c in elementos_passivos)
        else:
            Z_s = sum(calc_z(r, omega) for r in res)
            Y_p = sum(1 / calc_z(c, omega) for c in reat)
            Z_eq = Z_s + (1 / Y_p)
except ZeroDivisionError:
    st.error("Ressonância extrema ou impedância nula detectada.")
    st.stop()

# Grandezas Resultantes
abs_Z = abs(Z_eq)
angle_Z_rad = cmath.phase(Z_eq)
angle_Z_deg = np.degrees(angle_Z_rad)

I_rms = V_fonte / abs_Z if abs_Z > 0 else 0
angle_I_deg = -angle_Z_deg

S = V_fonte * I_rms
P = S * np.cos(angle_Z_rad)
Q = S * np.sin(angle_Z_rad)
FP = np.cos(angle_Z_rad)
carater = (
    "Indutivo" if Q > 0.01 else "Capacitivo" if Q < -0.01 else "Resistivo Puro"
)

# --- EXIBIÇÃO DOS RESULTADOS ---
st.subheader("📊 Resultados dos Cálculos")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Impedância |Z_eq|", f"{abs_Z:.2f} Ω")
m2.metric("Corrente Total |I|", f"{I_rms:.2f} A")
m3.metric("Potência Ativa (P)", f"{P:.2f} W")
m4.metric("Fator de Potência", f"{FP:.4f}")

# --- DIAGRAMAS VECTORIAIS ---
st.markdown("---")
st.subheader("📐 Diagramas Fasorial e de Potências")
g1, g2 = st.columns(2)

with g1:
    st.markdown("**Diagrama Fasorial (V e I)**")
    fig_fasor, ax_f = plt.subplots(figsize=(4, 4))
    escala_I = (V_fonte / I_rms) * 0.4 if I_rms > 0 else 1.0

    ax_f.quiver(
        0,
        0,
        V_fonte,
        0,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="red",
        label=f"V = {V_fonte:.1f}V ∠0°",
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

    lim = max(V_fonte, abs(I_rms * escala_I)) * 1.2
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
    ax_p.set_xlim(-10, max_v)
    ax_p.set_ylim(-max_v if Q < 0 else -10, max_v if Q >= 0 else 10)
    ax_p.grid(True, linestyle=":", alpha=0.6)
    ax_p.legend(loc="upper left", fontsize=8)
    st.pyplot(fig_pot)

# --- GERADOR DE RELATÓRIO PDF ---
st.markdown("---")
st.subheader("📄 Exportar Relatório PDF")


def gerar_pdf(comps, topologia, v_f, f_f, z_c, i_val, p_val, q_val, s_val, fp_val):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Relatorio Tecnico do Circuito RLC", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True)
    pdf.cell(0, 6, f"Topologia: {topologia}", ln=True)
    pdf.cell(0, 6, f"Fonte CA: {v_f:.2f} V @ {f_f:.2f} Hz", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "Componentes do Circuito:", ln=True)
    pdf.set_font("Arial", size=10)
    for idx, c in enumerate(comps, 1):
        unid = "Ohm" if c["unid"] == "Ω" else c["unid"]
        pdf.cell(
            0,
            5,
            f"  Slot {idx}: {c['tipo']} - Valor: {c['valor']:.2f} {unid}",
            ln=True,
        )

    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "Resultados Calculados:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 5, f"  Impedancia Equivalente: {abs(z_c):.2f} Ohm", ln=True)
    pdf.cell(0, 5, f"  Corrente Total RMS: {i_val:.2f} A", ln=True)
    pdf.cell(0, 5, f"  Potencia Ativa (P): {p_val:.2f} W", ln=True)
    pdf.cell(0, 5, f"  Potencia Reativa (Q): {q_val:.2f} VAR", ln=True)
    pdf.cell(0, 5, f"  Potencia Aparente (S): {s_val:.2f} VA", ln=True)
    pdf.cell(0, 5, f"  Fator de Potencia: {fp_val:.4f}", ln=True)

    return bytes(pdf.output())


pdf_data = gerar_pdf(
    st.session_state.circuito,
    modo_arranjo,
    V_fonte,
    freq_fonte,
    Z_eq,
    I_rms,
    P,
    Q,
    S,
    FP,
)

st.download_button(
    label="📥 Baixar Relatório PDF Completo",
    data=pdf_data,
    file_name=f"relatorio_circuito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
    mime="application/pdf",
    use_container_width=True,
)
