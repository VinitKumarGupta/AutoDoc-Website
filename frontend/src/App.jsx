import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ManagerBookings from './ManagerBookings'
import ChatbotWidget from './ChatbotWidget'
import './App.css'

function App() {
  // --- AUTH STATE ---
  const [session, setSession] = useState(null)
  const [role, setRole] = useState(null)
  
  // Login Form Inputs
  const [loginUser, setLoginUser] = useState()
  const [loginPass, setLoginPass] = useState()
  const [loginRole, setLoginRole] = useState("dealer")
  const [authError, setAuthError] = useState("")
  const [loading, setLoading] = useState(false)

  // --- DEALER STATE ---
  const [activeTab, setActiveTab] = useState("inventory")
  const [newVin, setNewVin] = useState("")
  const [newModel, setNewModel] = useState("")
  
  // [FIX 1] Change State to an Object to handle multiple inputs independently
  // Structure: { "VIN-123": "username1", "VIN-456": "username2" }
  const [assignTargets, setAssignTargets] = useState({}) 

  // --- USER STATE ---
  const [selectedCar, setSelectedCar] = useState(null)
  const [telemetry, setTelemetry] = useState(null)
  const [attackMode, setAttackMode] = useState(false)
  const [ticket, setTicket] = useState(null)
  const [centerId, setCenterId] = useState("SC_MUMBAI")
  const [securityLogs, setSecurityLogs] = useState([])
  const socketRef = useRef(null)

  const SERVICE_CENTERS = [
    {"id": "SC_MUMBAI", "name": "Mumbai Central Service", "lat": 19.0760, "lon": 72.8777, "manager": "mumbai.manager@svc.local"},
    {"id": "SC_PUNE", "name": "Pune Express Service", "lat": 18.5204, "lon": 73.8567, "manager": "pune.manager@svc.local"},
    {"id": "SC_DELHI", "name": "Delhi NCR AutoHub", "lat": 28.7041, "lon": 77.1025, "manager": "delhi.manager@svc.local"},
    {"id": "SC_BLR", "name": "Bangalore TechCheck", "lat": 12.9716, "lon": 77.5946, "manager": "blr.manager@svc.local"},
    {"id": "SC_CHENNAI", "name": "Chennai Coastal Care", "lat": 13.0827, "lon": 80.2707, "manager": "chennai.manager@svc.local"},
    {"id": "SC_KOLKATA", "name": "Kolkata Eastern Motors", "lat": 22.5726, "lon": 88.3639, "manager": "kolkata.manager@svc.local"},
  ]

  // [HELPER] Determine styling/placeholders based on Dealer Brand
  const isHero = (session?.brand || session?.username || '').toUpperCase().includes('HERO');
  const vinPlaceholder = isHero ? "e.g. HERO-MVR-205" : "e.g. MAH-XUV-705";
  const modelPlaceholder = isHero ? "e.g. Mavrick 440" : "e.g. XUV 7XO";

  const styles = {
    card: {
      background: 'var(--bg-card)',
      padding: '1.5rem',
      borderRadius: '12px',
      border: '1px solid rgba(255, 255, 255, 0.05)',
      marginTop: '20px'
    },
    input: {
      padding: '10px',
      borderRadius: '8px',
      background: 'rgba(0,0,0,0.2)',
      border: '1px solid rgba(255,255,255,0.1)',
      color: 'white',
      width: '100%',
      boxSizing: 'border-box'
    },
    table: { width: '100%', borderCollapse: 'collapse' },
    th: { textAlign: 'left', padding: '10px', color: '#94a3b8', borderBottom: '1px solid #334155' },
    td: { padding: '10px', borderBottom: '1px solid #334155' },
    btn: {
      padding: '8px 16px',
      borderRadius: '6px',
      border: 'none',
      background: 'var(--primary)',
      color: 'white',
      cursor: 'pointer'
    }
  }

  // ================= API CALLS =================

  const handleLogin = async (e) => {
    e.preventDefault()
    setAuthError("")
    setLoading(true)
    try {
      const res = await axios.post("http://localhost:8000/login", {
        username: loginUser, password: loginPass, role: loginRole
      })
      setSession(res.data.data)
      setRole(res.data.role)
      
      if (res.data.role === "user" && res.data.data.vehicles.length > 0) {
        setSelectedCar(res.data.data.vehicles[0])
      }
    } catch (err) { 
      setAuthError("Login Failed. Check credentials or backend.") 
    } finally {
      setLoading(false)
    }
  }

  const addStock = async () => {
    if(!newVin) return alert("Enter VIN")
    try {
      const res = await axios.post("http://localhost:8000/dealer/add-stock", {
        dealer_id: session.dealer_id,
        chassis_number: newVin,
        model: newModel
      })
      alert("Stock Added!")
    } catch (e) { alert("Error adding stock") }
  }

  // [FIX 1] Updated assignCar to read from the object state
  const assignCar = async (vin) => {
    const targetUser = assignTargets[vin]; // Get specific input for this car

    if (!targetUser) return alert("Please enter a username to sell to.");

    try {
      const res = await axios.post("http://localhost:8000/dealer/assign", {
        dealer_id: session.dealer_id, 
        chassis_number: vin, 
        target_username: targetUser
      })
      
      setSession(prev => ({
        ...prev, 
        inventory: res.data.inventory, 
        sold_vehicles: res.data.sold
      }))
      
      // Clear the input for this specific car after success
      setAssignTargets(prev => ({...prev, [vin]: ""})) 
      
      alert(`Assigned ${vin} to ${targetUser}`)
    } catch (e) { alert("Assignment Failed (User exists?)") }
  }

  const toggleAttack = async () => {
    const next = !attackMode
    setAttackMode(next)
    await axios.post(`http://localhost:8000/toggle-attack/${next}`)
  }

  const bookService = async () => {
    if (!selectedCar || !telemetry?.predicted_failure_type) {
      return alert("No issue detected to book against yet.")
    }
    try {
      const res = await axios.post("http://localhost:8000/book-service", {
        chassis_number: selectedCar.chassis_number,
        owner_name: session.full_name,
        issue: telemetry.predicted_failure_type,
        dealer_name: selectedCar.dealer_id || "Hero MotoCorp",
        center_id: centerId,
      })
      const tid = res.data.ticket_id ?? "TKT-000"
      setTicket(tid)
    } catch (err) {
      alert("Booking failed")
    }
  }

  // ================= WEBSOCKET =================
  useEffect(() => {
    if (role !== "user" || !selectedCar) return;
    const ws = new WebSocket(`ws://localhost:8000/ws/1?vehicle_id=${selectedCar.chassis_number}&role=user`)
    ws.onmessage = (e) => setTelemetry(JSON.parse(e.data))
    socketRef.current = ws
    return () => ws.close()
  }, [selectedCar, role])

  useEffect(() => {
    const fetchSecurity = async () => {
      if (role !== "dealer") return
      try {
        const res = await axios.get("http://localhost:8000/security/logs")
        setSecurityLogs(res.data.logs || [])
      } catch (e) { /* ignore */ }
    }
    fetchSecurity()
  }, [role])


  // ================= VIEW: LOGIN =================
  if (!session) return (
    <div className="login-wrapper">
      <div className="login-card">
        <div className="login-header">
          <h1>AutoDoc</h1>
          <p>Intelligent Fleet Management</p>
        </div>
        
        <div style={{display:'flex', justifyContent:'center', gap:'10px', marginBottom:'20px'}}>
           <button 
             className={`login-btn ${loginRole !== 'dealer' ? 'secondary' : ''}`} 
             style={{background: loginRole==='dealer'?'var(--primary)':'rgba(255,255,255,0.1)'}}
             onClick={()=>setLoginRole('dealer')}
           >Dealer</button>
           <button 
             className={`login-btn ${loginRole !== 'user' ? 'secondary' : ''}`}
             style={{background: loginRole==='user'?'var(--primary)':'rgba(255,255,255,0.1)'}}
             onClick={()=>setLoginRole('user')}
           >Owner</button>
        </div>

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label>Username</label>
            <input value={loginUser} onChange={e=>setLoginUser(e.target.value)} placeholder="Enter Username" />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={loginPass} onChange={e=>setLoginPass(e.target.value)} placeholder="Enter Password" />
          </div>
          
          {authError && <div className="error-message">{authError}</div>}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? 'Authenticating...' : 'LOGIN'}
          </button>
        </form>
        
        <div className="login-footer">
          <p>Note:<br></br>Password for Dealers: <strong>admin</strong><br></br>Password for Owners: <strong>123</strong></p>
        </div>
      </div>
    </div>
  )

  // ================= VIEW: DEALER DASHBOARD =================
  if (role === "dealer") return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h2>AutoDoc <span className="highlight">Dealer Portal</span></h2>
        <div style={{display:'flex', alignItems:'center'}}>
          <span style={{marginRight:'15px', color:'var(--text-gray)'}}>{session.full_name}</span>
          <button onClick={()=>setSession(null)} className="logout-btn">Logout</button>
        </div>
      </header>

      <main className="dashboard-content">
        <div className="stats-grid">
            <div className="stat-card">
              <h3>Inventory</h3>
              <p className="stat-number">{session.inventory?.length || 0}</p>
            </div>
            <div className="stat-card">
              <h3>Vehicles Sold</h3>
              <p className="stat-number">{session.sold_vehicles?.length || 0}</p>
            </div>
            <div className="stat-card">
               <h3>Security Alerts</h3>
               <p className="stat-number alert">{securityLogs.length}</p>
            </div>
        </div>

        {/* TABS */}
        <div style={{marginBottom:'20px'}}>
          <button 
            className="login-btn" 
            style={{width:'auto', marginRight:'10px', background: activeTab==='inventory'?'var(--primary)':'var(--bg-card)'}} 
            onClick={()=>setActiveTab('inventory')}
          >📦 Unassigned Stock</button>
          <button 
            className="login-btn" 
            style={{width:'auto', background: activeTab==='sold'?'var(--primary)':'var(--bg-card)'}} 
            onClick={()=>setActiveTab('sold')}
          >🤝 Sales History</button>
        </div>

        {activeTab === 'inventory' && (
        <div className="inventory-section">
          <h3>Add New Vehicle Stock</h3>
          <div style={{display:'flex', gap:'10px', marginBottom:'20px', alignItems:'end'}}>
            <div className="form-group" style={{marginBottom:0, flex:1}}>
              <label>VIN (Chassis Number)</label>
              <input 
                style={styles.input}
                value={newVin} 
                onChange={e=>setNewVin(e.target.value)} 
                placeholder={vinPlaceholder} 
              />
            </div>
            <div className="form-group" style={{marginBottom:0, flex:1}}>
              <label>Model Name</label>
              <input 
                  style={styles.input} 
                  value={newModel} 
                  onChange={e=>setNewModel(e.target.value)} 
                  placeholder={modelPlaceholder}
              />
            </div>
            <button className="login-btn" style={{width:'auto', background:'var(--success)', height:'42px'}} onClick={addStock}>
              + ADD STOCK
            </button>
          </div>

          <h3>Available Inventory</h3>
          <table style={styles.table}>
            <thead>
              <tr>
                  <th style={styles.th}>VIN</th>
                  <th style={styles.th}>Model</th>
                  <th style={styles.th}>Buyer Username</th>
              </tr>
            </thead>
            <tbody>
              {(session.inventory || []).map(car => (
                <tr key={car.chassis_number}>
                  <td style={styles.td}>{car.chassis_number}</td>
                  <td style={styles.td}>{car.model}</td>
                  <td style={styles.td}>
                    <div style={{display:'flex', gap:'10px'}}>
                      {/* [FIX 1] Independent Input for each row */}
                      <input 
                          placeholder="Enter Username" 
                          style={{...styles.input, padding:'5px', fontSize:'0.9em'}} 
                          value={assignTargets[car.chassis_number] || ""} 
                          onChange={e => setAssignTargets({
                              ...assignTargets, 
                              [car.chassis_number]: e.target.value
                          })} 
                      />
                      <button className="badge success" style={{border:'none', cursor:'pointer'}} onClick={()=>assignCar(car.chassis_number)}>
                          SELL
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {/* ... Rest of Dealer View (Sales History, etc.) ... */}
      {activeTab === 'sold' && (
          <div className="inventory-section">
            <h3>Sales History</h3>
            <table>
              <thead><tr><th>VIN</th><th>Model</th><th>Owner</th><th>Date</th></tr></thead>
              <tbody>
                {(session.sold_vehicles || []).map(sale => (
                  <tr key={sale.chassis_number}>
                    <td>{sale.chassis_number}</td>
                    <td>{sale.model}</td>
                    <td><span className="badge success">{sale.owner_username}</span></td>
                    <td>{sale.sale_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{marginTop:'2rem'}}>
           <ManagerBookings 
             centerId={centerId} 
             onCenterChange={setCenterId} 
             serviceCenters={SERVICE_CENTERS} 
             styles={styles} 
           />
        </div>

        <div className="inventory-section" style={{marginTop:'2rem'}}>
          <h3>🛡️ UEBA Security Logs</h3>
          <table>
            <thead><tr><th>Path</th><th>Method</th><th>Score</th><th>Findings</th></tr></thead>
            <tbody>
              {securityLogs.slice(-10).reverse().map((log, idx) => (
                <tr key={idx}>
                  <td>{log.path}</td>
                  <td>{log.method}</td>
                  <td style={{color: log.score > 50 ? 'var(--danger)' : 'var(--text-light)'}}>{log.score}</td>
                  <td>{(log.findings || []).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )

  // ================= VIEW: USER DASHBOARD =================
  return (
    <div className="dashboard-container">
      {/* ... (Header and Stats) ... */}
      <header className="dashboard-header">
        <h2>My <span className="highlight">Garage</span></h2>
        <div style={{display:'flex', alignItems:'center', gap:'15px'}}>
          <button 
            className="badge" 
            style={{background: attackMode?'var(--danger)':'var(--bg-card)', color:'white', border:'1px solid #555', cursor:'pointer'}} 
            onClick={toggleAttack}
          >
            {attackMode ? '⚠️ STOP SIMULATION' : '🧪 SIMULATE ATTACK'}
          </button>
          <button onClick={()=>setSession(null)} className="logout-btn">Logout</button>
        </div>
      </header>

      <main className="dashboard-content">
        {(session.vehicles || []).length === 0 ? (
          <div className="stat-card" style={{textAlign:'center'}}>
            <h2>Empty Garage 😢</h2>
            <p>You haven't bought any cars yet.</p>
          </div>
        ) : (
          <div className="content-row">
            {/* CAR SELECTOR */}
            <div style={{display:'flex', flexDirection:'column', gap:'15px'}}>
               {(session.vehicles || []).map(v => (
                 <div key={v.chassis_number} onClick={()=>{setSelectedCar(v); setTicket(null)}} 
                      className="stat-card"
                      style={{cursor:'pointer', border: selectedCar?.chassis_number===v.chassis_number?'2px solid var(--primary)':'1px solid transparent'}}>
                   <h3>{v.model}</h3>
                   <p style={{margin:0, color:'var(--text-gray)'}}>{v.chassis_number}</p>
                 </div>
               ))}
            </div>
            
            {/* MAIN MONITOR */}
            <div style={{flex:1}}>
              {telemetry ? (
                <div className="stat-card" style={{borderTop: '4px solid var(--primary)'}}>
                   {/* ... (Telemetry Grid) ... */}
                   <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                      <div>
                        <h2 className="monitor-label">Live Monitor</h2>
                        <div className="monitor-vehicle-title">{selectedCar.model}</div>
                      </div>
                      <div className={`risk-score ${telemetry.risk_score_numeric > 0.8 ? 'danger' : 'safe'}`}>
                          {telemetry.risk_score_numeric > 0.8 && <span style={{fontSize:'1.2em'}}>⚠️</span>}
                          <span>Risk: {telemetry.risk_score_numeric}</span>
                      </div>
                   </div>
                   
                   <div className="stats-grid">
                      <div style={{background:'rgba(0,0,0,0.3)', padding:'15px', borderRadius:'8px', textAlign:'center'}}>
                         <div style={{color:'var(--text-gray)'}}>TEMP</div>
                         <div style={{fontSize:'1.5rem', fontWeight:'bold'}}>{telemetry.temperature}°C</div>
                      </div>
                      <div style={{background:'rgba(0,0,0,0.3)', padding:'15px', borderRadius:'8px', textAlign:'center'}}>
                         <div style={{color:'var(--text-gray)'}}>VIBRATION</div>
                         <div style={{fontSize:'1.5rem', fontWeight:'bold'}}>{telemetry.vibration}</div>
                      </div>
                      <div style={{background:'rgba(0,0,0,0.3)', padding:'15px', borderRadius:'8px', textAlign:'center'}}>
                         <div style={{color:'var(--text-gray)'}}>RPM</div>
                         <div style={{fontSize:'1.5rem', fontWeight:'bold'}}>{telemetry.rpm}</div>
                      </div>
                   </div>

                   {telemetry.ueba && (
                     <div style={{marginTop:'15px', padding:'15px', background:'rgba(255,255,255,0.05)', borderRadius:'8px'}}>
                       <div style={{fontWeight:'bold', color:'var(--primary)'}}>🛡️ Data Integrity Check</div>
                       <div style={{fontSize:'0.9rem', marginTop:'5px'}}>Status: {telemetry.ueba.ueba_status} (Score: {telemetry.ueba.ueba_score})</div>
                     </div>
                   )}

                   <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(120px, 1fr))', gap:'10px', marginTop:'20px'}}>
                      <div className="badge">Oil Quality <br></br>{telemetry.oil_quality_contaminants_V_oil}</div>
                      <div className="badge">Battery <br></br>{telemetry.battery_soh_percent}%</div>
                      <div className="badge">Brake Wear <br></br>{telemetry.brake_pad_wear_percent}%</div>
                   </div>

                   {/* ALERT & BOOKING */}
                   {telemetry.predicted_failure_type !== "None" && telemetry.risk_score_numeric > 0.5 && (
                     <div style={{marginTop:'20px', padding:'20px', background:'rgba(239, 68, 68, 0.1)', borderRadius:'8px', border:'1px solid var(--danger)'}}>
                        <h3 style={{color:'var(--danger)', margin:'0 0 10px 0'}}>⚠️ Issue Detected: {telemetry.predicted_failure_type}</h3>
                        <p>Recommended Action: Check {telemetry.root_cause_sensor}</p>
                        
                        <div style={{marginTop:'15px', display:'flex', gap:'10px', alignItems:'center'}}>
                          
                          {/* [FIX 2] Variable Name Mismatch Corrected: SERVICE_CENTERS */}
                          <select 
                              style={{...styles.input, width:'auto', cursor:'pointer', background:'var(--bg-card)'}} 
                              value={centerId} 
                              onChange={e=>setCenterId(e.target.value)}
                          >
                              {SERVICE_CENTERS.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                          </select>
                          
                          {ticket ? (
                            <div className="badge success">✅ Booked! Ticket: {ticket}</div>
                          ) : (
                            <button onClick={bookService} className="login-btn" style={{width:'auto', background:'var(--danger)'}}>
                              BOOK REPAIR
                            </button>
                          )}
                        </div>
                     </div>
                   )}
                </div>
              ) : <p style={{padding:'20px'}}>📡 Connecting to vehicle telemetry...</p>}
              
              <ChatbotWidget 
                vehicleId={selectedCar?.chassis_number} 
                styles={styles}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App