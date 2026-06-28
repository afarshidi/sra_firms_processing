import ast
import streamlit as st
import pandas as pd
import plotly.express as px

# Set page layout
st.set_page_config(page_title="SRA Work Area Analysis", layout="wide")
st.title("⚖️ Legal Market & Work Area Analyzer")
st.markdown("Analyze law firm specialisms across different UK locations.")

# --- 1. LOAD AND CLEAN DATA ---
@st.cache_data
def load_and_clean_data():
    # Load from the parquet file we created earlier
    df = pd.read_parquet("sra_organisations.parquet")
    
    # Convert string back to Python objects
    df["Offices"] = df["Offices"].apply(ast.literal_eval)
    df["WorkArea"] = df["WorkArea"].apply(ast.literal_eval)
    
    # Explode Offices to get rows per branch
    df_flat = df.explode("Offices")
    
    # Extract Town safely and clean it
    df_flat["Town"] = df_flat["Offices"].apply(
        lambda x: x.get("Town").strip().title() if isinstance(x, dict) and x.get("Town") else None
    )
    
    # Explode WorkArea so we map work areas to those towns
    df_flat = df_flat.explode("WorkArea")
    df_flat = df_flat.dropna(subset=["WorkArea", "Town"])
    
    # --- RULE: Deduplicate multiple offices of the same firm in the same town ---
    # This prevents a firm with 10 branches in London from skewing the results
    df_dedup = df_flat.drop_duplicates(subset=["PracticeName", "Town", "WorkArea"])
    
    return df_dedup

try:
    df_clean = load_and_clean_data()
except Exception as e:
    st.error(f"Could not load parquet file. Make sure 'sra_organisations.parquet' is in the same directory. Error: {e}")
    st.stop()

# --- PRE-COMPUTE METRICS FOR THE "LONDON PROBLEM" ---
# 1. Total unique firms per town (across all work areas combined)
town_totals = df_clean.groupby("Town")["PracticeName"].nunique().reset_index(name="Total_Unique_Firms_In_Town")

# 2. Total unique firms per town per work area
work_town_counts = df_clean.groupby(["Town", "WorkArea"])["PracticeName"].nunique().reset_index(name="Firm_Count")

# Merge them back together
market_share_df = pd.merge(work_town_counts, town_totals, on="Town")

# Calculate Local Market Share % (What % of this city's firms do this work?)
market_share_df["Market_Share_Pct"] = (market_share_df["Firm_Count"] / market_share_df["Total_Unique_Firms_In_Town"]) * 100


# --- TABBED NAVIGATION ---
tab1, tab2 = st.tabs(["📍 Analyze a Location", "💼 Compare Cities by Work Area"])

# =====================================================================
# TAB 1: SELECT A LOCATION & SEE TOP WORK AREAS
# =====================================================================
with tab1:
    st.header("Location Deep-Dive")
    
    # Sidebar/Control inputs
    all_towns = sorted(df_clean["Town"].unique())
    selected_town = st.selectbox("Select a Town/City:", all_towns, index=all_towns.index("Manchester") if "Manchester" in all_towns else 0)
    top_n = st.slider("Number of top work areas to display:", min_value=5, max_value=30, value=10)
    
    # Filter data for selected town
    town_data = market_share_df[market_share_df["Town"] == selected_town].sort_values(by="Firm_Count", ascending=False)
    
    if not town_data.empty:
        total_local_firms = town_data["Total_Unique_Firms_In_Town"].iloc[0]
        st.metric(label=f"Total Unique Law Firms in {selected_town}", value=int(total_local_firms))
        
        # Plot
        fig1 = px.bar(
            town_data.head(top_n),
            x="Firm_Count",
            y="WorkArea",
            orientation="h",
            title=f"Top {top_n} Work Areas in {selected_town} (by Unique Firm Count)",
            labels={"Firm_Count": "Number of Unique Firms", "WorkArea": "Work Area"},
            text="Firm_Count"
        )
        fig1.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.warning("No data found for this location.")

# =====================================================================
# TAB 2: SELECT WORK AREA & COMPARE CITIES
# =====================================================================
with tab2:
    st.header("Cross-City Work Area Comparison")
    
    all_areas = sorted(df_clean["WorkArea"].unique())
    selected_area = st.selectbox("Select a Work Area:", all_areas)
    
    # Filter data for selected work area
    area_data = market_share_df[market_share_df["WorkArea"] == selected_area]
    
    # Minimum size filter to prevent cities with only 1 or 2 firms total from showing up as 100%
    min_size = st.number_input("Minimum total firms required in a city to be included (Filters out tiny sample sizes):", min_value=1, value=5)
    area_data = area_data[area_data["Total_Unique_Firms_In_Town"] >= min_size]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("By Raw Firm Count (Favours Large Cities)")
        top_raw = area_data.sort_values(by="Firm_Count", ascending=False).head(10)
        
        fig_raw = px.bar(
            top_raw,
            x="Town",
            y="Firm_Count",
            title=f"Top Cities for {selected_area} (Raw Counts)",
            labels={"Firm_Count": "Unique Firms", "Town": "City"},
            color="Firm_Count",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig_raw, use_container_width=True)
        
    with col2:
        st.subheader("By Concentration / Market Share (Fair for Smaller Cities)")
        st.markdown("*Shows what % of the town's total local law firms offer this service.*")
        top_share = area_data.sort_values(by="Market_Share_Pct", ascending=False).head(10)
        
        fig_share = px.bar(
            top_share,
            x="Town",
            y="Market_Share_Pct",
            title=f"Top Cities Specialising in {selected_area} (% of Local Market)",
            labels={"Market_Share_Pct": "% of Local Firms Specialising", "Town": "City"},
            color="Market_Share_Pct",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig_share, use_container_width=True)