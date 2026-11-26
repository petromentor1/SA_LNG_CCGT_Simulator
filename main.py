import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Industrial LNG Export Simulator")

st.title("🏭 Industrial LNG Liquefaction & Export Simulator")
st.markdown("Select the location, technology, and process settings. The 3D plant will react to your configuration. Labels identify every major unit operation.")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🌍 Feed Gas & Location")
location = st.sidebar.selectbox("Select Export Terminal", ["Angola LNG (Soyo)", "Qatar LNG (Ras Laffan)", "USA LNG (Sabine Pass)"])

# Dynamic defaults based on location
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

st.sidebar.header("⚙️ Technology & Plant Design")
tech = st.sidebar.radio("Select Liquefaction Technology", 
    ["SMR (Single Mixed Refrigerant)", "C3MR (Propane Pre-cooled)", "DMR (Dual Mixed Refrigerant)"], 
    help="SMR: Low CAPEX, Low Eff. | C3MR: Industry Standard | DMR: High Capacity, High Eff.")

st.sidebar.header("🛠️ Bypass & Operations")
n2_injection = st.sidebar.slider("Nitrogen Injection (Wobbe Control)", 0, 15, 0)
bypass_agru = st.sidebar.checkbox("BYPASS Acid Gas Removal (AGRU)", value=False)
bypass_dehy = st.sidebar.checkbox("BYPASS Dehydration (Mole Sieves)", value=False)
bypass_frac = st.sidebar.checkbox("BYPASS Fractionation (NGL Extraction)", value=False)

# ==========================================
# 2. THERMODYNAMIC & PROCESS LOGIC
# ==========================================
# Product Specs after processing
final_h2s = h2s_ppm if bypass_agru else min(h2s_ppm, 4.0) # Spec is <4 ppm
final_co2 = co2_ppm if bypass_agru else min(co2_ppm, 50.0) # Spec is <50 ppm
final_h2o = h2o_ppm if bypass_dehy else min(h2o_ppm, 0.1)  # Spec is <0.1 ppm

# Heavy Hydrocarbons & Wobbe Index
final_c3 = c3_percent if bypass_frac else max(c3_percent - 8.0, 2.0)
wobbe_index = 48.0 + (final_c3 * 1.5) - (n2_injection * 0.5)
heating_value = 45.0 + (final_c3 * 0.8) # MJ/kg

# Efficiency & Power
if "SMR" in tech:
    base_power, capex, cap_mtpa = 400, 1.0, 1.5
elif "C3MR" in tech:
    base_power, capex, cap_mtpa = 300, 1.5, 4.0
else:
    base_power, capex, cap_mtpa = 280, 1.8, 8.0

if final_c3 > 8.0: base_power += 20 # Recycle penalty
if wobbe_index > 54.0: base_power += 15 # N2 blending penalty

# Financials
daily_tonnes = cap_mtpa * 1e6 / 365
daily_power_cost = (daily_tonnes * base_power) * 0.08
daily_revenue = daily_tonnes * 600 # $600/tonne
daily_profit = daily_revenue - daily_power_cost

# Failure Modes
h2s_fail = final_h2s > 4.0
co2_fail = final_co2 > 50.0
h2o_fail = final_h2o > 0.1
plant_tripped = h2s_fail or co2_fail or h2o_fail

# ==========================================
# 3. 3D PLANT GEOMETRY & LABELS
# ==========================================
fig = go.Figure()

# --- Helper functions ---
def draw_pipe(x0, x1, y, z, color='#4B5563'):
    fig.add_trace(go.Scatter3d(x=[x0, x1], y=[y, y], z=[z, z], mode='lines', line=dict(color=color, width=8), showlegend=False))

def draw_cylinder(x, y, z_base, height, radius, color, opacity=1.0):
    z = np.linspace(z_base, z_base + height, 20)
    theta = np.linspace(0, 2*np.pi, 40)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = x + radius * np.cos(theta_grid)
    y_grid = y + radius * np.sin(theta_grid)
    fig.add_trace(go.Surface(x=x_grid, y=y_grid, z=z_grid, colorscale=[[0, color], [1, color]], showscale=False, opacity=opacity, hoverinfo="skip"))

def draw_box(x, y, z_base, height, width, depth, color, opacity=0.8):
    vertices = [
        (x, y, z_base), (x+width, y, z_base), (x+width, y+depth, z_base), (x, y+depth, z_base),
        (x, y, z_base+height), (x+width, y, z_base+height), (x+width, y+depth, z_base+height), (x, y+depth, z_base+height)
    ]
    i = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6]
    j = [1, 2, 2, 5, 3, 6, 0, 7, 5, 6, 6, 7]
    k = [2, 3, 5, 6, 6, 7, 7, 4, 6, 7, 1, 2]
    x_vals = [v[0] for v in vertices]
    y_vals = [v[1] for v in vertices]
    z_vals = [v[2] for v in vertices]
    fig.add_trace(go.Mesh3d(x=x_vals, y=y_vals, z=z_vals, i=i, j=j, k=k, color=color, opacity=opacity, hoverinfo="skip"))

def add_label(x, y, z, text):
    fig.add_trace(go.Scatter3d(x=[x], y=[y], z=[z], mode='text', text=[text], textfont=dict(size=12, color='black', family='Arial'), showlegend=False))

# --- BUILD THE PROCESS TRAIN ---

# 1. Slug Catcher & Feed
draw_box(-18, -2, 0, 2, 3, 4, '#9CA3AF')
add_label(-16.5, 0, 3, "Slug Catcher")
draw_pipe(-15, -12, 0, 0)

# 2. AGRU (Acid Gas Removal)
agru_color = '#EF4444' if bypass_agru else '#10B981'
draw_box(-12, -2, 0, 5, 3, 4, agru_color)
add_label(-10.5, 0, 6, "AGRU (Amine)")
draw_pipe(-9, -6, 0, 0)

# 3. Dehydration (Mole Sieves)
dehy_color = '#EF4444' if bypass_dehy else '#3B82F6'
draw_cylinder(-5, 0, 0, 6, 1.5, dehy_color)
add_label(-5, 0, 7, "Mole Sieves")
draw_pipe(-3.5, -1, 0, 0)

# 4. Mercury Removal
draw_cylinder(0, 0, 0, 4, 1.0, '#9CA3AF')
add_label(0, 0, 5, "Hg Removal")
draw_pipe(1, 3, 0, 0)

# 5. NGL Fractionation Column
frac_color = '#EF4444' if (final_c3 > 8.0 and not bypass_frac) else '#10B981'
draw_cylinder(4, 0, 0, 9, 1.2, frac_color)
add_label(4, 0, 10, "Fractionation")
draw_pipe(5.2, 7, 0, 0)

# 6. Liquefaction Cold Box
cold_box_color = '#EF4444' if plant_tripped else '#06B6D4'
draw_box(7, -2.5, 0, 6, 5, 5, cold_box_color)
add_label(9.5, 0, 7, "Cryogenic Cold Box")

# 7. Refrigerant Compressors (Tech specific)
if "SMR" in tech:
    draw_cylinder(8, 3.5, 0, 4, 1.2, '#F59E0B')
    add_label(8, 3.5, 5, "SMR Compressor")
elif "C3MR" in tech:
    draw_cylinder(7.5, 3.5, 0, 4, 1.0, '#F59E0B')
    draw_cylinder(9.5, 3.5, 0, 4, 1.0, '#8B5CF6')
    add_label(8.5, 3.5, 5, "C3/MR Compressors")
else:
    draw_cylinder(7, 3.5, 0, 4, 1.0, '#F59E0B')
    draw_cylinder(9, 3.5, 0, 4, 1.0, '#8B5CF6')
    draw_cylinder(11, 3.5, 0, 4, 1.0, '#10B981')
    add_label(9, 3.5, 5, "DMR Compressors")

# 8. Nitrogen Injection (If used)
if n2_injection > 0:
    draw_cylinder(13, 0, 0, 4, 1.0, '#93C5FD')
    add_label(13, 0, 5, "N2 Injection")

# 9. LNG Storage & Loading
draw_pipe(12, 15, 0, 0)
draw_cylinder(17, -3, 0, 5, 2.5, '#F3F4F6') # Tank 1
draw_cylinder(17, 3, 0, 5, 2.5, '#F3F4F6')  # Tank 2
add_label(17, -3, 6, "LNG Tank 1")
add_label(17, 3, 6, "LNG Tank 2")
draw_pipe(19.5, 22, 0, 0)

# Jetty & Loading Arm
draw_box(22, -1, 0, 1, 3, 2, '#4B5563')
add_label(23.5, 0, 2, "Loading Jetty")

# Flare Stack (Goes red if AGRU bypassed)
flare_color = '#EF4444' if (bypass_agru and (h2s_ppm > 4 or co2_ppm > 50)) else '#9CA3AF'
draw_cylinder(10, -6, 0, 10, 0.3, flare_color)
add_label(10, -6, 11, "Flare Stack")

# Control Room
draw_box(-15, 4, 0, 2, 4, 4, '#D1D5DB')
add_label(-13, 6, 3, "Control Room")

# Layout
fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-19, 25]),
        yaxis=dict(visible=False, range=[-7, 7]),
        zaxis=dict(visible=False, range=[0, 12]),
        camera=dict(eye=dict(x=0.3, y=-2.2, z=0.8)),
        aspectmode='manual', aspectratio=dict(x=2.2, y=1, z=0.8)
    ),
    margin=dict(l=0, r=0, b=0, t=0), height=600,
    paper_bgcolor="#F8FAFC", plot_bgcolor="#F8FAFC"
)

# ==========================================
# 4. DASHBOARD & ALARMS
# ==========================================
st.subheader("📊 Process Specifications & Economics")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("H2S", f"{final_h2s:.1f} ppm", "Fail" if h2s_fail else "Pass", delta_color="inverse")
c2.metric("CO2", f"{final_co2:.0f} ppm", "Fail" if co2_fail else "Pass", delta_color="inverse")
c3.metric("H2O", f"{final_h2o:.2f} ppm", "Fail" if h2o_fail else "Pass", delta_color="inverse")
c4.metric("Wobbe Index", f"{wobbe_index:.1f} MJ/m³", "Off-Spec" if (wobbe_index > 54 or wobbe_index < 45) else "Spec")
c5.metric("Heating Value", f"{heating_value:.1f} MJ/kg")
c6.metric("Daily Profit", f"${daily_profit:,.0f}")

if plant_tripped:
    st.error("🚨 **CRITICAL FAILURE:** Specifications exceeded. The cryogenic cold box has frozen (Hydrates or Dry Ice). The plant has tripped, and the Flare Stack is ignited to burn off inventory.")
elif wobbe_index > 54:
    st.warning("⚠️ **WARNING:** Rich LNG. Wobbe Index exceeds 54 MJ/m³. Increase Nitrogen Injection or enable Fractionation.")
elif wobbe_index < 45:
    st.warning("⚠️ **WARNING:** Lean LNG. Wobbe Index too low. Reduce Nitrogen injection.")
else:
    st.success("✅ **PLANT OPTIMAL:** All specs met. LNG is ready for custody transfer.")

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. DETAILED TECHNICAL CONTEXT
# ==========================================
with st.expander("📖 Full Plant Equipment & Engineering Context"):
    st.markdown(f"""
    **Current Configuration:** {location} | {tech}
    *   **Slug Catcher:** Removes liquid water and condensate from raw well fluid.
    *   **AGRU (Acid Gas Removal Unit):** Uses MDEA (Methyl Diethanolamine) to absorb H2S and CO2. If you bypass this, acid gases enter the cold box, freeze (dry ice), and plug the plant.
    *   **Mole Sieves (Dehydration):** Removes water to <0.1 ppm. If bypassed, hydrates (ice-like structures) form instantly at cryogenic temperatures, causing catastrophic plugging.
    *   **Mercury Removal:** Uses sulfur-impregnated carbon beds. If mercury slips through, it amalgamates with the aluminum plate-fin heat exchangers in the cold box, causing rapid corrosion.
    *   **Fractionation Column:** Removes C3+ (propane and heavier). If bypassed, the LNG becomes too "rich," resulting in a high Wobbe Index that makes it unusable for standard European or SA gas turbines.
    *   **Cold Box:** The heart of the plant. Uses multi-stream cryogenic heat exchangers to cool the gas to -162°C.
    *   **Compressors:** The technology you chose ({tech}) determines the number of compressor trains required. SMR uses 1, C3MR uses 2, and DMR uses 3 or more to achieve the same cooling.
    """)
