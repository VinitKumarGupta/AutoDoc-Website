import operator
import psycopg2
import json
from typing import Annotated, List, Literal, TypedDict, Union

from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver 
from pydantic import BaseModel
from dotenv import load_dotenv

import uuid # Needed for ticket generation
from robust_db import record_service_booking

load_dotenv()

# --- CONFIG ---
print("🕷️ Connecting to Local Ollama (Qwen 2.5)...")

llm_supervisor = ChatOllama(model="qwen2.5:7b", temperature=0, base_url="http://localhost:11434")
llm_worker = ChatOllama(model="qwen2.5:7b", temperature=0, base_url="http://localhost:11434")

# --- POSTGRES CONNECTION ---
DB_CONFIG = {
    "dbname": "fleet_management_v3", 
    "user": "postgres",
    "password": "Prerita#12", 
    "host": "localhost"
}

def query_pg(query, args=(), one=False):
    """Helper for Postgres Tools"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query, args)
        if query.strip().upper().startswith("SELECT"):
            cols = [desc[0] for desc in cur.description]
            rv = [dict(zip(cols, row)) for row in cur.fetchall()]
            conn.close()
            return (rv[0] if rv else None) if one else rv
        else:
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        return str(e)

# --- TOOLS ---

@tool
def analyze_fleet_trends(scope: str = "all"):
    """
    Analyzes the ENTIRE fleet to forecast service center demand and workload.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. Get Fleet Health Distribution (Assuming 'status' column exists in vehicles)
        cursor.execute("SELECT is_active, COUNT(*) FROM vehicles GROUP BY is_active")
        status_raw = cursor.fetchall()
        # Map boolean to text for report
        status_dist = {("Active" if row[0] else "Inactive"): row[1] for row in status_raw}

        # 2. Identify High-Risk Vehicles (Using basic criteria since we don't have live telemetry in SQL for all cars yet)
        # For demo purposes, we count cars older than 2020 as 'High Risk' if no error codes present
        cursor.execute("SELECT chassis_number, model FROM vehicles WHERE manufacturing_year < 2022")
        high_risk_cars = cursor.fetchall()
        
        demand_count = len(high_risk_cars)
        estimated_hours = demand_count * 3 

        # 3. Get High Mileage Trends (Simulated AVG based on standard usage)
        # Since we just created the DB, we might default to a value if table is empty
        avg_odometer = 45000 

        conn.close()

        return f"""
        📊 FLEET FORECAST REPORT
        ------------------------
        1. Health Overview: {status_dist}
        2. Immediate Service Demand: {demand_count} vehicles require attention (Older models).
           - Details: {[f"{c[0]} ({c[1]})" for c in high_risk_cars[:5]]} ...
        3. Projected Service Center Workload: {estimated_hours} Hours of labor required this week.
        4. Long-term Wear: Average fleet mileage is {int(avg_odometer):,} miles.
        
        RECOMMENDATION FOR SCHEDULER:
        {'🔴 Heavy Load - Open more slots immediately.' if demand_count > 3 else '🟢 Normal Load - Standard scheduling applies.'}
        """
    except Exception as e:
        return f"Error analyzing fleet: {e}"

@tool
def get_maintenance_history(vehicle_id: str):
    """Fetches historical service records (SQL) for a vehicle."""
    rows = query_pg("SELECT * FROM maintenance_history WHERE chassis_number = %s ORDER BY service_date DESC LIMIT 5", (vehicle_id,))
    if not rows or isinstance(rows, str): return "No maintenance history found."
    return "\n".join([f"- {row['service_date']}: {row['service_type']} ({row['description']})" for row in rows])

@tool
def diagnose_issue(error_code: str, engine_temp: int):
    """Analyzes diagnostic trouble codes (DTC) and sensor readings."""
    if engine_temp is None: return "Insufficient Data"
    
    issues = []
    if int(engine_temp) > 110:
        issues.append(f"CRITICAL OVERHEATING detected (Temp: {engine_temp}°C).")
    if error_code == "P0118":
        issues.append("Sensor Failure: Coolant Temperature Circuit High input.")
    if error_code == "P0420":
        issues.append("Catalyst System Efficiency Below Threshold.")
        
    if issues:
        return "DIAGNOSIS REPORT: " + " ".join(issues)
        
    return "Status: Normal. All parameters within operating limits."

@tool
def get_rca_insights(diagnosis: str):
    """Queries Manufacturing CAPA database for recurring defects."""
    rows = query_pg("SELECT * FROM capa_records")
    if not rows or isinstance(rows, str): return "No CAPA records found."
    
    matches = []
    for row in rows:
        if row["component"] in diagnosis or row["defect_type"] in diagnosis:
            matches.append(f"RCA INSIGHT: Batch {row['batch_id']} - {row['action_required']} (Match: {row['component']})")
            
    if matches: return " ".join(matches)
    return "No recurring manufacturing defects found in CAPA DB."

@tool
def check_schedule_availability():
    """Checks open slots in Postgres."""
    rows = query_pg("SELECT slot_time FROM appointments WHERE is_booked = FALSE LIMIT 4")
    if not rows or isinstance(rows, str): return "No slots available in the system."
    return f"OPEN SLOTS: {[r['slot_time'] for r in rows]}"

@tool
def book_appointment(slot: str, vehicle_id: str, issue_summary: str = "Routine Maintenance"):
    """
    Books a slot in Postgres AND creates a service ticket.
    """
    # 1. Standardize Slot Time
    clean_slot = slot.lower().replace("am", "").replace("pm", "").strip()
    if len(clean_slot) <= 2: clean_slot = f"{int(clean_slot):02d}:00"
    
    # 2. Check Availability
    existing = query_pg("SELECT appt_id, slot_time FROM appointments WHERE slot_time LIKE %s AND is_booked = FALSE", (f"%{clean_slot}%",), one=True)
    if not existing: return "Slot unavailable. Please pick another time."
    
    # 3. Mark Appointment as Booked
    query_pg("UPDATE appointments SET is_booked = TRUE, booked_chassis = %s WHERE appt_id = %s", (vehicle_id, existing['appt_id']))
    
    # 4. [FIX] Create Full Service Ticket for Manager View
    # We assign a random center for the chatbot (or default to Mumbai if not specified)
    ticket_id = f"AI-SRV-{uuid.uuid4().hex[:6].upper()}"
    
    # Call the robust_db function to insert into 'service_bookings'
    # This ensures it shows up in the Manager Dashboard
    record_service_booking(
        ticket_id=ticket_id,
        chassis=vehicle_id,
        owner_name="AI Booking", # Simplified
        issue=issue_summary,
        center_id="SC_DELHI",    # Defaulting to Delhi for AI bookings or you can make this dynamic
        center_name="Delhi NCR AutoHub"
    )

    return f"BOOKING CONFIRMED: Ticket {ticket_id} generated for {vehicle_id} at {existing['slot_time']}."

@tool
def update_vehicle_status(vehicle_id: str, status: str):
    """Updates the active status of a vehicle in the database."""
    is_active = True if status.lower() == "active" else False
    query_pg("UPDATE vehicles SET is_active = %s WHERE chassis_number = %s", (is_active, vehicle_id))
    return f"Status for {vehicle_id} updated to {status}."

@tool
def brave_search(query: str):
    """Performs a web search (Simulated offline mode)."""
    return "Offline Mode: Internet unavailable. Please use internal diagnosis tools."

@tool
def send_notification_to_owner(vehicle_id: str, message: str):
    """Sends an alert to the maintenance team."""
    return "Notification sent."

@tool
def send_alert_to_maintenance_team(vehicle_id: str, message: str):
    """Sends an alert to the maintenance team."""
    return "Alert sent."

@tool
def log_customer_feedback(feedback: str, rating: int):
    """Logs customer feedback and rating."""
    return "Feedback saved."

@tool
def report_manufacturing_defect(component: str, issue_description: str, vehicle_id: str):
    """Reports a manufacturing defect to the engineering team."""
    print(f"🏭 REPORTING TO FACTORY: Defect in {component} for {vehicle_id}: {issue_description}")
    return "Defect report submitted to Engineering Team."

@tool
def analyze_current_telemetry(telemetry_json: str):
    """Analyzes the LIVE JSON data passed from the vehicle sensors."""
    try:
        data = json.loads(telemetry_json)
        # Basic check for key values
        temp = data.get('temperature', data.get('engine_temp', 'N/A'))
        error = data.get('error_code', 'None')
        return f"Analysis: Current Temp is {temp}, Error Code: {error}"
    except:
        return "Could not parse telemetry."

# --- AGENTS (RESTORED PROMPTS) ---

data_analyst = create_react_agent(
    llm_worker, 
    tools=[analyze_current_telemetry, analyze_fleet_trends, get_maintenance_history, brave_search], 
    prompt=(
        "You are a Lead Data Analyst. "
        "1. If asked about a SPECIFIC vehicle, use 'analyze_current_telemetry' and 'get_maintenance_history'. "
        "2. If asked about 'Fleet Status', 'Forecasting', or 'Demand', use 'analyze_fleet_trends'. "
        "3. Output the data summary clearly and then STOP."
    )
)

diagnostician = create_react_agent(
    llm_worker, 
    tools=[diagnose_issue, update_vehicle_status, send_alert_to_maintenance_team, analyze_current_telemetry, brave_search], 
    prompt=(
        "You are an empathetic but urgent Vehicle Health Expert. "
        "1. When identifying a CRITICAL issue, explain the RISK in plain English. "
        "2. DO NOT ASK 'Would you like to proceed?' or 'Should I book?'. "
        "3. Instead, state: 'I am alerting the maintenance team and checking appointment slots immediately.' "
        "4. Your job is to alarm the user enough to fix it, then STOP."
    )
)

quality_engineer = create_react_agent(
    llm_worker, 
    tools=[get_rca_insights, report_manufacturing_defect], 
    prompt=(
        "You are a Senior Quality Engineer. "
        "1. Check 'get_rca_insights'. "
        "2. If a match is found, say: 'Good news—we have seen this before. It is a known issue with [Batch/Part].' "
        "3. State the solution clearly. "
        "4. End with 'QUALITY CHECK COMPLETE'."
    )
)

scheduler = create_react_agent(
    llm_worker, 
    tools=[check_schedule_availability, book_appointment, send_notification_to_owner, update_vehicle_status], 
    prompt=(
        "You are a persuasive Service Concierge. "
        "1. Your goal is to secure the booking. Do NOT ask 'Do you want to proceed?'. "
        "2. Assume the user wants to book. Call 'check_schedule_availability' immediately. "
        "3. State: 'To prevent damage, I have located priority slots at [List Slots].' "
        "4. End with a specific Call to Action: 'Which of these times works best for you?'"
        "5. If user provides a time, call 'book_appointment'."
    )
)

feedback_agent = create_react_agent(llm_worker, tools=[log_customer_feedback], prompt="Log feedback and say goodbye.")

# --- SUPERVISOR ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    next: str
    is_proactive: bool

members = ["DataAnalyst", "Diagnostician", "QualityEngineer", "Scheduler", "FeedbackAgent"]

class Router(BaseModel):
    next: Literal["DataAnalyst", "Diagnostician", "QualityEngineer", "Scheduler", "FeedbackAgent", "FINISH"]

supervisor_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "You are a Supervisor. Select the next agent."),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Metadata: is_proactive={is_proactive}"),
        ("system", "Who acts next? {options}"),
    ]).partial(options=str(members + ["FINISH"]))
    | llm_supervisor.with_structured_output(Router)
)

def supervisor_node(state: AgentState):
    """Hybrid Supervisor Logic - RESTORED from Project B"""
    messages = state["messages"]
    last_msg = messages[-1]
    history_str = " ".join([m.content for m in messages])
    is_proactive = state.get("is_proactive", False)

    # 1. AI JUST SPOKE
    if isinstance(last_msg, AIMessage):
        content = last_msg.content
        if "FLEET FORECAST REPORT" in content: return {"next": "FINISH"}
        if "CRITICAL" in content and "QUALITY CHECK COMPLETE" not in history_str: return {"next": "QualityEngineer"}
        if "QUALITY CHECK COMPLETE" in content:
            if "OPEN SLOTS" not in history_str: return {"next": "Scheduler"}
            else: return {"next": "FINISH"}
        if "OPEN SLOTS" in content: return {"next": "FINISH"} # Wait for user
        if "BOOKING COMPLETE" in content:
            if is_proactive: return {"next": "FINISH"}
            return {"next": "FeedbackAgent"}
        return {"next": "FINISH"}

    # 2. HUMAN JUST SPOKE
    user_text = last_msg.content.lower()
    
    # "Yes/Do it" Trap
    if ("yes" in user_text or "fix it" in user_text) and "OPEN SLOTS" not in history_str:
        return {"next": "Scheduler"}

    if "manufacturing" in user_text or "rca" in user_text: return {"next": "QualityEngineer"}
    if "fleet" in user_text or "forecast" in user_text: return {"next": "DataAnalyst"}
    
    # Missing basic data?
    if "Engine Temp" not in history_str and "Current Vehicle Telemetry" not in history_str:
        return {"next": "DataAnalyst"} 
        
    if "CRITICAL" not in history_str and "Status: Normal" not in history_str:
        return {"next": "Diagnostician"}
    
    if "QUALITY CHECK COMPLETE" in history_str and "BOOKING COMPLETE" not in history_str:
        return {"next": "Scheduler"}
        
    return {"next": "Scheduler"}

# --- GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("DataAnalyst", data_analyst)
workflow.add_node("Diagnostician", diagnostician)
workflow.add_node("QualityEngineer", quality_engineer)
workflow.add_node("Scheduler", scheduler)
workflow.add_node("FeedbackAgent", feedback_agent)

workflow.add_edge(START, "Supervisor")
workflow.add_conditional_edges("Supervisor", lambda s: s["next"], 
    {"DataAnalyst":"DataAnalyst", "Diagnostician":"Diagnostician", "QualityEngineer":"QualityEngineer", 
     "Scheduler":"Scheduler", "FeedbackAgent":"FeedbackAgent", "FINISH":END})
for m in members: workflow.add_edge(m, "Supervisor")

app = workflow.compile(checkpointer=MemorySaver())