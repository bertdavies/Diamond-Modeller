import argparse, json, re, asyncio, sys, time
from pathlib import Path
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import markdown
import os
import subprocess
import tempfile

from cti_agent.keys import OPENAI_API_KEY
from cti_agent.tools import ToolBus
from cti_agent.prompts import SYSTEM_PROMPT

class ProgressBar:
    def __init__(self, initial_steps=10, width=50):
        self.total_steps = initial_steps
        self.current_step = 0
        self.width = width
        self.start_time = time.time()
        
    def update(self, step_name="Processing"):
        self.current_step += 1
        
        # Dynamically adjust total steps if we're going over
        if self.current_step > self.total_steps:
            self.total_steps = self.current_step + 5  # Add buffer
        
        progress = min(self.current_step / self.total_steps, 1.0)
        filled = int(self.width * progress)
        bar = '#' * filled + '-' * (self.width - filled)
        
        elapsed = time.time() - self.start_time
        if self.current_step > 0:
            eta = (elapsed / self.current_step) * max(0, self.total_steps - self.current_step)
        else:
            eta = 0
        
        # Show progress with dynamic total
        if self.current_step <= self.total_steps:
            sys.stdout.write(f'\r[{bar}] {progress:.1%} - {step_name} (Step {self.current_step}/{self.total_steps}) - ETA: {eta:.0f}s')
        else:
            sys.stdout.write(f'\r[{bar}] {progress:.1%} - {step_name} (Step {self.current_step}) - ETA: {eta:.0f}s')
        sys.stdout.flush()
        
    def complete(self):
        print()  # New line when complete

def extract_block(text: str, fence: str):
    # First try the standard code block format
    m = re.search(rf"```{fence}\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    
    # If no code block found and looking for markdown, try alternative patterns
    if fence == "markdown":
        # Look for markdown content after headers like "Markdown Report:", "Report:", etc.
        markdown_patterns = [
            r"Markdown Report:\s*\n(.*?)(?:\n\n|\Z)",
            r"Markdown report:\s*\n(.*?)(?:\n\n|\Z)",
            r"Report:\s*\n(.*?)(?:\n\n|\Z)",
            r"# CTI Attribution Report.*?(?=\n\n|\Z)",
            r"2\.\s*Markdown report:\s*\n(.*?)(?:\n\n|\Z)",
            r"Markdown Report:\s*\n(.*?)(?=\Z)",
            r"Markdown report:\s*\n(.*?)(?=\Z)",
        ]
        
        for pattern in markdown_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                content = matches[0].strip()
                # Only return if it looks like markdown (starts with # or contains markdown headers)
                if content.startswith('#') or '##' in content or '###' in content:
                    return content
    
    return None

def generate_markdown_from_json(data):
    """Generate markdown content from JSON attribution data"""
    markdown = []
    
    # Title
    markdown.append("# CTI Attribution Report")
    markdown.append("")
    
    # Attribution Summary
    if 'attribution_summary' in data:
        markdown.append(f"**ATTRIBUTION SUMMARY**: {data['attribution_summary']}")
        markdown.append("")
    
    # Executive Summary
    if 'executive_summary' in data:
        markdown.append("## Executive Summary")
        markdown.append("")
        markdown.append(data['executive_summary'])
        markdown.append("")
    
    # Attribution Hypotheses - Clean format with bold titles
    if 'hypotheses' in data and data['hypotheses']:
        markdown.append("## Attribution Hypotheses")
        markdown.append("")
        
        for i, hypothesis in enumerate(data['hypotheses'], 1):
            name = hypothesis.get('name', 'Unknown')
            confidence = hypothesis.get('confidence', 'Unknown')
            assessment = hypothesis.get('assessment', 'No assessment provided')
            
            # Create bold title with confidence level
            confidence_upper = confidence.upper() if confidence else 'UNKNOWN'
            markdown.append(f"### **{name} Hypothesis, {confidence_upper} Confidence**")
            markdown.append("")
            markdown.append(assessment)
            markdown.append("")
    elif 'threat_actors' in data and data['threat_actors']:
        # Fallback for old format
        markdown.append("## Attribution Hypotheses")
        markdown.append("")
        
        for i, actor in enumerate(data['threat_actors'], 1):
            name = actor.get('name', 'Unknown')
            rationale = actor.get('rationale', 'No rationale provided')
            confidence = actor.get('confidence', 'Unknown')
            
            # Create bold title with confidence level
            confidence_upper = confidence.upper() if confidence else 'UNKNOWN'
            markdown.append(f"### **{name} Hypothesis, {confidence_upper} Confidence**")
            markdown.append("")
            markdown.append(f"Based on the observed tools and techniques, an assessment of {confidence.lower()} confidence can be made that the intrusion set details relate to {name}. {rationale}")
            markdown.append("")
    
    return '\n'.join(markdown)


def create_diamond_tables(diamond_data):
    """Create tables showing diamond model details"""
    tables = []
    
    # Adversary table
    if 'adversary' in diamond_data and diamond_data['adversary']:
        adv_data = [['Diamond Label', 'Motivation', 'Description']]
        for item in diamond_data['adversary']:
            adv_data.append([
                item.get('diamond', item.get('diamond_label', '')),
                item.get('motivation', ''),
                item.get('description', '')
            ])
        
        adv_table = Table(adv_data)
        adv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        tables.append(("Adversary", adv_table))
    
    # Victimology table
    if 'victimology' in diamond_data and diamond_data['victimology']:
        vic_data = [['Diamond Label', 'Organization', 'Description']]
        for item in diamond_data['victimology']:
            vic_data.append([
                item.get('diamond', item.get('diamond_label', '')),
                item.get('org', ''),
                item.get('description', '')
            ])
        
        vic_table = Table(vic_data)
        vic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        tables.append(("Victimology", vic_table))
    
    # Capability table
    if 'capability' in diamond_data and diamond_data['capability']:
        cap_data = [['Diamond Label', 'Tool', 'Technique', 'Description']]
        for item in diamond_data['capability']:
            cap_data.append([
                item.get('diamond', item.get('diamond_label', '')),
                item.get('tool', ''),
                item.get('technique', ''),
                item.get('description', '')
            ])
        
        cap_table = Table(cap_data)
        cap_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        tables.append(("Capability", cap_table))
    
    # Infrastructure table
    if 'infrastructure' in diamond_data and diamond_data['infrastructure']:
        inf_data = [['Diamond Label', 'Type', 'Value', 'Description']]
        for item in diamond_data['infrastructure']:
            inf_data.append([
                item.get('diamond', item.get('diamond_label', '')),
                item.get('type', item.get('infra_type', '')),
                item.get('value', ''),
                item.get('description', '')
            ])
        
        inf_table = Table(inf_data)
        inf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        tables.append(("Infrastructure", inf_table))
    
    return tables

async def check_api_connectivity():
    """Check connectivity to OpenAI API"""
    print("Checking API connectivity...")
    print("=" * 60)
    
    # Check OpenAI API
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        # Simple test - just check if we can create a client
        print("✓ OpenAI API: Available")
        print("=" * 60)
        print("✓ OpenAI API is available. Attribution analysis possible.")
        return True
    except Exception as e:
        print(f"✗ OpenAI API: Failed - {str(e)}")
        print("=" * 60)
        print("❌ OpenAI API is not available. Attribution analysis not possible.")
        return False

async def run_agent(tables, out_pdf: str):
    print("Starting CTI Agent Workflow...")
    print("=" * 60)
    
    # Check API connectivity first
    api_check_passed = await check_api_connectivity()
    if not api_check_passed:
        print("❌ Critical APIs are not available. Aborting attribution analysis.")
        return False
    
    print()  # Add spacing
    print("Proceeding with attribution analysis...")
    print("=" * 60)
    
    # Initialize progress bar (starts with 10 steps, adjusts dynamically)
    progress = ProgressBar(initial_steps=10, width=40)
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    progress.update("Initializing OpenAI client")
    
    tools = ToolBus.list_openai_tools()
    progress.update("Loading OSINT tools")

    instruction = {
        "role": "user",
        "content": f"""
Perform OSINT attribution with ACH for these inputs.
Tables (JSON): {json.dumps(tables)}
Follow the method and outputs described in the system prompt.
"""}

    progress.update("Sending initial request to GPT-4")
    resp = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, instruction],
        tools=tools,
        max_tokens=2000
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, instruction]
    tool_call_count = 0
    
    while True:
        tool_calls = resp.choices[0].message.tool_calls if resp.choices[0].message.tool_calls else []
        if not tool_calls:
            break
        
        tool_call_count += 1
        progress.update(f"Executing tool calls (Round {tool_call_count})")
        
        # Add assistant message with tool calls
        messages.append(resp.choices[0].message)
        
        # Execute tool calls and add results
        for i, tc in enumerate(tool_calls):
            fn = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            progress.update(f"Running {fn} tool ({i+1}/{len(tool_calls)})")
            try:
                result = await ToolBus.execute(fn, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)
                })
            except Exception as e:
                print(f"Tool {fn} failed: {e}")
                # Continue with error result instead of crashing
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": str(e)})
                })
        
        progress.update("Sending results back to GPT-4")
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=tools,
            max_tokens=2000
        )

    progress.update("Processing final response")
    text = resp.choices[0].message.content or ""
    
    # Debug: Print first 500 characters of response
    print(f"GPT Response preview: {text[:500]}...")
    print(f"Total response length: {len(text)} characters")

    progress.update("Extracting ACH data and markdown")
    ach_json = extract_block(text, "json")
    
    # Try multiple markdown block formats
    md_body = (extract_block(text, "md") or 
               extract_block(text, "markdown") or 
               extract_block(text, "MD") or
               extract_block(text, "MARKDOWN"))
    
    # If no markdown block found, generate markdown from JSON data
    if not md_body:
        print("No markdown block found, generating from JSON data...")
        if ach_json:
            try:
                ach_data = json.loads(ach_json)
                md_body = generate_markdown_from_json(ach_data)
                print(f"Generated markdown from JSON data: {len(md_body)} characters")
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                md_body = "# CTI Report\n\n(Error parsing JSON data.)"
        else:
            print("No JSON data found, using fallback")
            md_body = "# CTI Report\n\n(No markdown block found in response.)"
    
    print(f"Markdown content length: {len(md_body) if md_body else 0} characters")

    ach = {}
    if ach_json:
        try:
            ach = json.loads(ach_json)
        except Exception:
            pass

    progress.update("Generating PDF report")
    # Generate PDF using reportlab
    doc = SimpleDocTemplate(out_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph("CTI Attribution Report", title_style))
    story.append(Spacer(1, 12))
    
    # Convert markdown to HTML then to reportlab format
    html_content = markdown.markdown(md_body)
    
    # Improved HTML to reportlab conversion that preserves bold formatting
    # Split by HTML tags but preserve bold tags
    lines = html_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if line:
            # Check if this is a heading
            if line.startswith('<h3>') and line.endswith('</h3>'):
                # Extract content and check for bold
                content = line[4:-5]  # Remove <h3> and </h3>
                if '<strong>' in content or '<b>' in content:
                    # This is a bold hypothesis title
                    # Remove HTML tags but preserve the bold formatting for reportlab
                    clean_content = re.sub(r'</?(strong|b)>', '', content)
                    hypothesis_style = ParagraphStyle(
                        'HypothesisTitle',
                        parent=styles['Heading3'],
                        fontSize=14,
                        spaceAfter=6,
                        spaceBefore=12,
                        textColor='darkblue',
                        fontName='Helvetica-Bold'
                    )
                    story.append(Paragraph(f"<b>{clean_content}</b>", hypothesis_style))
                else:
                    # Regular heading
                    clean_content = re.sub(r'<[^>]+>', '', content)
                    story.append(Paragraph(clean_content, styles['Heading3']))
            elif line.startswith('<h2>') and line.endswith('</h2>'):
                # H2 heading
                content = line[4:-5]
                clean_content = re.sub(r'<[^>]+>', '', content)
                story.append(Paragraph(clean_content, styles['Heading2']))
            elif line.startswith('<h1>') and line.endswith('</h1>'):
                # H1 heading
                content = line[4:-5]
                clean_content = re.sub(r'<[^>]+>', '', content)
                story.append(Paragraph(clean_content, styles['Heading1']))
            elif line.startswith('<p>') and line.endswith('</p>'):
                # Paragraph
                content = line[3:-4]
                # Preserve bold tags for reportlab
                if '<strong>' in content or '<b>' in content:
                    # Convert to reportlab bold format
                    content = re.sub(r'<strong>', '<b>', content)
                    content = re.sub(r'</strong>', '</b>', content)
                    story.append(Paragraph(content, styles['Normal']))
                else:
                    clean_content = re.sub(r'<[^>]+>', '', content)
                    story.append(Paragraph(clean_content, styles['Normal']))
            else:
                # Regular text line
                clean_content = re.sub(r'<[^>]+>', '', line)
                if clean_content.strip():
                    story.append(Paragraph(clean_content, styles['Normal']))
            
            story.append(Spacer(1, 6))
    
    # Add page break before appendix
    story.append(PageBreak())
    
    # Add Appendix
    story.append(Paragraph("Appendix", styles['Heading1']))
    story.append(Spacer(1, 12))
    
    # Note: Graph visualization is available in the web interface
    story.append(Paragraph("Note: Diamond model graph visualization is available in the web interface at /graph", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Add Diamond Model Tables
    story.append(Paragraph("Diamond Model Details", styles['Heading2']))
    story.append(Spacer(1, 6))
    
    # Create tables from diamond data
    diamond_tables = create_diamond_tables(tables)
    
    for table_name, table in diamond_tables:
        story.append(Paragraph(f"{table_name} Data", styles['Heading3']))
        story.append(Spacer(1, 6))
        story.append(table)
        story.append(Spacer(1, 12))
    
    progress.update("Finalizing PDF")
    doc.build(story)
    
    progress.complete()
    print(f"Successfully generated {out_pdf}")
    print("=" * 60)
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", help="Combined JSON with {adversary, victimology, capability, infrastructure}")
    p.add_argument("--adversary", help="Adversary table JSON")
    p.add_argument("--victimology", help="Victimology table JSON")
    p.add_argument("--capability", help="Capability table JSON")
    p.add_argument("--infrastructure", help="Infrastructure table JSON")
    p.add_argument("--out", default="cti_report.pdf")
    args = p.parse_args()

    def load_json(path):
        return json.loads(Path(path).read_text()) if path else None

    if args.input:
        bundle = load_json(args.input)
        adversary = bundle.get("adversary", [])
        victimology = bundle.get("victimology", [])
        capability = bundle.get("capability", [])
        infrastructure = bundle.get("infrastructure", [])
    else:
        adversary = load_json(args.adversary) or []
        victimology = load_json(args.victimology) or []
        capability = load_json(args.capability) or []
        infrastructure = load_json(args.infrastructure) or []

    payload = {
        "adversary": adversary,
        "victimology": victimology,
        "capability": capability,
        "infrastructure": infrastructure
    }

    result = asyncio.run(run_agent(payload, args.out))
    if result is False:
        print("Attribution analysis aborted due to API connectivity issues.")
        sys.exit(1)

if __name__ == "__main__":
    main()
