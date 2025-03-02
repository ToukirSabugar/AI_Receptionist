from pymongo import MongoClient

# MongoDB Connection
MONGO_URL = "mongodb://localhost:27017"
client = MongoClient(MONGO_URL)
db = client["ai_receptionist"]
business_data = db["business_data"]

business_info = {
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

# Insert Data into MongoDB
business_data.insert_one(business_info)

print("Business data inserted successfully!")


# Find the duplicate entries
duplicates = business_data.find({"business_name": "TechFix Solutions"})

# Delete one of the duplicate entries
if duplicates.count() > 1:
    business_data.delete_one({"_id": duplicates[0]["_id"]})

print("Duplicate business data entry deleted successfully!")