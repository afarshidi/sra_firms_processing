import ast
import pandas as pd
import plotly.express as px
import streamlit as st

# Set page layout
st.set_page_config(page_title="SRA Work Area Analysis", layout="wide")
st.title("⚖️ Legal Market & Work Area Analyzer")
st.markdown("Analyze law firm specialisms across different UK locations.")


# --- 1. LOAD AND CLEAN DATA ---
@st.cache_data
def load_and_clean_data():
    df = pd.read_parquet("sra_organisations.parquet")

    df["Offices"] = df["Offices"].apply(ast.literal_eval)
    df["WorkArea"] = df["WorkArea"].apply(ast.literal_eval)

    df_flat = df.explode("Offices")

    df_flat["Town"] = df_flat["Offices"].apply(
        lambda x: (
            x.get("Town").strip().title()
            if isinstance(x, dict) and x.get("Town")
            else None
        )
    )

    df_flat = df_flat.explode("WorkArea")
    df_flat = df_flat.dropna(subset=["WorkArea", "Town"])

    # Deduplicate multiple offices of the same firm in the same town
    df_dedup = df_flat.drop_duplicates(subset=["PracticeName", "Town", "WorkArea"])

    return df_dedup


try:
    df_clean = load_and_clean_data()
except Exception as e:
    st.error(
        f"Could not load parquet file. Make sure 'sra_organisations.parquet' is in the same directory. Error: {e}"
    )
    st.stop()

# --- PRE-COMPUTE METRICS ---
town_totals = (
    df_clean.groupby("Town")["PracticeName"]
    .nunique()
    .reset_index(name="Total_Unique_Firms_In_Town")
)
work_town_counts = (
    df_clean.groupby(["Town", "WorkArea"])["PracticeName"]
    .nunique()
    .reset_index(name="Firm_Count")
)
market_share_df = pd.merge(work_town_counts, town_totals, on="Town")
market_share_df["Market_Share_Pct"] = (
    market_share_df["Firm_Count"] / market_share_df["Total_Unique_Firms_In_Town"]
) * 100

# --- DYNAMIC LIMIT FOR SLIDER ---
# Get the absolute maximum number of unique work areas present in the dataset
absolute_max_work_areas = int(df_clean["WorkArea"].nunique())


# --- TABBED NAVIGATION ---
tab1, tab2 = st.tabs(["📍 Analyze a Location", "💼 Compare Cities by Work Area"])

# =====================================================================
# TAB 1: SELECT A LOCATION & SEE TOP WORK AREAS
# =====================================================================
with tab1:
    st.header("Location Deep-Dive")

    all_towns = sorted(df_clean["Town"].unique())
    selected_town = st.selectbox(
        "Select a Town/City:",
        all_towns,
        index=(
            all_towns.index("Manchester") if "Manchester" in all_towns else 0
        ),
    )

    # Dynamic Slider: max_value adapts seamlessly to your data
    top_n = st.slider(
        "Number of top work areas to display:",
        min_value=5,
        max_value=absolute_max_work_areas,
        value=min(10, absolute_max_work_areas),
    )

    town_data = market_share_df[market_share_df["Town"] == selected_town].sort_values(
        by="Firm_Count", ascending=False
    )

    if not town_data.empty:
        total_local_firms = town_data["Total_Unique_Firms_In_Town"].iloc[0]
        st.metric(
            label=f"Total Unique Law Firms in {selected_town}",
            value=int(total_local_firms),
        )

        # Subset data based on slider selection
        plot_data = town_data.head(top_n)

        # DYNAMIC HEIGHT CALCULATION:
        # We give each bar 35 pixels of space, plus a 150px base for margins/titles.
        # This stops text overlapping when top_n is high!
        calculated_height = 150 + (len(plot_data) * 35)

        fig1 = px.bar(
            plot_data,
            x="Firm_Count",
            y="WorkArea",
            orientation="h",
            title=f"Top {len(plot_data)} Work Areas in {selected_town}",
            labels={"Firm_Count": "Number of Unique Firms", "WorkArea": "Work Area"},
            text="Firm_Count",
        )
        fig1.update_layout(
            yaxis={"categoryorder": "total ascending"},
            height=calculated_height,  # Applied here
            margin=dict(l=20, r=20, t=50, b=50),
        )
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

    area_data = market_share_df[market_share_df["WorkArea"] == selected_area]

    min_size = st.number_input(
        "Minimum total firms required in a city to be included:",
        min_value=1,
        value=5,
    )
    area_data = area_data[area_data["Total_Unique_Firms_In_Town"] >= min_size]

    # Added a dynamic selector for how many cities to compare
    top_cities_n = st.slider(
        "Number of cities to compare:", min_value=5, max_value=50, value=10
    )

    col1, col2 = st.columns(2)

    # Calculate dynamic height for vertical bars if the user compares a lot of cities
    # (Rotated text looks better when chart has breathing room)
    v_calculated_height = 450 if top_cities_n <= 15 else 600

    with col1:
        st.subheader("By Raw Firm Count (Favours Large Cities)")
        top_raw = area_data.sort_values(by="Firm_Count", ascending=False).head(
            top_cities_n
        )

        fig_raw = px.bar(
            top_raw,
            x="Town",
            y="Firm_Count",
            title=f"Top Cities for {selected_area} (Raw Counts)",
            labels={"Firm_Count": "Unique Firms", "Town": "City"},
            color="Firm_Count",
            color_continuous_scale="Reds",
        )
        fig_raw.update_layout(height=v_calculated_height)
        st.plotly_chart(fig_raw, use_container_width=True)

    with col2:
        st.subheader("By Concentration / Market Share (Fair for Smaller Cities)")
        top_share = area_data.sort_values(
            by="Market_Share_Pct", ascending=False
        ).head(top_cities_n)

        fig_share = px.bar(
            top_share,
            x="Town",
            y="Market_Share_Pct",
            title=f"Top Cities Specialising in {selected_area}",
            labels={
                "Market_Share_Pct": "% of Local Firms Specialising",
                "Town": "City",
            },
            color="Market_Share_Pct",
            color_continuous_scale="Blues",
        )
        fig_share.update_layout(height=v_calculated_height)
        st.plotly_chart(fig_share, use_container_width=True)