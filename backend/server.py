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
from datetime import datetime, timezone
from enum import Enum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Enums
class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class TaskColumn(str, Enum):
    todo = "todo"
    in_progress = "in_progress" 
    done = "done"


# Helper functions for MongoDB serialization
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Parse ISO strings back to datetime objects from MongoDB"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key in ['created_at', 'updated_at', 'due_date'] and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
    return item


# Models
class Board(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BoardCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class BoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    board_id: str
    title: str
    description: Optional[str] = ""
    priority: TaskPriority = TaskPriority.medium
    column: TaskColumn = TaskColumn.todo
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    priority: TaskPriority = TaskPriority.medium
    due_date: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    column: Optional[TaskColumn] = None
    due_date: Optional[datetime] = None

class TaskMove(BaseModel):
    column: TaskColumn


# Board Routes
@api_router.get("/boards", response_model=List[Board])
async def get_boards():
    """Get all boards"""
    boards = await db.boards.find().to_list(length=None)
    return [Board(**parse_from_mongo(board)) for board in boards]

@api_router.post("/boards", response_model=Board)
async def create_board(board_data: BoardCreate):
    """Create a new board"""
    board = Board(**board_data.dict())
    board_dict = prepare_for_mongo(board.dict())
    await db.boards.insert_one(board_dict)
    return board

@api_router.get("/boards/{board_id}", response_model=Board)
async def get_board(board_id: str):
    """Get a specific board"""
    board = await db.boards.find_one({"id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return Board(**parse_from_mongo(board))

@api_router.put("/boards/{board_id}", response_model=Board)
async def update_board(board_id: str, board_update: BoardUpdate):
    """Update a board"""
    board = await db.boards.find_one({"id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    update_data = {k: v for k, v in board_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data = prepare_for_mongo(update_data)
    
    await db.boards.update_one({"id": board_id}, {"$set": update_data})
    
    updated_board = await db.boards.find_one({"id": board_id})
    return Board(**parse_from_mongo(updated_board))

@api_router.delete("/boards/{board_id}")
async def delete_board(board_id: str):
    """Delete a board and all its tasks"""
    board = await db.boards.find_one({"id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Delete all tasks in this board
    await db.tasks.delete_many({"board_id": board_id})
    # Delete the board
    await db.boards.delete_one({"id": board_id})
    
    return {"message": "Board deleted successfully"}


# Task Routes
@api_router.get("/boards/{board_id}/tasks", response_model=List[Task])
async def get_board_tasks(board_id: str, priority: Optional[TaskPriority] = None, column: Optional[TaskColumn] = None):
    """Get all tasks for a board with optional filtering"""
    # Verify board exists
    board = await db.boards.find_one({"id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Build filter query
    filter_query = {"board_id": board_id}
    if priority:
        filter_query["priority"] = priority
    if column:
        filter_query["column"] = column
    
    tasks = await db.tasks.find(filter_query).to_list(length=None)
    return [Task(**parse_from_mongo(task)) for task in tasks]

@api_router.post("/boards/{board_id}/tasks", response_model=Task)
async def create_task(board_id: str, task_data: TaskCreate):
    """Create a new task in a board"""
    # Verify board exists
    board = await db.boards.find_one({"id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    task = Task(board_id=board_id, **task_data.dict())
    task_dict = prepare_for_mongo(task.dict())
    await db.tasks.insert_one(task_dict)
    return task

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """Get a specific task"""
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return Task(**parse_from_mongo(task))

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    """Update a task"""
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {k: v for k, v in task_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data = prepare_for_mongo(update_data)
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id})
    return Task(**parse_from_mongo(updated_task))

@api_router.patch("/tasks/{task_id}/move", response_model=Task)
async def move_task(task_id: str, move_data: TaskMove):
    """Move a task to a different column (for drag-and-drop)"""
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {
        "column": move_data.column,
        "updated_at": datetime.now(timezone.utc)
    }
    update_data = prepare_for_mongo(update_data)
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id})
    return Task(**parse_from_mongo(updated_task))

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.tasks.delete_one({"id": task_id})
    return {"message": "Task deleted successfully"}


# Health check route
@api_router.get("/")
async def root():
    return {"message": "Kanban Board API is running"}

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        await db.list_collection_names()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()