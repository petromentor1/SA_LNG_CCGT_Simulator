import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Industrial LNG Export Simulator")

st.title("🏭 Industrial LNG Liquefaction & Export Simulator")
st.markdown("Use the **Play/Pause** button on the 3D plant to see the gas flow rate. Adjust the **Plant Capacity (MTPA)** and **Technology** to see the economic and physical limitations of your design.")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🌍 Feed Gas & Location")
location = st.sidebar.selectbox("Select Export Terminal", ["Angola LNG (Soyo)", "Qatar LNG (Ras Laffan)", "USA LNG (Sabine Pass)"])

if location == "Angola LNG (Soyo)":
    def_h2s, def_co2, def_h2o, def_c3 = 50, 1500, 200, 12.0
elif location == "Qatar LNG (Ras Laffan)":
    def_h2s, def_co2, def_h2o, def_c3 = 500, 2500, 300, 8.0
else:
    def_h2s, def_co2, def_h2o, def_c3 = 0, 50, 100, 3.0

h2s_ppm = st.sidebar.slider("Feed H2S (ppm)", 0, 1000, def_h2s)
co2_ppm = st.sidebar.slider("Feed CO2 (ppm)", 0, 3000, def_co2)
h2o_ppm = st.sidebar.slider("Feed H2O (ppm)", 1, 500, def_h2o)
c3_percent = st.sidebar.slider("Feed C3+ (Richness) %", 1.0, 20.0, def_c3)

st.sidebar.header("⚙️ Plant Capacity & Tech")
# NEW: MTPA Slider
mtpa = st.sidebar.slider("Plant Capacity (MTPA)", 0.5, 10.0, 4.0, 0.1, help="Maximum capacity per train. SMR maxes out at 2, C3MR at 6, DMR at 10+.")

# Dynamic Technology Recommendation based on MTPA
if mtpa <= 2.0:
    default_tech = "SMR (Single Mixed Refrigerant)"
elif mtpa <= 6.0:
    default_tech = "C3MR (Propane Pre-cooled)"
else:
    default_tech = "DMR (Dual Mixed Refrigerant)"

tech = st.sidebar.radio("Select Liquefaction Technology", 
    ["SMR (Single Mixed Refrigerant)", "C3MR (Propane Pre-cooled)", "DMR (Dual Mixed Refrigerant)"], 
    index=["SMR (Single Mixed Refrigerant)", "C3MR (Propane Pre-cooled)", "DMR (Dual Mixed Refrigerant)"].index(default_tech),
    help="The technology must match the plant capacity. For example, SMR cannot handle 8 MTPA.")

st.sidebar.header("🛠️ Bypass & Operations")
n2_injection = st.sidebar.slider("Nitrogen Injection (Wobbe Control)", 0, 15, 0)
bypass_agru = st.sidebar.checkbox("BYPASS Acid Gas Removal (AGRU)", value=False)
bypass_dehy = st.sidebar.checkbox("BYPASS Dehydration (Mole Sieves)", value=False)
bypass_frac = st.sidebar.checkbox("BYPASS Fractionation (NGL Extraction)", value=False)

# ==========================================
# 2. THERMODYNAMIC & ECONOMIC LOGIC
# ==========================================
final_h2s = h2s_ppm if bypass_agru else min(h2s_ppm, 4.0)
final_co2 = co2_ppm if bypass_agru else min(co2_ppm, 50.0)
final_h2o = h2o_ppm if bypass_dehy else min(h2o_ppm, 0.1)

final_c3 = c3_percent if bypass_frac else max(c3_percent - 8.0, 2.0)
wobbe_index = 48.0 + (final_c3 * 1.5) - (n2_injection * 0.5)
heating_value = 45.0 + (final_c3 * 0.8)

# Tech Efficiency & Limits
if "SMR" in tech:
    power_per_tonne, capex_factor, max_cap = 400, 1.0, 2.0
elif "C3MR" in tech:
    power_per_tonne, capex_factor, max_cap = 300, 1.5, 6.0
else:
    power_per_tonne, capex_factor, max_cap = 280, 1.8, 10.0

if final_c3 > 8.0: power_per_tonne += 20 # Recycle penalty
if wobbe_index > 54.0: power_per_tonne += 15 # N2 blending penalty

# Financials
daily_tonnes = mtpa * 1e6 / 365
daily_power_cost = (daily_tonnes * power_per_tonne) * 0.08
daily_revenue = daily_tonnes * 600 # $600/tonne
daily_profit = daily_revenue - daily_power_cost

# Failures & Warnings
h2s_fail = final_h2s > 4.0
co2_fail = final_co2 > 50.0
h2o_fail = final_h2o > 0.1
plant_tripped = h2s_fail or co2_fail or h2o_fail
tech_mismatch = mtpa > max_cap

# ==========================================
# 3. 3D PLANT GEOMETRY & LABELS
# ==========================================
def draw_pipe(x0, x1, y, z, color='#4B5563'):
    return go.Scatter3d(x=[x0, x1], y=[y, y], z=[z, z], mode='lines', line=dict(color=color, width=8), showlegend=False)

def draw_cylinder(x, y, z_base, height, radius, color, opacity=1.0):
    z = np.linspace(z_base, z_base + height, 20)
    theta = np.linspace(0, 2*np.pi, 40)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = x + radius * np.cos(theta_grid)
    y_grid = y + radius * np.sin(theta_grid)
    return go.Surface(x=x_grid, y=y_grid, z=z_grid, colorscale=[[0, color], [1, color]], showscale=False, opacity=opacity, hoverinfo="skip")

def draw_box(x, y, z_base, height, width, depth, color, opacity=0.8):
    vertices = [
        (x, y, z_base), (x+width, y, z_base), (x+width, y+depth, z_base), (x, y+depth, z_base),
        (x, y, z_base+height), (x+width, y, z_base+height), (x+width, y+depth, z_base+height), (x, y+depth, z_base+height)
    ]
    i = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6]
    j = [1, 2, 2, 5, 3, 6, 0, 7, 5, 6, 6, 7]
    k = [2, 3, 5, 6, 6, 7, 7, 4, 6, 7, 1, 2]
    return go.Mesh3d(x=[v[0] for v in vertices], y=[v[1] for v in vertices], z=[v[2] for v in vertices], i=i, j=j, k=k, color=color, opacity=opacity, hoverinfo="skip")

def add_label(x, y, z, text):
    return go.Scatter3d(x=[x], y=[y], z=[z], mode='text', text=[text], textfont=dict(size=12, color='black', family='Arial'), showlegend=False)

# --- Static Plant Geometry ---
static_traces = []
static_traces.append(draw_pipe(-15, -12, 0, 0))
static_traces.append(draw_box(-18, -2, 0, 2, 3, 4, '#9CA3AF')) # Slug Catcher
static_traces.append(add_label(-16.5, 0, 3, "Slug Catcher"))

static_traces.append(draw_pipe(-9, -6, 0, 0))
static_traces.append(draw_box(-12, -2, 0, 5, 3, 4, '#EF4444' if bypass_agru else '#10B981')) # AGRU
static_traces.append(add_label(-10.5, 0, 6, "AGRU (Amine)"))

static_traces.append(draw_pipe(-3.5, -1, 0, 0))
static_traces.append(draw_cylinder(-5, 0, 0, 6, 1.5, '#EF4444' if bypass_dehy else '#3B82F6')) # Mole Sieves
static_traces.append(add_label(-5, 0, 7, "Mole Sieves"))

static_traces.append(draw_pipe(1, 3, 0, 0))
static_traces.append(draw_cylinder(0, 0, 0, 4, 1.0, '#9CA3AF')) # Hg Removal
static_traces.append(add_label(0, 0, 5, "Hg Removal"))

static_traces.append(draw_pipe(5.2, 7, 0, 0))
static_traces.append(draw_cylinder(4, 0, 0, 9, 1.2, '#EF4444' if (final_c3 > 8.0 and not bypass_frac) else '#10B981')) # Fractionation
static_traces.append(add_label(4, 0, 10, "Fractionation"))

# --- Tech-Specific Cold Boxes ---
cold_box_color = '#EF4444' if plant_tripped else '#06B6D4'
if "SMR" in tech:
    static_traces.append(draw_box(7, -2.5, 0, 6, 5, 5, cold_box_color))
    static_traces.append(add_label(9.5, 0, 7, "SMR Cold Box"))
    static_traces.append(draw_cylinder(9.5, 3.5, 0, 4, 1.2, '#F59E0B'))
    static_traces.append(add_label(9.5, 3.5, 5, "Single MR Compressor"))
elif "C3MR" in tech:
    # Propane Pre-cool Box + Main MR Box
    static_traces.append(draw_box(7, -2.5, 0, 4, 2.5, 5, '#F97316')) # Pre-cool
    static_traces.append(add_label(8.25, 0, 5, "Propane Cooler"))
    static_traces.append(draw_box(9.5, -2.5, 0, 6, 2.5, 5, cold_box_color)) # Liquefaction
    static_traces.append(add_label(10.75, 0, 7, "MR Cold Box"))
    static_traces.append(draw_cylinder(8.25, 3.5, 0, 4, 1.0, '#F59E0B'))
    static_traces.append(draw_cylinder(10.75, 3.5, 0, 4, 1.0, '#8B5CF6'))
    static_traces.append(add_label(9.5, 3.5, 5, "Propane & MR Compressors"))
else: # DMR
    # Pre-cool MR + Liquefaction MR + Sub-cool MR
    static_traces.append(draw_box(7, -2.5, 0, 4, 1.8, 5, '#F97316')) # Pre-cool
    static_traces.append(add_label(7.9, 0, 5, "MR-1 Pre-cool"))
    static_traces.append(draw_box(9, -2.5, 0, 5, 1.8, 5, cold_box_color)) # Liquefaction
    static_traces.append(add_label(9.9, 0, 6, "MR-2 Liquefaction"))
    static_traces.append(draw_box(11, -2.5, 0, 6, 1.8, 5, '#1E3A8A')) # Sub-cool
    static_traces.append(add_label(11.9, 0, 7, "MR-3 Sub-cool"))
    static_traces.append(draw_cylinder(7.9, 3.5, 0, 4, 1.0, '#F59E0B'))
    static_traces.append(draw_cylinder(9.9, 3.5, 0, 4, 1.0, '#8B5CF6'))
    static_traces.append(draw_cylinder(11.9, 3.5, 0, 4, 1.0, '#10B981'))
    static_traces.append(add_label(9.9, 3.5, 5, "DMR Compressors"))

if n2_injection > 0:
    static_traces.append(draw_cylinder(13.5, 0, 0, 4, 1.0, '#93C5FD'))
    static_traces.append(add_label(13.5, 0, 5, "N2 Injection"))

static_traces.append(draw_pipe(13, 16, 0, 0))
static_traces.append(draw_cylinder(17, -3, 0, 5, 2.5, '#F3F4F6')) # Tank 1
static_traces.append(draw_cylinder(17, 3, 0, 5, 2.5, '#F3F4F6'))  # Tank 2
static_traces.append(add_label(17, -3, 6, "LNG Tank 1"))
static_traces.append(add_label(17, 3, 6, "LNG Tank 2"))

static_traces.append(draw_pipe(19.5, 22, 0, 0))
static_traces.append(draw_box(22, -1, 0, 1, 3, 2, '#4B5563'))
static_traces.append(add_label(23.5, 0, 2, "Loading Jetty"))

# Flare
static_traces.append(draw_cylinder(10, -6, 0, 10, 0.3, '#EF4444' if (bypass_agru and (h2s_ppm > 4 or co2_ppm > 50)) else '#9CA3AF'))
static_traces.append(add_label(10, -6, 11, "Flare Stack"))

static_traces.append(draw_box(-15, 4, 0, 2, 4, 4, '#D1D5DB'))
static_traces.append(add_label(-13, 6, 3, "Control Room"))

# ==========================================
# 4. ANIMATION FRAMES (The Flow)
# ==========================================
frames = []
num_frames = 40
# Speed of flow depends on MTPA
speed_factor = mtpa * 0.2 

for i in range(num_frames):
    frame_traces = static_traces.copy()
    
    # Animate a particle moving through the train
    t = (i / num_frames)
    # Path: 0 to 1 mapped to x: -18 to 23
    x_pos = -18 + (t * 41)
    y_pos = 0
    z_pos = 0.5
    
    # Change particle color to simulate cooling
    if x_pos < 7:
        p_color = '#EF4444' # Hot Gas (Red)
        p_size = 10
    elif x_pos < 10:
        p_color = '#F59E0B' # Pre-cooled (Orange)
        p_size = 12
    elif x_pos < 13:
        p_color = '#06B6D4' # Liquefied (Cyan)
        p_size = 14
    else:
        p_color = '#1E3A8A' # Sub-cooled LNG (Dark Blue)
        p_size = 16
        
    particle = go.Scatter3d(
        x=[x_pos], y=[y_pos], z=[z_pos], 
        mode='markers', 
        marker=dict(size=p_size, color=p_color, symbol='circle'),
        name='Gas Particle'
    )
    frame_traces.append(particle)
    
    # Add secondary particle for continuous flow effect
    x_pos2 = -18 + ((t + 0.5) % 1.0) * 41
    particle2 = go.Scatter3d(
        x=[x_pos2], y=[y_pos], z=[z_pos], 
        mode='markers', 
        marker=dict(size=p_size, color=p_color, symbol='circle'),
        showlegend=False
    )
    frame_traces.append(particle2)
    
    frames.append(go.Frame(data=frame_traces, name=str(i)))

# ==========================================
# 5. BUILD THE FIGURE
# ==========================================
fig = go.Figure(data=frames[0].data, frames=frames)

fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-19, 25]),
        yaxis=dict(visible=False, range=[-7, 7]),
        zaxis=dict(visible=False, range=[0, 12]),
        camera=dict(eye=dict(x=0.3, y=-2.2, z=0.8)),
        aspectmode='manual', aspectratio=dict(x=2.2, y=1, z=0.8)
    ),
    updatemenus=[dict(
        type="buttons", showactive=False, x=0.1, y=0,
        buttons=[
            dict(label="▶️ Play Flow", method="animate", 
                 args=[None, dict(frame=dict(duration=80, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="⏸️ Pause", method="animate", 
                 args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])
        ]
    )],
    margin=dict(l=0, r=0, b=0, t=0), height=600,
    paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC"
)

# ==========================================
# 6. DASHBOARD & ALARMS
# ==========================================
st.subheader("📊 Process Specifications & Economics")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("H2S", f"{final_h2s:.1f} ppm", "Fail" if h2s_fail else "Pass", delta_color="inverse")
c2.metric("CO2", f"{final_co2:.0f} ppm", "Fail" if co2_fail else "Pass", delta_color="inverse")
c3.metric("H2O", f"{final_h2o:.2f} ppm", "Fail" if h2o_fail else "Pass", delta_color="inverse")
c4.metric("Wobbe Index", f"{wobbe_index:.1f} MJ/m³", "Off-Spec" if (wobbe_index > 54 or wobbe_index < 45) else "Spec")
c5.metric("Plant Size", f"{mtpa} MTPA")
c6.metric("Daily Profit", f"${daily_profit:,.0f}")

if tech_mismatch:
    st.error(f"🚨 **TECHNOLOGY MISMATCH:** You selected {tech} but the plant capacity is {mtpa} MTPA. The maximum capacity for {tech.split(' ')[0]} is {max_cap} MTPA. You must use a larger technology (like C3MR or DMR) to process this volume.")
elif plant_tripped:
    st.error("🚨 **CRITICAL FAILURE:** Specifications exceeded. The cryogenic cold box has frozen. Plant tripped, Flare Stack ignited.")
elif wobbe_index > 54:
    st.warning("⚠️ **WARNING:** Rich LNG. Wobbe Index exceeds 54 MJ/m³. Increase Nitrogen Injection or enable Fractionation.")
else:
    st.success("✅ **PLANT OPTIMAL:** Specs met. LNG ready for custody transfer.")

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. DETAILED TECHNICAL CONTEXT
# ==========================================
with st.expander("📖 Full Plant Equipment & Engineering Context"):
    st.markdown(f"""
    **Current Configuration:** {location} | {tech} | {mtpa} MTPA
    *   **Slug Catcher:** Removes liquid water and condensate from raw well fluid.
    *   **AGRU (Acid Gas Removal Unit):** Uses MDEA to absorb H2S and CO2. If bypassed, acid gases enter the cold box, freeze (dry ice), and plug the plant.
    *   **Mole Sieves (Dehydration):** Removes water to <0.1 ppm. If bypassed, hydrates form instantly at cryogenic temperatures.
    *   **Mercury Removal:** Sulfur-impregnated carbon beds. Prevents amalgamation with aluminum heat exchangers.
    *   **Fractionation Column:** Removes C3+ (propane and heavier). If bypassed, the LNG becomes too "rich," resulting in a high Wobbe Index.
    *   **Liquefaction Tech:** 
        *   *SMR:* 1 mixed refrigerant cycle. Best for <2 MTPA. Low CAPEX, low efficiency.
        *   *C3MR:* Propane pre-cooling + MR liquefaction. Best for 2-6 MTPA. The industry standard.
        *   *DMR:* Dual MR cycles. Best for >6 MTPA. Highest efficiency, highest CAPEX.
    *   **Compressors:** The technology determines the number of compressor trains. SMR uses 1, C3MR uses 2, and DMR uses 3 to achieve the same cooling.
    """)
