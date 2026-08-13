# app.py

import streamlit as st
import os
from dotenv import load_dotenv
from graph import app
import time

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Multi-Agent Research Assistant 🤖",
    page_icon="🧠",
    layout="wide"
)

from agents import configure_agents

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("🧠 Model & Search Provider")
    
    llm_provider = st.selectbox(
        "LLM Provider",
        ["Google Gemini (Free)", "Groq (Free)", "Together AI"],
        index=0,
        help="Google Gemini and Groq offer generous 100% free tiers without credit card requirements."
    )
    
    if "Google Gemini" in llm_provider:
        provider_key_type = "google"
        model_options = [
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "Custom Model Name..."
        ]
        gemini_model_choice = st.selectbox(
            "Gemini Model",
            model_options,
            index=0,
            help="gemini-3.6-flash is Google's latest recommended flagship flash model."
        )
        if gemini_model_choice == "Custom Model Name...":
            chosen_model = st.text_input("Enter Model Name", value="gemini-3.6-flash")
        else:
            chosen_model = gemini_model_choice
            
        env_gemini = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        if env_gemini == "placeholder_key":
            env_gemini = ""
        api_key_input = st.text_input(
            "Google Gemini API Key",
            value=env_gemini,
            type="password",
            help="Get your free API key at https://aistudio.google.com/app/apikey"
        )
        st.markdown("[👉 Get Free Google Gemini API Key](https://aistudio.google.com/app/apikey)")
    elif "Groq" in llm_provider:
        provider_key_type = "groq"
        groq_model = st.selectbox(
            "Groq Model",
            ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            index=0
        )
        env_groq = os.environ.get("GROQ_API_KEY", "")
        if env_groq == "placeholder_key":
            env_groq = ""
        api_key_input = st.text_input(
            "Groq API Key",
            value=env_groq,
            type="password",
            help="Get your free API key at https://console.groq.com/"
        )
        st.markdown("[👉 Get Free Groq API Key](https://console.groq.com/)")
        chosen_model = groq_model
    else:
        provider_key_type = "together"
        env_together = os.environ.get("TOGETHER_API_KEY", "")
        if env_together == "placeholder_key":
            env_together = ""
        api_key_input = st.text_input(
            "Together AI API Key",
            value=env_together,
            type="password",
            help="Get your key at https://www.together.ai/"
        )
        chosen_model = "mistralai/Mixtral-8x7B-Instruct-v0.1"

    st.divider()
    st.header("🔍 Search Provider")
    search_provider_choice = st.selectbox(
        "Search Engine",
        ["DuckDuckGo (100% Free - No Key Required)", "Tavily Search"],
        index=0
    )
    
    if "Tavily" in search_provider_choice:
        search_provider_type = "tavily"
        env_tavily = os.environ.get("TAVILY_API_KEY", "")
        if env_tavily == "placeholder_key":
            env_tavily = ""
        search_key_input = st.text_input(
            "Tavily API Key",
            value=env_tavily,
            type="password",
            help="Get your key at https://tavily.com/"
        )
    else:
        search_provider_type = "duckduckgo"
        search_key_input = None
        st.caption("✅ DuckDuckGo search is active and requires no API key.")

    # Configure agents with current selections
    configure_agents(
        provider=provider_key_type,
        api_key=api_key_input,
        model=chosen_model,
        search_provider=search_provider_type,
        search_api_key=search_key_input
    )

    st.divider()
    st.header("⚙️ Configuration")
    max_iterations = st.slider(
        "Max Workflow Iterations",
        min_value=5,
        max_value=25,
        value=15,
        help="Maximum number of agent interactions"
    )
    
    st.divider()
    st.subheader("📋 How it works")
    st.markdown("""
    1. **Supervisor** analyzes the task
    2. **Researcher** gathers information
    3. **Writer** creates a draft
    4. **Critiquer** reviews quality
    5. Loop continues until approved
    """)

# --- Check for API Keys ---
def check_api_keys():
    """Check if required API keys are present based on active provider."""
    if provider_key_type == "google":
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        if not key or key == "placeholder_key":
            st.warning("""
            🚨 **Google Gemini API Key Required**
            
            Please enter your **Google Gemini API Key** in the sidebar or set `GEMINI_API_KEY` in your [`.env`](file:///.env) file.
            - Get a free key with no credit card required at [Google AI Studio](https://aistudio.google.com/app/apikey).
            """)
            return False
    elif provider_key_type == "groq":
        key = os.environ.get("GROQ_API_KEY", "")
        if not key or key == "placeholder_key":
            st.warning("🚨 **Groq API Key Required**: Please enter your Groq API Key in the sidebar or `.env` file.")
            return False
    elif provider_key_type == "together":
        key = os.environ.get("TOGETHER_API_KEY", "")
        if not key or key == "placeholder_key":
            st.warning("🚨 **Together AI API Key Required**: Please enter your Together AI Key in the sidebar or `.env` file.")
            return False
            
    if search_provider_type == "tavily":
        tav_key = os.environ.get("TAVILY_API_KEY", "")
        if not tav_key or tav_key == "placeholder_key":
            st.warning("🚨 **Tavily API Key Required**: Please enter your Tavily API Key or switch search engine to DuckDuckGo (Free).")
            return False
    
    st.success("✅ Provider configured & ready.")
    return True

# --- Header ---
st.title("Multi-Agent Research Assistant 🤖🧠")
st.markdown("""
Welcome to your intelligent research assistant! 
Enter a research topic, and a team of AI agents will collaborate to produce a comprehensive report.

**Agent Team:**
- 🎯 **Supervisor**: Manages the workflow and coordinates tasks
- 🔍 **Researcher**: Gathers information using web search
- ✍️ **Writer**: Creates and revises the research report
- 🔎 **Critiquer**: Reviews drafts and provides feedback
""")

st.divider()

# Display API key status banner if not configured
keys_ready = check_api_keys()

# --- Main Application ---
st.header("🚀 Start Your Research")

# User input
topic = st.text_input(
    "Enter your research topic:",
    placeholder="e.g., Impact of quantum computing on cybersecurity",
    key="topic_input"
)

# Start button
if st.button("🚀 Start Research", type="primary", use_container_width=True):
    if not keys_ready:
        st.error("⚠️ Please provide both Together AI and Tavily API keys in the sidebar or .env file before starting research.")
    elif not topic:
        st.error("⚠️ Please enter a research topic.")
    else:
        # Define the initial state
        initial_state = {
            "main_task": topic,
            "research_findings": [],
            "draft": "",
            "critique_notes": "",
            "revision_number": 0,
            "next_step": "",
            "current_sub_task": ""
        }
        
        # Configuration
        config = {"recursion_limit": max_iterations}
        
        st.info("🤖 Agents are starting their work...")
        
        # Create containers for live updates
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        
        # Container for step-by-step progress
        progress_container = st.container()
        
        final_state = None
        step_count = 0
        # Track full accumulated state and individual node states
        all_states = []
        accumulated_state = {
            "main_task": topic,
            "research_findings": [],
            "draft": "",
            "critique_notes": "",
            "revision_number": 0,
            "next_step": "",
            "current_sub_task": ""
        }
        
        try:
            # Stream the graph execution
            with progress_container:
                st.subheader("🔄 Agent Activity Log")
                
                for step in app.stream(initial_state, config=config):
                    step_count += 1
                    progress_bar.progress(min(step_count / max_iterations, 1.0))
                    
                    # Get node name and output
                    node_name = list(step.keys())[0]
                    node_output = step[node_name]
                    
                    # Store the step state
                    all_states.append((node_name, node_output))
                    
                    # Accumulate into complete state
                    if isinstance(node_output, dict):
                        for k, v in node_output.items():
                            if k == "research_findings" and isinstance(v, list):
                                for item in v:
                                    if item and item not in accumulated_state["research_findings"]:
                                        accumulated_state["research_findings"].append(item)
                            elif k == "draft":
                                # Don't overwrite an existing good draft with an error message
                                if v and not str(v).startswith("Error"):
                                    accumulated_state["draft"] = v
                                elif not accumulated_state.get("draft"):
                                    accumulated_state["draft"] = v
                            else:
                                accumulated_state[k] = v
                    
                    # Display node output with expandable previews
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"### 🤖 Agent: `{node_name.upper()}`")
                        
                        with col2:
                            st.caption(f"Step {step_count}")
                        
                        if node_name == "supervisor":
                            next_step = node_output.get('next_step', 'N/A')
                            task = node_output.get('current_sub_task', 'N/A')
                            st.markdown(f"**Decision:** {next_step}")
                            st.markdown(f"**Task:** {task}")
                        
                        elif node_name == "researcher":
                            findings = node_output.get('research_findings', [])
                            if findings:
                                latest = findings[-1]
                                st.success("✓ Research completed")
                                
                                # Preview with "Show More" button
                                preview_length = 300
                                if len(latest) > preview_length:
                                    st.markdown("**Research Preview:**")
                                    st.info(latest[:preview_length] + "...")
                                    
                                    # Unique key for each expander
                                    with st.expander(f"📖 Show Full Research (Step {step_count})"):
                                        st.markdown(latest)
                                else:
                                    st.markdown("**Research:**")
                                    st.info(latest)
                        
                        elif node_name == "writer":
                            draft = node_output.get('draft', '')
                            revision = node_output.get('revision_number', 0)
                            if draft.startswith("Error"):
                                st.error(f"❌ {draft}")
                            else:
                                st.success(f"✓ Draft {revision} generated ({len(draft)} chars)")
                            
                            # Preview with "Show More" button
                            preview_length = 400
                            if len(draft) > preview_length:
                                st.markdown("**Draft Preview:**")
                                st.info(draft[:preview_length] + "...")
                                
                                # Unique key for each expander
                                with st.expander(f"📖 Show Full Draft (Step {step_count})"):
                                    st.markdown(draft)
                            else:
                                st.markdown("**Draft:**")
                                if draft.startswith("Error"):
                                    st.error(draft)
                                else:
                                    st.info(draft)
                        
                        elif node_name == "critiquer":
                            critique = node_output.get('critique_notes', '')
                            if "APPROVED" in critique.upper():
                                st.success("✅ Draft APPROVED!")
                            else:
                                st.warning("📝 Revisions requested")
                            
                            # Preview with "Show More" button
                            preview_length = 300
                            if len(critique) > preview_length:
                                st.markdown("**Critique Preview:**")
                                st.info(critique[:preview_length] + "...")
                                
                                # Unique key for each expander
                                with st.expander(f"📖 Show Full Critique (Step {step_count})"):
                                    st.markdown(critique)
                            else:
                                st.markdown("**Critique:**")
                                st.info(critique)
                        
                        st.divider()
            
            # Update status when done
            status_placeholder.success("✅ Research Complete!")
            progress_bar.progress(1.0)
            
        except Exception as e:
            status_placeholder.error("❌ Error occurred")
            st.error(f"An error occurred during workflow: {str(e)}")
            st.exception(e)
        
        # Display final report
        st.divider()
        
        # Extract results from accumulated_state
        final_draft = accumulated_state.get("draft", "")
        all_research = accumulated_state.get("research_findings", [])
        revision_count = accumulated_state.get("revision_number", 0)
        
        # If draft is missing from accumulated_state, search backwards through all_states
        if not final_draft or len(final_draft.strip()) < 50:
            for node_name, state in reversed(all_states):
                if isinstance(state, dict) and state.get("draft"):
                    draft_candidate = state.get("draft", "")
                    if len(draft_candidate.strip()) > 50 and not draft_candidate.startswith("Error"):
                        final_draft = draft_candidate
                        break
        
        # Ensure all research findings are gathered from all states
        if not all_research:
            for node_name, state in all_states:
                if isinstance(state, dict) and "research_findings" in state:
                    for f in state["research_findings"]:
                        if f and f not in all_research:
                            all_research.append(f)
        
        if final_draft and len(final_draft.strip()) > 50 and not final_draft.startswith("Error"):
            st.header("📄 Final Research Report")
            
            # Display report in a nice container
            with st.container():
                st.markdown(final_draft)
            
            st.divider()
            
            # Display metadata
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Report Statistics")
                word_count = len(final_draft.split())
                
                st.metric("Revisions", revision_count)
                st.metric("Research Sources", len(all_research))
                st.metric("Word Count", word_count)
                st.metric("Character Count", len(final_draft))
            
            with col2:
                st.subheader("🔍 Research Findings")
                if all_research:
                    with st.expander(f"View all {len(all_research)} research data entries", expanded=True):
                        for idx, finding in enumerate(all_research, 1):
                            st.markdown(f"**Finding {idx}:**")
                            st.markdown(finding)
                            if idx < len(all_research):
                                st.divider()
                else:
                    st.info("No research findings available")
            
            # Download button
            st.download_button(
                label="📥 Download Report",
                data=final_draft,
                file_name=f"research_report_{topic.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.error("❌ No report was generated. Please try again.")
            if final_state:
                with st.expander("🔍 Debug: View Final State"):
                    st.json(final_state if isinstance(final_state, dict) else {"error": "State is not a dictionary"})

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>Powered by LangChain, LangGraph, Together AI & Tavily</p>
</div>
""", unsafe_allow_html=True)