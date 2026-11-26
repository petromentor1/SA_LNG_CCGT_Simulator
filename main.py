import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Advanced LNG Export Simulator")

st.title("🏭 Advanced LNG Liquefaction & Export Simulator")
st.markdown("Select a **Case Study** to simulate real-world plant failures. Watch the 3D animation: if the gas is **Off-Spec**, the flow will divert up the Flare Stack instead of going to the LNG Tanks.")

# ==========================================
# 1. SIDEBAR CONTROLS & CASE STUDIES
# ==========================================
st.sidebar.header("🎯 Case Study Scenarios")
case_study = st.sidebar.selectbox(
    "Load a Real-World Scenario",
    [
        "Normal Operation (Perfect Specs)",
        "Case 1: Hydrate Formation (Dehydration Failure)",
        "Case 2: CO2 Freeze (AGRU Failure)",
        "Case 3: Mercury Slip (Cold Box Corrosion)",
        "Case 4: Rich Gas (Wobbe Index Too High)"
    ]
)

st.sidebar.header("🌍 Feed Gas & Location")
location = st.sidebar.selectbox("Select Export Terminal", ["Angola LNG (Soyo)", "Qatar LNG (Ras Laffan)", "USA LNG (Sabine Pass)"])

# Base defaults by location
if location == "Angola LNG (Soyo)":
    b_h2s, b_co2, b_h2o, b_hg, b_c3 = 50, 1500, 200, 2, 12.0
elif location == "Qatar LNG (Ras Laffan)":
    b_h2s, b_co2, b_h2o, b_hg, b_c3 = 500, 2500, 300, 5, 8.0
else:
    b_h2s, b_co2, b_h2o, b_hg, b_c3 = 0, 50, 100, 1, 3.0

# Override defaults based on Case Study
if "Normal" in case_study:
    h2s_ppm, co2_ppm, h2o_ppm, hg_ppb, c3_percent = b_h2s, b_co2, b_h2o, b_hg, b_c3
    bypass_agru, bypass_dehy, bypass_frac = False, False, False
elif "Hydrate" in case_study:
    h2s_ppm, co2_ppm, h2o_ppm, hg_ppb, c3_percent = b_h2s, b_co2, 350, b_hg, b_c3
    bypass_agru, bypass_dehy, bypass_frac = False, True, False
elif "CO2" in case_study:
    h2s_ppm, co2_ppm, h2o_ppm, hg_ppb, c3_percent = b_h2s, 2500, b_h2o, b_hg, b_c3
    bypass_agru, bypass_dehy, bypass_frac = True, False, False
elif "Mercury" in case_study:
    h2s_ppm, co2_ppm, h2o_ppm, hg_ppb, c3_percent = b_h2s, b_co2, b_h2o, 8, b_c3
    bypass_agru, bypass_dehy, bypass_frac = False, False, False
elif "Rich Gas" in case_study:
    h2s_ppm, co2_ppm, h2o_ppm, hg_ppb, c3_percent = b_h2s, b_co2, b_h2o, b_hg, 18.0
    bypass_agru, bypass_dehy, bypass_frac = False, False, True

h2s_ppm = st.sidebar.slider("Feed H2S (ppm)", 0, 1000, h2s_ppm)
co2_ppm = st.sidebar.slider("Feed CO2 (ppm)", 0, 3000, co2_ppm)
h2o_ppm = st.sidebar.slider("Feed H2O (ppm)", 1, 500, h2o_ppm)
hg_ppb = st.sidebar.slider("Feed Mercury (ppb)", 0, 10, hg_ppb)
c3_percent = st.sidebar.slider("Feed C3+ (Richness) %", 1.0, 20.0, c3_percent)

st.sidebar.header("⚙️ Plant Capacity & Tech")
mtpa = st.sidebar.slider("Plant Capacity (MTPA)", 0.5, 10.0, 4.0, 0.1)
tech = st.sidebar.radio("Liquefaction Technology", 
    ["SMR (Single Mixed Refrigerant)", "C3MR (Propane Pre-cooled)", "DMR (Dual Mixed Refrigerant)"])

st.sidebar.header("🛠️ Manual Operations")
n2_injection = st.sidebar.slider("Nitrogen Injection (Wobbe Control)", 0, 15, 0)
bypass_agru = st.sidebar.checkbox("BYPASS Acid Gas Removal (AGRU)", value=bypass_agru)
bypass_dehy = st.sidebar.checkbox("BYPASS Dehydration (Mole Sieves)", value=bypass_dehy)
bypass_frac = st.sidebar.checkbox("BYPASS Fractionation (NGL)", value=bypass_frac)

# ==========================================
# 2. THERMODYNAMIC & ECONOMIC LOGIC
# ==========================================
final_h2s = h2s_ppm if bypass_agru else min(h2s_ppm, 4.0)
final_co2 = co2_ppm if bypass_agru else min(co2_ppm, 50.0)
final_h2o = h2o_ppm if bypass_dehy else min(h2o_ppm, 0.1)
final_hg = hg_ppb # Mercury removal is assumed active unless bypassed (not explicitly modeled as toggle to save space)
final_c3 = c3_percent if bypass_frac else max(c3_percent - 8.0, 2.0)

wobbe_index = 48.0 + (final_c3 * 1.5) - (n2_injection * 0.5)
heating_value = 45.0 + (final_c3 * 0.8)

# Tech Efficiency
if "SMR" in tech: power_per_tonne, max_cap = 400, 2.0
elif "C3MR" in tech: power_per_tonne, max_cap = 300, 6.0
else: power_per_tonne, max_cap = 280, 10.0

if final_c3 > 8.0: power_per_tonne += 20 # Recycle penalty
if wobbe_index > 54.0: power_per_tonne += 15 # N2 blending penalty

# Refrigeration Duty (MW)
daily_tonnes = mtpa * 1e6 / 365
refrigeration_duty_mw = (daily_tonnes * power_per_tonne) / 24000 

# Failures
h2s_fail = final_h2s > 4.0
co2_fail = final_co2 > 50.0
h2o_fail = final_h2o > 0.1
hg_fail = final_hg > 2.0
wobbe_fail = wobbe_index > 54.0 or wobbe_index < 45.0
tech_mismatch = mtpa > max_cap

plant_tripped = h2s_fail or co2_fail or h2o_fail or hg_fail or wobbe_fail

# ==========================================
# 3. 3D PLANT GEOMETRY
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
    vertices = [(x, y, z_base), (x+width, y, z_base), (x+width, y+depth, z_base), (x, y+depth, z_base),
                (x, y, z_base+height), (x+width, y, z_base+height), (x+width, y+depth, z_base+height), (x, y+depth, z_base+height)]
    i = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 6]; j = [1, 2, 2, 5, 3, 6, 0, 7, 5, 6, 6, 7]; k = [2, 3, 5, 6, 6, 7, 7, 4, 6, 7, 1, 2]
    return go.Mesh3d(x=[v[0] for v in vertices], y=[v[1] for v in vertices], z=[v[2] for v in vertices], i=i, j=j, k=k, color=color, opacity=opacity, hoverinfo="skip")

def add_label(x, y, z, text):
    return go.Scatter3d(x=[x], y=[y], z=[z], mode='text', text=[text], textfont=dict(size=12, color='black', family='Arial'), showlegend=False)

static_traces = []
static_traces.append(draw_pipe(-15, -12, 0, 0))
static_traces.append(draw_box(-18, -2, 0, 2, 3, 4, '#9CA3AF')); static_traces.append(add_label(-16.5, 0, 3, "Slug Catcher"))

static_traces.append(draw_pipe(-9, -6, 0, 0))
static_traces.append(draw_box(-12, -2, 0, 5, 3, 4, '#EF4444' if (bypass_agru and (h2s_ppm>4 or co2_ppm>50)) else '#10B981')); static_traces.append(add_label(-10.5, 0, 6, "AGRU (Amine)"))

static_traces.append(draw_pipe(-3.5, -1, 0, 0))
static_traces.append(draw_cylinder(-5, 0, 0, 6, 1.5, '#EF4444' if (bypass_dehy and h2o_ppm>0.1) else '#3B82F6')); static_traces.append(add_label(-5, 0, 7, "Mole Sieves"))

static_traces.append(draw_pipe(1, 3, 0, 0))
static_traces.append(draw_cylinder(0, 0, 0, 4, 1.0, '#EF4444' if hg_ppb>2 else '#9CA3AF')); static_traces.append(add_label(0, 0, 5, "Hg Removal"))

static_traces.append(draw_pipe(5.2, 7, 0, 0))
static_traces.append(draw_cylinder(4, 0, 0, 9, 1.2, '#EF4444' if (final_c3 > 8.0 and not bypass_frac) else '#10B981')); static_traces.append(add_label(4, 0, 10, "Fractionation"))

cold_box_color = '#EF4444' if (co2_fail or h2o_fail) else '#06B6D4'
if "SMR" in tech:
    static_traces.append(draw_box(7, -2.5, 0, 6, 5, 5, cold_box_color)); static_traces.append(add_label(9.5, 0, 7, "SMR Cold Box"))
    static_traces.append(draw_cylinder(9.5, 3.5, 0, 4, 1.2, '#F59E0B')); static_traces.append(add_label(9.5, 3.5, 5, "MR Compressor"))
elif "C3MR" in tech:
    static_traces.append(draw_box(7, -2.5, 0, 4, 2.5, 5, '#F97316')); static_traces.append(add_label(8.25, 0, 5, "Propane Cooler"))
    static_traces.append(draw_box(9.5, -2.5, 0, 6, 2.5, 5, cold_box_color)); static_traces.append(add_label(10.75, 0, 7, "MR Cold Box"))
    static_traces.append(draw_cylinder(8.25, 3.5, 0, 4, 1.0, '#F59E0B'))
    static_traces.append(draw_cylinder(10.75, 3.5, 0, 4, 1.0, '#8B5CF6'))
    static_traces.append(add_label(9.5, 3.5, 5, "Propane & MR Comp."))
else:
    static_traces.append(draw_box(7, -2.5, 0, 4, 1.8, 5, '#F97316')); static_traces.append(add_label(7.9, 0, 5, "MR-1 Pre-cool"))
    static_traces.append(draw_box(9, -2.5, 0, 5, 1.8, 5, cold_box_color)); static_traces.append(add_label(9.9, 0, 6, "MR-2 Liquefaction"))
    static_traces.append(draw_box(11, -2.5, 0, 6, 1.8, 5, '#1E3A8A')); static_traces.append(add_label(11.9, 0, 7, "MR-3 Sub-cool"))
    static_traces.append(draw_cylinder(7.9, 3.5, 0, 4, 1.0, '#F59E0B'))
    static_traces.append(draw_cylinder(9.9, 3.5, 0, 4, 1.0, '#8B5CF6'))
    static_traces.append(draw_cylinder(11.9, 3.5, 0, 4, 1.0, '#10B981'))
    static_traces.append(add_label(9.9, 3.5, 5, "DMR Compressors"))

if n2_injection > 0:
    static_traces.append(draw_cylinder(13.5, 0, 0, 4, 1.0, '#93C5FD')); static_traces.append(add_label(13.5, 0, 5, "N2 Injection"))

static_traces.append(draw_pipe(13, 16, 0, 0))
static_traces.append(draw_cylinder(17, -3, 0, 5, 2.5, '#F3F4F6')); static_traces.append(add_label(17, -3, 6, "LNG Tank 1"))
static_traces.append(draw_cylinder(17, 3, 0, 5, 2.5, '#F3F4F6')); static_traces.append(add_label(17, 3, 6, "LNG Tank 2"))

static_traces.append(draw_pipe(19.5, 22, 0, 0))
static_traces.append(draw_box(22, -1, 0, 1, 3, 2, '#4B5563')); static_traces.append(add_label(23.5, 0, 2, "Loading Jetty"))

# Flare Stack - Always present, but red if tripped
flare_color = '#EF4444' if plant_tripped else '#9CA3AF'
static_traces.append(draw_cylinder(10, -6, 0, 10, 0.3, flare_color))
static_traces.append(add_label(10, -6, 11, "Flare Stack"))
# Pipe to Flare
static_traces.append(draw_pipe(10, 10, -2, 0.5, color='#EF4444' if plant_tripped else '#4B5563'))

static_traces.append(draw_box(-15, 4, 0, 2, 4, 4, '#D1D5DB')); static_traces.append(add_label(-13, 6, 3, "Control Room"))

# ==========================================
# 4. ANIMATION FRAMES (The Flow Routing)
# ==========================================
frames = []
num_frames = 40

for i in range(num_frames):
    frame_traces = static_traces.copy()
    t = (i / num_frames)
    
    # Waypoints
    if plant_tripped:
        # Path: Inlet -> Cold Box -> Flare Stack (up)
        if t < 0.7:
            x_pos = -18 + ((t/0.7) * 30) # -18 to 12
            y_pos = 0
            z_pos = 0.5
        else:
            x_pos = 12 - (((t-0.7)/0.3) * 2) # 12 to 10
            y_pos = -6 * ((t-0.7)/0.3) # 0 to -6
            z_pos = 0.5 + (((t-0.7)/0.3) * 11) # 0.5 to 11.5
        p_color = '#EF4444' # Red (Off-spec)
    else:
        # Path: Inlet -> Tanks -> Jetty
        x_pos = -18 + (t * 41)
        y_pos = 0
        z_pos = 0.5
        p_color = '#1E3A8A' # Dark Blue (LNG)
        
    # Main Particle
    particle = go.Scatter3d(
        x=[x_pos], y=[y_pos], z=[z_pos], mode='markers', 
        marker=dict(size=15, color=p_color, symbol='circle'), name='Product Flow'
    )
    frame_traces.append(particle)
    
    # Secondary Particle
    t2 = (t + 0.5) % 1.0
    if plant_tripped:
        if t2 < 0.7:
            x2, y2, z2 = -18 + ((t2/0.7) * 30), 0, 0.5
        else:
            x2 = 12 - (((t2-0.7)/0.3) * 2)
            y2 = -6 * ((t2-0.7)/0.3)
            z2 = 0.5 + (((t2-0.7)/0.3) * 11)
    else:
        x2, y2, z2 = -18 + (t2 * 41), 0, 0.5
        
    frame_traces.append(go.Scatter3d(x=[x2], y=[y2], z=[z2], mode='markers', 
        marker=dict(size=15, color=p_color, symbol='circle'), showlegend=False))
    
    # Add visual flame if flaring
    if plant_tripped:
        flame = go.Scatter3d(x=[10, 10, 10], y=[-6, -6, -6], z=[11.5, 12.5, 13.5], 
                             mode='markers', marker=dict(size=[20, 30, 20], color='orange'), showlegend=False)
        frame_traces.append(flame)
    
    frames.append(go.Frame(data=frame_traces, name=str(i)))

# ==========================================
# 5. BUILD THE FIGURE
# ==========================================
fig = go.Figure(data=frames[0].data, frames=frames)
fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False, range=[-19, 25]), yaxis=dict(visible=False, range=[-8, 7]), zaxis=dict(visible=False, range=[0, 14]),
        camera=dict(eye=dict(x=0.3, y=-2.2, z=0.8)), aspectmode='manual', aspectratio=dict(x=2.2, y=1, z=0.8)
    ),
    updatemenus=[dict(type="buttons", showactive=False, x=0.1, y=0,
        buttons=[
            dict(label="▶️ Play Flow", method="animate", args=[None, dict(frame=dict(duration=80, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
            dict(label="⏸️ Pause", method="animate", args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])
        ])],
    margin=dict(l=0, r=0, b=0, t=0), height=600, paper_bgcolor="#F8FAFC"
)

# ==========================================
# 6. DASHBOARD & ALARMS
# ==========================================
st.subheader("📊 Process Specifications & Economics")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("H2O", f"{final_h2o:.2f} ppm", "Fail" if h2o_fail else "Pass", delta_color="inverse")
c2.metric("CO2", f"{final_co2:.0f} ppm", "Fail" if co2_fail else "Pass", delta_color="inverse")
c3.metric("Hg", f"{final_hg} ppb", "Fail" if hg_fail else "Pass", delta_color="inverse")
c4.metric("Wobbe Index", f"{wobbe_index:.1f}", "Off-Spec" if wobbe_fail else "Spec")
c5.metric("Refrigeration Duty", f"{refrigeration_duty_mw:.0f} MW") # NEW METRIC
c6.metric("Feed C3+ Adjustment", f"{c3_percent:.1f}% ➔ {final_c3:.1f}%")

if tech_mismatch:
    st.error(f"🚨 **TECHNOLOGY MISMATCH:** You selected {tech} but the plant capacity is {mtpa} MTPA. Max capacity is {max_cap} MTPA.")
elif plant_tripped:
    st.error("🚨 **CRITICAL FAILURE:** Off-spec gas detected! The flow has been diverted to the Flare Stack (follow the red particle). The LNG tanks are isolated.")
elif wobbe_fail:
    st.warning("⚠️ **WARNING:** Rich/Lean LNG. Wobbe Index is out of spec.")
else:
    st.success("✅ **PLANT OPTIMAL:** Specs met. Flow is going to the LNG tanks.")

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. DETAILED TECHNICAL CONTEXT
# ==========================================
with st.expander("📖 Case Study Engineering Context"):
    if "Hydrate" in case_study:
        st.markdown("**Case 1: Hydrate Formation.** Dehydration (Mole Sieves) was bypassed. Water at 350 ppm entered the cryogenic cold box. At -162°C, water freezes into ice/hydrates, instantly plugging the aluminum plate-fin heat exchangers. The plant tripped, and all gas is being flared.")
    elif "CO2" in case_study:
        st.markdown("**Case 2: CO2 Freeze.** The AGRU was bypassed. CO2 at 2500 ppm entered the cold box. At -56°C, CO2 forms dry ice, plugging the cold box. The plant tripped, and all gas is being flared.")
    elif "Mercury" in case_study:
        st.markdown("**Case 3: Mercury Slip.** Mercury at 8 ppb slipped through the carbon beds. Mercury amalgamates with the aluminum heat exchangers in the cold box, causing rapid corrosion and structural failure. Plant tripped.")
    elif "Rich Gas" in case_study:
        st.markdown("**Case 4: Rich Gas.** Fractionation was bypassed. C3+ is high, causing the Wobbe Index to spike above 54 MJ/m³. The LNG is unusable for standard gas turbines. The gas is being flared because it cannot be sold.")
    else:
        st.markdown("**Normal Operation:** All units are online. Gas flows smoothly to the LNG tanks and out to the jetty.")
