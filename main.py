import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Global LNG Export Plant Simulator")

st.title("🏭 Global LNG Liquefaction Plant Simulator (Angola / Qatar / USA)")
st.markdown("Toggle the plant configurations and feed qualities to see how the 3D process train reacts, and how it impacts the final LNG product specifications.")

# ==========================================
# 1. SIDEBAR CONTROLS (Locations & Toggles)
# ==========================================
st.sidebar.header("🌍 Feed Gas Origin")
location = st.sidebar.selectbox("Select Export Terminal Location", ["Angola LNG (Soyo)", "Qatar LNG (Ras Laffan)", "USA LNG (Sabine Pass)"])
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Plant Operations (Bypasses)")
# Toggles to simulate equipment failure or bypass
bypass_amine = st.sidebar.checkbox("BYPASS Acid Gas Removal (Amine)", value=False, help="If bypassed, CO2 and H2S enter the cryogenic cold box.")
bypass_fractionation = st.sidebar.checkbox("BYPASS NGL Fractionation", value=False, help="If bypassed, heavy hydrocarbons (C3+) remain in the LNG, spiking the Wobbe Index.")

# Default feed qualities based on location
if location == "Angola LNG (Soyo)":
    default_co2 = 150 # ppm (needs treatment)
    default_c3 = 12.0 # % (Rich gas)
    default_n2 = 0.5
elif location == "Qatar LNG (Ras Laffan)":
    default_co2 = 2500 # ppm (Very sour)
    default_c3 = 8.0
    default_n2 = 0.8
else: # USA
    default_co2 = 50 # ppm (Sweet)
    default_c3 = 3.0 # % (Lean)
    default_n2 = 2.5 # High Nitrogen

st.sidebar.markdown("---")
st.sidebar.header("🧪 Raw Feed Composition")
co2_ppm = st.sidebar.slider("Feed CO2 (ppm)", 0, 3000, default_co2)
c3_percent = st.sidebar.slider("Feed C3+ (Propane & Heavier) %", 1.0, 20.0, default_c3)
n2_percent = st.sidebar.slider("Feed Nitrogen (N2) %", 0.1, 5.0, default_n2)

# ==========================================
# 2. THERMODYNAMIC & PROCESS LOGIC
# ==========================================
# Ideal LNG specs: Wobbe Index ~ 50-52 MJ/m3, CO2 < 50 ppm
# Calculate final product specs based on toggles
final_co2 = co2_ppm if bypass_amine else min(co2_ppm, 50)
final_c3 = c3_percent if bypass_fractionation else max(c3_percent - 8.0, 2.0) # Fractionation removes C3
final_n2 = n2_percent # Nitrogen usually stays in LNG unless specifically rejected

# Simplified Wobbe Index Calculation (Higher C3 = Higher Wobbe, Higher N2 = Lower Wobbe)
wobbe_index = 48.0 + (final_c3 * 1.5) - (final_n2 * 2.0)

# Determine Plant Status
plant_status = "🟢 Optimal"
cold_box_status = "Normal"
spec_status = "In Spec"

if final_co2 > 50:
    cold_box_status = "FROZEN"
    plant_status = "🔴 SHUTDOWN"
elif wobbe_index > 54.0:
    spec_status = "OFF-SPEC (Rich)"
elif wobbe_index < 45.0:
    spec_status = "OFF-SPEC (Lean)"

# ==========================================
# 3. 3D PLANT GEOMETRY GENERATOR
# ==========================================
# Helper function to draw cylinders (columns) and boxes
def create_cylinder(x, y, z_base, height, radius, color):
    z = np.linspace(z_base, z_base + height, 20)
    theta = np.linspace(0, 2*np.pi, 40)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = x + radius * np.cos(theta_grid)
    y_grid = y + radius * np.sin(theta_grid)
    return go.Surface(x=x_grid, y=y_grid, z=z_grid, colorscale=[[0, color], [1, color]], showscale=False, hoverinfo="skip")

def create_box(x, y, z_base, height, width, depth, color):
    x_vals = [x, x+width, x+width, x, x]
    y_vals = [y, y, y+depth, y+depth, y]
    # Draw 4 walls
    traces = []
    for i in range(4):
        traces.append(go.Mesh3d(
            x=[x_vals[i], x_vals[i+1], x_vals[i+1], x_vals[i]],
            y=[y_vals[i], y_vals[i+1], y_vals[i+1], y_vals[i]],
            z=[z_base, z_base, z_base+height, z_base+height],
            color=color, opacity=0.5, hoverinfo="skip"
        ))
    return traces

# Build the 3D Scene
fig = go.Figure()

# 1. Feed Gas Pipeline (Gray)
fig.add_trace(go.Scatter3d(x=[-10, -5], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='gray', width=8), name="Feed Gas"))

# 2. Acid Gas Removal (Amine Unit) - Box
amine_color = 'red' if bypass_amine else 'green'
fig.add_trace(go.Mesh3d(x=[-4, -1, -1, -4], y=[-1, -1, 1, 1], z=[0, 0, 2, 2], color=amine_color, opacity=0.8, name="Amine Unit"))
fig.add_trace(go.Scatter3d(x=[-5, -4], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='gray', width=8), showlegend=False))

# 3. Dehydration & Mercury Removal - Short Cylinder
fig.add_trace(go.Scatter3d(x=[-1, 1], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='gray', width=8), showlegend=False))
fig.add_trace(create_cylinder(x=1.5, y=0, z_base=0, height=3, radius=0.5, color='blue'))

# 4. Fractionation Column (NGL Extraction) - Tall Cylinder
frac_color = 'red' if bypass_fractionation else 'green'
fig.add_trace(go.Scatter3d(x=[2, 5], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='gray', width=8), showlegend=False))
fig.add_trace(create_cylinder(x=6, y=0, z_base=0, height=6, radius=0.8, color=frac_color))

# 5. Cryogenic Cold Box (Main Liquefaction) - Big Box
cold_box_color = 'red' if final_co2 > 50 else 'cyan'
fig.add_trace(go.Scatter3d(x=[7, 10], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='gray', width=8), showlegend=False))
for trace in create_box(x=11, y=-1.5, z_base=0, height=4, width=3, depth=3, color=cold_box_color):
    fig.add_trace(trace)

# 6. LNG Storage Tank (Dome Tank)
fig.add_trace(go.Scatter3d(x=[14, 17], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='blue', width=8), showlegend=False))
# Tank Body
fig.add_trace(create_cylinder(x=19, y=0, z_base=0, height=3, radius=2, color='white'))
# Tank Dome
u = np.linspace(0, 2*np.pi, 40); v = np.linspace(0, np.pi/2, 10)
u_g, v_g = np.meshgrid(u, v)
x_dome = 19 + 2 * np.cos(u_g) * np.sin(v_g)
y_dome = 0 + 2 * np.sin(u_g) * np.sin(v_g)
z_dome = 3 + 1.5 * np.cos(v_g)
fig.add_trace(go.Surface(x=x_dome, y=y_dome, z=z_dome, colorscale=[[0, 'silver'], [1, 'silver']], showscale=False))

# Layout Adjustments
fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-11, 22]),
        yaxis=dict(visible=False, range=[-5, 5]),
        zaxis=dict(visible=False, range=[0, 10]),
        camera=dict(eye=dict(x=0.5, y=-2.0, z=0.8)),
        aspectmode='manual', aspectratio=dict(x=2, y=1, z=1)
    ),
    margin=dict(l=0, r=0, b=0, t=0), height=500, showlegend=False,
    paper_bgcolor="#f4f4f4"
)

# ==========================================
# 4. DASHBOARD & ALERTS
# ==========================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Plant Status", plant_status)
col2.metric("Final CO2", f"{final_co2} ppm", delta="- Danger" if final_co2 > 50 else "Safe", delta_color="inverse")
col3.metric("LNG Wobbe Index", f"{wobbe_index:.1f} MJ/m³", delta=f"{wobbe_index - 50:.1f} vs Ideal", delta_color="inverse")
col4.metric("Product Spec", spec_status)

if final_co2 > 50:
    st.error(f"🚨 **CRITICAL FAILURE:** CO2 levels are at {final_co2} ppm. At temperatures below -56°C, CO2 forms dry ice. The cryogenic cold box (highlighted in RED) has frozen solid and plugged. The plant has tripped.")
elif spec_status == "OFF-SPEC (Rich)":
    st.warning("⚠️ **WARNING (Rich LNG):** Bypassing fractionation leaves heavy hydrocarbons (C3+) in the LNG. The Wobbe Index is too high. If this is sent to Europe or SA, it will cause gas turbine flashback. You must install a Nitrogen Injection unit.")
elif spec_status == "OFF-SPEC (Lean)":
    st.warning("⚠️ **WARNING (Lean LNG):** High Nitrogen content from US shale gas has dropped the Wobbe Index. The heating value is too low for most international markets.")
else:
    st.success(f"✅ **PLANT OPTIMAL:** The feed gas has been properly treated. The LNG meets all international custody transfer specifications.")

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. CASE STUDY CONTEXT
# ==========================================
st.markdown("### 📖 Plant Context & Geographical Challenges")
if location == "Angola LNG (Soyo)":
    st.info("**Angola:** Produces very 'rich' gas (high C3+). The fractionation column (tall cylinder) is critical here. If bypassed, the LNG Wobbe Index will spike above 54, meaning it cannot be sold on the global spot market without blending.")
elif location == "Qatar LNG (Ras Laffan)":
    st.info("**Qatar:** Produces 'sour' gas from the North Field with massive CO2 and H2S content. The Amine Unit (box) is the most critical piece of equipment. If bypassed, the cryogenic cold box will freeze instantly.")
else:
    st.info("**USA (Sabine Pass):** Produces very 'lean' shale gas with high Nitrogen. While easy to liquefy without freezing, the high Nitrogen lowers the Wobbe Index and heating value. The plant may need a Nitrogen Rejection Unit (NRU) to meet specs.")
