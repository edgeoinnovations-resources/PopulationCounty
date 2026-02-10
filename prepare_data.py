"""
Prepare US County Population Data for 3D Map
Fetches county GeoJSON + ACS 2024 population data, merges, and saves locally.
Run once: python prepare_data.py
"""
import json
import math
import os

import pandas as pd
import requests

print("=" * 70)
print("US County Population - Data Preparation")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. Download US county boundary GeoJSON (simplified 20m from Census via Plotly)
# ---------------------------------------------------------------------------
print("\n[1/5] Downloading US county boundaries...")
COUNTIES_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)
resp = requests.get(COUNTIES_URL, timeout=60)
resp.raise_for_status()
counties_geojson = resp.json()
print(f"       Loaded {len(counties_geojson['features']):,} county polygons")

# ---------------------------------------------------------------------------
# 2. Fetch ACS 2024 5-Year population data from Census Bureau API
#    Table B01003_001E = Total Population
# ---------------------------------------------------------------------------
print("[2/5] Fetching ACS 2024 population data from Census Bureau...")
CENSUS_URL = (
    "https://api.census.gov/data/2024/acs/acs5"
    "?get=NAME,B01003_001E"
    "&for=county:*"
    "&in=state:*"
)
resp = requests.get(CENSUS_URL, timeout=60)
resp.raise_for_status()
census_raw = resp.json()

# Parse: first row is header, rest is data
header = census_raw[0]
rows = census_raw[1:]
df = pd.DataFrame(rows, columns=header)

# Build 5-digit FIPS code (state + county)
df["FIPS"] = df["state"] + df["county"]

# Convert population to numeric (Census returns strings; -666666666 = missing)
df["population"] = pd.to_numeric(df["B01003_001E"], errors="coerce")
df = df[df["population"] > 0].copy()

print(f"       Loaded {len(df):,} counties with valid population data")
print(f"       Range: {df['population'].min():,.0f} - {df['population'].max():,.0f}")
print(f"       Median: {df['population'].median():,.0f}")

# ---------------------------------------------------------------------------
# 3. Compute derived fields
# ---------------------------------------------------------------------------
print("[3/5] Computing derived fields...")

# log10(population + 1) for extrusion — compresses huge range
df["log_pop"] = df["population"].apply(lambda x: math.log10(x + 1))

# Formatted population for tooltips
df["population_formatted"] = df["population"].apply(lambda x: f"{int(x):,}")

# ---------------------------------------------------------------------------
# 4. Compute quantile-based color ramp
#    blue -> cyan -> green -> yellow -> red
# ---------------------------------------------------------------------------
print("[4/5] Computing quantile-based colors...")

# Assign quantile rank (0.0 to 1.0) so rural counties get visual spread
df["quantile"] = df["population"].rank(pct=True)


def population_color(t):
    """Map quantile [0, 1] to a blue->cyan->green->yellow->red color ramp."""
    if t < 0.25:
        s = t / 0.25
        r, g, b = int(30), int(60 + 140 * s), int(150 + 105 * s)
    elif t < 0.5:
        s = (t - 0.25) / 0.25
        r, g, b = int(30 + 100 * s), int(200 + 55 * s), int(255 - 100 * s)
    elif t < 0.75:
        s = (t - 0.5) / 0.25
        r, g, b = int(130 + 125 * s), int(255 - 55 * s), int(155 - 105 * s)
    else:
        s = (t - 0.75) / 0.25
        r, g, b = int(255), int(200 - 130 * s), int(50 - 50 * s)
    return [r, g, b, 200]


df["fill_color"] = df["quantile"].apply(population_color)

# ---------------------------------------------------------------------------
# 5. Merge into GeoJSON and save
# ---------------------------------------------------------------------------
print("[5/5] Merging data into GeoJSON and saving...")

# Build lookup dict
value_lookup = {}
for _, row in df.iterrows():
    value_lookup[row["FIPS"]] = {
        "population": int(row["population"]),
        "population_formatted": row["population_formatted"],
        "log_pop": round(row["log_pop"], 4),
        "quantile": round(row["quantile"], 4),
        "fill_color": row["fill_color"],
        "county_name": row["NAME"],
    }

# Inject into GeoJSON properties
matched_features = []
for feature in counties_geojson["features"]:
    fips = feature.get("id") or feature["properties"].get("GEO_ID", "")[-5:]
    if fips in value_lookup:
        info = value_lookup[fips]
        feature["properties"]["population"] = info["population"]
        feature["properties"]["population_formatted"] = info["population_formatted"]
        feature["properties"]["log_pop"] = info["log_pop"]
        feature["properties"]["quantile"] = info["quantile"]
        feature["properties"]["fill_color"] = info["fill_color"]
        feature["properties"]["county_name"] = info["county_name"]
        feature["properties"]["fips"] = fips
        matched_features.append(feature)

counties_geojson["features"] = matched_features
print(f"       Matched {len(matched_features):,} counties")

# Save files
os.makedirs("data", exist_ok=True)

geojson_path = "data/us_counties_population.geojson"
with open(geojson_path, "w") as f:
    json.dump(counties_geojson, f)
geojson_size = os.path.getsize(geojson_path) / (1024 * 1024)
print(f"       Saved {geojson_path} ({geojson_size:.1f} MB)")

csv_path = "data/us_counties_population.csv"
df_out = df[["FIPS", "NAME", "population", "population_formatted", "log_pop", "quantile"]].copy()
df_out.to_csv(csv_path, index=False)
csv_size = os.path.getsize(csv_path) / 1024
print(f"       Saved {csv_path} ({csv_size:.0f} KB)")

print(f"\n{'=' * 70}")
print("SUCCESS: Data preparation complete")
print(f"{'=' * 70}")
print(f"\nNext: streamlit run app.py")
