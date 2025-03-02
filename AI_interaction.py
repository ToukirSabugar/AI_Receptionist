import re  # Import regex to handle placeholders
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from transformers import pipeline
from datetime import datetime  
from bson import ObjectId  # Add ObjectId handling

# Create a router for AI interaction
router = APIRouter()

# Connect to MongoDB
MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client["ai_receptionist"]
business_data = db["business_data"]
calendar = db["calendar"]
customer_queries = db["customer_queries"]
custom_responses = db["custom_responses"]

# Load Pre-trained NLP Model (Hugging Face)
nlp_model = pipeline("text-classification", model="facebook/bart-large-mnli")

# Define Request Model
class QueryRequest(BaseModel):
    user_query: str

async def format_response(template, user_query):
    """Dynamically format response with placeholders like {Service_Name}, {User_Name}."""
    placeholders = re.findall(r"\{(.*?)\}", template)  # Extract placeholders

    for placeholder in placeholders:
        if placeholder.lower() == "user_name":
            user_name = "Guest"  # Replace with actual user lookup logic
            template = template.replace(f"{{{placeholder}}}", user_name)

        elif placeholder.lower() == "service_name":
            service_data = await business_data.find_one({}, {"_id": 0, "services": 1})
            service_name = service_data["services"][0] if service_data and "services" in service_data else "our services"
            template = template.replace(f"{{{placeholder}}}", service_name)

    return template

async def serialize_doc(doc):
    """Convert MongoDB document to a JSON-serializable format."""
    if not doc:
        return None
    doc["_id"] = str(doc["_id"]) if "_id" in doc else None
    return doc

# AI-Powered Customer Interaction
@router.post("/ask-ai", summary="Ask AI about services, scheduling, etc.")
async def ask_ai(request: QueryRequest):
    """AI handles customer queries intelligently."""
    user_query = request.user_query

    # Classify Query Type
    query_type = nlp_model(user_query)[0]["label"]

    # Check for a Custom Response First
    custom_response = await custom_responses.find_one(
        {"query_type": query_type}, 
        {"_id": 0, "custom_response_template": 1}
    )

    if custom_response:
        response_text = await format_response(custom_response["custom_response_template"], user_query)
        response = {"message": response_text}
    else:
        response = None

        # Fetch Business Info
        if "service" in user_query.lower():
            business = await business_data.find_one({}, {"_id": 0, "services": 1})
            response = {"message": "Here are our available services:", "services": business["services"]} if business and "services" in business else {"message": "No services found."}

        # Check for Scheduling Requests
        elif "book" in user_query.lower() or "appointment" in user_query.lower():
            available_slots = await calendar.find({"available": True}).to_list(length=None)
            response = {"message": "Here are the available time slots:", "slots": available_slots} if available_slots else {"message": "No available time slots."}

        # Fetch Operating Hours
        elif "hours" in user_query.lower() or "open" in user_query.lower():
            business = await business_data.find_one({}, {"_id": 0, "operating_hours": 1})
            response = {"message": "Our operating hours are:", "hours": business["operating_hours"]} if business and "operating_hours" in business else {"message": "Operating hours not available."}

        # Default Response
        else:
            response = {"message": "Sorry, I couldn't understand your request. Please ask about services, scheduling, or operating hours."}

    # Log Query to MongoDB with Timestamp
    log_entry = {
        "query": user_query,
        "query_type": query_type,
        "response": response,
        "timestamp": datetime.utcnow()
    }
    log_entry = await customer_queries.insert_one(log_entry)

    return response
