from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

# Connect to MongoDB
MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client["ai_receptionist"]
custom_responses = db["custom_responses"]

admin_router = APIRouter()

class CustomResponse(BaseModel):
    query_type: str
    custom_response_template: str

@admin_router.post("/custom-response", summary="Add a custom response template")
async def add_custom_response(response: CustomResponse):
    """Insert or update custom response templates."""
    await custom_responses.update_one(
        {"query_type": response.query_type},
        {"$set": response.dict()},
        upsert=True
    )
    return {"message": "Custom response saved successfully."}

@admin_router.get("/custom-response/{query_type}", summary="Fetch a custom response template")
async def get_custom_response(query_type: str):
    """Retrieve a custom response template by query type."""
    response = await custom_responses.find_one({"query_type": query_type}, {"_id": 0})
    if not response:
        raise HTTPException(status_code=404, detail="Custom response not found")
    return response
