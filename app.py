import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import math

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# PAGE CONFIG

st.set_page_config(page_title="Factory Optimization", layout="wide")

st.title("🍬 Nassu Factory Reallocation & Optimization Dashboard")

# LOAD DATA

df = pd.read_excel("Nassau Candy Distributor.xlsx")

# LEAD TIME

df['Order Date'] = pd.to_datetime(df['Order Date'])
df['Ship Date'] = pd.to_datetime(df['Ship Date'])
df['Lead_Time'] = (df['Ship Date'] - df['Order Date']).dt.days

# FACTORY MAP

factory_map = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious": "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy": "Sugar Shack",
    "SweeTARTS": "Sugar Shack",
    "Nerds": "Sugar Shack",
    "Fun Dip": "Sugar Shack",
    "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory",
    "Hair Toffee": "The Other Factory",
    "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory",
    "Kazookles": "The Other Factory"
}

df['Factory'] = df['Product Name'].map(factory_map)
df['Route'] = df['Factory'] + " → " + df['Region']

# COORDINATES

factory_coords = {
    "Lot's O' Nuts": (32.88, -111.76),
    "Wicked Choccy's": (32.07, -81.08),
    "Sugar Shack": (48.11, -96.18),
    "Secret Factory": (41.44, -90.56),
    "The Other Factory": (35.11, -89.97)
}

region_coords = {
    "West": (36.77, -119.41),
    "East": (40.71, -74.00),
    "Central": (41.25, -95.93),
    "South": (29.76, -95.36)
}

def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

# MODEL PREP

df_encoded = pd.get_dummies(df[['Sales','Units','Region','Ship Mode','Factory']], drop_first=True)
df_encoded['Lead_Time'] = df['Lead_Time']

X = df_encoded.drop('Lead_Time', axis=1)
y = df_encoded['Lead_Time']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# MODELS

models = {
    "Linear": LinearRegression(),
    "RandomForest": RandomForestRegressor(),
    "GradientBoost": GradientBoostingRegressor()
}

results = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    results[name] = {
        "MAE": mean_absolute_error(y_test, pred),
        "RMSE": np.sqrt(mean_squared_error(y_test, pred)),
        "R2": r2_score(y_test, pred)
    }

best_model_name = max(results, key=lambda x: results[x]['R2'])
best_model = models[best_model_name]

# SIDEBAR FILTERS

st.sidebar.header(" Filters")

product = st.sidebar.selectbox("Product", df['Product Name'].unique())
region = st.sidebar.selectbox("Region", df['Region'].unique())
ship_mode = st.sidebar.selectbox("Ship Mode", df['Ship Mode'].unique())

st.sidebar.subheader(" Optimization Priority")
priority = st.sidebar.slider("0 = Distance | 1 = Speed", 0.0, 1.0, 0.7)

filtered_df = df[
    (df['Product Name'] == product) &
    (df['Region'] == region) &
    (df['Ship Mode'] == ship_mode)
]

# KPI CARDS

st.markdown("##  Key Metrics")

col1, col2, col3 = st.columns(3)

if not filtered_df.empty:
    avg_lead = filtered_df['Lead_Time'].mean()
    global_avg = df['Lead_Time'].mean()
    delta = ((avg_lead - global_avg) / global_avg) * 100

    col1.metric(" Avg Lead Time", round(avg_lead,2), f"{round(delta,2)}%", delta_color="inverse")
    col2.metric(" Total Profit", int(filtered_df['Gross Profit'].sum()))
    col3.metric(" Total Sales", int(filtered_df['Sales'].sum()))

st.markdown("---")

# MAP + MODE

col1, col2 = st.columns(2)

with col1:
    st.subheader("Factory Locations")
    map_df = pd.DataFrame([
        {"lat": v[0], "lon": v[1]} for v in factory_coords.values()
    ])
    st.map(map_df)

with col2:
    st.subheader(" Optimization Mode")
    if priority > 0.7:
        st.success(" Speed Priority")
    elif priority < 0.3:
        st.info(" Cost Priority")
    else:
        st.warning("Balanced Mode")

st.markdown("---")

# OPTIMIZATION ENGINE

st.subheader(" Optimization Engine")

if st.button("Run Optimization"):

    if filtered_df.empty:
        st.warning("No data available")

    else:
        sample = filtered_df.iloc[0]
        factories = df['Factory'].dropna().unique()

        sim_results = []
        current_lead = filtered_df['Lead_Time'].mean()

        for f in factories:

            temp = pd.DataFrame([{
                "Sales": sample['Sales'],
                "Units": sample['Units'],
                "Region": region,
                "Ship Mode": ship_mode,
                "Factory": f
            }])

            temp_encoded = pd.get_dummies(temp)
            temp_encoded = temp_encoded.reindex(columns=X.columns, fill_value=0)

            pred = best_model.predict(temp_encoded)[0]

            f_lat, f_lon = factory_coords[f]
            r_lat, r_lon = region_coords.get(region, (40, -95))

            distance = calculate_distance(f_lat, f_lon, r_lat, r_lon)

            score = (priority * pred) + ((1 - priority) * distance)

            sim_results.append({
                "Factory": f,
                "Route": f + " → " + region,
                "Lead Time": round(pred,2),
                "Distance": round(distance,2),
                "Score": round(score,2)
            })

        sim_df = pd.DataFrame(sim_results).sort_values(by="Score")

        best = sim_df.iloc[0]
        improvement = ((current_lead - best['Lead Time']) / current_lead) * 100

        st.success(f" Best Factory: {best['Factory']}")
        st.write(f" Route: {best['Route']}")
        st.write(f" Improvement: {round(improvement,2)}%")

        st.subheader(" Top 3 Factories")
        st.dataframe(sim_df.head(3))

        st.subheader(" Factory Comparison")
        sim_df['Performance Score'] = 100 - sim_df['Score']

        styled_df = sim_df.style.background_gradient(
            subset=['Performance Score'], cmap='RdYlGn'
        )

        st.dataframe(styled_df, use_container_width=True)

st.markdown("---")


# INTERACTIVE PLOTLY CHARTS

col1, col2 = st.columns(2)

with col1:
    st.subheader(" Lead Time by Region")

    region_data = df.groupby('Region')['Lead_Time'].mean().reset_index()

    fig1 = px.bar(
        region_data,
        x='Region',
        y='Lead_Time',
        text='Lead_Time',
        color='Lead_Time',
        color_continuous_scale='RdYlGn_r'
    )

    fig1.update_traces(texttemplate='%{text:.2f}', textposition='outside')

    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader(" Profit by Region")

    profit_data = df.groupby('Region')['Gross Profit'].sum().reset_index()

    fig2 = px.bar(
        profit_data,
        x='Region',
        y='Gross Profit',
        text='Gross Profit',
        color='Gross Profit',
        color_continuous_scale='Blues'
    )

    fig2.update_traces(texttemplate='%{text:.0f}', textposition='outside')

    st.plotly_chart(fig2, use_container_width=True)

# DATA
st.subheader(" Filtered Data")
st.dataframe(filtered_df.head())