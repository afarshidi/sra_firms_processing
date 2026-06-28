import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# 1. API Setup
subscription_key = os.getenv("MY_SECRET_API_KEY")
api_url = "https://sra-prod-apim.azure-api.net/datashare/api/V1/organisation/GetAll"
headers = {"Ocp-Apim-Subscription-Key": subscription_key, "Cache-Control": "no-cache"}

print(f"Fetching data from: {api_url}")

try:
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        # 2. Extract list safely
        organisations_list = None
        if "Organisations" in data:
            organisations_list = data["Organisations"]
        elif "value" in data and isinstance(data["value"], list):
            organisations_list = data["value"]
        elif isinstance(data, list):
            organisations_list = data

        if organisations_list:
            # 3. Load into DataFrame natively (keeps objects completely intact)
            df = pd.DataFrame(organisations_list)

            # 4. Prepare nested columns for Parquet storage
            # Parquet requires complex list/dict columns to be cast to strings,
            # but unlike Excel, Parquet has NO maximum character limits.
            for col in ["Offices", "WorkArea"]:
                if col in df.columns:
                    df[col] = df[col].astype(str)

            # 5. Output to Parquet
            output_parquet = "sra_organisations.parquet"
            df.to_parquet(output_parquet, engine="pyarrow", index=False)

            print("\n" + "=" * 50)
            print(f"SUCCESS: Saved {len(df)} rows to {output_parquet}")
            print("=" * 50)
        else:
            print("No organization data found in response.")
    else:
        print(f"API failed with status code {response.status_code}")

except Exception as e:
    print(f"An error occurred: {e}")