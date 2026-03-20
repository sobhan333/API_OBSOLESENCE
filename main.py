import os
import requests
import customtkinter as ctk
from dotenv import load_dotenv

# Load environment variables from the .env file
# Load environment variables securely
load_dotenv()
MOUSER_API_KEY = os.getenv("MOUSER_API")
DIGIKEY_CLIENT_ID = os.getenv("DIGIKEY_CLIENT_ID")
DIGIKEY_CLIENT_SECRET = os.getenv("DIGIKEY_CLIENT_SECRET")

# Strip whitespace from keys just in case
if MOUSER_API_KEY: MOUSER_API_KEY = MOUSER_API_KEY.strip()
if DIGIKEY_CLIENT_ID: DIGIKEY_CLIENT_ID = DIGIKEY_CLIENT_ID.strip()
if DIGIKEY_CLIENT_SECRET: DIGIKEY_CLIENT_SECRET = DIGIKEY_CLIENT_SECRET.strip()
# Set the theme and color for CustomTkinter
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class PartCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Part Lifecycle Checker")
        self.geometry("600x450")

        # Create TabView
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(padx=20, pady=20, fill="both", expand=True)

        # Add Tabs
        self.tab_manual = self.tab_view.add("Manual Checker")
        self.tab_bom = self.tab_view.add("Automatic BOM Detection (WIP)")

        self.setup_manual_tab()
        self.setup_bom_tab()

    def setup_manual_tab(self):
        # --- UI Elements for Manual Tab ---
        
        # Manufacturer Dropdown
        # Wesco, EBHorsman, Gescan, and Westburne are included but currently 
        # lack public APIs for this specific endpoint. We will handle them in the logic.
        self.manufacturers = ["Mouser", "DigiKey", "Wesco", "EB Horsman (WIP)", "Gescan (WIP)", "Westburne (WIP)"]
        
        self.manufac_var = ctk.StringVar(value="Mouser")
        self.dropdown_manufac = ctk.CTkOptionMenu(self.tab_manual, values=self.manufacturers, variable=self.manufac_var)
        self.dropdown_manufac.pack(pady=(10, 10))

        # Part Number Search Bar
        self.entry_part = ctk.CTkEntry(self.tab_manual, placeholder_text="Enter Part Number (e.g., NE555DR)", width=300)
        self.entry_part.pack(pady=(0, 10))

        # Search Button
        self.btn_search = ctk.CTkButton(self.tab_manual, text="Search Part", command=self.perform_search)
        self.btn_search.pack(pady=(0, 10))

        # Output Text Box
        self.textbox_output = ctk.CTkTextbox(self.tab_manual, width=500, height=200)
        self.textbox_output.pack(pady=(10, 10), fill="both", expand=True)

    def setup_bom_tab(self):
        # --- UI Elements for BOM Tab (WIP) ---
        self.lbl_wip = ctk.CTkLabel(self.tab_bom, text="Automatic BOM Detection is a Work In Progress.", font=("Arial", 16))
        self.lbl_wip.pack(pady=50)

        '''
        TODO FOR LATER:
        1. Add a ctk.CTkButton here called "Upload Excel".
        2. Use `customtkinter.filedialog.askopenfilename()` to let the user select a .xlsx file.
        3. Use `import pandas as pd` to read the Excel file:
           df = pd.read_excel(filepath)
        4. Loop through the dataframe rows:
           for index, row in df.iterrows():
               part_num = row['Part Number Column Name']
               manufac = row['Manufacturer Column Name']
               # Call the respective API function here
        5. Output the results to a new Excel file or display them in a datagrid/textbox here.
        '''

    def perform_search(self):
        # Clear previous output
        self.textbox_output.delete("0.0", "end")
        
        part_number = self.entry_part.get().strip()
        manufacturer = self.manufac_var.get()

        if not part_number:
            self.textbox_output.insert("0.0", "Error: Please enter a part number.\n")
            return

        self.textbox_output.insert("end", f"Searching for '{part_number}' via {manufacturer}...\n\n")

        # --- API Routing Logic ---
        if manufacturer == "Mouser":
            self.search_mouser(part_number)
        elif manufacturer == "DigiKey":
            self.search_digikey(part_number)
        else:
            # Placeholder for the other manufacturers
            self.textbox_output.insert("end", f"API integration for {manufacturer} is not yet implemented or requires a custom B2B/EDI setup.\n")
            self.textbox_output.insert("end", "Please check their respective web portals for now.\n")


    def search_digikey(self, part_number):
            if not DIGIKEY_CLIENT_ID or not DIGIKEY_CLIENT_SECRET:
                self.textbox_output.insert("end", "Error: Digi-Key credentials missing in .env file.\n")
                return

            self.textbox_output.insert("end", "Authenticating with Digi-Key...\n")
            self.update() # Forces the UI to update so you see the auth message!

            # Step 1: Request an Access Token
            token_url = "https://api.digikey.com/v1/oauth2/token"
            token_data = {
                "client_id": DIGIKEY_CLIENT_ID,
                "client_secret": DIGIKEY_CLIENT_SECRET,
                "grant_type": "client_credentials"
            }

            try:
                token_res = requests.post(token_url, data=token_data)
                token_res.raise_for_status()
                access_token = token_res.json().get("access_token")
            except requests.exceptions.RequestException as e:
                self.textbox_output.insert("end", f"Digi-Key Auth Error: {e}\n")
                return

            # Step 2: Use the Token to Search for the Part
            search_url = "https://api.digikey.com/products/v4/search/keyword"
            headers = {
                "X-DIGIKEY-Client-Id": DIGIKEY_CLIENT_ID,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            payload = {"Keywords": part_number}

            try:
                search_res = requests.post(search_url, json=payload, headers=headers)
                search_res.raise_for_status()
                data = search_res.json()

                # Digi-Key V4 nests results in a few different possible arrays depending on the match type
                products = data.get("ExactManufacturerProducts", [])
                if not products:
                    products = data.get("Products", [])

                if products:
                    part = products[0]
                    
                    # Digi-Key loves nesting dictionaries. This safely extracts the strings.
                    mfg = part.get("Manufacturer", {})
                    mfg_name = mfg.get("Value", mfg.get("Name", "N/A")) if isinstance(mfg, dict) else str(mfg)
                    
                    status = part.get("ProductStatus", {})
                    status_val = status.get("Value", status.get("Status", "N/A")) if isinstance(status, dict) else str(status)

                    output_text = (
                        f"--- Digi-Key Results ---\n"
                        f"Manufacturer: {mfg_name}\n"
                        f"Description:  {part.get('ProductDescription', 'N/A')}\n"
                        f"Lifecycle:    {status_val}\n"
                        f"Stock:        {part.get('QuantityAvailable', 'N/A')}\n"
                    )
                    self.textbox_output.insert("end", output_text)
                else:
                    self.textbox_output.insert("end", "No part found with that number on Digi-Key.\n")

            except requests.exceptions.RequestException as e:
                self.textbox_output.insert("end", f"Digi-Key Search Error: {e}\n")


    def search_mouser(self, part_number):
        if not MOUSER_API_KEY:
            self.textbox_output.insert("end", "Error: MOUSER_API_KEY not found in .env file.\n")
            return

        url = f"https://api.mouser.com/api/v1/search/partnumber?apiKey={MOUSER_API_KEY}"
        payload = {
            "SearchByPartRequest": {
                "mouserPartNumber": part_number,
                "partSearchOptions": "string"
            }
        }
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 1. Check if the API returned an explicit error list
            if data.get('Errors'):
                # Extract error messages if they exist
                error_messages = ", ".join([err.get('Message', 'Unknown error') for err in data['Errors']])
                self.textbox_output.insert("end", f"Mouser API Error: {error_messages}\n")
                return

            # 2. Safely grab SearchResults (returns None if it's null in JSON)
            search_results = data.get('SearchResults')

            # 3. Check if search_results is valid AND has more than 0 results
            if search_results and search_results.get('NumberOfResult', 0) > 0:
                part = search_results['Parts'][0]
                
                # Format and display the output
                output_text = (
                    f"--- Mouser Results ---\n"
                    f"Manufacturer: {part.get('Manufacturer', 'N/A')}\n"
                    f"Description:  {part.get('Description', 'N/A')}\n"
                    f"Availability: {part.get('Availability', 'N/A')}\n"
                    f"Lifecycle:    {part.get('LifecycleStatus', 'N/A')}\n"
                    f"Data Sheet:   {part.get('DataSheetUrl', 'N/A')}\n"
                )
                self.textbox_output.insert("end", output_text)
            else:
                self.textbox_output.insert("end", "No part found with that number on Mouser.\n")

        except requests.exceptions.RequestException as e:
            self.textbox_output.insert("end", f"Network or HTTP Error: {e}\n")

if __name__ == "__main__":
    app = PartCheckerApp()
    app.mainloop()