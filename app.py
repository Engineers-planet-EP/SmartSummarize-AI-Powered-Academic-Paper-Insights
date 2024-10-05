import streamlit as st
import PyPDF2
import docx
import openai
import os
import requests
import re

# Function to read PDF files with error handling
def read_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

# Function to read DOCX files with error handling
def read_docx(file):
    try:
        doc = docx.Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        return f"Error reading DOCX: {e}"

# Function to detect valid headings
def detect_headings(text):
    possible_headings = [
        "Abstract", "INTRODUCTION", "METHODOLOGY", "CONCLUSION", "Related Work",
        "Study Design", "Experimental Setup", "Datasets", "Experimental Results", 
        "Observations", "Future Work"
    ]
    
    detected_headings = []
    headings_pattern = re.compile(r'|'.join([r'\b' + re.escape(heading) + r'\b(?:\s*[-:])?' for heading in possible_headings]), re.IGNORECASE)
    
    for line in text.splitlines():
        cleaned_line = line.strip()
        match = headings_pattern.search(cleaned_line)
        if match:
            heading = match.group(0).capitalize().strip()  # Ensuring proper case formatting
            if heading not in detected_headings:
                detected_headings.append(heading)
    
    return detected_headings

# Function to find a heading's approximate location in the text
def find_heading_position(text, heading):
    heading_pattern = re.compile(re.escape(heading), re.IGNORECASE)
    match = heading_pattern.search(text)
    if match:
        return match.start()
    return -1  # Return -1 if not found

# Function to summarize text using Azure OpenAI API, avoiding references and repetition
def summarize_text(text, heading):
    api_key = os.getenv('OPENAI_API_KEY')  
    endpoint = os.getenv('API_END_POINT')  
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': api_key
    }
    
    data = {
        "model": "gpt-35-turbo",
        "prompt": (
            f"You are summarizing an academic paper section titled '{heading}'. "
            f"Summarize the key technical details relevant to the heading in no more than 100 words. "
            f"Focus on processes, algorithms, models used, and avoid including references, URLs, or redundant content. "
            f"Do not repeat phrases like 'Answer' or the heading itself. "
            f"Only include relevant details without general introductory statements or unrelated information.\n\n"
            f"Text:\n{text}"
        ),
        "max_tokens": 150,  # Enough tokens for a concise summary
        "temperature": 0.1,
        "frequency_penalty": 0.9,
        "presence_penalty": 0.7
    }
    
    response = requests.post(endpoint, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()['choices'][0]['text'].strip()
    else:
        return f"Error: {response.status_code} - {response.text}"

# App Layout

# Custom CSS for the title, background, and layout
st.markdown("""
    <style>
    /* Change the entire app background to white */
    .stApp {
        background-color: white;
    }
    
    /* Adjust the top title/heading and background to white */
    .main-title {
        background-color: white;
        color: black;  /* Ensure text is black */
        font-size: 35px;
        text-align: center;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Logo styling */
    .main-title img {
        margin-right: 10px;
    }
    
    /* Styling for text areas and outputs */
    .stTextArea textarea {
        background-color: white !important;
        color: black !important;  /* Ensure text is black */
        border: 1px solid #ccc;  /* Optional border */
    }
    
    /* Label for editable summaries */
    .edit-label {
        color: black;  /* Black font for the label */
        font-size: 18px;
        font-weight: bold;
    }

    </style>
    """, unsafe_allow_html=True)

# Adjust the layout to be completely white and black text for output
logo_path = 'logo/logo.jpg'

# Horizontal layout for logo and title
col1, col2 = st.columns([3, 6])
with col1:
    st.image(logo_path, width=180)
with col2:
    st.markdown("<h3 style='color: black; text-align: left;'>SmartSummarize: AI-Powered Academic Paper Insights</h3>", unsafe_allow_html=True)

# Sidebar for file upload
uploaded_file = st.sidebar.file_uploader("Upload your Research Paper or Thesis (PDF/DOCX)", type=["pdf", "docx"])

if uploaded_file:
    # Read and process the uploaded file
    if uploaded_file.type == "application/pdf":
        text = read_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = read_docx(uploaded_file)

    headings = detect_headings(text)
    
    if "headings" not in st.session_state:
        st.session_state.headings = headings

    st.sidebar.subheader("Detected Headings")
    
    if "selected_headings" not in st.session_state:
        st.session_state.selected_headings = []

    for heading in st.session_state.headings:
        if st.sidebar.checkbox(heading, key=f"heading_{heading}"):
            if heading not in st.session_state.selected_headings:
                st.session_state.selected_headings.append(heading)
        else:
            if heading in st.session_state.selected_headings:
                st.session_state.selected_headings.remove(heading)

    if st.session_state.selected_headings:
        for heading in st.session_state.selected_headings:
            heading_start = find_heading_position(text, heading)
            if heading_start == -1:
                st.warning(f"Heading '{heading}' not found in the document text.")
                continue
            
            # Try to find the next heading, or go to the end of the text
            next_heading_start = -1
            for next_heading in st.session_state.headings:
                if next_heading != heading:
                    pos = find_heading_position(text[heading_start + len(heading):], next_heading)
                    if pos != -1:
                        next_heading_start = heading_start + len(heading) + pos
                        break
            heading_end = next_heading_start if next_heading_start != -1 else len(text)
            
            heading_text = text[heading_start:heading_end].strip()

            if heading_text:
                if f"summary_{heading}" not in st.session_state:
                    summarized_text = summarize_text(heading_text, heading)
                    st.session_state[f"summary_{heading}"] = summarized_text
                
                # Label for editing the summary, now in black font
                st.markdown(f"<h3 style='color: black;'>{heading}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p class='edit-label'>Edit Summary for {heading}</p>", unsafe_allow_html=True)
                
                # Editable output using st.text_area with a white background and black text
                editable_summary = st.text_area(f"Edit Summary for {heading}", value=st.session_state[f"summary_{heading}"], height=200, key=f"textarea_{heading}")
                
                # Update session state with edited summary
                st.session_state[f"summary_{heading}"] = editable_summary
            else:
                st.warning(f"No content found under the heading '{heading}'.")
