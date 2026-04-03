"""
Diamond Modeller — business logic and data services.

Author: Albert Davies
License: CC BY-NC-SA 4.0
"""

from sqlmodel import Session, select, delete
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime
from app.models import Diamond, Vertex, Indicator, Edge, VertexType, VertexIndicator
from app.indicators import process_indicators
import json
import os
import sys
import subprocess
import asyncio

def create_diamond_with_indicators(
    session: Session, 
    label: str, 
    notes: str = None,
    color: str = "#4ecdc4",
    adversary_indicators: List[str] = None,
    victimology_indicators: List[str] = None,
    capability_indicators: List[str] = None,
    infrastructure_indicators: List[str] = None
) -> Diamond:
    """Create a diamond with vertices and indicators"""
    # Create diamond
    diamond = Diamond(label=label, notes=notes, color=color)
    session.add(diamond)
    session.commit()
    session.refresh(diamond)
    
    # Create vertices and process indicators
    vertex_configs = [
        (VertexType.ADVERSARY, adversary_indicators or []),
        (VertexType.VICTIMOLOGY, victimology_indicators or []),
        (VertexType.CAPABILITY, capability_indicators or []),
        (VertexType.INFRASTRUCTURE, infrastructure_indicators or [])
    ]
    
    for vertex_type, indicators in vertex_configs:
        if indicators:
            # Create vertex
            vertex = Vertex(diamond_id=diamond.id, type=vertex_type)
            session.add(vertex)
            session.commit()
            session.refresh(vertex)
            
            # Process and add indicators
            processed_indicators = process_indicators(indicators)
            for value, raw_value, kind, hash_value in processed_indicators:
                # Get or create indicator
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
                
                # Link indicator to vertex
                vertex_indicator = VertexIndicator(vertex_id=vertex.id, indicator_id=indicator.id)
                session.add(vertex_indicator)
    
    session.commit()
    return diamond

def find_overlapping_diamonds(session: Session, diamond_id: int) -> List[Dict[str, Any]]:
    """Find diamonds that share indicators with the given diamond (case-insensitive)"""
    
    # Get all indicators for this diamond with their vertex types
    diamond_indicators = session.exec(
        select(Indicator, Vertex.type)
        .join(VertexIndicator, Indicator.id == VertexIndicator.indicator_id)
        .join(Vertex, VertexIndicator.vertex_id == Vertex.id)
        .where(Vertex.diamond_id == diamond_id)
    ).all()
    
    if not diamond_indicators:
        return []
    
    indicator_values = [ind.value for ind, _ in diamond_indicators]
    indicator_values_lower = [ind.value.lower() for ind, _ in diamond_indicators]
    
    # Find other diamonds with overlapping indicators, including vertex types (case-insensitive)
    overlapping_diamonds = session.exec(
        select(Diamond, Indicator.value, Vertex.type)
        .join(Vertex, Diamond.id == Vertex.diamond_id)
        .join(VertexIndicator, Vertex.id == VertexIndicator.vertex_id)
        .join(Indicator, VertexIndicator.indicator_id == Indicator.id)
        .where(
            Diamond.id != diamond_id,
            func.lower(Indicator.value).in_(indicator_values_lower)
        )
    ).all()
    
    # Group by diamond and organize overlaps by vertex type
    overlap_counts = {}
    for diamond, indicator_value, vertex_type in overlapping_diamonds:
        if diamond.id not in overlap_counts:
            overlap_counts[diamond.id] = {
                'diamond': diamond, 
                'count': 0, 
                'indicators': [],
                'by_type': {}
            }
        overlap_counts[diamond.id]['count'] += 1
        overlap_counts[diamond.id]['indicators'].append(indicator_value)
        
        # Group by vertex type
        if vertex_type not in overlap_counts[diamond.id]['by_type']:
            overlap_counts[diamond.id]['by_type'][vertex_type] = []
        overlap_counts[diamond.id]['by_type'][vertex_type].append(indicator_value)
    
    return list(overlap_counts.values())

def create_automatic_links(session: Session, diamond_id: int):
    """Create automatic links based on indicator overlaps"""
    overlaps = find_overlapping_diamonds(session, diamond_id)
    
    for overlap in overlaps:
        target_diamond = overlap['diamond']
        by_type = overlap['by_type']
        
        # Create individual links for each unique indicator
        for vertex_type, indicators in by_type.items():
            for indicator in indicators:
                # Check if this specific link already exists (case-insensitive)
                existing_link = session.exec(
                    select(Edge).where(
                        ((Edge.src_diamond_id == diamond_id) & (Edge.dst_diamond_id == target_diamond.id)) |
                        ((Edge.src_diamond_id == target_diamond.id) & (Edge.dst_diamond_id == diamond_id)),
                        func.lower(Edge.reason).like(f"%{vertex_type.value.title().lower()}: {indicator.lower()}%"),
                        Edge.is_manual == False
                    )
                ).first()
                
                # Create new individual link
                vertex_type_name = vertex_type.value.title()
                reason = f"{vertex_type_name}: {indicator}"
                
                if not existing_link:
                    edge = Edge(
                        src_diamond_id=diamond_id,
                        dst_diamond_id=target_diamond.id,
                        reason=reason,
                        overlap_count=1,
                        is_manual=False
                    )
                    session.add(edge)
    
    session.commit()

def regenerate_all_links(session: Session):
    """Regenerate all automatic links with improved labeling"""
    # Get all diamonds
    diamonds = session.exec(select(Diamond)).all()
    
    # Clear all automatic links
    automatic_edges = session.exec(select(Edge).where(Edge.is_manual == False)).all()
    for edge in automatic_edges:
        session.delete(edge)
    session.commit()
    
    # Regenerate links for all diamonds
    for diamond in diamonds:
        create_automatic_links(session, diamond.id)

def get_graph_data(session: Session) -> Dict[str, Any]:
    """Get graph data in Cytoscape format"""
    # Get all diamonds
    diamonds = session.exec(select(Diamond)).all()
    
    # Get all edges
    edges = session.exec(select(Edge)).all()
    
    # Build nodes
    nodes = []
    for diamond in diamonds:
        nodes.append({
            "data": {
                "id": f"d{diamond.id}",
                "label": diamond.label,
                "color": diamond.color
            }
        })
    
    # Build edges
    edges_data = []
    for edge in edges:
        edge_data = {
            "data": {
                "id": f"e{edge.id}",
                "source": f"d{edge.src_diamond_id}",
                "target": f"d{edge.dst_diamond_id}",
                "label": edge.reason or f"Overlap: {edge.overlap_count}"
            }
        }
        if edge.is_manual:
            edge_data["data"]["class"] = "manual"
        
        edges_data.append(edge_data)
    
    return {
        "elements": {
            "nodes": nodes,
            "edges": edges_data
        }
    }


def export_analysis(session: Session) -> Dict[str, Any]:
    """Export full analysis as JSON: diamonds (with indicators) and edges (by label)."""
    diamonds = session.exec(select(Diamond).order_by(Diamond.id)).all()
    edges = session.exec(select(Edge)).all()
    diamond_ids = {d.id: d for d in diamonds}

    diamond_list = []
    for diamond in diamonds:
        indicators = {
            "adversary": [],
            "victimology": [],
            "capability": [],
            "infrastructure": [],
        }
        vertices = session.exec(select(Vertex).where(Vertex.diamond_id == diamond.id)).all()
        for vertex in vertices:
            links = session.exec(
                select(VertexIndicator).where(VertexIndicator.vertex_id == vertex.id)
            ).all()
            for link in links:
                ind = session.get(Indicator, link.indicator_id)
                if ind:
                    indicators[vertex.type.value].append(ind.value)
        diamond_list.append({
            "label": diamond.label,
            "notes": diamond.notes or "",
            "color": diamond.color,
            "adversary_indicators": indicators["adversary"],
            "victimology_indicators": indicators["victimology"],
            "capability_indicators": indicators["capability"],
            "infrastructure_indicators": indicators["infrastructure"],
        })

    edge_list = []
    for edge in edges:
        src = diamond_ids.get(edge.src_diamond_id)
        dst = diamond_ids.get(edge.dst_diamond_id)
        if not src or not dst:
            continue
        edge_list.append({
            "src_label": src.label,
            "dst_label": dst.label,
            "reason": edge.reason or "",
            "is_manual": edge.is_manual,
        })

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "diamonds": diamond_list,
        "edges": edge_list,
    }


def import_analysis(session: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """Import analysis from JSON. Replaces current diamonds and edges."""
    version = data.get("version", "1.0")
    diamonds_data = data.get("diamonds") or []
    edges_data = data.get("edges") or []

    if not isinstance(diamonds_data, list) or not isinstance(edges_data, list):
        raise ValueError("Invalid format: diamonds and edges must be arrays")

    # Delete in dependency order
    session.exec(delete(VertexIndicator))
    session.exec(delete(Vertex))
    session.exec(delete(Edge))
    session.exec(delete(Diamond))
    session.commit()

    label_to_id: Dict[str, int] = {}
    for d in diamonds_data:
        if not isinstance(d, dict):
            continue
        label = (d.get("label") or "").strip()
        if not label:
            continue
        diamond = create_diamond_with_indicators(
            session,
            label=label,
            notes=d.get("notes") or "",
            color=(d.get("color") or "#4ecdc4").strip(),
            adversary_indicators=d.get("adversary_indicators") or [],
            victimology_indicators=d.get("victimology_indicators") or [],
            capability_indicators=d.get("capability_indicators") or [],
            infrastructure_indicators=d.get("infrastructure_indicators") or [],
        )
        label_to_id[label] = diamond.id

    for e in edges_data:
        if not isinstance(e, dict):
            continue
        src_label = (e.get("src_label") or "").strip()
        dst_label = (e.get("dst_label") or "").strip()
        if src_label not in label_to_id or dst_label not in label_to_id:
            continue
        reason = (e.get("reason") or "").strip() or f"Imported link"
        edge = Edge(
            src_diamond_id=label_to_id[src_label],
            dst_diamond_id=label_to_id[dst_label],
            reason=reason,
            overlap_count=0,
            is_manual=e.get("is_manual", True),
        )
        session.add(edge)
    session.commit()

    return {
        "imported_diamonds": len(label_to_id),
        "imported_edges": sum(1 for e in edges_data if isinstance(e, dict)),
    }


def export_diamonds_for_attribution(session: Session) -> Dict[str, List[Dict[str, Any]]]:
    """Export all diamond models to the JSON format expected by the attribution app"""
    
    # Get all diamonds with their indicators
    diamonds = session.exec(select(Diamond)).all()
    
    # Initialize the attribution data structure
    attribution_data = {
        "adversary": [],
        "victimology": [],
        "capability": [],
        "infrastructure": []
    }
    
    # Process each diamond
    for diamond in diamonds:
        # Get all vertices for this diamond
        vertices = session.exec(select(Vertex).where(Vertex.diamond_id == diamond.id)).all()
        
        for vertex in vertices:
            # Get indicators for this vertex
            vertex_indicators = session.exec(
                select(Indicator)
                .join(VertexIndicator, Indicator.id == VertexIndicator.indicator_id)
                .where(VertexIndicator.vertex_id == vertex.id)
            ).all()
            
            # Create entries for each indicator - simplified format
            for indicator in vertex_indicators:
                # Create minimal entry with just essential info
                entry = {
                    "value": indicator.value,
                    "type": indicator.kind.value if indicator.kind else "other",
                    "diamond": diamond.label
                }
                
                # Add specific fields based on vertex type - only if meaningful
                if vertex.type == VertexType.ADVERSARY:
                    if any(motivation_word in indicator.value.lower() for motivation_word in ["financial", "gain", "profit", "money", "espionage", "sabotage", "disruption"]):
                        entry["motivation"] = indicator.value
                elif vertex.type == VertexType.VICTIMOLOGY:
                    if any(org_word in indicator.value.lower() for org_word in ["org", "company", "corp", "inc", "ltd", "bank", "hospital", "university", "government"]):
                        entry["org"] = indicator.value
                elif vertex.type == VertexType.CAPABILITY:
                    entry["tool"] = indicator.value
                elif vertex.type == VertexType.INFRASTRUCTURE:
                    entry["infra_type"] = indicator.kind.value if indicator.kind else "other"
                
                attribution_data[vertex.type.value].append(entry)
    
    return attribution_data

def run_attribution_analysis(session: Session) -> Dict[str, Any]:
    """Run the attribution analysis using the attribution app"""
    try:
        # Export diamond data to JSON format
        attribution_data = export_diamonds_for_attribution(session)
        
        # Create temporary JSON file
        temp_json_path = "temp_attribution_input.json"
        with open(temp_json_path, 'w') as f:
            json.dump(attribution_data, f, indent=2)
        
        # Set up the attribution app path
        attribution_app_path = os.path.join("attribution", "app.py")
        
        print("Starting attribution analysis...")
        print("=" * 60)
        
        # Generate unique filename to avoid permission issues
        import time
        timestamp = int(time.time())
        output_filename = f"attribution_report_{timestamp}.pdf"
        output_path = os.path.abspath(output_filename)

        # Run the attribution app with real-time output and progress bar
        result = subprocess.run([
            sys.executable, attribution_app_path,
            "--input", temp_json_path,
            "--out", output_filename
        ], cwd=os.getcwd(),
        stdout=None,  # Inherit stdout from parent process
        stderr=None,  # Inherit stderr from parent process
        text=True,    # Ensure text mode
        bufsize=0)    # Unbuffered output for real-time display
        
        # Clean up temporary file
        if os.path.exists(temp_json_path):
            os.remove(temp_json_path)
        
        print("=" * 60)
        
        if result.returncode == 0:
            print("Attribution analysis completed successfully!")
            return {
                "success": True,
                "message": f"Attribution analysis completed successfully. Report saved as {output_filename}",
                "pdf_path": output_path,
                "stdout": "",
                "stderr": ""
            }
        else:
            print(f"Attribution analysis failed with return code: {result.returncode}")
            return {
                "success": False,
                "message": f"Attribution analysis failed with return code: {result.returncode}",
                "stdout": "",
                "stderr": ""
            }
            
    except Exception as e:
        print(f"Error running attribution analysis: {str(e)}")
        return {
            "success": False,
            "message": f"Error running attribution analysis: {str(e)}",
            "stdout": "",
            "stderr": str(e)
        }

