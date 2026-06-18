# 🚀 InsightPilot

**InsightPilot** is a state-of-the-art, autonomous, natural-language-to-SQL analytics platform. Designed to bridge the gap between business questions and raw data, it allows non-technical users to converse directly with their data using advanced LLMs and high-performance databases. 

Built with an ultra-fast **DuckDB** analytics backend and powered by **Llama-3.3-70B** (via Groq), InsightPilot turns ad-hoc questions into optimized SQL queries, dynamic tables, and highly interactive **Plotly** visualizations in milliseconds.

![InsightPilot Demo](https://img.shields.io/badge/Status-Active-brightgreen) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue) ![DuckDB](https://img.shields.io/badge/Database-DuckDB-yellow)

---

## 🌟 Key Features

### 🧠 Autonomous AI SQL Engine
* **Natural Language to SQL**: Ask complex analytical questions in plain English. The agent translates them into optimized DuckDB queries using Retrieval-Augmented Generation (RAG).
* **Self-Healing SQL Loop**: If the LLM generates syntax that DuckDB rejects (e.g., strict `GROUP BY` rules), InsightPilot invisibly intercepts the error, feeds it back to the AI for self-correction, and executes the fixed query—ensuring the user never sees a technical crash.
* **Instant Direct Analytics**: Built-in, zero-latency shortcuts for common schema and metadata questions ("Which table has the most records?", "Show column types") that bypass the LLM entirely.

### ⚡ Blazing Fast Architecture
* **DuckDB Backend**: Utilizes DuckDB as an in-process, highly-vectorized SQL OLAP engine, allowing you to slice through millions of rows of data instantly.
* **Groq LPU Inference**: Leverages the Groq API for near-instantaneous LLM inference, reducing the "thinking time" from seconds to milliseconds.

### 📈 Dynamic Visualizations & Insights
* **Auto-Generated Plotly Charts**: The agent automatically writes and safely executes Python Plotly code to generate the most appropriate chart for your specific query.
* **Smart Summaries & Follow-ups**: After every successful query, the AI generates a plain-English executive summary of the data alongside three contextual follow-up questions to guide deeper analysis.

### 🎨 Modern, Premium UI
* **Vibe-Coded Aesthetics**: A stunning, custom-styled interface featuring a glassmorphic design, smooth CSS transitions, and fully integrated Dark/Light modes.
* **Workspace Management**: Upload CSVs directly through the UI. InsightPilot parses the files, infers data types, and dynamically builds the DuckDB schema on the fly.
* **Insight Bookmarking**: Pin your favorite analyses to your "Saved Insights" dashboard for one-click retrieval in future sessions.

---

## 🛠️ Technology Stack

* **Frontend**: [Streamlit](https://streamlit.io/) with custom HTML/CSS injections for modern UI tokens.
* **LLM Engine**: [Groq API](https://groq.com/) (Llama-3.3-70b-versatile).
* **SQL Generation & RAG**: [Vanna.ai](https://vanna.ai/) (Extended with a custom Groq wrapper).
* **Database**: [DuckDB](https://duckdb.org/) (In-memory/local analytical processing).
* **Visualization**: [Plotly](https://plotly.com/) / [Pandas](https://pandas.pydata.org/).

---

## 🚀 Quickstart

### Prerequisites
1. Python 3.10 or higher
2. A Groq API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Suksha128/InsightPilot.git
   cd InsightPilot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your API Key:**
   You can either input your Groq API key directly into the application UI upon launch or set it as an environment variable:
   ```bash
   export GROQ_API_KEY="your_api_key_here"
   ```

4. **Run the Application:**
   ```bash
   streamlit run app.py
   ```

---

## 💼 Use Cases
InsightPilot is designed to act as a robust portfolio product demonstrating proficiency in **AI Engineering, Data Engineering, and UI/UX Design**. It is perfectly suited for:
* **B2B SaaS Portfolios**: Showcasing enterprise-grade analytics capability.
* **Internal BI Tooling**: Allowing sales, marketing, and HR teams to query their data securely without waiting on data engineers.
* **Hackathons & Demos**: A highly polished, bug-resistant, self-correcting showcase of autonomous agents.

---

## 🔒 Security & Guardrails
* **Read-Only Connections**: All LLM-generated SQL is executed through a strictly `read_only=True` DuckDB connection to prevent SQL injection or accidental data deletion.
* **Keyword Blacklists**: Advanced regex parsers intercept destructive keywords (`DROP`, `DELETE`, `TRUNCATE`, `ALTER`) before they ever reach the database layer.
* **Row Limits**: Queries are aggressively capped (`LIMIT 1000`) to prevent OOM errors and browser crashes during client-side rendering.

---

*Built with ❤️ for modern data exploration.*
