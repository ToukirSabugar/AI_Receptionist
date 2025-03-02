from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from AI_interaction import router as ai_router
from admin import admin_router  # Import admin routes

# Initialize FastAPI
app = FastAPI(title="AI Receptionist API", version="1.0")

# MongoDB Connection
MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client["ai_receptionist"]

# Collections
business_data = db["business_data"]
calendar = db["calendar"]
appointments = db["appointments"]
customer_queries = db["customer_queries"]
custom_responses = db["custom_responses"]

class AppointmentRequest(BaseModel):
    customer_name: str
    service: str
    date: str  # Format: YYYY-MM-DD
    time: str  # Format: HH:MM

# Helper function to convert MongoDB ObjectId
def fix_id(document: dict) -> dict:
    """Convert MongoDB ObjectId to string for JSON responses."""
    if document and "_id" in document:
        document["_id"] = str(document["_id"])
    return document

# Insert sample business data (runs only once)
async def insert_sample_data():
    """Insert sample business data if not exists."""
    existing = await business_data.find_one({"business_name": "TechFix Solutions"})
    if not existing:
        sample_data = {
            "business_name": "TechFix Solutions",
            "services": [
                {"name": "Laptop Repair", "description": "Fix hardware and software issues", "price": 50},
                {"name": "Mobile Repair", "description": "Screen replacement and battery fix", "price": 30},
                {"name": "Data Recovery", "description": "Recover lost files from hard drives", "price": 80},
                {"name": "Virus Removal", "description": "Remove malware and optimize performance", "price": 40},
                {"name": "Networking Support", "description": "Set up and troubleshoot WiFi networks", "price": 60},
                {"name": "Software Installation", "description": "Install and configure software applications", "price": 25},
                {"name": "Printer Repair", "description": "Fix paper jams and connectivity issues", "price": 35},
                {"name": "Battery Replacement", "description": "Replace laptop and mobile batteries", "price": 45},
                {"name": "Screen Replacement", "description": "Replace cracked or damaged screens", "price": 90},
                {"name": "Custom PC Build", "description": "Assemble and optimize custom PCs", "price": 150}
            ],
            "operating_hours": {"open": "09:00 AM", "close": "06:00 PM"},
            "contact_info": {"phone": "+123456789", "email": "info@techfix.com"}
        }
        await business_data.insert_one(sample_data)
        print("Business data inserted!")

# Insert sample available slots
async def insert_sample_slots():
    """Insert sample available slots for appointments if none exist."""
    existing_slots = await calendar.count_documents({})
    if existing_slots == 0:
        slots = [
            {"date": "2025-03-01", "start_time": "09:00", "end_time": "10:00", "available": True},
            {"date": "2025-03-01", "start_time": "10:00", "end_time": "11:00", "available": True},
            {"date": "2025-03-02", "start_time": "09:00", "end_time": "10:00", "available": True}
        ]
        await calendar.insert_many(slots)
        print("Sample slots inserted!")

# Run sample data insertion on startup
@app.on_event("startup")
async def startup_event():
    try:
        await insert_sample_data()
        await insert_sample_slots()
    except Exception as e:
        print(f"Startup error: {e}")

# Fetch Business Info
@app.get("/business", summary="Get business details", tags=["Business"])
async def get_business_info():
    """Fetch business details from MongoDB."""
    business = await business_data.find_one({}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business data not found")
    return business

# Fetch Available Services
@app.get("/services", summary="Get available services", tags=["Business"])
async def get_services():
    """Fetch list of services the business offers."""
    business = await business_data.find_one({}, {"_id": 0, "services": 1})
    if not business:
        raise HTTPException(status_code=404, detail="No services found")
    return business["services"]

# Book an Appointment
@app.post("/schedule", summary="Book an appointment", tags=["Appointments"])
async def schedule_appointment(request: AppointmentRequest):
    """Books an appointment if the requested slot is available."""

    # Validate date and time format
    try:
        requested_date = datetime.strptime(request.date, "%Y-%m-%d").date()
        requested_time = datetime.strptime(request.time, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time format. Use YYYY-MM-DD and HH:MM.")
    

    # Prevent past-date booking
    if requested_date < datetime.now().date():
        raise HTTPException(status_code=400, detail="Cannot book past dates.")

    # Check if the slot exists and is available
    slot = await calendar.find_one({"date": request.date, "start_time": request.time, "available": True})

    if not slot:
        raise HTTPException(status_code=400, detail="Requested time slot is unavailable.")

    # Mark slot as booked
    await calendar.update_one({"_id": slot["_id"]}, {"$set": {"available": False}})

    # Store appointment separately
    appointment_data = {
        "customer_name": request.customer_name,
        "service": request.service,
        "date": request.date,
        "time": request.time
    }

    result = await appointments.insert_one(appointment_data)

    # Convert ObjectId to string before returning response
    appointment_data["_id"] = str(result.inserted_id)

    return {"message": "Appointment booked!", "appointment": appointment_data}

# Fetch All Appointments
@app.get("/appointments", summary="Get all appointments", tags=["Appointments"])
async def get_appointments():
    """Fetch all booked appointments."""
    appointments_list = await appointments.find().to_list(length=None)
    
    if not appointments_list:
        raise HTTPException(status_code=404, detail="No appointments found")

    return jsonable_encoder([fix_id(app) for app in appointments_list])

# Include Admin & AI Interaction Routers
app.include_router(admin_router, prefix="/admin")  # Admin-related endpoints
app.include_router(ai_router, prefix="/ai", tags=["AI Interaction"])

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
