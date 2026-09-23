import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Alocação Interativa de Componentes RLC",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Montagem de Circuito por Arraste (Drag & Drop)")
st.write(
    "Arraste os componentes da bancada à esquerda e solte-os nos slots vagos do circuito à direita."
)

# HTML, CSS e JavaScript unificados para Drag and Drop nativo
drag_drop_html = """
<!DOCTYPE html>
<html>
<head>
<style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f8f9fa;
        margin: 0;
        padding: 10px;
    }
    .container {
        display: flex;
        gap: 30px;
        justify-content: center;
        align-items: flex-start;
    }
    .palette, .circuit-board {
        background: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .palette {
        width: 260px;
    }
    .circuit-board {
        width: 550px;
        background-color: #f4f6f8;
    }
    h3 {
        margin-top: 0;
        color: #2c3e50;
        font-size: 16px;
        border-bottom: 2px solid #3498db;
        padding-bottom: 8px;
    }
    .component {
        padding: 12px 15px;
        margin: 10px 0;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        cursor: grab;
        user-select: none;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.1s, box-shadow 0.1s;
    }
    .component:active {
        cursor: grabbing;
        transform: scale(1.02);
    }
    .resistor { background-color: #e67e22; }
    .indutor { background-color: #2980b9; }
    .capacitor { background-color: #8e44ad; }

    /* Slots de destino no circuito */
    .circuit-grid {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin-top: 20px;
        padding: 20px 0;
        position: relative;
    }
    /* Linha do barramento do circuito */
    .circuit-line {
        position: absolute;
        top: 50%;
        left: 5%;
        right: 5%;
        height: 4px;
        background-color: #34495e;
        z-index: 1;
    }
    .slot {
        width: 130px;
        height: 90px;
        border: 2px dashed #95a5a6;
        border-radius: 10px;
        background-color: #ffffff;
        z-index: 2;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: background-color 0.2s, border-color 0.2s;
    }
    .slot.drag-over {
        background-color: #e8f8f5;
        border-color: #2ecc71;
    }
    .slot-label {
        font-size: 11px;
        color: #7f8c8d;
        margin-bottom: 4px;
        font-weight: bold;
    }
    .reset-btn {
        margin-top: 15px;
        padding: 8px 16px;
        background-color: #e74c3c;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-weight: bold;
    }
    .reset-btn:hover { background-color: #c0392b; }
</style>
</head>
<body>

<div class="container">
    <!-- BANCADA DE COMPONENTES PRÉ-DEFINIDOS -->
    <div class="palette">
        <h3>📦 Componentes Disponíveis</h3>
        <div class="component resistor" draggable="true" id="comp-r1" data-tipo="Resistor" data-valor="100 Ω">
            <span>R1 (Resistor)</span> <span>100 Ω</span>
        </div>
        <div class="component indutor" draggable="true" id="comp-l1" data-tipo="Indutor" data-valor="312 mH">
            <span>L1 (Indutor)</span> <span>312 mH</span>
        </div>
        <div class="component capacitor" draggable="true" id="comp-c1" data-tipo="Capacitor" data-valor="30.01 µF">
            <span>C1 (Capacitor)</span> <span>30.01 µF</span>
        </div>
    </div>

    <!-- ÁREA DO CIRCUITO -->
    <div class="circuit-board">
        <h3>🔌 Esquema do Circuito (Arraste para os Slots)</h3>
        <div class="circuit-grid">
            <div class="circuit-line"></div>
            
            <div class="slot" id="slot-1" ondragover="allowDrop(event)" ondragleave="leaveDrop(event)" ondrop="drop(event)">
                <span class="slot-label">SLOT 1 (Série)</span>
            </div>
            
            <div class="slot" id="slot-2" ondragover="allowDrop(event)" ondragleave="leaveDrop(event)" ondrop="drop(event)">
                <span class="slot-label">SLOT 2 (Ramo A)</span>
            </div>
            
            <div class="slot" id="slot-3" ondragover="allowDrop(event)" ondragleave="leaveDrop(event)" ondrop="drop(event)">
                <span class="slot-label">SLOT 3 (Ramo B)</span>
            </div>
        </div>
        <button class="reset-btn" onclick="resetCircuit()">🔄 Reiniciar Posicionamento</button>
    </div>
</div>

<script>
    function allowDrop(ev) {
        ev.preventDefault();
        ev.currentTarget.classList.add('drag-over');
    }

    function leaveDrop(ev) {
        ev.currentTarget.classList.remove('drag-over');
    }

    document.querySelectorAll('.component').forEach(comp => {
        comp.addEventListener('dragstart', ev => {
            ev.dataTransfer.setData("text/plain", ev.target.id);
        });
    });

    function drop(ev) {
        ev.preventDefault();
        const slot = ev.currentTarget;
        slot.classList.remove('drag-over');
        
        const compId = ev.dataTransfer.getData("text/plain");
        const compElement = document.getElementById(compId);
        
        if (compElement && slot.children.length <= 1) {
            slot.appendChild(compElement);
            compElement.style.margin = "0";
            compElement.style.width = "90%";
        }
    }

    function resetCircuit() {
        const palette = document.querySelector('.palette');
        document.querySelectorAll('.component').forEach(comp => {
            comp.style.margin = "10px 0";
            comp.style.width = "auto";
            palette.appendChild(comp);
        });
    }
</script>

</body>
</html>
"""

# Renderiza a interface dentro do Streamlit
components.html(drag_drop_html, height=350)
