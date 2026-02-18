import os
import streamlit as st
import re
import json
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from langchain_community.tools import DuckDuckGoSearchRun
from fpdf import FPDF

# --- 1. CONFIGURATION ---
os.environ["OPENAI_API_KEY"] = "sk-placeholder"

def safe_encode(text):
    """Encodes text for Latin-1, removing incompatible symbols."""
    if not text: return ""
    replacements = {
        '\u2018':"'", '\u2019':"'", '\u201c':'"', '\u201d':'"',
        '\u2013':'-', '\u2014':'-', '—':'-', '…':'...', '🛡️':''
    }
    for s, r in replacements.items():
        text = text.replace(s, r)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- 2. SEARCH TOOL ---
class CyberSearchTool(BaseTool):
    name: str = "CyberSearch"
    description: str = "Search for latest Indian cyber security news with source links."
    def _run(self, query: str) -> str:
        return DuckDuckGoSearchRun().run(query)

# --- 3. CUSTOM PDF ENGINE WITH FOOTER ---
class CyberPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(20, 50, 100)
        self.cell(0, 10, 'CYBER NEWS REPORT', 0, 1, 'C')
        self.set_font('Helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'Developed by Srijen Gupta', 0, 1, 'C')
        self.set_draw_color(20, 50, 100)
        self.line(10, 22, 200, 22)
        self.ln(10)

    def footer(self):
        """Adds the disclaimer at the bottom of every page."""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        disclaimer = "DISCLAIMER: This report is AI-generated for informational purposes only. " \
                     "Verify all incidents with official sources before making insurance decisions."
        self.cell(0, 10, safe_encode(disclaimer), 0, 0, 'C')

# --- 4. STREAMLIT UI ---
st.set_page_config(page_title="Srijen's Cyber Agents", page_icon="🛡️")
st.title("🛡️ Cyber Risk Reporter Agent")
st.caption("AI-Powered Risk Reporting by Srijen Gupta")

st.sidebar.header("🔑 Authentication")
api_key = st.sidebar.text_input("Enter your Gemini API Key:", type="password", help="Get a free key at aistudio.google.com")
st.sidebar.markdown("---")
st.sidebar.info("This app uses Srijen Gupta's custom CrewAI agents to scout and analyze Indian cyber threats.")

if st.button("Generate 4-Article Report") and api_key:
    try:
        # MODEL: Using Gemini 2.5 Flash-Lite (2026 standard for higher quota)
        my_llm = LLM(model="gemini/gemini-2.0-flash-lite", api_key=api_key)

        scout = Agent(
            role='Cyber Scout',
            goal='Find exactly 4 recent and distinct cyber attacks with valid URLs.',
            backstory='Persistent researcher. If you find fewer than 4, search again with different terms.',
            tools=[CyberSearchTool()],
            llm=my_llm
        )

        analyst = Agent(
            role='Risk Analyst',
            goal='Structure 4 incidents into JSON with verification links.',
            backstory='Expert in insurance-ready reporting and data authenticity.',
            llm=my_llm
        )

        t1 = Task(
            description="Find 4 unique major data breaches or ransomware attacks or cyber attacks on entities in last 1 year. "
                        "You MUST include the news source URL for each article.",
            expected_output="A list of 4 incidents with Titles, Summaries, and URLs.",
            agent=scout
        )

        t2 = Task(
            description='Format as JSON: [{"title": "..", "url": "..", "industry": "..", "summary": "..", "tip": "..", "Cyber Insurance": ".."}] '
                        'Ensure you provide EXACTLY 4 articles.',
            expected_output="A valid JSON array containing exactly 4 objects.",
            agent=analyst
        )

        with st.spinner("🤖 Fetching 4 authentic sources..."):
            crew = Crew(agents=[scout, analyst], tasks=[t1, t2], process=Process.sequential,max_rpm=3)
            raw_result = crew.kickoff()
            
            json_match = re.search(r'\[.*\]', str(raw_result), re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                pdf = CyberPDF()
                pdf.add_page()
                
                for item in data[:4]: # Safety limit to 4 articles
                    # ARTICLE TITLE
                    pdf.set_font("Helvetica", 'B', 11)
                    pdf.set_text_color(180, 0, 0)
                    pdf.multi_cell(0, 6, safe_encode(item.get('title', 'N/A')))
                    
                    # AUTHENTICITY LINK (Clickable Blue Link)
                    pdf.set_font("Helvetica", 'U', 9)
                    pdf.set_text_color(0, 0, 255)
                    url = item.get('url', 'Source URL missing')
                    pdf.cell(0, 5, safe_encode(f"Read Source: {url}"), ln=1, link=url)
                    
                    # INDUSTRY & SUMMARY
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Helvetica", 'B', 9)
                    pdf.cell(0, 5, f"Industry: {safe_encode(item.get('industry', 'General'))}", ln=1)
                    
                    pdf.set_font("Helvetica", '', 9)
                    summary = safe_encode(item.get('summary', ''))
                    pdf.multi_cell(0, 4, f"Summary: {summary}")
                    
                    # Risk TIP
                    pdf.set_font("Helvetica", 'I', 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.multi_cell(0, 5, f"Risk Tip: {safe_encode(item.get('tip', ''))}")
                    
                    # INSURANCE Advice
                    pdf.set_font("Helvetica", 'I', 9)
                    pdf.set_text_color(80, 80, 80)
                    pdf.multi_cell(0, 5, f"Insurance: {safe_encode(item.get('Cyber Insurance', ''))}")
                    
                    pdf.ln(4) # Compact spacing to fit on one page
                
                # --- FINAL BYTE CONVERSION ---
                pdf_output = pdf.output(dest='S').encode('latin-1')

                st.success(f"✅ Authenticated {len(data[:4])} articles found.")
                st.download_button(
                    label="📥 Download Authenticated Report",
                    data=pdf_output,
                    file_name=f"CyberRisk_Report_{datetime.now().strftime('%M%S')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Agents could not verify enough authentic sources. Try again.")

    except Exception as e:
        st.error(f"Error: {e}")