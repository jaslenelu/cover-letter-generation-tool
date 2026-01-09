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

# Sidebar - Language selection first
st.sidebar.title("Configuration")

# Language selection
language = st.sidebar.selectbox(
    "Language / 語言",
    ("English", "繁體中文"),
    help="Select the language for the recommendation letter"
)

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
    st.sidebar.warning("Please enter your OpenAI API key to use this tool" if language == "English" else "請輸入您的 OpenAI API 密鑰")
else:
    st.sidebar.success("API key configured" if language == "English" else "API 密鑰已配置")

st.sidebar.markdown("---")

# UI
if language == "English":
    st.title("Academic Recommendation Letter Generator")
else:
    st.title("學術推薦信生成器")

st.sidebar.markdown("---")

recommender_role = st.sidebar.selectbox(
    "Your Role" if language == "English" else "您的角色",
    ("Professor", "Manager", "Supervisor", "Research Advisor") if language == "English"
    else ("教授", "經理", "主管", "研究顧問"),
    help="Select your role as a recommender" if language == "English" else "選擇您作為推薦人的角色"
)

st.sidebar.markdown("---")
if language == "English":
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
else:
    st.sidebar.markdown("""
### 使用方法
1. 在上方輸入您的 OpenAI API 密鑰
2. 選擇您的推薦人角色
3. 填寫候選人資訊
4. 上傳 PDF 或手動輸入文字
5. 點擊生成按鈕建立推薦信

### 取得 API 密鑰
前往 [OpenAI Platform](https://platform.openai.com/api-keys)
""")


# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input Information" if language == "English" else "輸入資訊")

    candidate_name = st.text_input(
        "Candidate Name *" if language == "English" else "候選人姓名 *",
        placeholder="e.g., John Doe" if language == "English" else "例如：王大明",
        help="Enter the name of the person you are recommending" if language == "English" else "輸入您要推薦的人的姓名"
    )

    target_program = st.text_input(
        "Target Program/Position *" if language == "English" else "目標項目/職位 *",
        placeholder="e.g., PhD in Computer Science at MIT" if language == "English" else "例如：台灣大學資訊工程博士班",
        help="Enter the program or position the candidate is applying for" if language == "English" else "輸入候選人申請的項目或職位"
    )

    st.markdown("### Upload PDF or Enter Text" if language == "English" else "### 上傳 PDF 或輸入文字")

    # PDF upload option
    uploaded_file = st.file_uploader(
        "Upload PDF (CV, Resume, etc.)" if language == "English" else "上傳 PDF（履歷、CV 等）",
        type=['pdf'],
        help="Upload a PDF file containing the candidate's information" if language == "English" else "上傳包含候選人資訊的 PDF 檔案"
    )

    # Text area for manual input
    raw_materials = st.text_area(
        "Or Enter Raw Materials Manually" if language == "English" else "或手動輸入原始資料",
        placeholder="Paste the candidate's CV, achievements, research experience, publications, skills, and any other relevant information here..." if language == "English" else "在此貼上候選人的履歷、成就、研究經驗、發表論文、技能及其他相關資訊...",
        help="Provide detailed information about the candidate that will be used to extract verifiable facts" if language == "English" else "提供候選人的詳細資訊，將用於提取可驗證的事實",
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
            if language == "English":
                st.success(f"PDF uploaded successfully! Extracted {len(pdf_text)} characters from {len(pdf_reader.pages)} pages.")
            else:
                st.success(f"PDF 上傳成功！從 {len(pdf_reader.pages)} 頁中提取了 {len(pdf_text)} 個字元。")
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}" if language == "English" else f"讀取 PDF 時發生錯誤：{str(e)}")

    st.markdown("---")
    generate_button = st.button(
        "Generate Recommendation Letter" if language == "English" else "生成推薦信",
        type="primary",
        use_container_width=True
    )

with col2:
    st.subheader("Generated Recommendation Letter" if language == "English" else "生成的推薦信")

    if generate_button:
        # Check API key first
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar" if language == "English" else "請在側邊欄輸入您的 OpenAI API 密鑰")
        else:
            # Combine PDF text and manual input
            combined_materials = ""
            if pdf_text:
                combined_materials += ("=== Content from PDF ===\n" if language == "English" else "=== PDF 內容 ===\n") + pdf_text + "\n\n"
            if raw_materials:
                combined_materials += ("=== Additional Information ===\n" if language == "English" else "=== 額外資訊 ===\n") + raw_materials

            # Validate required fields
            if not candidate_name or not target_program or not combined_materials.strip():
                st.error("Please fill in all required fields marked with * and provide either a PDF or text input" if language == "English" else "請填寫所有標有 * 的必填欄位，並提供 PDF 或文字輸入")
            else:
                with st.spinner("Generating your recommendation letter..." if language == "English" else "正在生成您的推薦信..."):
                    try:
                        # Build graph and prepare state
                        graph = build_graph(api_key, language)

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
                        st.error(f"Error generating letter: {str(e)}" if language == "English" else f"生成推薦信時發生錯誤：{str(e)}")
                        st.exception(e)

    # Display generated letter
    if st.session_state.generated_letter:
        # Show validation info with clear heading
        st.markdown("### Verification Results" if language == "English" else "### 驗證結果")
        risk = st.session_state.hallucination_risk

        if risk == "low":
            st.success("**Low Risk** - The letter is well-supported by verified facts." if language == "English" else "**低風險** - 推薦信內容有充分的事實支持。")
        elif risk == "medium":
            st.warning("**Medium Risk** - Some sentences may need more support." if language == "English" else "**中等風險** - 某些句子可能需要更多支持。")
        elif risk == "high":
            st.error("**High Risk** - Please review unsupported sentences below." if language == "English" else "**高風險** - 請檢查以下不受支持的句子。")
        else:
            st.info(f"Verification Status: {risk}" if language == "English" else f"驗證狀態：{risk}")

        # Show unsupported sentences if any
        if st.session_state.unsupported_sentences and len(st.session_state.unsupported_sentences) > 0:
            expander_title = f"Unsupported Sentences ({len(st.session_state.unsupported_sentences)} found)" if language == "English" else f"不受支持的句子（找到 {len(st.session_state.unsupported_sentences)} 個）"
            with st.expander(expander_title, expanded=True):
                for i, sentence in enumerate(st.session_state.unsupported_sentences, 1):
                    st.write(f"{i}. {sentence}")
        else:
            st.success("All sentences are supported by verified facts!" if language == "English" else "所有句子都有可驗證的事實支持！")

        # Show verified facts in an expander
        if st.session_state.verified_facts and len(st.session_state.verified_facts) > 0:
            facts_title = f"Verified Facts Extracted ({len(st.session_state.verified_facts)} facts)" if language == "English" else f"已提取的可驗證事實（{len(st.session_state.verified_facts)} 個）"
            with st.expander(facts_title, expanded=False):
                for i, fact in enumerate(st.session_state.verified_facts, 1):
                    st.markdown(f"**{i}. {fact.claim}**")
                    if language == "English":
                        st.markdown(f"   - Evidence: {fact.evidence}")
                        st.markdown(f"   - Confidence: {fact.confidence}")
                    else:
                        st.markdown(f"   - 證據：{fact.evidence}")
                        st.markdown(f"   - 可信度：{fact.confidence}")
                    st.markdown("---")

        st.markdown("---")

        # Display letter
        st.markdown("### Generated Letter" if language == "English" else "### 生成的推薦信")
        st.text_area(
            "Your Recommendation Letter" if language == "English" else "您的推薦信",
            value=st.session_state.generated_letter,
            height=400,
            help="You can copy this text or export it using the buttons below" if language == "English" else "您可以複製此文字或使用下方按鈕匯出"
        )

        # Export options
        st.subheader("Export Options" if language == "English" else "匯出選項")
        col_export1, col_export2, col_export3 = st.columns(3)

        with col_export1:
            # TXT Export
            txt_data = st.session_state.generated_letter.encode('utf-8')
            st.download_button(
                label="Download as TXT" if language == "English" else "下載為 TXT",
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
                label="Download as Word" if language == "English" else "下載為 Word",
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
                    label="Download as PDF" if language == "English" else "下載為 PDF",
                    data=pdf_buffer,
                    file_name=f"recommendation_letter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF export error: {str(e)}" if language == "English" else f"PDF 匯出錯誤：{str(e)}")
    else:
        st.info("Fill in the information on the left and click 'Generate Recommendation Letter' to start" if language == "English" else "填寫左側資訊並點擊「生成推薦信」開始")