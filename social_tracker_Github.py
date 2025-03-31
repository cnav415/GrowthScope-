import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Load Data with Date Parsing
@st.cache_data  # Updated from st.cache to st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    df['Date'] = pd.to_datetime(df['Date'])  # Ensure Date column is parsed correctly
    # Convert all columns (except 'Artist Name' and 'Date') to numeric, coercing errors to NaN
    for col in df.columns:
        if col not in ['Artist Name', 'Date']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# Calculate Growth
def calculate_growth(data):
    start_value = data.iloc[0]
    end_value = data.iloc[-1]
    growth_int = end_value - start_value
    growth_pct = ((end_value - start_value) / start_value) * 100 if start_value != 0 else 0
    return growth_int, growth_pct

# Map platforms for monetary growth
def get_monetary_platforms(platforms, monetary=False):
    if monetary:
        return [f"{platform} Revenue" for platform in platforms]
    return platforms

# Generate Summary Line Chart
def summary_growth_chart(df, platforms, metric="percentage", monetary=False):
    label = "Revenue" if monetary else "Followers"
    st.subheader(f"Summary of Growth: Comparison by Platform ({label})")
    plt.figure(figsize=(10, 6))

    adjusted_platforms = get_monetary_platforms(platforms, monetary)
    for platform, adjusted_platform in zip(platforms, adjusted_platforms):
        platform_data = df.groupby('Date')[adjusted_platform].sum()
        if monetary:
            platform_data = platform_data / 100
        start_value = platform_data.iloc[0]
        growth = (
            ((platform_data - start_value) / start_value * 100)
            if metric == "percentage"
            else (platform_data - start_value)
        )
        plt.plot(platform_data.index, growth, label=platform)

    metric_label = f"Growth (%) ({label})" if metric == "percentage" else f"Growth (Absolute) ({label})"
    plt.title(f"Platform Comparison: {metric_label}")
    plt.xlabel("Date")
    plt.ylabel(metric_label)
    plt.legend()
    st.pyplot(plt)

# Generate Visualization for Growth (Social or Monetary)
def plot_data(df, artists, platforms, start_date, end_date, monetary=False):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    adjusted_platforms = get_monetary_platforms(platforms, monetary)

    filtered_df = df[
        (df['Artist Name'].isin(artists)) &
        (df['Date'] >= start_date) &
        (df['Date'] <= end_date)
    ]

    label = "Revenue" if monetary else "Followers"
    st.subheader(f"Line Chart: Growth Over Time ({label})")
    for platform, adjusted_platform in zip(platforms, adjusted_platforms):
        plt.figure(figsize=(10, 6))
        for artist in artists:
            artist_data = filtered_df[filtered_df['Artist Name'] == artist]
            if adjusted_platform not in artist_data.columns:
                st.error(f"Column '{adjusted_platform}' not found for {artist} on {platform}. Please ensure your CSV file includes this column for monetary data.")
                continue
            revenue_data = artist_data[adjusted_platform]
            if monetary:
                revenue_data = revenue_data / 100
            plt.plot(artist_data['Date'], revenue_data, label=artist)
            if revenue_data.empty:
                st.warning(f"No data available for {artist} on {platform} within the selected date range.")
                continue
            growth_int, growth_pct = calculate_growth(revenue_data)
            growth_color = "green" if growth_int > 0 else "red"
            st.markdown(
                f"<span style='color:{growth_color};font-size:16px;'>"
                f"Growth for {artist} on {platform}: {growth_int} ({growth_pct:.2f}%)</span>",
                unsafe_allow_html=True,
            )
        plt.title(f"Growth on {platform} ({label})")
        plt.xlabel("Date")
        plt.ylabel(label)
        plt.legend()
        st.pyplot(plt)

    st.subheader(f"Bar Chart: Total {label} and Growth")
    latest_data = filtered_df[filtered_df['Date'] == filtered_df['Date'].max()]
    growth = latest_data.groupby('Artist Name')[adjusted_platforms].sum().reset_index()
    if monetary:
        growth[adjusted_platforms] = growth[adjusted_platforms] / 100
    st.bar_chart(growth.set_index('Artist Name'))

    st.subheader(f"Pie Chart: Total {label} by Platform")
    total = filtered_df[adjusted_platforms].sum()
    if monetary:
        total = total / 100
    if total.sum() == 0:
        st.warning(f"No data available for pie chart for {label}.")
    else:
        plt.figure(figsize=(8, 8))
        plt.pie(
            total,
            labels=platforms,
            autopct='%1.1f%%',
            startangle=140,
            colors=plt.cm.Paired.colors
        )
        plt.title(f"Total {label} by Platform")
        st.pyplot(plt)

    # Summary Section with Ranking
    st.subheader(f"Summary of {label} Growth")
    summary_data = {}
    for platform, adjusted_platform in zip(platforms, adjusted_platforms):
        total_start = filtered_df.groupby('Date')[adjusted_platform].first()
        total_end = filtered_df.groupby('Date')[adjusted_platform].last()
        if monetary:
            total_start = total_start / 100
            total_end = total_end / 100
        growth_int, growth_pct = calculate_growth(total_end)
        summary_data[platform] = (growth_int, growth_pct)
        growth_color = "green" if growth_int > 0 else "red"
        st.markdown(
            f"<span style='color:{growth_color};font-size:18px;'>"
            f"{platform} Growth: {growth_int} ({growth_pct:.2f}%)</span>",
            unsafe_allow_html=True,
        )

    # Rank Platforms by Growth
    st.subheader(f"Platform Ranking ({label})")
    ranking = pd.DataFrame.from_dict(
        summary_data,
        orient="index",
        columns=["Absolute Growth", "Percentage Growth"]
    ).sort_values(by="Percentage Growth", ascending=False)
    st.write(ranking)

    metric = st.radio(f"Select Metric for {label} Comparison", ["percentage", "absolute"])
    selected_platforms = st.multiselect(
        f"Select Platforms for {label} Comparison", platforms, default=platforms
    )
    summary_growth_chart(filtered_df, selected_platforms, metric, monetary)

# Main App with Sidebar Menu
st.title("Growth Dashboard")
menu = st.sidebar.selectbox("Select a View", ["Social Growth", "Monetary Growth"])

st.sidebar.header("Upload CSV File")
uploaded_file = st.sidebar.file_uploader("Upload your CSV file here", type=["csv"])

if uploaded_file:
    data = load_data(uploaded_file)
    st.write("Data Preview:")
    st.write(data.head())

    st.sidebar.header("Filters")
    artists = st.sidebar.multiselect("Select Artists", data['Artist Name'].unique())
    platforms = st.sidebar.multiselect(
        "Select Platforms", ["Facebook", "Instagram", "TikTok", "YouTube", "Spotify"]
    )
    date_range = st.sidebar.date_input(
        "Select Date Range",
        [data['Date'].min().date(), data['Date'].max().date()]
    )

    # Ensure date_range is always a tuple/list
    if isinstance(date_range, tuple) or isinstance(date_range, list):
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1]) if len(date_range) > 1 else start_date  # Handle single date selection
    else:
        start_date = pd.to_datetime(date_range)
        end_date = start_date  # Default to the same date if only one is selected

    if menu == "Social Growth":
        if artists and platforms:
            plot_data(data, artists, platforms, start_date, end_date, monetary=False)
        else:
            st.write("Please select at least one artist and one platform.")
    elif menu == "Monetary Growth":
        if artists and platforms:
            plot_data(data, artists, platforms, start_date, end_date, monetary=True)
        else:
            st.write("Please select at least one artist and one platform.")
else:
    st.write("Awaiting CSV file upload.")

st.sidebar.write("Ensure your CSV file has the following columns:")
st.sidebar.write("`Artist Name`, `Date`, `Facebook`, `Instagram`, `TikTok`, `YouTube`, `Spotify`.")