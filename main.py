import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Global LNG Export Plant Simulator")

st.title("🏭 Global LNG Liquefaction Plant Simulator")
st.markdown("Switch locations, choose your liquefaction technology, and manipulate process parameters to see the economic and physical impacts on the plant.")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🌍 Location & Feed")
location = st.sidebar.selectbox("Select Export Terminal", ["Angola LNG (Soyo)", "Qatar LNG (Ras Laffan)", "USA LNG (Sabine Pass)"])
co2_ppm = st.sidebar.slider("Feed CO2 (ppm)", 0, 3000, 1000)
water_ppm = st.sidebar.slider("Feed Water (ppm)", 1, 500, 250)
c3_percent = st.sidebar.slider("Feed C3+ (Richness) %", 1.0, 20.0, 12.0)

st.sidebar.header("⚙️ Liquefaction Technology")
tech = st.sidebar.radio("Select Technology", ["SMR (Single Mixed Refrigerant)", "C3MR (Propane Pre-cooled)", "DMR (Dual Mixed Refrigerant)"], 
                        help="SMR: Low CAPEX, Low Eff. | C3MR: Industry Standard | DMR: High Capacity, High Eff.")

st.sidebar.header("🛠️ Plant Configurations")
n2_injection = st.sidebar.slider("Nitrogen Injection for Wobbe Control (mols)", 0, 15, 0, help="Injects N2 to lower the Wobbe Index of rich gas.")
bypass_dehydration = st.sidebar.checkbox("BYPASS Dehydration (Molecular Sieves)", value=False)
bypass_fractionation = st.sidebar.checkbox("BYPASS NGL Fractionation", value=False)

# ==========================================
# 2. THERMODYNAMIC & ECONOMIC LOGIC
# ==========================================
# Wobbe Index Calculation
final_c3 = c3_percent if bypass_fractionation else max(c3_percent - 8.0, 2.0)
wobbe_index = 48.0 + (final_c3 * 1.5) - (n2_injection * 0.5)

# Efficiency & Power Consumption (kWh/tonne of LNG)
if tech == "SMR (Single Mixed Refrigerant)":
    base_power = 380 # kWh/t
    capex_factor = 1.0
    plant_capacity = 1.5 # MTPA
elif tech == "C3MR (Propane Pre-cooled)":
    base_power = 300 # kWh/t
    capex_factor = 1.5
    plant_capacity = 4.0 # MTPA
else: # DMR
    base_power = 280 # kWh/t
    capex_factor = 1.8
    plant_capacity = 8.0 # MTPA

# Penalties for off-spec conditions
if final_c3 > 8.0: base_power += 20 # Recycle penalties for heavy gas
if wobbe_index > 54.0: base_power += 15 # Injecting N2 or blending

# Financials (Simplified)
lng_price_per_tonne = 600 # USD
daily_production = plant_capacity * 1e6 / 365 # Tonnes per day
daily_power_cost = (daily_production * base_power) * 0.08 # $0.08/kWh
daily_revenue = daily_production * lng_price_per_tonne
daily_profit = daily_revenue - daily_power_cost

# Failure Modes
hydrate_risk = water_ppm > 1.0 and bypass_dehydration
co2_freeze = co2_ppm > 50.0 

# ==========================================
# 3. 3D PLANT GEOMETRY (Detailed)
# ==========================================
fig = go.Figure()

# Helper functions for 3D shapes
def draw_pipe(x0, x1, y, z, color='gray'):
    fig.add_trace(go.Scatter3d(x=[x0, x1], y=[y, y], z=[z, z], mode='lines', line=dict(color=color, width=6), showlegend=False))

def draw_cylinder(x, y, z_base, height, radius, color, opacity=1.0):
    z = np.linspace(z_base, z_base + height, 20)
    theta = np.linspace(0, 2*np.pi, 40)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = x + radius * np.cos(theta_grid)
    y_grid = y + radius * np.sin(theta_grid)
    fig.add_trace(go.Surface(x=x_grid, y=y_grid, z=z_grid, colorscale=[[0, color], [1, color]], showscale=False, opacity=opacity, hoverinfo="skip"))

def draw_box(x, y, z_base, height, width, depth, color, opacity=0.8):
    # Draws a simple 3D box using Mesh3d
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

# --- BUILD THE PROCESS TRAIN ---

# 1. Inlet & Slug Catcher
draw_box(-12, -2, 0, 2, 3, 4, 'gray')
draw_pipe(-12, -8, 0, 0)

# 2. AGRU (Acid Gas Removal)
agru_color = 'red' if co2_freeze else 'green'
draw_box(-8, -2, 0, 4, 3, 4, agru_color)
draw_pipe(-5, -2, 0, 0)

# 3. Dehydration (Molecular Sieves)
dehy_color = 'red' if hydrate_risk else 'blue'
draw_cylinder(-1.5, 0, 0, 5, 1.5, dehy_color)
draw_pipe(0, 2, 0, 0)

# 4. Mercury Removal
draw_cylinder(3, 0, 0, 3, 1.0, 'silver')
draw_pipe(4, 5, 0, 0)

# 5. NGL Fractionation Column
frac_color = 'red' if final_c3 > 8.0 else 'green'
draw_cylinder(6, 0, 0, 8, 1.0, frac_color)
draw_pipe(7, 8, 0, 0)

# 6. Liquefaction Train (The Cold Box)
cold_box_color = 'red' if (co2_freeze or hydrate_risk) else 'cyan'
draw_box(8, -2, 0, 5, 4, 4, cold_box_color)

# 7. Refrigerant Compressors (Based on Tech)
if "SMR" in tech:
    draw_cylinder(9, 3, 0, 3, 1.2, 'orange') # Single compressor
elif "C3MR" in tech:
    draw_cylinder(8.5, 3, 0, 3, 1.0, 'orange') # Propane comp
    draw_cylinder(10, 3, 0, 3, 1.0, 'purple') # MR comp
else: # DMR
    draw_cylinder(8, 3, 0, 3, 1.0, 'orange') 
    draw_cylinder(9.5, 3, 0, 3, 1.0, 'purple')
    draw_cylinder(11, 3, 0, 3, 1.0, 'green')

# 8. Nitrogen Injection Unit (If used)
if n2_injection > 0:
    draw_cylinder(13, 0, 0, 4, 1.0, 'lightblue')

# 9. LNG Storage & Loading
draw_pipe(12, 15, 0, 0)
# LNG Tank 1
draw_cylinder(16, -2, 0, 4, 2.5, 'white')
# LNG Tank 2
draw_cylinder(16, 3, 0, 4, 2.5, 'white')
# Jetty / Loading Arm
draw_pipe(16, 20, 0, 0)
draw_pipe(20, 22, 2, 0)

# Layout
fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-13, 23]),
        yaxis=dict(visible=False, range=[-5, 6]),
        zaxis=dict(visible=False, range=[0, 10]),
        camera=dict(eye=dict(x=0.2, y=-2.5, z=1.0)),
        aspectmode='manual', aspectratio=dict(x=2.5, y=1, z=1)
    ),
    margin=dict(l=0, r=0, b=0, t=0), height=500,
    paper_bgcolor="#e8ecf1"
)

# ==========================================
# 4. DASHBOARD & ECONOMICS
# ==========================================
st.subheader("📊 Plant Operations & Economics")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Plant Capacity", f"{plant_capacity} MTPA", tech.split(" ")[0])
c2.metric("Specific Power", f"{base_power} kWh/t")
c3.metric("Wobbe Index", f"{wobbe_index:.1f} MJ/m³", "Rich" if wobbe_index > 54 else "Lean" if wobbe_index < 45 else "Spec", delta_color="inverse" if wobbe_index > 54 else "normal")
c4.metric("Daily Profit", f"${daily_profit:,.0f}")
c5.metric("Feed Water", f"{water_ppm} ppm", "Frozen" if hydrate_risk else "Safe", delta_color="inverse" if hydrate_risk else "normal")

if hydrate_risk:
    st.error("🚨 **HYDRATE FORMATION!** Dehydration was bypassed. Water entered the cryogenic cold box and froze into ice/hydrates, completely plugging the heat exchangers. Plant has tripped offline.")
elif co2_freeze:
    st.error("🚨 **CO2 FREEZE!** Acid Gas Removal was insufficient. CO2 entered the cold box and froze into dry ice. Heat exchangers are plugged. Plant has tripped offline.")
elif wobbe_index > 54:
    st.warning("⚠️ **OFF-SPEC LNG (RICH):** The gas is too rich. The Wobbe Index is too high for European or SA buyers. You must increase Nitrogen Injection or increase fractionation.")
else:
    st.success("✅ **PLANT ONLINE:** Running optimally. LNG meets global custody transfer specifications.")

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. TECHNOLOGY & ECONOMIC BREAKDOWN
# ==========================================
with st.expander("💰 Liquefaction Technology Economics & Thermodynamics"):
    st.markdown(f"### Currently Selected: **{tech}**")
    if "SMR" in tech:
        st.write("- **Thermodynamics:** Uses one mixed refrigerant cycle (methane/ethane/propane).")
        st.write("- **Pros:** Lower CAPEX (~$600/tonne). Easier to build and operate. Great for remote/modular FLNG.")
        st.write("- **Cons:** Lower thermal efficiency (~320-380 kWh/t). Lower capacity. Harder to optimize for rich gas.")
    elif "C3MR" in tech:
        st.write("- **Thermodynamics:** Propane pre-cools the gas to -35°C, then a Mixed Refrigerant (MR) cools it to -162°C.")
        st.write("- **Pros:** Industry standard (APCI). High efficiency (~300 kWh/t). Reliable. Used in Qatar.")
        st.write("- **Cons:** High CAPEX. Highly complex to start up.")
    else:
        st.write("- **Thermodynamics:** Two separate Mixed Refrigerant cycles (one pre-cooling, one liquefaction).")
        st.write("- **Pros:** Highest capacity (up to 8 MTPA per train). Excellent efficiency (~280 kWh/t) for rich gas. Used by Shell.")
        st.write("- **Cons:** Highest CAPEX. Extreme operational complexity.")

# ==========================================
# 6. LOCATION CONTEXT
# ==========================================
if location == "Angola LNG (Soyo)":
    st.info("**Angola:** The gas here is extremely 'rich' (high C3+). If you don't use the Fractionation Column, your Wobbe Index will spike, and you won't be able to sell it.")
elif location == "Qatar LNG (Ras Laffan)":
    st.info("**Qatar:** The North Field has massive CO2 reserves. The Amine Unit (AGRU) must be maintained at 100% capacity. If you bypass it, the CO2 will freeze and destroy the cold box.")
else:
    st.info("**USA (Sabine Pass):** The gas is very lean. You need less fractionation, but you must watch out for high water content which can quickly freeze in the cold box if the molecular sieves are bypassed.")
