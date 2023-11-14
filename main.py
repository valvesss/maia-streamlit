import streamlit as st
from streamlit.logger import get_logger
import pandas as pd
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from maia.database import supabase

LOGGER = get_logger(__name__)


def run():
    st.set_page_config(
        page_title="MAIA",
        page_icon="👋",
    )

    st.title("Meus Arquivos")

    # Predefined files
    files = [
        {"Name": "Example1.pdf", "Type": "pdf", "Size": 1024},
        {"Name": "Example2.mp3", "Type": "mp3", "Size": 2048}
    ]

    # Initialize or reset session state for the file uploader
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0

    # Button to clear the uploaded files
    if st.button('Clear Uploaded Files'):
        st.session_state.uploader_key += 1
        
    # Section for file upload
    uploaded_files = st.file_uploader("Choose files", 
                                      accept_multiple_files=True,
                                      type=['mp3', 'pdf'])

    # Check if files are uploaded
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Store file details
            file_info = {
                "Name": uploaded_file.name,
                "Type": uploaded_file.type,
                "Size": uploaded_file.size
            }
            files.append(file_info)
        st.session_state.clear_uploader = False
    
    df = pd.DataFrame(files)
    df[''] = ['' for _ in range(len(df))]
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_selection(selection_mode='single', use_checkbox=True)
    gd.configure_side_bar(filters_panel=False, columns_panel=False)
    # Configure the checkbox column with a specific width
    gd.configure_column('', width=45)  # Adjust the width as needed
    gd.configure_column('Name', cellStyle={'textAlign': 'center'}, headerTextAlign='right',)
    gd.configure_column('Size', cellStyle={'textAlign': 'center'})
    gd.configure_column('Type', cellStyle={'textAlign': 'center'})
    gridoptions = gd.build()
    grid_table = AgGrid(df,
                        gridOptions=gridoptions,
                        update_mode=GridUpdateMode.SELECTION_CHANGED)            


if __name__ == "__main__":
    run()
