"""LegalLens - Streamlit application entry point.

A Gen AI application that makes legal documents easier to understand.
Note: LegalLens provides legal INFORMATION, never legal advice.
"""

from pathlib import Path
import streamlit as st

from services.action_service import generate_action_plan
from services.compare_service import compare_documents
from services.qa_service import ask_question
from services.risk_service import analyze_risks
from services.simplify_service import simplify_document
from utils.doc_exporter import export_to_docx
from utils.file_reader import extract_text
from utils.legal_checker import is_likely_legal_document
from utils.security import sanitize_error_message, sanitize_html, sanitize_input


def render_ai_footer() -> None:
    """Render a small educational and non-advice disclaimer on every AI result."""
    st.caption(
        "⚖️ *AI-generated legal information. Always verify against the original document "
        "and consult a qualified lawyer.*"
    )


def update_active_document(new_text: str, new_name: str) -> None:
    """Update active document and invalidate cached analyses if the document changed."""
    sanitized_text = sanitize_input(new_text, max_length=100_000)
    if st.session_state.get("doc_text") != sanitized_text:
        st.session_state["doc_text"] = sanitized_text
        st.session_state["doc_name"] = sanitize_input(new_name, max_length=255)
        # Invalidate previous document's cached results
        st.session_state.pop("simplify_result", None)
        st.session_state.pop("risk_result", None)
        st.session_state.pop("qa_chat_history", None)
        st.session_state.pop("action_result", None)


def main() -> None:
    """Render the main LegalLens interface."""
    # Page configuration
    st.set_page_config(
        page_title="LegalLens - AI Legal Document Assistant",
        page_icon="⚖️",
        layout="wide",
    )

    # Styling: reduce excessive top padding and polish brand presentation
    st.markdown(
        """
        <style>
        /* Eliminate large empty gap at top of page */
        .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 2rem !important;
        }

        /* Rounded brand logo with subtle glow */
        .brand-logo-img img {
            border-radius: 14px;
            box-shadow: 0 4px 16px rgba(56, 189, 248, 0.25);
        }

        /* Polish sidebar branding */
        [data-testid="stSidebar"] .block-container {
            padding-top: 1.8rem !important;
        }

        /* Spacious, modern card/pill styling for tabs */
        div[data-baseweb="tab-list"],
        [data-testid="stTabs"] [role="tablist"] {
            gap: 14px !important;
            padding: 8px 0 16px 0 !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
            margin-top: 0.5rem !important;
            margin-bottom: 1.2rem !important;
        }

        button[data-baseweb="tab"],
        [data-testid="stTabs"] [role="tab"] {
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            padding: 10px 22px !important;
            border-radius: 12px !important;
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.09) !important;
            color: #94a3b8 !important;
            transition: all 0.2s ease-in-out !important;
        }

        button[data-baseweb="tab"]:hover,
        [data-testid="stTabs"] [role="tab"]:hover {
            background: rgba(56, 189, 248, 0.1) !important;
            color: #f1f5f9 !important;
            border-color: rgba(56, 189, 248, 0.35) !important;
        }

        button[data-baseweb="tab"][aria-selected="true"],
        [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: rgba(56, 189, 248, 0.18) !important;
            color: #38bdf8 !important;
            border-color: #38bdf8 !important;
            box-shadow: 0 4px 16px rgba(56, 189, 248, 0.25) !important;
        }

        /* Hide the default skinny underline indicator */
        div[data-baseweb="tab-highlight"],
        div[data-baseweb="tab-border"] {
            display: none !important;
        }

        /* WCAG 2.4.7 Focus Visible: Clear keyboard focus indicator */
        button:focus-visible,
        [tabindex]:focus-visible,
        input:focus-visible,
        select:focus-visible,
        textarea:focus-visible,
        [role="tab"]:focus-visible {
            outline: 2px solid #38bdf8 !important;
            outline-offset: 2px !important;
        }

        /* WCAG 1.4.3 Contrast: Ensure text passes 7:1 contrast ratio */
        .stMarkdown p, .stMarkdown li, .stMarkdown span {
            color: #f1f5f9 !important;
        }

        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


    # Brand Header with Logo and Title
    logo_path = Path(__file__).parent / "assets" / "logo.jpg"
    col_logo, col_title = st.columns([1, 11])
    with col_logo:
        if logo_path.exists():
            st.markdown('<div class="brand-logo-img" role="img" aria-label="LegalLens Logo - AI Legal Document Assistant">', unsafe_allow_html=True)
            st.image(str(logo_path), width=76)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("## ⚖️")
    with col_title:
        st.markdown(
            "<h1 style='margin-bottom: 2px; padding-top: 0px;'>LegalLens "
            "<span style='font-size: 0.85rem; font-weight: 500; vertical-align: middle; "
            "background: rgba(56, 189, 248, 0.12); color: #38bdf8; padding: 4px 12px; "
            "border-radius: 16px; border: 1px solid rgba(56, 189, 248, 0.28); margin-left: 8px;'>"
            "AI Legal Document Assistant</span></h1>",
            unsafe_allow_html=True,
        )
        st.caption(
            "AI-assisted legal document understanding. "
            "Provides legal information only, never legal advice."
        )

    # How it works overview section
    with st.expander("ℹ️ How LegalLens Works", expanded=not bool(st.session_state.get("doc_text"))):
        step1, step2, step3 = st.columns(3)
        with step1:
            st.markdown("#### 1. Upload Document")
            st.write(
                "Upload a PDF, Word (.docx), or plain text contract, lease, or agreement "
                "via the sidebar, or click **Load sample contract** to explore immediately."
            )
        with step2:
            st.markdown("#### 2. Choose Analysis")
            st.write(
                "Switch between **Simplify** (plain-language summary), **Risks** (score & clause flags), "
                "**Ask** (grounded Q&A), or **Compare** (version differences)."
            )
        with step3:
            st.markdown("#### 3. Take Action")
            st.write(
                "Use the **Action Plan** tab to review your pre-signing checklist, copy questions "
                "for a lawyer, and download a complete Word (.docx) report."
            )


    # Initialize session state for document text
    if "doc_text" not in st.session_state:
        st.session_state["doc_text"] = ""
    if "doc_name" not in st.session_state:
        st.session_state["doc_name"] = ""

    # Sidebar: Branding, Document Upload & Sample Loader
    with st.sidebar:
        if logo_path.exists():
            col_sb_logo, col_sb_title = st.columns([1, 3])
            with col_sb_logo:
                st.markdown('<div class="brand-logo-img">', unsafe_allow_html=True)
                st.image(str(logo_path), width=48)
                st.markdown('</div>', unsafe_allow_html=True)
            with col_sb_title:
                st.markdown("<h3 style='margin: 0; padding-top: 4px;'>LegalLens</h3>", unsafe_allow_html=True)
                st.caption("AI Assistant")
            st.markdown("---")

        st.header("📄 Document Upload")
        uploaded_file = st.file_uploader(
            "Upload a legal document",
            type=["pdf", "docx", "txt"],
            help="Upload a contract, lease, or legal agreement in PDF, DOCX, or TXT format.",
        )

        if uploaded_file is not None:
            try:
                extracted = extract_text(uploaded_file)
                update_active_document(extracted, uploaded_file.name)
                st.success(f"Loaded: {uploaded_file.name}")
            except Exception as exc:
                st.error(f"Error reading file: {sanitize_error_message(exc)}")

        st.markdown("---")
        st.subheader("💡 Try a Sample")
        sample_path = Path(__file__).parent / "tests" / "sample_contract.txt"

        if st.button("Load sample contract", use_container_width=True):
            if sample_path.exists():
                with open(sample_path, "r", encoding="utf-8") as f:
                    sample_content = f.read()
                update_active_document(sample_content, "sample_contract.txt")
                st.success("Loaded sample rental agreement!")
            else:
                st.error("Sample contract file not found.")

        # Show status indicator if a document is loaded
        if st.session_state["doc_text"]:
            st.markdown("---")
            st.markdown(f"**Active Document:** `{st.session_state['doc_name']}`")
            st.caption(f"{len(st.session_state['doc_text']):,} characters loaded")

        # Sidebar Privacy & Legal Notice
        st.markdown("---")
        st.info("🔒 **Privacy**: Documents are processed in-session and not stored.")
        st.caption("⚖️ **Legal Notice**: LegalLens provides general information, not legal advice. Consult a qualified lawyer for your situation.")

    # Document-type check warning
    if st.session_state["doc_text"] and not is_likely_legal_document(st.session_state["doc_text"]):
        st.warning(
            "⚠️ **Document Notice**: The uploaded text does not appear to be a standard legal document "
            "(e.g., contract, agreement, or lease). AI analysis may be less accurate."
        )

    # Five main feature tabs with icons and clear labels
    tab_simplify, tab_risks, tab_ask, tab_compare, tab_action_plan = st.tabs(
        [
            "📄 Simplify",
            "⚠️ Risks",
            "💬 Ask",
            "⚖️ Compare",
            "📋 Action Plan",
        ]
    )


    with tab_simplify:
        st.header("Simplify Document")
        st.write("Get a clear, plain-language summary of the loaded legal document.")

        if not st.session_state["doc_text"]:
            st.info(
                "👈 Please upload a legal document or click **'Load sample contract'** "
                "in the sidebar to get started."
            )
        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                reading_level = st.radio(
                    "Reading Level",
                    options=["Simple", "Explain like I'm 15"],
                    horizontal=True,
                )
            with col2:
                language = st.selectbox(
                    "Language",
                    options=["English", "Hindi", "Kannada"],
                )

            if st.button("Simplify", type="primary"):
                with st.spinner("Analyzing document with Gemini..."):
                    try:
                        result = simplify_document(
                            st.session_state["doc_text"],
                            reading_level=reading_level,
                            language=language,
                        )
                        st.session_state["simplify_result"] = result
                    except Exception as exc:
                        st.error(f"Failed to simplify document: {sanitize_error_message(exc)}")

            # Display results if available
            if "simplify_result" in st.session_state:
                res = st.session_state["simplify_result"]

                st.markdown("---")
                st.subheader(f"📄 Document Type: {res.get('document_type', 'Not specified')}")
                st.write(res.get("one_paragraph_summary", ""))

                st.subheader("📌 Key Points")
                for point in res.get("key_points", []):
                    st.markdown(f"- {point}")

                glossary = res.get("jargon_glossary", [])
                if glossary:
                    with st.expander("📖 Jargon Glossary", expanded=True):
                        for item in glossary:
                            term = item.get("term", "")
                            meaning = item.get("simple_meaning", "")
                            st.markdown(f"- **{term}**: {meaning}")

                st.caption(f"Reading Level: {res.get('reading_level_used', reading_level)}")
                st.markdown("---")
                render_ai_footer()


    with tab_risks:
        st.header("Risk & Clause Analysis")
        st.write(
            "Identify notable clauses, assess potential risks, and check for document inconsistencies."
        )

        if not st.session_state["doc_text"]:
            st.info(
                "👈 Please upload a legal document or click **'Load sample contract'** "
                "in the sidebar to get started."
            )
        else:
            if st.button("Analyze Risks", type="primary"):
                with st.spinner("Analyzing clauses, inconsistencies, and risk levels..."):
                    try:
                        result = analyze_risks(st.session_state["doc_text"])
                        st.session_state["risk_result"] = result
                    except Exception as exc:
                        st.error(f"Failed to analyze risks: {sanitize_error_message(exc)}")

            if "risk_result" in st.session_state:
                res = st.session_state["risk_result"]

                # Overall risk score metric
                score = res.get("overall_risk_score", 0)
                st.markdown("---")
                col_metric, col_summary = st.columns([1, 2])
                with col_metric:
                    st.metric(label="Overall Risk Score", value=f"{score} / 100")
                with col_summary:
                    if score < 35:
                        st.success("🟢 **Low Risk**: The document appears to contain mostly standard, balanced terms.")
                    elif score < 70:
                        st.warning("🟠 **Medium Risk**: Contains clauses that require careful attention and clarification.")
                    else:
                        st.error("🔴 **High Risk**: Heavily one-sided or contains strict penalties and liability terms.")

                # Inconsistencies section
                inconsistencies = res.get("inconsistencies", [])
                if inconsistencies:
                    st.subheader("⚠️ Document Inconsistencies")
                    for inc in inconsistencies:
                        st.warning(f"• {inc}")

                # Clause Filters
                st.subheader("📋 Analyzed Clauses")
                filter_col1, filter_col2 = st.columns(2)
                with filter_col1:
                    category_options = [
                        "All",
                        "Payment",
                        "Termination",
                        "Liability",
                        "Privacy",
                        "Penalty",
                        "Renewal",
                        "Other",
                    ]
                    selected_cat = st.selectbox("Filter by Category", category_options)
                with filter_col2:
                    level_options = ["All", "High", "Medium", "Low"]
                    selected_level = st.selectbox("Filter by Risk Level", level_options)

                # Filter clauses
                clauses = res.get("clauses", [])
                filtered = [
                    c
                    for c in clauses
                    if (selected_cat == "All" or c.get("category") == selected_cat)
                    and (selected_level == "All" or c.get("risk_level") == selected_level)
                ]

                if not filtered:
                    st.info("No clauses match the selected filters.")
                else:
                    for clause in filtered:
                        risk_lvl = clause.get("risk_level", "Low")
                        category = clause.get("category", "Other")
                        title = clause.get("clause_title", "Clause")
                        quote = clause.get("exact_quote", "")
                        explanation = clause.get("plain_explanation", "")
                        why = clause.get("why_it_matters", "")
                        question = clause.get("suggested_question_to_ask", "")
                        verification = clause.get("verification_status", "verified")

                        # Color badges for risk level
                        if risk_lvl == "High":
                            badge = "🔴 :red[**HIGH RISK**]"
                        elif risk_lvl == "Medium":
                            badge = "🟠 :orange[**MEDIUM RISK**]"
                        else:
                            badge = "🟢 :green[**LOW RISK**]"

                        # Verification badge
                        verification_badge = (
                            "✅ :green[Quote Verified]"
                            if verification == "verified"
                            else "⚠️ :red[**Unverified Quote - not found in text**]"
                        )

                        with st.container(border=True):
                            st.markdown(f"### {title} | {badge} | `{category}`")
                            st.markdown(f"**Verification:** {verification_badge}")
                            st.markdown("**Source Quote:**")
                            st.markdown(f"> *\"{quote}\"*")
                            st.markdown(f"**Plain Explanation:** {explanation}")
                            st.markdown(f"**Why It Matters:** {why}")
                            st.markdown(f"**Suggested Question to Ask:** *{question}*")

                st.markdown("---")
                render_ai_footer()



    with tab_ask:
        st.header("Ask LegalLens")
        st.write("Ask any question about your document. Answers are strictly grounded in the document text.")

        if not st.session_state["doc_text"]:
            st.info(
                "👈 Please upload a legal document or click **'Load sample contract'** "
                "in the sidebar to start asking questions."
            )
        else:
            # Initialize chat history in session state
            if "qa_chat_history" not in st.session_state:
                st.session_state["qa_chat_history"] = []

            # Clickable suggested questions
            st.markdown("**Suggested questions:**")
            col_sq1, col_sq2, col_sq3 = st.columns(3)
            prompt_to_process = None

            with col_sq1:
                if st.button("❓ Can I terminate early?", use_container_width=True):
                    prompt_to_process = "Can I terminate early?"
            with col_sq2:
                if st.button("⚠️ What are the penalties?", use_container_width=True):
                    prompt_to_process = "What are the penalties?"
            with col_sq3:
                if st.button("📋 What are my obligations?", use_container_width=True):
                    prompt_to_process = "What are my obligations?"

            # Text chat input with length limit
            user_input = st.chat_input("Ask a question about this document...", max_chars=1000)
            if user_input:
                prompt_to_process = user_input

            # Render existing chat history
            for msg in st.session_state["qa_chat_history"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    quotes = msg.get("quotes", [])
                    if quotes:
                        with st.expander("📌 Supporting Quotes"):
                            for q in quotes:
                                st.markdown(f"> *\"{q}\"*")
                    if msg.get("needs_lawyer"):
                        st.info("⚖️ **Note**: This topic may involve legal rights or questions not fully addressed in the document. Consider consulting a lawyer.")

            # Process new query if submitted
            if prompt_to_process:
                # Add user message to state and display
                st.session_state["qa_chat_history"].append({"role": "user", "content": prompt_to_process})
                with st.chat_message("user"):
                    st.write(prompt_to_process)

                with st.chat_message("assistant"):
                    with st.spinner("Reviewing document..."):
                        try:
                            # Pass existing history (excluding current question)
                            res = ask_question(
                                document_text=st.session_state["doc_text"],
                                question=prompt_to_process,
                                chat_history=st.session_state["qa_chat_history"][:-1],
                            )
                            answer = res.get("answer", "")
                            quotes = res.get("supporting_quotes", [])
                            needs_lawyer = res.get("needs_lawyer", False)

                            st.write(answer)
                            if quotes:
                                with st.expander("📌 Supporting Quotes"):
                                    for q in quotes:
                                        st.markdown(f"> *\"{q}\"*")
                            if needs_lawyer:
                                st.info("⚖️ **Note**: This topic may involve legal rights or questions not fully addressed in the document. Consider consulting a lawyer.")

                            st.session_state["qa_chat_history"].append({
                                "role": "assistant",
                                "content": answer,
                                "quotes": quotes,
                                "confidence": res.get("confidence", "Medium"),
                                "needs_lawyer": needs_lawyer,
                            })
                        except Exception as exc:
                            st.error(f"Error answering question: {sanitize_error_message(exc)}")

            if st.session_state["qa_chat_history"]:
                st.markdown("---")
                render_ai_footer()


    with tab_compare:
        st.header("Compare Documents")
        st.write(
            "Compare two contracts or versions of an agreement to see differences, "
            "missing clauses, and which version is more favorable to you."
        )

        # Initialize session state for comparison documents
        if "doc_a_text" not in st.session_state:
            st.session_state["doc_a_text"] = ""
        if "doc_a_name" not in st.session_state:
            st.session_state["doc_a_name"] = ""
        if "doc_b_text" not in st.session_state:
            st.session_state["doc_b_text"] = ""
        if "doc_b_name" not in st.session_state:
            st.session_state["doc_b_name"] = ""

        # Sample versions button
        col_sample, _ = st.columns([1, 2])
        with col_sample:
            if st.button("📋 Load 2 sample versions", use_container_width=True):
                sample_v1 = Path(__file__).parent / "tests" / "sample_contract_v1.txt"
                sample_v2 = Path(__file__).parent / "tests" / "sample_contract_v2.txt"

                if sample_v1.exists() and sample_v2.exists():
                    with open(sample_v1, "r", encoding="utf-8") as f:
                        new_text_a = f.read()
                    with open(sample_v2, "r", encoding="utf-8") as f:
                        new_text_b = f.read()

                    if st.session_state["doc_a_text"] != new_text_a or st.session_state["doc_b_text"] != new_text_b:
                        st.session_state["doc_a_text"] = new_text_a
                        st.session_state["doc_a_name"] = "sample_contract_v1.txt"
                        st.session_state["doc_b_text"] = new_text_b
                        st.session_state["doc_b_name"] = "sample_contract_v2.txt"
                        st.session_state.pop("compare_result", None)

                    st.success("Loaded Sample Version 1 (Document A) and Version 2 (Document B)!")
                else:
                    st.error("Sample comparison contracts not found in tests/ directory.")

        # Document uploaders for A and B
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Document A")
            uploaded_a = st.file_uploader(
                "Upload Document A",
                type=["pdf", "docx", "txt"],
                key="uploader_doc_a",
            )
            if uploaded_a:
                try:
                    new_text_a = extract_text(uploaded_a)
                    if st.session_state["doc_a_text"] != new_text_a:
                        st.session_state["doc_a_text"] = new_text_a
                        st.session_state["doc_a_name"] = uploaded_a.name
                        st.session_state.pop("compare_result", None)
                    st.success(f"Loaded: {uploaded_a.name}")
                except Exception as exc:
                    st.error(f"Error reading Document A: {exc}")

            if st.session_state["doc_a_name"]:
                st.caption(f"Active: `{st.session_state['doc_a_name']}` ({len(st.session_state['doc_a_text'])} chars)")

        with col_b:
            st.subheader("Document B")
            uploaded_b = st.file_uploader(
                "Upload Document B",
                type=["pdf", "docx", "txt"],
                key="uploader_doc_b",
            )
            if uploaded_b:
                try:
                    new_text_b = extract_text(uploaded_b)
                    if st.session_state["doc_b_text"] != new_text_b:
                        st.session_state["doc_b_text"] = new_text_b
                        st.session_state["doc_b_name"] = uploaded_b.name
                        st.session_state.pop("compare_result", None)
                    st.success(f"Loaded: {uploaded_b.name}")
                except Exception as exc:
                    st.error(f"Error reading Document B: {exc}")

            if st.session_state["doc_b_name"]:
                st.caption(f"Active: `{st.session_state['doc_b_name']}` ({len(st.session_state['doc_b_text'])} chars)")

        st.markdown("---")

        # Compare action button
        can_compare = bool(st.session_state["doc_a_text"] and st.session_state["doc_b_text"])
        if not can_compare:
            st.info("👈 Please load or upload both Document A and Document B to compare them.")
        else:
            if st.button("Compare Documents", type="primary"):
                with st.spinner("Analyzing differences, favorability, and clauses..."):
                    try:
                        result = compare_documents(
                            doc_a_text=st.session_state["doc_a_text"],
                            doc_b_text=st.session_state["doc_b_text"],
                        )
                        st.session_state["compare_result"] = result
                    except Exception as exc:
                        st.error(f"Failed to compare documents: {sanitize_error_message(exc)}")

            if "compare_result" in st.session_state:
                res = st.session_state["compare_result"]

                # Display any truncation warnings
                trunc_warnings = res.get("truncation_warnings", [])
                for tw in trunc_warnings:
                    st.warning(f"⚠️ {tw}")

                # Overall recommendation
                rec = res.get("overall_recommendation_for_signer", "")
                if rec:
                    st.subheader("💡 Overall Signer Summary")
                    st.info(rec)

                # Differences Table
                differences = res.get("differences", [])
                if differences:
                    st.subheader("📊 Key Differences Table")
                    table_rows = []
                    for d in differences:
                        fav = d.get("which_is_more_favorable_to_signer", "Neither")
                        fav_badge = (
                            "🟢 Document A" if fav == "A"
                            else "🟢 Document B" if fav == "B"
                            else "⚪ Neither"
                        )
                        table_rows.append({
                            "Topic": d.get("topic", ""),
                            "Document A": d.get("document_a_says", ""),
                            "Document B": d.get("document_b_says", ""),
                            "More Favorable": fav_badge,
                        })
                    st.dataframe(table_rows, use_container_width=True)

                    # Expander per difference for the impact explanation
                    st.subheader("🔍 Detailed Impact Analysis")
                    for d in differences:
                        fav = d.get("which_is_more_favorable_to_signer", "Neither")
                        topic = d.get("topic", "Difference")
                        with st.expander(f"📌 {topic} (More Favorable: {fav})"):
                            st.markdown(f"**Document A says:** {d.get('document_a_says', '')}")
                            st.markdown(f"**Document B says:** {d.get('document_b_says', '')}")
                            st.markdown(f"**Impact on Signer:** {d.get('impact_explanation', '')}")

                # Missing clauses in each document
                missing = res.get("missing_clauses_in_each", {})
                missing_a = missing.get("missing_in_a", [])
                missing_b = missing.get("missing_in_b", [])

                if missing_a or missing_b:
                    st.subheader("📑 Missing Clauses")
                    col_ma, col_mb = st.columns(2)
                    with col_ma:
                        st.markdown("**Present in B, but Missing in A:**")
                        if missing_a:
                            for item in missing_a:
                                st.markdown(f"- ❌ {item}")
                        else:
                            st.markdown("*(None identified)*")

                    with col_mb:
                        st.markdown("**Present in A, but Missing in B:**")
                        if missing_b:
                            for item in missing_b:
                                st.markdown(f"- ❌ {item}")
                        else:
                            st.markdown("*(None identified)*")

                st.markdown("---")
                render_ai_footer()


    with tab_action_plan:
        st.header("Action Plan & Next Steps")
        st.write(
            "Review your pre-signing checklist, track key deadlines, and prepare questions for legal counsel."
        )

        if not st.session_state["doc_text"]:
            st.info(
                "👈 Please upload a legal document or click **'Load sample contract'** "
                "in the sidebar to generate an action plan."
            )
        else:
            col_act_btn, col_exp_btn = st.columns([1, 1])
            with col_act_btn:
                if st.button("Generate Action Plan", type="primary"):
                    with st.spinner("Creating checklist, deadlines, and questions for counsel..."):
                        try:
                            result = generate_action_plan(st.session_state["doc_text"])
                            st.session_state["action_result"] = result
                        except Exception as exc:
                            st.error(f"Failed to generate action plan: {sanitize_error_message(exc)}")

            # Export button available whenever analysis is present
            with col_exp_btn:
                # Prepare Word document export
                doc_bytes = export_to_docx(
                    summary_data=st.session_state.get("simplify_result"),
                    risks_data=st.session_state.get("risk_result"),
                    action_data=st.session_state.get("action_result"),
                    doc_name=st.session_state.get("doc_name", "Document"),
                )
                clean_name = Path(st.session_state.get("doc_name", "document")).stem
                st.download_button(
                    label="📥 Download as Word file (.docx)",
                    data=doc_bytes.getvalue(),
                    file_name=f"LegalLens_Report_{clean_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

            if "action_result" in st.session_state:
                res = st.session_state["action_result"]

                st.markdown("---")

                # Checklist before signing with interactive checkboxes
                st.subheader("✅ Pre-Signing Checklist")
                st.caption("Review and check off items as you verify them before signing:")
                checklist = res.get("checklist_before_signing", [])
                for idx, item in enumerate(checklist):
                    st.checkbox(item, key=f"action_chk_{idx}")

                # Obligations & Deadlines
                st.subheader("📅 Obligations & Deadlines")
                obligations = res.get("obligations_and_deadlines", [])
                if obligations:
                    st.dataframe(obligations, use_container_width=True)

                # Questions for a Lawyer (8-10 questions)
                st.subheader("⚖️ Questions for a Lawyer")
                st.caption("Specific, targeted questions to ask an attorney before signing:")
                questions = res.get("questions_for_a_lawyer", [])
                for i, q in enumerate(questions, start=1):
                    st.markdown(f"**{i}.** {q}")

                # Possible Next Steps & Documents to Gather in two columns
                col_steps, col_docs = st.columns(2)
                with col_steps:
                    st.subheader("🚀 Possible Next Steps")
                    for step in res.get("possible_next_steps", []):
                        st.markdown(f"- {step}")

                with col_docs:
                    st.subheader("📁 Documents to Gather")
                    for d in res.get("documents_to_gather", []):
                        st.markdown(f"- 📄 {d}")

                st.markdown("---")
                render_ai_footer()

    # Global footer disclaimer
    st.markdown("---")
    st.caption(
        "⚖️ **Legal Notice**: LegalLens provides general legal information, not legal advice. "
        "Consult a qualified lawyer for your situation."
    )




if __name__ == "__main__":
    main()

