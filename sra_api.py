import requests
import pandas as pd

import os
from dotenv import load_dotenv

load_dotenv()

# 1. SET YOUR API SUBSCRIPTION KEY
subscription_key = os.getenv("MY_SECRET_API_KEY")

# 2. API ENDPOINT URL
api_url = "https://sra-prod-apim.azure-api.net/datashare/api/V1/organisation/GetAll"

# 3. HEADERS
headers = {
    "Ocp-Apim-Subscription-Key": subscription_key,
    "Cache-Control": "no-cache"
}

print(f"Attempting to fetch data from: {api_url}")

try:
    # 4. MAKE THE API REQUEST
    response = requests.get(api_url, headers=headers)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        print("Data fetched successfully.")
        
        # Convert the JSON response to a Python dictionary
        data = response.json()
        
        organisations_list = None
        
        if 'Organisations' in data:
            organisations_list = data['Organisations']
        elif 'value' in data and isinstance(data['value'], list):
            organisations_list = data['value']
        elif isinstance(data, list):
            organisations_list = data
        else:
            print("Error: Could not find the list of organisations in the response.")
            print("Response content (first 500 chars):", str(data)[:500])
            exit()

        if organisations_list is not None and len(organisations_list) > 0:
            # Convert the list of organisations into a pandas DataFrame
            df = pd.DataFrame(organisations_list)

            # 6. SAVE TO EXCEL
            output_file = "sra_organisations.xlsx"
            df.to_excel(output_file, index=False)
            
            # The 'Count' key from your output tells us the total
            total_count = data.get('Count', len(df)) 
            print(f"Successfully saved {len(df)} organisations to {output_file} (Total count from API: {total_count})")
        
        elif organisations_list is not None and len(organisations_list) == 0:
            print("The request was successful, but the API returned 0 organisations.")
        
        else:
            print("Could not process the data.")


    else:
        # Handle other errors (e.g., 401 Unauthorized, 403 Forbidden)
        print(f"Error: API request failed with status code {response.status_code}")
        print("Response text:", response.text)
        if response.status_code == 401 or response.status_code == 403:
            print("\nThis 'Unauthorized' or 'Forbidden' error means your key is incorrect,")
            print("expired, or not subscribed to this API product.")


except requests.exceptions.RequestException as e:
    print(f"An error occurred during the request: {e}")
except Exception as e:
    print(f"An error occurred: {e}")