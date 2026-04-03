"""
Diamond Modeller — FastAPI application routes.

Author: Albert Davies
License: CC BY-NC-SA 4.0
"""

from fastapi import FastAPI, Depends, Request, HTTPException, Form, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlmodel import Session, select
from typing import List
from datetime import datetime
from pathlib import Path
import os
import markdown

from app.database import get_session, create_db_and_tables
from app.models import Diamond, DiamondResponse, LinkCreate, GraphResponse, VertexType
from app.services import create_diamond_with_indicators, create_automatic_links, get_graph_data, regenerate_all_links, run_attribution_analysis, export_analysis, import_analysis

# Create FastAPI app
app = FastAPI(title="Diamond Modeller", description="Cyber Threat Intelligence Diamond Model Analysis", version="1.0")

# Load .env so OPENAI_API_KEY etc. are available
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except Exception:
    pass

# Create database tables
create_db_and_tables()

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/sa_theme/assets", StaticFiles(directory="templates/sa_theme/dist/assets"), name="sa-theme-assets")
app.mount("/examples", StaticFiles(directory="examples"), name="examples")

def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Session = Depends(get_session)):
    return RedirectResponse(url="/graph/", status_code=302)

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """Serve README.md rendered as HTML."""
    readme_path = _project_root() / "README.md"
    if not readme_path.is_file():
        return templates.TemplateResponse("about.html", {"request": request, "readme_html": "<p>README.md not found.</p>"})
    try:
        text = readme_path.read_text(encoding="utf-8", errors="replace")
        readme_html = markdown.markdown(text, extensions=["fenced_code", "tables"])
        readme_html = readme_html.replace('src="examples/', 'src="/examples/')
    except Exception as e:
        readme_html = f"<p>Could not load README: {e!s}</p>"
    return templates.TemplateResponse("about.html", {"request": request, "readme_html": readme_html})

@app.post("/test", response_class=HTMLResponse)
async def test_endpoint():
    return "<p>Test endpoint works!</p>"

@app.get("/debug-form", response_class=HTMLResponse)
async def debug_form():
    return """
    <div>
        <h3>Form Debug Info</h3>
        <p>This endpoint can be used to test form submission</p>
        <form hx-post="/test" hx-target="#debug-result">
            <input type="text" name="test" value="test value">
            <button type="submit">Test Submit</button>
        </form>
        <div id="debug-result"></div>
    </div>
    """

@app.post("/create-diamond", response_class=HTMLResponse)
async def create_diamond_form(
    request: Request,
    label: str = Form(""),
    notes: str = Form(""),
    color: str = Form("#4ecdc4"),
    adversary_indicators: str = Form(""),
    victimology_indicators: str = Form(""),
    capability_indicators: str = Form(""),
    infrastructure_indicators: str = Form(""),
    session: Session = Depends(get_session)
):
    """Create a new diamond with indicators"""
    print("=== CREATE ENDPOINT CALLED ===")
    print(f"Request method: {request.method}")
    print(f"Request URL: {request.url}")
    try:
        # Parse form data
        if not label:
            return templates.TemplateResponse("diamond_list.html", {
                "request": request,
                "diamonds": session.exec(select(Diamond)).all(),
                "error": "Diamond label is required"
            })
        
        # Check if label already exists
        print(f"DEBUG CREATE: Checking for existing diamond with label '{label}'")
        existing_diamond = session.exec(select(Diamond).where(Diamond.label == label)).first()
        if existing_diamond:
            print(f"DEBUG CREATE: Found existing diamond with label '{label}' and ID {existing_diamond.id}")
            return templates.TemplateResponse("diamond_list.html", {
                "request": request,
                "diamonds": session.exec(select(Diamond)).all(),
                "error": f"Diamond with label \"{label}\" already exists. Please choose a different label."
            })
        
        # Convert string indicators to lists
        adv_indicators = [line.strip() for line in adversary_indicators.split('\n') if line.strip()]
        vic_indicators = [line.strip() for line in victimology_indicators.split('\n') if line.strip()]
        cap_indicators = [line.strip() for line in capability_indicators.split('\n') if line.strip()]
        inf_indicators = [line.strip() for line in infrastructure_indicators.split('\n') if line.strip()]
        
        diamond = create_diamond_with_indicators(
            session=session,
            label=label,
            notes=notes,
            color=color,
            adversary_indicators=adv_indicators,
            victimology_indicators=vic_indicators,
            capability_indicators=cap_indicators,
            infrastructure_indicators=inf_indicators
        )
        
        # Create automatic links
        create_automatic_links(session, diamond.id)
        
        # Return updated diamond list for HTMX
        diamonds = session.exec(select(Diamond)).all()
        return templates.TemplateResponse("diamond_list.html", {
            "request": request,
            "diamonds": diamonds
        })
        
    except Exception as e:
        print(f"Error creating diamond: {e}")
        return templates.TemplateResponse("diamond_list.html", {
            "request": request,
            "diamonds": session.exec(select(Diamond)).all(),
            "error": f"Error creating diamond: {str(e)}"
        })


@app.get("/diamonds/{diamond_id}", response_model=DiamondResponse)
async def get_diamond(diamond_id: int, session: Session = Depends(get_session)):
    """Get diamond details"""
    diamond = session.get(Diamond, diamond_id)
    if not diamond:
        raise HTTPException(status_code=404, detail="Diamond not found")
    return DiamondResponse(
        id=diamond.id,
        label=diamond.label,
        notes=diamond.notes,
        color=diamond.color,
        created_at=diamond.created_at,
        updated_at=diamond.updated_at
    )

@app.get("/diamonds/{diamond_id}/details")
async def get_diamond_details(diamond_id: int, session: Session = Depends(get_session)):
    """Get detailed diamond information including all vertex data"""
    diamond = session.get(Diamond, diamond_id)
    if not diamond:
        raise HTTPException(status_code=404, detail="Diamond not found")
    
    # Get indicators for each vertex type
    from app.models import Vertex, VertexIndicator, Indicator, VertexType
    
    indicators = {
        'adversary': [],
        'victimology': [],
        'capability': [],
        'infrastructure': []
    }
    
    vertices = session.exec(select(Vertex).where(Vertex.diamond_id == diamond_id)).all()
    for vertex in vertices:
        # Get vertex indicators using a simpler approach
        vertex_indicator_links = session.exec(
            select(VertexIndicator).where(VertexIndicator.vertex_id == vertex.id)
        ).all()
        
        for link in vertex_indicator_links:
            indicator = session.get(Indicator, link.indicator_id)
            if indicator:
                indicators[vertex.type.value].append(indicator.value)
    
    return {
        "id": diamond.id,
        "label": diamond.label,
        "notes": diamond.notes or "",
        "color": diamond.color,
        "created_at": diamond.created_at.isoformat() if diamond.created_at else None,
        "updated_at": diamond.updated_at.isoformat() if diamond.updated_at else None,
        "adversary_indicators": indicators['adversary'],
        "victimology_indicators": indicators['victimology'],
        "capability_indicators": indicators['capability'],
        "infrastructure_indicators": indicators['infrastructure']
    }

@app.get("/diamonds/{diamond_id}/edit")
async def get_diamond_for_edit(diamond_id: int, session: Session = Depends(get_session)):
    """Get diamond details for editing"""
    diamond = session.get(Diamond, diamond_id)
    if not diamond:
        raise HTTPException(status_code=404, detail="Diamond not found")
    
    # Get indicators for each vertex type
    from app.models import Vertex, VertexIndicator, Indicator, VertexType
    
    indicators = {
        'adversary': [],
        'victimology': [],
        'capability': [],
        'infrastructure': []
    }
    
    vertices = session.exec(select(Vertex).where(Vertex.diamond_id == diamond_id)).all()
    for vertex in vertices:
        # Get vertex indicators using a simpler approach
        vertex_indicator_links = session.exec(
            select(VertexIndicator).where(VertexIndicator.vertex_id == vertex.id)
        ).all()
        
        for link in vertex_indicator_links:
            indicator = session.get(Indicator, link.indicator_id)
            if indicator:
                indicators[vertex.type.value].append(indicator.value)
    
    return {
        "id": diamond.id,
        "label": diamond.label,
        "notes": diamond.notes or "",
        "color": diamond.color,
        "adversary_indicators": "\n".join(indicators['adversary']),
        "victimology_indicators": "\n".join(indicators['victimology']),
        "capability_indicators": "\n".join(indicators['capability']),
        "infrastructure_indicators": "\n".join(indicators['infrastructure'])
    }

@app.get("/diamonds/", response_class=HTMLResponse)
async def search_diamonds(
    request: Request,
    query: str = "",
    session: Session = Depends(get_session)
):
    """Search diamonds by label or indicators"""
    if query:
        # Simple search - in real implementation, use FTS5
        diamonds = session.exec(
            select(Diamond).where(Diamond.label.contains(query))
        ).all()
    else:
        diamonds = session.exec(select(Diamond)).all()
    
    return templates.TemplateResponse("diamond_list.html", {
        "request": request,
        "diamonds": diamonds
    })

@app.post("/links/")
async def create_manual_link(
    link_data: LinkCreate,
    session: Session = Depends(get_session)
):
    """Create a manual link between diamonds"""
    from app.models import Edge
    
    # Check if diamonds exist
    src_diamond = session.get(Diamond, link_data.src_diamond_id)
    dst_diamond = session.get(Diamond, link_data.dst_diamond_id)
    
    if not src_diamond or not dst_diamond:
        raise HTTPException(status_code=404, detail="One or both diamonds not found")
    
    # Create manual link
    edge = Edge(
        src_diamond_id=link_data.src_diamond_id,
        dst_diamond_id=link_data.dst_diamond_id,
        reason=link_data.reason,
        is_manual=True
    )
    session.add(edge)
    session.commit()
    
    return {"message": "Manual link created successfully"}

@app.get("/graph", response_model=GraphResponse)
async def get_graph(session: Session = Depends(get_session)):
    """Get graph data in Cytoscape format"""
    graph_data = get_graph_data(session)
    return GraphResponse(elements=graph_data["elements"])

@app.get("/graph/", response_class=HTMLResponse)
async def graph_view(request: Request, session: Session = Depends(get_session)):
    """Graph visualization page"""
    diamonds = session.exec(select(Diamond)).all()
    return templates.TemplateResponse("graph.html", {"request": request, "diamonds": diamonds})

@app.post("/regenerate-links")
async def regenerate_links(session: Session = Depends(get_session)):
    """Regenerate all automatic links with improved labeling"""
    try:
        regenerate_all_links(session)
        return {"message": "All automatic links regenerated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating links: {str(e)}")


@app.get("/api/export-analysis")
async def api_export_analysis(session: Session = Depends(get_session)):
    """Export full analysis as JSON (diamonds + edges) for sharing."""
    data = export_analysis(session)
    return data


@app.post("/api/import-analysis")
async def api_import_analysis(body: dict = Body(...), session: Session = Depends(get_session)):
    """Import analysis from JSON. Replaces current diamonds and edges."""
    try:
        result = import_analysis(session, body)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_env_path() -> Path:
    """Path to .env file (project root)."""
    env_file = os.getenv("ENV_FILE")
    if env_file:
        return Path(env_file)
    # Default: .env in project root (parent of app/)
    return Path(__file__).resolve().parent.parent / ".env"

@app.post("/api/settings/openai-api-key")
async def update_openai_api_key(body: dict = Body(...)):
    """Update OPENAI_API_KEY in .env and reload into process environment."""
    api_key = (body.get("api_key") or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required and cannot be empty")
    env_path = _get_env_path()
    try:
        lines = []
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()
        replaced = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("OPENAI_API_KEY="):
                new_lines.append(f"OPENAI_API_KEY={api_key}\n")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            new_lines.append(f"OPENAI_API_KEY={api_key}\n")
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        os.environ["OPENAI_API_KEY"] = api_key
        return {"success": True, "message": "OpenAI API key updated and reloaded."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update .env: {str(e)}")

@app.get("/api/settings/openai-api-key")
async def get_openai_api_key_status():
    """Return whether an API key is set (not the value)."""
    key = os.environ.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    return {"set": bool(key and key.strip())}

@app.post("/conduct-attribution")
async def conduct_attribution(session: Session = Depends(get_session)):
    """Conduct attribution analysis on all current diamond models. Returns PDF as download on success."""
    import traceback
    try:
        result = run_attribution_analysis(session)
        if result.get("success") and result.get("pdf_path") and os.path.isfile(result["pdf_path"]):
            return FileResponse(
                result["pdf_path"],
                filename=os.path.basename(result["pdf_path"]),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=\"{os.path.basename(result['pdf_path'])}\""}
            )
        return result
    except Exception as e:
        traceback.print_exc()
        return {
            "success": False,
            "message": str(e),
            "stdout": "",
            "stderr": traceback.format_exc()
        }

@app.put("/diamonds/{diamond_id}")
async def update_diamond(
    diamond_id: int,
    request: Request,
    label: str = Form(""),
    notes: str = Form(""),
    color: str = Form("#4ecdc4"),
    adversary_indicators: str = Form(""),
    victimology_indicators: str = Form(""),
    capability_indicators: str = Form(""),
    infrastructure_indicators: str = Form(""),
    session: Session = Depends(get_session)
):
    """Update an existing diamond with new details"""
    print("=== UPDATE ENDPOINT CALLED ===")
    print(f"Request method: {request.method}")
    print(f"Request URL: {request.url}")
    print(f"Diamond ID: {diamond_id}")
    print(f"Received data - Label: '{label}', Notes: '{notes}', Color: '{color}'")
    print(f"Adversary indicators: '{adversary_indicators}'")
    print(f"Victimology indicators: '{victimology_indicators}'")
    print(f"Capability indicators: '{capability_indicators}'")
    print(f"Infrastructure indicators: '{infrastructure_indicators}'")
    try:
        # Get the diamond
        diamond = session.get(Diamond, diamond_id)
        if not diamond:
            raise HTTPException(status_code=404, detail="Diamond not found")
        
        # Check if label already exists (excluding current diamond)
        print(f"DEBUG: Updating diamond ID {diamond_id} with label '{label}'")
        print(f"DEBUG: Current diamond label is '{diamond.label}'")
        
        # Only check for duplicates if the label is actually changing
        if label != diamond.label:
            existing_diamond = session.exec(select(Diamond).where(Diamond.label == label, Diamond.id != diamond_id)).first()
            if existing_diamond:
                print(f"DEBUG: Found existing diamond with label '{label}' and ID {existing_diamond.id}")
                return templates.TemplateResponse("diamond_list.html", {
                    "request": request,
                    "diamonds": session.exec(select(Diamond)).all(),
                    "error": f"Diamond with label \"{label}\" already exists. Please choose a different label."
                })
        else:
            print(f"DEBUG: Label unchanged, skipping duplicate check")
        
        # Update diamond basic info
        diamond.label = label
        diamond.notes = notes
        diamond.color = color
        diamond.updated_at = datetime.utcnow()
        
        # Delete existing vertices and their indicators
        from app.models import Vertex, VertexIndicator
        vertices = session.exec(select(Vertex).where(Vertex.diamond_id == diamond_id)).all()
        for vertex in vertices:
            # Delete vertex-indicator relationships
            vertex_indicators = session.exec(select(VertexIndicator).where(VertexIndicator.vertex_id == vertex.id)).all()
            for vi in vertex_indicators:
                session.delete(vi)
            # Delete the vertex
            session.delete(vertex)
        
        # Parse and add new indicators (deduplicate to avoid issues)
        adv_indicators = list(dict.fromkeys([line.strip() for line in adversary_indicators.split('\n') if line.strip()]))
        vic_indicators = list(dict.fromkeys([line.strip() for line in victimology_indicators.split('\n') if line.strip()]))
        cap_indicators = list(dict.fromkeys([line.strip() for line in capability_indicators.split('\n') if line.strip()]))
        inf_indicators = list(dict.fromkeys([line.strip() for line in infrastructure_indicators.split('\n') if line.strip()]))
        
        # Clear existing vertices and their relationships for this diamond
        from app.models import Vertex, VertexIndicator
        existing_vertices = session.exec(select(Vertex).where(Vertex.diamond_id == diamond.id)).all()
        for vertex in existing_vertices:
            # Delete vertex-indicator relationships first
            vertex_indicators = session.exec(select(VertexIndicator).where(VertexIndicator.vertex_id == vertex.id)).all()
            for vi in vertex_indicators:
                session.delete(vi)
            # Delete the vertex
            session.delete(vertex)
        session.commit()
        
        # Create new vertices and process indicators
        vertex_configs = [
            (VertexType.ADVERSARY, adv_indicators),
            (VertexType.VICTIMOLOGY, vic_indicators),
            (VertexType.CAPABILITY, cap_indicators),
            (VertexType.INFRASTRUCTURE, inf_indicators)
        ]
        
        for vertex_type, indicators in vertex_configs:
            if indicators:
                try:
                    # Create vertex
                    vertex = Vertex(diamond_id=diamond.id, type=vertex_type)
                    session.add(vertex)
                    session.commit()
                    session.refresh(vertex)
                    
                    # Process and add indicators
                    from app.indicators import process_indicators
                    processed_indicators = process_indicators(indicators)
                    for value, raw_value, kind, hash_value in processed_indicators:
                        try:
                            # Get or create indicator
                            from app.models import Indicator
                            indicator = session.exec(select(Indicator).where(Indicator.value == value)).first()
                            if not indicator:
                                indicator = Indicator(
                                    value=value,
                                    raw_value=raw_value,
                                    kind=kind,
                                    hash=hash_value
                                )
                                session.add(indicator)
                                session.commit()
                                session.refresh(indicator)
                            
                            # Check if vertex-indicator relationship already exists before creating
                            existing_vi = session.exec(
                                select(VertexIndicator).where(
                                    VertexIndicator.vertex_id == vertex.id,
                                    VertexIndicator.indicator_id == indicator.id
                                )
                            ).first()
                            
                            if not existing_vi:
                                # Link indicator to vertex
                                vertex_indicator = VertexIndicator(vertex_id=vertex.id, indicator_id=indicator.id)
                                session.add(vertex_indicator)
                        except Exception as e:
                            print(f"Warning: Could not process indicator '{value}': {e}")
                            # Continue with other indicators instead of failing completely
                            continue
                            
                except Exception as e:
                    print(f"Warning: Could not create vertex for type {vertex_type}: {e}")
                    # Continue with other vertex types instead of failing completely
                    continue
        
        session.commit()
        
        # Regenerate all links after updating the diamond
        from app.services import regenerate_all_links
        print(f"DEBUG: Regenerating links after updating diamond {diamond_id}")
        regenerate_all_links(session)
        print(f"DEBUG: Links regenerated successfully")
        
        print(f"DEBUG: Diamond {diamond_id} updated successfully!")
        
        # Return updated diamond list for HTMX
        diamonds = session.exec(select(Diamond)).all()
        return templates.TemplateResponse("diamond_list.html", {
            "request": request,
            "diamonds": diamonds
        })
        
    except Exception as e:
        session.rollback()
        print(f"Error updating diamond: {e}")
        return templates.TemplateResponse("diamond_list.html", {
            "request": request,
            "diamonds": session.exec(select(Diamond)).all(),
            "error": f"Error updating diamond: {str(e)}"
        })

@app.delete("/diamonds/remove-all/")
async def remove_all_diamonds(session: Session = Depends(get_session)):
    """Remove all diamonds and all their associated data"""
    try:
        # Get all diamonds
        diamonds = session.exec(select(Diamond)).all()
        diamond_count = len(diamonds)
        
        if diamond_count == 0:
            return {"message": "No diamonds to remove", "count": 0}
        
        # Delete all edges
        from app.models import Edge
        all_edges = session.exec(select(Edge)).all()
        for edge in all_edges:
            session.delete(edge)
        
        # Delete all vertices and their indicators
        from app.models import Vertex, VertexIndicator
        all_vertices = session.exec(select(Vertex)).all()
        for vertex in all_vertices:
            # Delete vertex-indicator relationships
            vertex_indicators = session.exec(select(VertexIndicator).where(VertexIndicator.vertex_id == vertex.id)).all()
            for vi in vertex_indicators:
                session.delete(vi)
            
            # Delete the vertex
            session.delete(vertex)
        
        # Delete all diamonds
        for diamond in diamonds:
            session.delete(diamond)
        
        session.commit()
        
        return {"message": f"All {diamond_count} diamonds removed successfully", "count": diamond_count}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing all diamonds: {str(e)}")

@app.delete("/diamonds/{diamond_id}")
async def delete_diamond(diamond_id: int, session: Session = Depends(get_session)):
    """Delete a diamond and all its associated data"""
    try:
        # Get the diamond
        diamond = session.get(Diamond, diamond_id)
        if not diamond:
            raise HTTPException(status_code=404, detail="Diamond not found")
        
        # Delete all edges connected to this diamond
        from app.models import Edge
        edges_to_delete = session.exec(select(Edge).where(
            (Edge.src_diamond_id == diamond_id) | (Edge.dst_diamond_id == diamond_id)
        )).all()
        for edge in edges_to_delete:
            session.delete(edge)
        
        # Delete all vertices and their indicators
        from app.models import Vertex, VertexIndicator
        vertices = session.exec(select(Vertex).where(Vertex.diamond_id == diamond_id)).all()
        for vertex in vertices:
            # Delete vertex-indicator relationships
            vertex_indicators = session.exec(select(VertexIndicator).where(VertexIndicator.vertex_id == vertex.id)).all()
            for vi in vertex_indicators:
                session.delete(vi)
            
            # Delete the vertex
            session.delete(vertex)
        
        # Delete the diamond
        session.delete(diamond)
        session.commit()
        
        return {"message": "Diamond deleted successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting diamond: {str(e)}")

def main():
    """Main entry point"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
