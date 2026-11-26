import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="Global LNG Plant Simulator")

st.title("🌍 Global LNG Plant Simulator")

# ==========================================
# 1. SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("🕹️ Core Simulation")

country = st.sidebar.selectbox(
    "Select Country", 
    ["Angola", "Qatar", "USA"]
)

scenario = st.sidebar.selectbox(
    "Select Scenario", 
    ["Normal Operations", "Feed Quality Issue", "Product Specification Issue"]
)

current_day = st.sidebar.slider("Timeline (Days)", 1, 30, 15, 1)

st.sidebar.header("🌡️ Thermodynamics & Gas Quality")
initial_feed_quality = st.sidebar.slider("Initial Feed Quality (%)", 50, 95, 90, 5)
ambient_temp = st.sidebar.slider("Ambient Temperature (°C)", 15, 45, 30, 1)

# NEW: Feed Quality Control
feed_quality = st.sidebar.slider(
    "Feed Quality (%)", 
    45.0, 55.0, 50.0, 0.5,
    help="Ideal Feed Quality for this plant is ~50.0. Rich gas can cause overheat. Lean gas can cause flameout."
)

product_specification = st.sidebar.slider("Product Specification (%)", 90.0, 95.0, 92.0, 0.5)

st.sidebar.header("⚙️ Plant Operations")
production_rate = st.sidebar.slider("Production Rate (Mtpa)", 1.0, 5.0, 2.0, 0.1)
operating_efficiency = st.sidebar.slider("Operating Efficiency (%)", 80, 100, 90, 1)

# ==========================================
# 2. CALCULATION ENGINE
# ==========================================
base_efficiency = 0.85
if scenario == "Feed Quality Issue":
    base_efficiency *= 0.9
if scenario == "Product Specification Issue":
    base_efficiency *= 0.95

efficiency = base_efficiency * (operating_efficiency / 100.0)

# Calculate Power and Gas Consumption
power_mw = (production_rate * 1e9 * efficiency) / (365 * 24 * 3600)

# Calculate Gas Consumption
gas_consumed_tonnes_day = (production_rate * 1e6) / 365
gas_consumed_mmscfd = (gas_consumed_tonnes_day * 48) / 1000

# Calculate Revenue and Emissions
electricity_price = 2.50  # R/kWh
revenue_zar = power_mw * 1000 * 24 * electricity_price
methane_emitted_tons = (power_mw * 24 * 3600 / 48) * (1 - feed_quality / 100) * (1 - product_specification / 100) / 1000

# ==========================================
# 3. BUILD THE TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["📈 Production Metrics", "⚙️ Plant Operations", "🔍 Case Studies"])

# ==========================================
# TAB 1: Production Metrics
# ==========================================
with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Production Rate", f"{production_rate:,.1f} Mtpa")
    c2.metric("Efficiency", f"{efficiency*100:.1f} %")
    c3.metric("Electricity Consumption", f"{power_mw:,.0f} MW")

    st.divider()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[current_day], y=[gas_consumed_tonnes_day], mode='markers', marker=dict(size=10, color='red'), name='Gas Consumed'))
    fig.add_trace(go.Scatter(x=[current_day], y=[gas_consumed_mmscfd], mode='markers', marker=dict(size=10, color='blue'), name='Gas Flow'))
    fig.update_layout(title="Gas Consumption Metrics", xaxis_title="Day", yaxis_title="Metrics (Tons/day / MMSCFD)")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 2: Plant Operations
# ==========================================
with tab2:
    st.subheader("⚙️ Plant Operations")
    st.write(f"Country: {country}")
    st.write(f"Scenario: {scenario}")
    st.write(f"Initial Feed Quality: {initial_feed_quality}%")
    st.write(f"Feed Quality: {feed_quality}%")
    st.write(f"Product Specification: {product_specification}%")
    st.write(f"Efficiency: {efficiency*100:.1f}%")
    st.write(f"Electricity Consumption: {power_mw:,.0f} MW")
    st.write(f"Revenue: R {revenue_zar:,.0f}")
    st.write(f"Methane Emitted: {methane_emitted_tons:.1f} Tons/day")

# ==========================================
# TAB 3: Case Studies
# ==========================================
with tab3:
    st.subheader("🔍 Case Studies")
    st.markdown("Use the sliders in the sidebar to recreate these exact scenarios and drive the negotiation.")
    # ... (Case studies list here)
