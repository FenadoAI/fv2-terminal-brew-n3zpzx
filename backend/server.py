from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

# AI agents
from ai_agents.agents import AgentConfig, SearchAgent, ChatAgent


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# In-memory storage for demo (replace with MongoDB when available)
class InMemoryDB:
    def __init__(self):
        self.collections = {
            'menu': [],
            'orders': [],
            'status_checks': []
        }

    def get_collection(self, name):
        return InMemoryCollection(self.collections[name])

class InMemoryCollection:
    def __init__(self, data):
        self.data = data

    async def find(self, query=None):
        if query is None:
            return InMemoryCursor(self.data)
        # Simple query matching
        filtered = []
        for item in self.data:
            if self._matches_query(item, query):
                filtered.append(item)
        return InMemoryCursor(filtered)

    async def find_one(self, query):
        for item in self.data:
            if self._matches_query(item, query):
                return item
        return None

    async def insert_one(self, document):
        self.data.append(document)
        return type('InsertResult', (), {'inserted_id': document.get('id')})()

    async def insert_many(self, documents):
        self.data.extend(documents)
        return type('InsertResult', (), {'inserted_ids': [d.get('id') for d in documents]})()

    async def count_documents(self, query=None):
        if query is None:
            return len(self.data)
        count = 0
        for item in self.data:
            if self._matches_query(item, query):
                count += 1
        return count

    def _matches_query(self, item, query):
        for key, value in query.items():
            if key not in item or item[key] != value:
                return False
        return True

class InMemoryCursor:
    def __init__(self, data):
        self.data = data

    async def to_list(self, length=None):
        return self.data[:length] if length else self.data

# Logging config (moved up to be available early)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
try:
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    logger.info("Using MongoDB")
except Exception as e:
    logger.warning(f"MongoDB not available: {e}, using in-memory storage")
    db = InMemoryDB()
    client = None

# AI agents init
agent_config = AgentConfig()
search_agent: Optional[SearchAgent] = None
chat_agent: Optional[ChatAgent] = None

# Main app
app = FastAPI(title="AI Agents API", description="Minimal AI Agents API with LangGraph and MCP support")

# API router
api_router = APIRouter(prefix="/api")


# Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


# Coffee shop models
class CoffeeItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    origin: str
    description: str
    price: float
    available: bool = True

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_name: str
    coffee_id: str
    coffee_name: str
    quantity: int = 1
    total_price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, confirmed, ready, completed

class OrderCreate(BaseModel):
    customer_name: str
    coffee_id: str
    quantity: int = 1


# AI agent models
class ChatRequest(BaseModel):
    message: str
    agent_type: str = "chat"  # "chat" or "search"
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    success: bool
    response: str
    agent_type: str
    capabilities: List[str]
    metadata: dict = Field(default_factory=dict)
    error: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class SearchResponse(BaseModel):
    success: bool
    query: str
    summary: str
    search_results: Optional[dict] = None
    sources_count: int
    error: Optional[str] = None

# Routes
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    if isinstance(db, InMemoryDB):
        collection = db.get_collection('status_checks')
    else:
        collection = db.status_checks

    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await collection.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    if isinstance(db, InMemoryDB):
        collection = db.get_collection('status_checks')
    else:
        collection = db.status_checks

    status_checks = await collection.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


# AI agent routes
@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    # Chat with AI agent
    global search_agent, chat_agent
    
    try:
        # Init agents if needed
        if request.agent_type == "search" and search_agent is None:
            search_agent = SearchAgent(agent_config)
            
        elif request.agent_type == "chat" and chat_agent is None:
            chat_agent = ChatAgent(agent_config)
        
        # Select agent
        agent = search_agent if request.agent_type == "search" else chat_agent
        
        if agent is None:
            raise HTTPException(status_code=500, detail="Failed to initialize agent")
        
        # Execute agent
        response = await agent.execute(request.message)
        
        return ChatResponse(
            success=response.success,
            response=response.content,
            agent_type=request.agent_type,
            capabilities=agent.get_capabilities(),
            metadata=response.metadata,
            error=response.error
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return ChatResponse(
            success=False,
            response="",
            agent_type=request.agent_type,
            capabilities=[],
            error=str(e)
        )


@api_router.post("/search", response_model=SearchResponse)
async def search_and_summarize(request: SearchRequest):
    # Web search with AI summary
    global search_agent
    
    try:
        # Init search agent if needed
        if search_agent is None:
            search_agent = SearchAgent(agent_config)
        
        # Search with agent
        search_prompt = f"Search for information about: {request.query}. Provide a comprehensive summary with key findings."
        result = await search_agent.execute(search_prompt, use_tools=True)
        
        if result.success:
            return SearchResponse(
                success=True,
                query=request.query,
                summary=result.content,
                search_results=result.metadata,
                sources_count=result.metadata.get("tools_used", 0)
            )
        else:
            return SearchResponse(
                success=False,
                query=request.query,
                summary="",
                sources_count=0,
                error=result.error
            )
            
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        return SearchResponse(
            success=False,
            query=request.query,
            summary="",
            sources_count=0,
            error=str(e)
        )


@api_router.get("/agents/capabilities")
async def get_agent_capabilities():
    # Get agent capabilities
    try:
        capabilities = {
            "search_agent": SearchAgent(agent_config).get_capabilities(),
            "chat_agent": ChatAgent(agent_config).get_capabilities()
        }
        return {
            "success": True,
            "capabilities": capabilities
        }
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Coffee shop routes
@api_router.get("/menu", response_model=List[CoffeeItem])
async def get_menu():
    """Get all available coffee items"""
    try:
        if isinstance(db, InMemoryDB):
            collection = db.get_collection('menu')
        else:
            collection = db.menu
        menu_items = await collection.find({"available": True}).to_list(100)
        return [CoffeeItem(**item) for item in menu_items]
    except Exception as e:
        logger.error(f"Error getting menu: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch menu")


@api_router.post("/orders", response_model=Order)
async def create_order(order_create: OrderCreate):
    """Place a new order"""
    try:
        # Get collections
        if isinstance(db, InMemoryDB):
            menu_collection = db.get_collection('menu')
            orders_collection = db.get_collection('orders')
        else:
            menu_collection = db.menu
            orders_collection = db.orders

        # Get coffee item details
        coffee_item = await menu_collection.find_one({"id": order_create.coffee_id, "available": True})
        if not coffee_item:
            raise HTTPException(status_code=404, detail="Coffee item not found or unavailable")

        # Calculate total price
        total_price = coffee_item["price"] * order_create.quantity

        # Create order
        order_data = {
            **order_create.dict(),
            "coffee_name": coffee_item["name"],
            "total_price": total_price,
            "status": "pending"
        }
        order = Order(**order_data)

        # Save to database
        await orders_collection.insert_one(order.dict())

        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order")


@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """Get order details by ID"""
    try:
        if isinstance(db, InMemoryDB):
            collection = db.get_collection('orders')
        else:
            collection = db.orders

        order = await collection.find_one({"id": order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return Order(**order)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch order")


@api_router.get("/info")
async def get_shop_info():
    """Get coffee shop information"""
    return {
        "name": "Black Coffee Terminal",
        "description": "Premium black coffee only. No cream, no sugar, no compromises.",
        "location": "123 Terminal Street, Code City",
        "hours": "Mon-Fri: 6:00 AM - 8:00 PM, Sat-Sun: 7:00 AM - 6:00 PM",
        "philosophy": "We believe in the pure, unadulterated taste of quality coffee beans. Each cup is carefully selected and roasted to perfection.",
        "commands": [
            "menu - View our coffee selection",
            "info - Learn about our shop",
            "order <coffee_name> - Place an order",
            "help - Show available commands",
            "clear - Clear the terminal"
        ]
    }

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # Initialize agents on startup
    global search_agent, chat_agent
    logger.info("Starting AI Agents API...")

    # Initialize coffee menu if empty
    if isinstance(db, InMemoryDB):
        collection = db.get_collection('menu')
    else:
        collection = db.menu

    menu_count = await collection.count_documents({})
    if menu_count == 0:
        sample_menu = [
            {
                "id": str(uuid.uuid4()),
                "name": "Ethiopian Yirgacheffe",
                "origin": "Yirgacheffe, Ethiopia",
                "description": "Bright and floral with notes of lemon and tea-like qualities",
                "price": 4.50,
                "available": True
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Colombian Supremo",
                "origin": "Huila, Colombia",
                "description": "Medium body with chocolate and nutty undertones",
                "price": 4.25,
                "available": True
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Guatemalan Antigua",
                "origin": "Antigua, Guatemala",
                "description": "Full-bodied with smoky, spicy notes and bright acidity",
                "price": 4.75,
                "available": True
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Kenya AA",
                "origin": "Central Kenya",
                "description": "Wine-like acidity with blackcurrant and citrus notes",
                "price": 5.00,
                "available": True
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Brazil Santos",
                "origin": "São Paulo, Brazil",
                "description": "Smooth and balanced with chocolate and caramel sweetness",
                "price": 4.00,
                "available": True
            }
        ]
        await collection.insert_many(sample_menu)
        logger.info("Sample coffee menu initialized")

    # Lazy agent init for faster startup
    logger.info("AI Agents API ready!")


@app.on_event("shutdown")
async def shutdown_db_client():
    # Cleanup on shutdown
    global search_agent, chat_agent
    
    # Close MCP
    if search_agent and search_agent.mcp_client:
        # MCP cleanup automatic
        pass

    if client:  # Only close if MongoDB client exists
        client.close()
    logger.info("AI Agents API shutdown complete.")
