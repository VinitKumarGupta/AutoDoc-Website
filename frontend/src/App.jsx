import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ManagerBookings from './ManagerBookings'
import ChatbotWidget from './ChatbotWidget'
import './App.css' // Ensures the new styles are applied

function App() {
  // --- AUTH STATE ---
  const [session, setSession] = useState(null)
  const [role, setRole] = useState(null)
  
  // Login Form Inputs
  const [loginUser, setLoginUser] = useState() // Updated default
  const [loginPass, setLoginPass] = useState()
  const [loginRole, setLoginRole] = useState("dealer")
  const [authError, setAuthError] = useState("")
  const [loading, setLoading] = useState(false)

  // --- DEALER STATE ---
  const [activeTab, setActiveTab] = useState("inventory")
  const [newVin, setNewVin] = useState("")
  const [newModel, setNewModel] = useState("Tata Nexon EV")
  const [assignTarget, setAssignTarget] = useState("rahul")

  // --- USER STATE ---
  const [selectedCar, setSelectedCar] = useState(null)
  const [telemetry, setTelemetry] = useState(null)
  const [attackMode, setAttackMode] = useState(false)
  const [ticket, setTicket] = useState(null)
  const [centerId, setCenterId] = useState("SC_MUMBAI")
  const [securityLogs, setSecurityLogs] = useState([])
  const socketRef = useRef(null)

  const serviceCenters = [
    { id: "SC_MUMBAI", name: "Mumbai Central Service" },
    { id: "SC_PUNE", name: "Pune Express Service" },
    { id: "SC_NAVI", name: "Navi Mumbai AutoCare" },
  ]

  // ================= API CALLS =================

  const handleLogin = async (e) => {
    e.preventDefault()
    setAuthError("")
    setLoading(true)
    try {
      // Note: Backend port 8000 based on your previous config
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
        dealer_id: session.dealer_id, // Updated to match DB response
        chassis_number: newVin,       // Updated to match backend key
        model: newModel
      })
      // Refresh session logic or append locally
      alert("Stock Added!")
      // In a real app, we'd refetch dealer data here
    } catch (e) { alert("Error adding stock") }
  }

  const assignCar = async (vin) => {
    try {
      const res = await axios.post("http://localhost:8000/dealer/assign", {
        dealer_id: session.dealer_id, 
        chassis_number: vin, 
        target_username: assignTarget
      })
      // Update inventory locally for immediate feedback
      setSession(prev => ({
        ...prev, 
        inventory: res.data.inventory, 
        sold_vehicles: res.data.sold
      }))
      alert(`Assigned ${vin} to ${assignTarget}`)
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
    // Connecting to Backend Port 8000
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


  // ================= VIEW: LOGIN (Stylized) =================
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
            <input value={loginUser} onChange={e=>setLoginUser(e.target.value)} placeholder="e.g. HERO_DLR" />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={loginPass} onChange={e=>setLoginPass(e.target.value)} placeholder="Password" />
          </div>
          
          {authError && <div className="error-message">{authError}</div>}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? 'Authenticating...' : 'LOGIN'}
          </button>
        </form>
        
        <div className="login-footer">
          <p>Demo Dealer: <strong>HERO_DLR</strong> / <strong>admin</strong></p>
          <p>Demo Owner: <strong>rahul</strong> / <strong>123</strong></p>
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
              <div className="form-group" style={{marginBottom:0}}>
                <label>VIN</label>
                <input value={newVin} onChange={e=>setNewVin(e.target.value)} placeholder="e.g. MH-101" />
              </div>
              <div className="form-group" style={{marginBottom:0}}>
                <label>Model</label>
                <select style={{padding:'12px', borderRadius:'8px', background:'rgba(0,0,0,0.2)', color:'white', border:'1px solid rgba(255,255,255,0.1)'}} value={newModel} onChange={e=>setNewModel(e.target.value)}>
                  <option>Tata Nexon EV</option>
                  <option>Hero Splendor</option>
                  <option>Mahindra Thar</option>
                </select>
              </div>
              <button className="login-btn" style={{width:'auto', background:'var(--success)'}} onClick={addStock}>+ ADD</button>
            </div>

            <h3>Available Inventory</h3>
            <table>
              <thead><tr><th>VIN</th><th>Model</th><th>Action</th></tr></thead>
              <tbody>
                {(session.inventory || []).map(car => (
                  <tr key={car.chassis_number}>
                    <td>{car.chassis_number}</td>
                    <td>{car.model}</td>
                    <td>
                      <div style={{display:'flex', gap:'10px'}}>
                        <input placeholder="Username" style={{padding:'5px', background:'transparent', border:'1px solid #555', color:'white'}} value={assignTarget} onChange={e=>setAssignTarget(e.target.value)} />
                        <button className="badge success" style={{border:'none', cursor:'pointer'}} onClick={()=>assignCar(car.chassis_number)}>SELL</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

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
           <ManagerBookings centerId={centerId} onCenterChange={setCenterId} serviceCenters={serviceCenters} />
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
                   <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
                      <h2>Live Monitor: {selectedCar.model}</h2>
                      <div className="badge" style={{fontSize:'1rem', background: telemetry.risk_score_numeric > 0.8 ? 'var(--danger)' : 'var(--success)'}}>
                        Risk: {telemetry.risk_score_numeric}
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

                   {/* UEBA STATUS */}
                   {telemetry.ueba && (
                     <div style={{marginTop:'15px', padding:'15px', background:'rgba(255,255,255,0.05)', borderRadius:'8px'}}>
                       <div style={{fontWeight:'bold', color:'var(--primary)'}}>🛡️ Data Integrity Check</div>
                       <div style={{fontSize:'0.9rem', marginTop:'5px'}}>Status: {telemetry.ueba.ueba_status} (Score: {telemetry.ueba.ueba_score})</div>
                     </div>
                   )}

                   {/* EXTENDED TELEMETRY */}
                   <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(120px, 1fr))', gap:'10px', marginTop:'20px'}}>
                      <div className="badge">Oil Quality: {telemetry.oil_quality_contaminants_V_oil}</div>
                      <div className="badge">Battery: {telemetry.battery_soh_percent}%</div>
                      <div className="badge">Brake Wear: {telemetry.brake_pad_wear_percent}%</div>
                   </div>

                   {/* ALERT & BOOKING */}
                   {telemetry.predicted_failure_type !== "None" && telemetry.risk_score_numeric > 0.5 && (
                     <div style={{marginTop:'20px', padding:'20px', background:'rgba(239, 68, 68, 0.1)', borderRadius:'8px', border:'1px solid var(--danger)'}}>
                        <h3 style={{color:'var(--danger)', margin:'0 0 10px 0'}}>⚠️ Issue Detected: {telemetry.predicted_failure_type}</h3>
                        <p>Recommended Action: Check {telemetry.root_cause_sensor}</p>
                        
                        <div style={{marginTop:'15px', display:'flex', gap:'10px', alignItems:'center'}}>
                           <select style={{padding:'10px', borderRadius:'6px'}} value={centerId} onChange={e=>setCenterId(e.target.value)}>
                              {serviceCenters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
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
              
              <ChatbotWidget vehicleId={selectedCar?.chassis_number} />
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App