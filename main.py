import streamlit as st
from graph import build_graph
from datetime import datetime
import io
from docx import Document
from fpdf import FPDF
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Recommendation Letter Generator",
    layout="wide"
)

# Initialize session state
if 'generated_letter' not in st.session_state:
    st.session_state.generated_letter = None
if 'hallucination_risk' not in st.session_state:
    st.session_state.hallucination_risk = None
if 'unsupported_sentences' not in st.session_state:
    st.session_state.unsupported_sentences = None
if 'verified_facts' not in st.session_state:
    st.session_state.verified_facts = None

# UI
st.title("Academic Recommendation Letter Generator")

# Sidebar
st.sidebar.title("Configuration")
st.sidebar.markdown("---")

# API Key input
api_key = st.sidebar.text_input(
    "OpenAI API Key *",
    type="password",
    placeholder="sk-...",
    help="Enter your OpenAI API key. Get one at https://platform.openai.com/api-keys"
)

# Check if API key is provided
if not api_key:
    st.sidebar.warning("Please enter your OpenAI API key to use this tool")
else:
    st.sidebar.success("API key configured")

st.sidebar.markdown("---")

recommender_role = st.sidebar.selectbox(
    "Your Role",
    ("Professor", "Manager", "Supervisor", "Research Advisor"),
    help="Select your role as a recommender"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### How to Use
1. Enter your OpenAI API key above
2. Select your role as recommender
3. Fill in candidate information
4. Upload PDF or enter text manually
5. Click Generate to create the letter

### Get API Key
Visit [OpenAI Platform](https://platform.openai.com/api-keys)
""")


# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input Information")

    candidate_name = st.text_input(
        "Candidate Name *",
        placeholder="e.g., John Doe",
        help="Enter the name of the person you are recommending"
    )

    target_program = st.text_input(
        "Target Program/Position *",
        placeholder="e.g., PhD in Computer Science at MIT",
        help="Enter the program or position the candidate is applying for"
    )

    st.markdown("### Upload PDF or Enter Text")

    # PDF upload option
    uploaded_file = st.file_uploader(
        "Upload PDF (CV, Resume, etc.)",
        type=['pdf'],
        help="Upload a PDF file containing the candidate's information"
    )

    # Text area for manual input
    raw_materials = st.text_area(
        "Or Enter Raw Materials Manually",
        placeholder="Paste the candidate's CV, achievements, research experience, publications, skills, and any other relevant information here...",
        help="Provide detailed information about the candidate that will be used to extract verifiable facts",
        height=300
    )

    # Process PDF if uploaded
    pdf_text = ""
    if uploaded_file is not None:
        try:
            pdf_reader = PdfReader(uploaded_file)
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() + "\n"
            st.success(f"PDF uploaded successfully! Extracted {len(pdf_text)} characters from {len(pdf_reader.pages)} pages.")
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")

    st.markdown("---")
    generate_button = st.button("Generate Recommendation Letter", type="primary", use_container_width=True)

with col2:
    st.subheader("Generated Recommendation Letter")

    if generate_button:
        # Check API key first
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar")
        else:
            # Combine PDF text and manual input
            combined_materials = ""
            if pdf_text:
                combined_materials += "=== Content from PDF ===\n" + pdf_text + "\n\n"
            if raw_materials:
                combined_materials += "=== Additional Information ===\n" + raw_materials

            # Validate required fields
            if not candidate_name or not target_program or not combined_materials.strip():
                st.error("Please fill in all required fields marked with * and provide either a PDF or text input")
            else:
                with st.spinner("Generating your recommendation letter..."):
                    try:
                        # Build graph and prepare state
                        graph = build_graph(api_key)

                        initial_state = {
                            "candidate_name": candidate_name,
                            "recommender_role": recommender_role,
                            "target_program": target_program,
                            "raw_materials": combined_materials,
                            "verified_facts": [],
                            "draft_letter": None,
                            "hallucination_risk": None,
                            "unsupported_sentences": None
                        }

                        # Run the workflow
                        result = graph.invoke(initial_state)

                        # Store results in session state
                        st.session_state.generated_letter = result.get("draft_letter", "")
                        st.session_state.hallucination_risk = result.get("hallucination_risk", "unknown")
                        st.session_state.unsupported_sentences = result.get("unsupported_sentences", [])
                        st.session_state.verified_facts = result.get("verified_facts", [])

                    except Exception as e:
                        st.error(f"Error generating letter: {str(e)}")
                        st.exception(e)

    # Display generated letter
    if st.session_state.generated_letter:
        # Show validation info with clear heading
        st.markdown("### Verification Results")
        risk = st.session_state.hallucination_risk

        if risk == "low":
            st.success(" **Low Risk** - The letter is well-supported by verified facts.")
        elif risk == "medium":
            st.warning(" **Medium Risk** - Some sentences may need more support.")
        elif risk == "high":
            st.error(" **High Risk** - Please review unsupported sentences below.")
        else:
            st.info(f"Verification Status: {risk}")

        # Show unsupported sentences if any
        if st.session_state.unsupported_sentences and len(st.session_state.unsupported_sentences) > 0:
            with st.expander(f" Unsupported Sentences ({len(st.session_state.unsupported_sentences)} found)", expanded=True):
                for i, sentence in enumerate(st.session_state.unsupported_sentences, 1):
                    st.write(f"{i}. {sentence}")
        else:
            st.success(" All sentences are supported by verified facts!")

        # Show verified facts in an expander
        if st.session_state.verified_facts and len(st.session_state.verified_facts) > 0:
            with st.expander(f" Verified Facts Extracted ({len(st.session_state.verified_facts)} facts)", expanded=False):
                for i, fact in enumerate(st.session_state.verified_facts, 1):
                    st.markdown(f"**{i}. {fact.claim}**")
                    st.markdown(f"   - Evidence: {fact.evidence}")
                    st.markdown(f"   - Confidence: {fact.confidence}")
                    st.markdown("---")

        st.markdown("---")

        # Display letter
        st.markdown("### Generated Letter")
        st.text_area(
            "Your Recommendation Letter",
            value=st.session_state.generated_letter,
            height=400,
            help="You can copy this text or export it using the buttons below"
        )

        # Export options
        st.subheader("Export Options")
        col_export1, col_export2, col_export3 = st.columns(3)

        with col_export1:
            # TXT Export
            txt_data = st.session_state.generated_letter.encode('utf-8')
            st.download_button(
                label="Download as TXT",
                data=txt_data,
                file_name=f"recommendation_letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with col_export2:
            # Word Export
            doc = Document()
            doc.add_paragraph(st.session_state.generated_letter)

            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)

            st.download_button(
                label="Download as Word",
                data=buffer,
                file_name=f"recommendation_letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

        with col_export3:
            # PDF Export
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=11)

                # Handle text encoding for PDF
                text = st.session_state.generated_letter
                # Replace special characters that might cause issues
                text = text.encode('latin-1', 'replace').decode('latin-1')

                # Add text with proper line breaks
                for line in text.split('\n'):
                    if line.strip():
                        pdf.multi_cell(0, 5, txt=line)
                    else:
                        pdf.ln(3)

                pdf_buffer = io.BytesIO()
                pdf_output = pdf.output(dest='S').encode('latin-1')
                pdf_buffer.write(pdf_output)
                pdf_buffer.seek(0)

                st.download_button(
                    label="Download as PDF",
                    data=pdf_buffer,
                    file_name=f"recommendation_letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF export error: {str(e)}")
    else:
        st.info("Fill in the information on the left and click 'Generate Recommendation Letter' to start")