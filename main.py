import streamlit as st
import requests
import time
import base64
import io
import json
from pypdf import PdfReader, PdfWriter 

API_URL = "https://afb01a368719.ngrok-free.app/api/process/OcrBytes" 

st.set_page_config(
    page_title="PDF Classification",
    layout="wide"
)
st.title("PDF Metadata Extractor & Splitter 📄✂️")
st.markdown("API - **process/OcrBytes**")
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

st.markdown("""
<style>
.download-button-link {
    display: inline-flex; align-items: center; justify-content: center; font-weight: 500;
    padding: 0.25rem 0.75rem; border-radius: 0.25rem; margin: 0.5rem 0 0.5rem 0; 
    line-height: 1.6; color: white !important; background-color: rgb(14, 17, 23); 
    transition: background-color 0.3s;
    text-decoration: none !important;
}
.download-button-link:hover {
    background-color: rgb(40, 40, 40); color: white !important; text-decoration: none; 
}
.pdf-viewer-iframe {
    width: 100%;
    height: 600px; 
    border: 2px solid #ccc;
    border-radius: 8px;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

# Process Button
if uploaded_file is not None:
    st.info(f"File **'{uploaded_file.name}'** uploaded successfully & ready for processing.")
    process_button = st.button("Process PDF", key="process_api")
    if process_button:
        
        # Prepare the file for the POST request
        file_bytes = uploaded_file.getvalue()
        files = {
            'file': (uploaded_file.name, file_bytes, 'application/pdf')
        }

        try:
            with st.status("Sending Request and Processing PDF...", expanded=True) as status_container:
                
                start_time = time.time()
                status_container.write(f"Sending file to API at `{API_URL}` to extract page ranges...")
                response = requests.post(
                    API_URL, 
                    files=files, 
                    headers={'accept': 'application/json'},
                    timeout=300 
                )
                end_time = time.time()
                duration = round(end_time - start_time, 2)

            if response.status_code == 200:
                data = response.json()
                
                status_container.update(
                    label=f"Metadata Extracted Successfully! (Time Taken:  {duration} seconds)", 
                    state="complete", 
                    expanded=False
                )
                
                st.success(f"API call successful in **{duration} seconds**! [local PDF splitting and preview.]")
                # 1. Convert Python dict to formatted JSON string
                json_string = json.dumps(data, indent=4)
                
                # 2. Use columns to put the button next to the expander title
                col1, col2 = st.columns([1, 4])
                
                with col1:
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_string,
                        file_name=f"{uploaded_file.name}_metadata.json",
                        mime="application/json",
                        key="json_download_key",
                        use_container_width=True 
                    )
                
                # with col2:
                #     # 3. Display Raw JSON Response in an expander
                #     with st.expander("View Raw JSON Response"):
                #         st.json(data)

                st.markdown("---")
                extracted_data = data.get("data", {}).get("extracted_data", {}).get("gpt_extraction_output", {})
                containers = extracted_data.get("containers", [])

                # 1. Display Raw JSON Response
                with st.expander("View Raw JSON Response"):
                    st.json(data)
                    
                # PDF Splitting and Preview Logic 
                if containers:
                    
                    st.header(f"Results: {len(containers)} Containers Split and Ready")
                    pdf_reader = PdfReader(io.BytesIO(file_bytes))
                    for container in containers:
                        container_id = container.get("container_number", "N/A")
                        page_start_api = container.get("page_start_number", None)
                        page_end_api = container.get("page_end_number", None)
                        
                        st.subheader(f"📦 Container: **{container_id}** (Pages: {page_start_api} - {page_end_api})")
                        
                        if page_start_api is not None and page_end_api is not None:
                            try:
                                start_index = page_start_api - 1
                                end_index = page_end_api 
                                
                                pdf_writer = PdfWriter()
                                
                                for page_num in range(start_index, end_index):
                                    pdf_writer.add_page(pdf_reader.pages[page_num])
                                    
                                output_pdf_stream = io.BytesIO()
                                pdf_writer.write(output_pdf_stream)
                                output_pdf_bytes = output_pdf_stream.getvalue()
                                
                                base64_pdf = base64.b64encode(output_pdf_bytes).decode('utf-8')
                                data_url = f"data:application/pdf;base64,{base64_pdf}"
                                
                                #  1. DOWNLOAD LINK 
                                file_name = f"{container_id}_pages_{page_start_api}-{page_end_api}.pdf"
                                download_link_html = f"""
                                    <a href="{data_url}" 
                                        download="{file_name}"
                                        class="download-button-link">
                                        Download Split {file_name}
                                    </a>
                                """
                                st.markdown(download_link_html, unsafe_allow_html=True)
                                
                                #  2. SPLIT PDF PREVIEW 
                                preview_html = f"""
                                <iframe class="pdf-viewer-iframe" 
                                    src="{data_url}" 
                                    title="Split PDF Preview for {container_id}">
                                </iframe>
                                """
                                st.markdown(preview_html, unsafe_allow_html=True)

                            except Exception as e:
                                st.error(f"Error splitting PDF for container {container_id}: {e}")
                        else:
                            st.warning(f"Missing page range metadata for container {container_id}. Skipping split.")
                        document_data = {k: v for k, v in container.items() if isinstance(v, dict)}
                        if document_data:
                            st.markdown("##### Extracted Split Document : Metadata:")
                            table_data = []
                            for doc_type, pages in document_data.items():
                                start = pages.get("page_start_number", "N/A")
                                end = pages.get("page_end_number", "N/A")
                                table_data.append({
                                    "Document Type": doc_type.replace('_', ' ').title(),
                                    "Page Range": f"Page {start} to {end}" if start != end else f"Page {start}"
                                })
                            st.table(table_data)
                        
                        st.markdown("---")
                        
                else:
                    st.warning("The API returned data, but no container information was extracted for splitting.")
                    
            elif response.status_code == 404:
                status_container.update(label="API Endpoint Not Found (Status 404)", state="error", expanded=True)
                st.error(f"Error: API endpoint not found (Status **{response.status_code}**).")
            else:
                status_container.update(label=f"API Request Failed (Status {response.status_code})", state="error", expanded=True)
                st.error(f"API call failed with status code: **{response.status_code}**")
                try:
                    st.json(response.json())
                except requests.exceptions.JSONDecodeError:
                    st.code(response.text)
                
        except requests.exceptions.Timeout:
            status_container.update(label="Request Timed Out!", state="error", expanded=True)
            st.error(f"API request timed out after **300 seconds**")
        except requests.exceptions.RequestException as e:
            status_container.update(label="Connection Error!", state="error", expanded=True)
            st.error(f"An error occurred during the API request. Error: **{e}**")
