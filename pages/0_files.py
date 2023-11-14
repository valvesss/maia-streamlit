# Built-in libraries
from collections import OrderedDict

# 3rd part libraries
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridUpdateMode, ColumnsAutoSizeMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

# Local libraries
from maia.src.file import File

from pprint import pprint

user_id = "356f5ef1-6074-4f3d-9c03-778f44a4b08e"

st.set_page_config(
    page_title="Files",
    page_icon="📂",
    layout="wide"
)

st.title("Meus Arquivos")

def format_bytes(bytes):
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0

    while bytes >= 1024 and unit_index < len(units) - 1:
        bytes /= 1024
        unit_index += 1

    return f"{bytes:.2f} {units[unit_index]}"


backend_files = File(user_id).get_all_files()
formatted_files = []
for file in backend_files:
    table_file = {
        'Nome': file['name'],
        'Tipo': file['extension'],
        'Tamanho': format_bytes(file['size']),
        'Status': file['status']
    }
    formatted_files.append(table_file)
    
table_files = [OrderedDict([('', '')] + list(file.items())) for file in formatted_files]

# Section for file upload
uploaded_files = st.file_uploader("Selecione seus arquivos",
                                  help="Arraste e solte aqui",
                                  accept_multiple_files=True,
                                  type=['mp3', 'pdf'],
                                  label_visibility="hidden")

# Load dataframe
df = pd.DataFrame(table_files)

# Add Grid Options
gd = GridOptionsBuilder.from_dataframe(df)

gd.configure_selection(selection_mode='single', use_checkbox=True)

gd.configure_side_bar(filters_panel=False, 
                      columns_panel=False)

gd.configure_default_column(filterable=False)
gd.configure_column('', width=42)
gd.configure_column('id', hide=True)  # Hide the 'id' column
gd.configure_column('Nome', cellStyle={'textAlign': 'center'})
gd.configure_column('Tamanho', cellStyle={'textAlign': 'center'})
gd.configure_column('Tipo', cellStyle={'textAlign': 'center'})
gd.configure_column('Status', cellStyle={'textAlign': 'center'})

# Build Grid

custom_css = {
    # Style to centralize column headers
    ".ag-header-cell-label": {
        "justify-content": "center !important",
        "display": "flex",
        "align-items": "center"
    },
    ".ag-side-buttons": {
        "display": "none !important"
    },
}

grid_options = gd.build()
grid_options["scrollbarWidth"] = 8
grid_options["alwaysShowHorizontalScroll"] = True
grid_options["sideBar"] = False  # Disable the side bar
grid_table = AgGrid(df,
                    gridOptions=grid_options,
                    width="100%",
                    custom_css=custom_css,
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    update_mode=GridUpdateMode.SELECTION_CHANGED)

# Check if a row is selected
selected_rows = grid_table['selected_rows']
if selected_rows:
    # Process information from the selected row
    selected_row_data = selected_rows[0]  # Assuming single row selection
    st.write(f"Row ID: {selected_row_data['id']}")

# Function to update files list with uploaded files
def update_files_with_uploaded(uploaded_files):
    for uploaded_file in uploaded_files:
        file_info = {
            "Nome": uploaded_file.name,
            "Tipo": uploaded_file.type,
            "Tamanho": format_bytes(uploaded_file.size),
            "Status": "Carregando"
        }
        table_files.append(file_info)

    # Recreate DataFrame with updated files list
    # return table_files
    return [OrderedDict([('', '')] + list(file.items())) for file in table_files]

# Check if files are uploaded and update the grid
if uploaded_files:
    table_files += update_files_with_uploaded(uploaded_files)
    pprint(table_files)
    # grid_table.update_grid_data(df)
