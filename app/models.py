"""
Diamond Modeler — SQLModel / Pydantic data models.

Author: Albert Davies
License: CC BY-NC-SA 4.0
"""

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum

class VertexType(str, Enum):
    ADVERSARY = "adversary"
    VICTIMOLOGY = "victimology"
    CAPABILITY = "capability"
    INFRASTRUCTURE = "infrastructure"

class IndicatorKind(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    EMAIL = "email"
    TOOL = "tool"
    TTP = "ttp"
    OTHER = "other"

class Diamond(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str = Field(unique=True, index=True)
    notes: Optional[str] = None
    color: str = Field(default="#4ecdc4")  # Default teal color
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    vertices: List["Vertex"] = Relationship(back_populates="diamond")

class Vertex(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    diamond_id: int = Field(foreign_key="diamond.id")
    type: VertexType
    
    # Relationships
    diamond: Diamond = Relationship(back_populates="vertices")

class Indicator(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: str = Field(index=True, unique=True)
    raw_value: Optional[str] = None
    kind: IndicatorKind
    hash: Optional[str] = None
    
    # Relationships - handled manually for now

class VertexIndicator(SQLModel, table=True):
    vertex_id: int = Field(foreign_key="vertex.id", primary_key=True)
    indicator_id: int = Field(foreign_key="indicator.id", primary_key=True)

class Edge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    src_diamond_id: int = Field(foreign_key="diamond.id")
    dst_diamond_id: int = Field(foreign_key="diamond.id")
    reason: Optional[str] = None
    overlap_count: int = 0
    is_manual: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships - simplified for now
    # src_diamond: Diamond = Relationship(back_populates="src_edges")
    # dst_diamond: Diamond = Relationship(back_populates="dst_edges")

# Pydantic models for API requests/responses
class DiamondCreate(SQLModel):
    label: str
    notes: Optional[str] = None
    color: str = "#4ecdc4"
    adversary_indicators: List[str] = []
    victimology_indicators: List[str] = []
    capability_indicators: List[str] = []
    infrastructure_indicators: List[str] = []

class DiamondResponse(SQLModel):
    id: int
    label: str
    notes: Optional[str] = None
    color: str
    created_at: datetime
    updated_at: datetime

class LinkCreate(SQLModel):
    src_diamond_id: int
    dst_diamond_id: int
    reason: str

class GraphNode(SQLModel):
    id: str
    label: str

class GraphEdge(SQLModel):
    id: str
    source: str
    target: str
    label: str
    class_: Optional[str] = Field(alias="class", default=None)

class GraphResponse(SQLModel):
    elements: dict
