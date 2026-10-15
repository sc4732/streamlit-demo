import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

TEAL, AMBER, INK, MUTED, RULE = "#0F8DA6", "#E09A20", "#2E4752", "#6E8892", "#DCE7EB"
plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": RULE, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.labelcolor": INK, "font.size": 10,
})

DATA = "Airbnb_listing.csv"

st.set_page_config(page_title="NYC Airbnb pricing", layout="wide")


# ---------------------------------------------------------------- data
@st.cache_data
def load(data_path=DATA):
    df = pd.read_csv(data_path)
    df["price_num"] = (
        df["price"]
        .str.replace(r"[$,]", "", regex=True)
        .str.strip()
        .astype(float)
    )
    return df[df["price_num"] > 0]


priced = load()
market_median = priced["price_num"].median()

# ---------------------------------------------------------------- filters
all_boroughs = sorted(priced["neighbourhood_group"].unique())
all_rooms = sorted(priced["room_type"].unique())

st.sidebar.header("Filters")
boroughs = st.sidebar.multiselect("Borough", all_boroughs, default=all_boroughs)
rooms = st.sidebar.multiselect("Room type", all_rooms,
                               default=["Entire home/apt", "Private room"])
guests = st.sidebar.slider("Guests accommodated", 1, 16, (1, 4))

view = priced[
    priced["neighbourhood_group"].isin(boroughs)
    & priced["room_type"].isin(rooms)
    & priced["accommodates"].between(*guests)
]

if view.empty:
    st.warning("No listings match these filters. Widen one of them.")
    st.stop()

# ---------------------------------------------------------------- headline
st.title("What should a listing like this charge?")
st.caption(f"{len(view):,} of {len(priced):,} priced listings match the filters. "
           "Listings priced at \\$0 are excluded as missing data.")

p = view["price_num"]
q1, med, q3 = p.quantile([0.25, 0.5, 0.75])

k1, k2, k3, k4 = st.columns(4)
k1.metric("Listings", f"{len(view):,}")
gap = med - market_median
k2.metric("Median price", f"${med:,.0f}",
          delta=f"{'+' if gap >= 0 else '-'}${abs(gap):,.0f} vs. all NYC",
          delta_color="off")
k3.metric("Middle half", f"${q1:,.0f} – ${q3:,.0f}")
k4.metric("Mean price", f"${p.mean():,.0f}",
          help="Pulled up by a small number of very expensive listings. "
               "Use the median to price a typical listing.")

# ---------------------------------------------------------------- charts
tab1, tab2, tab3 = st.tabs(["Distribution", "By borough", "Listings"])

with tab1:
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.hist(p[p <= 600], bins=np.arange(0, 620, 20), color=TEAL)
    ax.axvline(med, color=AMBER, linestyle="--", linewidth=2)
    ax.text(med + 6, ax.get_ylim()[1] * 0.9, f"Median ${med:,.0f}",
            color=AMBER, fontweight="bold")
    ax.set_xlabel("Nightly price (listings up to $600)")
    ax.set_ylabel("Listings")
    st.pyplot(fig)

with tab2:
    order = view.groupby("neighbourhood_group")["price_num"].median().sort_values().index
    fig, ax = plt.subplots(figsize=(9, 3.4))
    bp = ax.boxplot([view.loc[view["neighbourhood_group"] == b, "price_num"] for b in order],
                    vert=False, widths=0.55, showfliers=False, patch_artist=True,
                    medianprops=dict(color=AMBER, linewidth=2))
    for b in bp["boxes"]:
        b.set(facecolor=TEAL, alpha=0.35, edgecolor=TEAL)
    ax.set_yticks(range(1, len(order) + 1), order)
    ax.set_xlabel("Nightly price")
    st.pyplot(fig)

with tab3:
    st.dataframe(
        view[["name", "neighbourhood_group", "neighbourhood", "room_type",
              "accommodates", "price_num"]]
        .sort_values("price_num")
        .rename(columns={"price_num": "price"}),
        hide_index=True,
    )

# ---------------------------------------------------------------- summary
st.subheader("Summary")
st.markdown(
    f"A listing matching these filters typically charges **\\${med:,.0f}** a night, "
    f"and half of them charge between **\\${q1:,.0f}** and **\\${q3:,.0f}**. "
    f"Pricing inside that band is competing in the market; pricing at the "
    f"\\${p.mean():,.0f} mean is asking more than "
    f"{(p < p.mean()).mean():.0%} of comparable listings."
)
