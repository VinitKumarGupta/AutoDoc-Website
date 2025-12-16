# 🚔 Fleet Command: Agentic AI Predictive Maintenance

**Fleet Command** is a production-ready **Agentic AI System** for the automotive industry. It bridges the gap between real-time vehicle telemetry, autonomous AI diagnosis, and secure service operations.

Designed for **Team Collaboration**, this project runs entirely in the cloud using **GitHub Codespaces** and a **Shared Neon Database**, ensuring all developers see the same live data instantly.

---

## 🌟 Key Features

### 1. Intelligent Core
* **Real-Time Telemetry:** Streams live sensor data (Temperature, Vibration, RPM) via WebSockets.
* **AI Diagnosis Agent:** Continuously analyzes streams to flag "High Risk" patterns.
* **UEBA Security Layer:** A "Firewall for AI" that blocks malicious commands (e.g., unauthorized engine blocks).
* **Automated RCA:** Root Cause Analysis agent provides specific repair fixes based on failure signatures.

### 2. Multi-Role Ecosystem
* **🏢 Dealer Portal:** Inventory management and CRM for assigning vehicles to users.
* **🚗 Owner Portal (My Garage):** Live health monitoring and one-click service booking.

---

## 🚀 Team Setup Guide (5 Minutes)

We use **GitHub Codespaces** for development. Follow these steps to get your environment running and connected to the team database.

### Phase 1: Launch Environment
1.  Go to the **GitHub Repository**.
2.  Click the green **Code** button -> **Codespaces** tab.
3.  Click **"Create codespace on main"**.
    * *Wait ~3 minutes for the container to build and install dependencies.*

### Phase 2: Connect to Shared Database
We use a shared cloud database (Neon) so the whole team stays in sync.

1.  **Get the Secret:** Ask your Team Lead for the `DATABASE_URL` connection string.
2.  **Configure Backend:**
    * Create a file named `.env` inside the `backend/` folder.
    * Paste the connection string:
        ```ini
        DATABASE_URL=postgres://neondb_owner:YOUR_PASSWORD@ep-cool-host.aws.neon.tech/neondb?sslmode=require
        ```
    * *Note: If you don't do this, the app might try to use a default read-only DB or fail to connect.*

### Phase 3: Start the Servers
Open two terminals in VS Code (`Terminal` -> `New Terminal`) and run:

**Terminal 1 (Backend):**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

**Terminal 2 (Frontend):**

```bash
cd frontend
npm run dev -- --host
```

### Phase 4: Connect Frontend to Backend (CRITICAL STEP)

Since Codespaces assigns a unique URL to your backend, you must update the frontend to talk to *your* specific instance.

1.  **Make Backend Public:**

      * Go to the **PORTS** tab (bottom panel).
      * Right-click **Port 8001** -\> **Port Visibility** -\> **Public**.
      * Copy the **Local Address** (e.g., `https://shiny-acorn-8001.app.github.dev`).

2.  **Update Config:**

      * Open `frontend/src/App.jsx`.
      * **Find & Replace** the old URL (e.g., `https://old-space...`) with **your new Backend URL**.
      * *Repeat this check for:*
          * `frontend/src/ChatbotWidget.jsx`
          * `frontend/src/ManagerBookings.jsx`

-----

## 🕹️ How to Use

**1. Access the App:**

  * Go to the **PORTS** tab.
  * Click the **Globe Icon** next to **Port 5173** (Frontend).

**2. Login Credentials:**

| Role | Username | Password | Features |
| :--- | :--- | :--- | :--- |
| **Dealer** | `DLR_TATA` | `admin` | Add stock, Sell cars, View service bookings |
| **User** | `rahul` | `123` | View My Garage, Simulate Issues, Chat with AI |

**3. Demo Flow:**

1.  Login as **Dealer** -\> Add a car (e.g., VIN: `MH-01`, Model: `Nexon`).
2.  Assign it to user `rahul`.
3.  Logout and login as **User** (`rahul`).
4.  You will see the car\! Click **"Simulate Issue"** to trigger the AI Agents.

-----

## 🛠️ Project Structure

```text
/
├── .devcontainer/      # Codespaces configuration (Python + Node + Postgres)
├── backend/            # FastAPI Application
│   ├── agent_graph.py  # LangGraph AI Logic
│   ├── main.py         # API Routes
│   └── database.py     # Database Models (SQLAlchemy)
└── frontend/           # React + Vite Application
    ├── src/App.jsx     # Main Dashboard Logic
    └── src/ChatbotWidget.jsx # AI Assistant Component
```

## 🤝 Collaboration Workflow

  * **Syncing Code:** Use the Source Control tab to **Commit** and **Sync Changes** (Push/Pull).
  * **Syncing Data:** Data is stored in the cloud. If you add a user, your teammates see it instantly.
