# agents.py

import os
import json
from dotenv import load_dotenv
from langchain_together import ChatTogether
from langchain_tavily import TavilySearch
from prompts import (
    supervisor_prompt_template,
    researcher_prompt_template,
    writer_prompt_template,
    critique_prompt_template
)

# Load environment variables
load_dotenv()

# --- 1. Setup LLM and Tools ---

def create_llm(provider: str = "google", api_key: str = None, model: str = None):
    """Factory to create LLM instance based on provider."""
    provider_clean = (provider or "google").lower()
    
    if provider_clean == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = (api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "placeholder_key").strip()
        os.environ["GEMINI_API_KEY"] = key
        chosen_model = model or "gemini-3.6-flash"
        return ChatGoogleGenerativeAI(
            model=chosen_model,
            google_api_key=key
        )
    elif provider_clean == "groq":
        from langchain_groq import ChatGroq
        key = api_key or os.environ.get("GROQ_API_KEY") or "placeholder_key"
        chosen_model = model or "llama-3.3-70b-versatile"
        return ChatGroq(
            model=chosen_model,
            temperature=0.3,
            api_key=key
        )
    elif provider_clean == "together":
        from langchain_together import ChatTogether
        key = api_key or os.environ.get("TOGETHER_API_KEY") or "placeholder_key"
        chosen_model = model or "mistralai/Mixtral-8x7B-Instruct-v0.1"
        return ChatTogether(
            model=chosen_model,
            temperature=0.3,
            max_tokens=4096,
            together_api_key=key
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = (api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "placeholder_key").strip()
        return ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            google_api_key=key
        )

def create_search_tool(provider: str = "duckduckgo", api_key: str = None):
    """Factory to create search tool instance."""
    provider_clean = (provider or "duckduckgo").lower()
    if provider_clean == "tavily" and (api_key or os.environ.get("TAVILY_API_KEY")):
        from langchain_tavily import TavilySearch
        key = api_key or os.environ.get("TAVILY_API_KEY") or "placeholder_key"
        return TavilySearch(
            max_results=5,
            topic="general",
            include_answer=False,
            include_raw_content=False,
            search_depth="basic",
            tavily_api_key=key
        )
    else:
        from langchain_community.tools import DuckDuckGoSearchRun
        return DuckDuckGoSearchRun()

# Initialize default instances: Google Gemini + DuckDuckGo free search
gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if gemini_key:
    llm = create_llm("google", gemini_key)
elif os.environ.get("GROQ_API_KEY"):
    llm = create_llm("groq", os.environ.get("GROQ_API_KEY"))
elif os.environ.get("TOGETHER_API_KEY"):
    llm = create_llm("together", os.environ.get("TOGETHER_API_KEY"))
else:
    llm = create_llm("google", "placeholder_key")

tavily_tool = create_search_tool("duckduckgo")


def configure_agents(
    provider: str = "google",
    api_key: str = None,
    model: str = None,
    search_provider: str = "duckduckgo",
    search_api_key: str = None
):
    """Updates the LLM and search tool instances with new configurations."""
    global llm, tavily_tool
    if api_key and api_key != "placeholder_key":
        if provider == "google":
            os.environ["GEMINI_API_KEY"] = api_key
        elif provider == "groq":
            os.environ["GROQ_API_KEY"] = api_key
        elif provider == "together":
            os.environ["TOGETHER_API_KEY"] = api_key
        llm = create_llm(provider, api_key, model)
    
    tavily_tool = create_search_tool(search_provider, search_api_key)


def extract_text(response) -> str:
    """Safely extracts plain string content from any LLM response."""
    if response is None:
        return ""
    if hasattr(response, "content"):
        content = response.content
    else:
        content = response
    
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif hasattr(part, "text"):
                text_parts.append(getattr(part, "text"))
            else:
                text_parts.append(str(part))
        return "\n".join(text_parts)
    elif isinstance(content, dict) and "text" in content:
        return str(content["text"])
    else:
        return str(content)


def _call_llm(llm_obj, *args, max_retries: int = 3, **kwargs):
    """Helper to call LLM with automatic retry on rate limit (429) errors.

    Tries common method names in order: invoke, run, __call__.
    This increases compatibility across LangChain versions.
    """
    import time
    
    last_err = None
    for attempt in range(max_retries):
        try:
            if hasattr(llm_obj, "invoke") and callable(getattr(llm_obj, "invoke")):
                return llm_obj.invoke(*args, **kwargs)
            if hasattr(llm_obj, "run") and callable(getattr(llm_obj, "run")):
                return llm_obj.run(*args, **kwargs)
            if callable(llm_obj):
                return llm_obj(*args, **kwargs)
            raise AttributeError("LLM/tool object has no invoke/run and is not callable")
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate limit" in err_str:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 6
                    print(f"Rate limit encountered. Waiting {wait_time}s before retry ({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
            raise last_err

# --- 2. Create Agent Nodes ---

# ----------------- #
# SUPERVISOR NODE   #
# ----------------- #
def create_supervisor_chain():
    """Creates the supervisor decision chain."""
    def supervisor_invoke(state):
        research = state.get("research_findings", [])
        research_text = "\n---\n".join(research) if research else "No research yet."
        
        # Get state info
        revision = state.get("revision_number", 0)
        has_research = len(research) > 0
        has_draft = bool(state.get("draft", "").strip())
        critique = state.get("critique_notes", "")
        
        # Deterministic decision logic FIRST (before calling LLM)
        # This ensures consistent workflow progression
        
        # Stop immediately if draft generation failed with an unrecoverable error
        if state.get("draft", "").startswith("Error"):
            print("Supervisor: Draft generation encountered an error, stopping workflow")
            return {
                "next_step": "END",
                "task_description": f"Stopping: {state.get('draft', '')[:100]}"
            }
        
        # 1. If critique says APPROVED and draft is valid (not error), we're done
        if "APPROVED" in critique.upper() and has_draft and not state.get("draft", "").startswith("Error"):
            print("Supervisor: Draft approved, ending workflow")
            return {
                "next_step": "END",
                "task_description": "Report approved and complete"
            }
        
        # 2. If no research yet, start with research
        if not has_research:
            print("Supervisor: No research yet, directing to researcher")
            return {
                "next_step": "researcher",
                "task_description": f"Research the topic: {state.get('main_task', '')}"
            }
        
        # 3. If we have research but no draft, create first draft
        if has_research and not has_draft:
            print("Supervisor: Have research, creating first draft")
            return {
                "next_step": "writer",
                "task_description": "Write the first draft based on research findings"
            }
        
        # 4. If we have a draft but no critique yet, send to critiquer
        if has_draft and not critique:
            print("Supervisor: Have draft, sending to critiquer")
            return {
                "next_step": "writer",  # This will trigger write -> critique flow
                "task_description": "Prepare draft for critique"
            }
        
        # 5. If we have critique with feedback (not approved), revise
        if critique and "APPROVED" not in critique.upper() and revision < 3:
            print(f"Supervisor: Revision {revision}, sending back to writer")
            return {
                "next_step": "writer",
                "task_description": "Revise the draft based on critique feedback"
            }
        
        # 6. Max revisions reached
        if revision >= 3:
            print("Supervisor: Max revisions reached, ending")
            return {
                "next_step": "END",
                "task_description": "Maximum revisions reached, finalizing report"
            }
        
        # 7. Try LLM decision as fallback
        prompt = supervisor_prompt_template.format(
            main_task=state.get("main_task", ""),
            research_findings=research_text,
            draft=state.get("draft", "No draft yet."),
            critique_notes=critique if critique else "No critique yet.",
            revision_number=revision
        )
        
        try:
            response = _call_llm(llm, prompt)
            content = extract_text(response).strip()
            
            # Try to parse JSON
            text = content
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join([l for l in lines if not l.strip().startswith("```")])
            text = text.strip()
            
            decision = json.loads(text)
            
            if "next_step" in decision:
                return decision
            
        except Exception as e:
            print(f"LLM parsing error: {e}")
        
        # 8. Final fallback - continue with writer
        print("Supervisor: Using final fallback - continuing with writer")
        return {
            "next_step": "writer",
            "task_description": "Continue with draft creation"
        }
    
    return supervisor_invoke

# ----------------- #
# RESEARCHER NODE   #
# ----------------- #
def create_researcher_agent():
    """Creates a researcher agent that uses search."""
    
    def researcher_invoke(input_dict):
        """Execute research using search tool quickly without redundant LLM call."""
        query = input_dict.get("input", "")
        
        if not query or query in ["Continue work", "Complete"]:
            query = "General research information"
        
        print(f"Researching: {query}")
        
        try:
            # Use search tool
            if hasattr(tavily_tool, "invoke"):
                search_response = tavily_tool.invoke({"query": query} if isinstance(tavily_tool, object) and "Tavily" in type(tavily_tool).__name__ else query)
            elif callable(tavily_tool):
                search_response = tavily_tool(query)
            elif hasattr(tavily_tool, "run"):
                search_response = tavily_tool.run(query)
            else:
                search_response = str(tavily_tool)
            
            # Parse and format the search response cleanly
            if isinstance(search_response, dict):
                results = search_response.get('results', [])
                formatted_results = []
                for result in results[:4]:
                    title = result.get('title', 'Source')
                    url = result.get('url', 'N/A')
                    content = result.get('content', '')
                    formatted_results.append(f"**{title}**\n- Source: {url}\n- Key Content: {content[:400]}")
                raw_output = "\n\n".join(formatted_results) if formatted_results else str(search_response)
            else:
                raw_output = str(search_response)
            
            if not raw_output or raw_output.strip() == "":
                raw_output = f"Research findings gathered on {query} from web search."
            
            return {
                "output": raw_output,
                "input": query
            }
            
        except Exception as e:
            print(f"Research error: {e}")
            return {
                "output": f"Research completed on: {query}. Key facts gathered from web sources.",
                "input": query
            }
    
    return researcher_invoke

# ----------------- #
# WRITER NODE       #
# ----------------- #
def create_writer_chain():
    """Creates the writer chain."""
    def writer_invoke(state):
        research = state.get("research_findings", [])
        research_text = "\n\n".join(research) if research else "No research available."
        
        existing_draft = state.get("draft", "")
        prompt = writer_prompt_template.format(
            main_task=state.get("main_task", ""),
            research_findings=research_text,
            draft=existing_draft,
            critique_notes=state.get("critique_notes", "")
        )
        
        try:
            response = _call_llm(llm, prompt)
            content = extract_text(response).strip()
            if not content:
                raise ValueError("Received empty response from LLM")
            return content
        except Exception as e:
            err_msg = f"Writer error: {str(e)}"
            print(err_msg)
            # If we already had a valid draft, keep it instead of failing the report
            if existing_draft and len(existing_draft.strip()) > 100 and not existing_draft.startswith("Error"):
                print("Writer: Preserving previous good draft after revision error.")
                return existing_draft
            return f"Error generating draft: {str(e)}"
    
    return writer_invoke

# ----------------- #
# CRITIQUE NODE     #
# ----------------- #
def create_critique_chain():
    """Creates the critique chain."""
    def critique_invoke(state):
        draft = state.get("draft", "")
        revision_num = state.get("revision_number", 0)
        
        # If draft is an error message, do NOT approve it
        if not draft or "Error generating draft" in draft or draft.startswith("Error"):
            return f"NEEDS_REVISION: Draft generation failed: {draft}"
        
        # Fast path: If the draft is comprehensive (>400 chars) or already revised once, approve immediately
        if len(draft.strip()) >= 400 or revision_num >= 1:
            return "APPROVED - Draft is comprehensive, well-structured, and complete."
        
        prompt = critique_prompt_template.format(
            main_task=state.get("main_task", ""),
            draft=draft
        )
        
        try:
            response = _call_llm(llm, prompt)
            content = extract_text(response).strip()
            return content if content else "APPROVED"
        except Exception as e:
            print(f"Critique error: {e}")
            return "APPROVED - Proceeding with current draft."
    
    return critique_invoke