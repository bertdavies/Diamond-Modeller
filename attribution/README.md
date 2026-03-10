# CTI Agent Starter (ACH + OSINT + PDF)

Kick off an agentic workflow from a **single prompt** via the OpenAI **Responses API** to:
- Ingest structured inputs (Adversary, Victimology, Capability, Infrastructure)
- Collect OSINT with tool calls
- Run **Analysis of Competing Hypotheses (ACH)**
- Render a **PDF CTI report**

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt

# Edit your API keys in cti_agent/keys.py

```
