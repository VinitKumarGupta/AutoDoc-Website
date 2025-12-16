import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import ManagerBookings from './ManagerBookings'
import ChatbotWidget from './ChatbotWidget'

function App() {
  // --- AUTH STATE ---
  const [session, setSession] = useState(null) // Holds full user/dealer object
  const [role, setRole] = useState(null) // 'user' | 'dealer'
  
  // Login Form Inputs
  const [loginUser, setLoginUser] = useState("DLR_TATA")
  const [loginPass, setLoginPass] = useState("admin")
  const [loginRole, setLoginRole] = useState("dealer")

  // --- DEALER STATE ---
  const [activeTab, setActiveTab] = useState("inventory") // 'inventory' | 'sold'
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
    try {
      const res = await axios.post("http://localhost:8001/login", {
        username: loginUser, password: loginPass, role: loginRole
      })
      setSession(res.data.data)
      setRole(res.data.role)
      
      // If User, auto-select first car
      if (res.data.role === "user" && res.data.data.vehicles.length > 0) {
        setSelectedCar(res.data.data.vehicles[0])
      }
    } catch (err) { alert("Login Failed") }
  }

  const addStock = async () => {
    if(!newVin) return alert("Enter VIN")
    try {
      const res = await axios.post("http://localhost:8001/dealer/add-stock", {
        dealer_id: session.id, vehicle_id: newVin, model: newModel
      })
      setSession({...session, inventory: res.data})
      setNewVin(""); alert("Stock Added!")
    } catch (e) { alert("Error adding stock") }
  }

  const assignCar = async (vin) => {
    try {
      const res = await axios.post("http://localhost:8001/dealer/assign", {
        dealer_id: session.id, vehicle_id: vin, target_username: assignTarget
      })
      setSession({...session, inventory: res.data.inventory, sold_vehicles: res.data.sold})
      alert(`Assigned ${vin} to ${assignTarget}`)
    } catch (e) { alert("Assignment Failed (User exists?)") }
  }

  const toggleAttack = async () => {
    const next = !attackMode
    setAttackMode(next)
    await axios.post(`http://localhost:8001/toggle-attack/${next}`)
  }

  const bookService = async () => {
    if (!selectedCar || !telemetry?.repair_recommendation) {
      return alert("No issue detected to book against yet.")
    }
    try {
      const res = await axios.post("http://localhost:8001/book-service", {
        vehicle_id: selectedCar.id,
        owner_name: session.name,
        issue: telemetry.repair_recommendation.issue,
        dealer_name: selectedCar.dealer.name,
        center_id: centerId, // ensure backend center selection
      })
      const tid = res.data.ticket_id ?? null
      if (tid) setTicket(tid)
    } catch (err) {
      const msg = err?.response?.data || err?.message || "Booking failed"
      alert(`Booking failed: ${JSON.stringify(msg)}`)
    }
  }

  // ================= WEBSOCKET =================
  useEffect(() => {
    if (role !== "user" || !selectedCar) return;
    const ws = new WebSocket(`ws://localhost:8001/ws/1?vehicle_id=${selectedCar.id}&role=user`)
    ws.onmessage = (e) => setTelemetry(JSON.parse(e.data))
    socketRef.current = ws
    return () => ws.close()
  }, [selectedCar, role])

  useEffect(() => {
    const fetchSecurity = async () => {
      if (role !== "dealer") return
      try {
        const res = await axios.get("http://localhost:8001/security/logs")
        setSecurityLogs(res.data.logs || [])
      } catch (e) { /* ignore */ }
    }
    fetchSecurity()
  }, [role])


  // ================= STYLES =================
  const styles = {
    base: { fontFamily: 'Segoe UI', background: '#0f172a', color: 'white', minHeight: '100vh', padding: '20px' },
    card: { background: '#1e293b', padding: '20px', borderRadius: '10px', marginBottom: '20px' },
    input: { padding: '10px', background: '#334155', border: '1px solid #475569', color: 'white', borderRadius: '5px', marginRight: '10px' },
    btn: { padding: '10px 20px', background: '#2563eb', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' },
    table: { width: '100%', borderCollapse: 'collapse', marginTop: '10px' },
    th: { textAlign: 'left', padding: '10px', color: '#94a3b8', borderBottom: '1px solid #334155' },
    td: { padding: '10px', borderBottom: '1px solid #334155' }
  }

  // ================= VIEW: LOGIN =================
  if (!session) return (
    <div style={{...styles.base, display:'flex', justifyContent:'center', alignItems:'center'}}>
      <div style={{...styles.card, width: '350px', textAlign: 'center'}}>
        <h1>🔐 Fleet Login</h1>
        <div style={{marginBottom:'20px'}}>
           <button style={{...styles.btn, background: loginRole==='dealer'?'#2563eb':'#334155'}} onClick={()=>setLoginRole('dealer')}>Dealer</button>
           <button style={{...styles.btn, marginLeft:'10px', background: loginRole==='user'?'#2563eb':'#334155'}} onClick={()=>setLoginRole('user')}>Owner</button>
        </div>
        <form onSubmit={handleLogin}>
          <input style={{...styles.input, width:'90%', marginBottom:'10px'}} value={loginUser} onChange={e=>setLoginUser(e.target.value)} placeholder="Username" />
          <input style={{...styles.input, width:'90%', marginBottom:'20px'}} type="password" value={loginPass} onChange={e=>setLoginPass(e.target.value)} placeholder="Password" />
          <button style={{...styles.btn, width:'100%'}}>LOGIN</button>
        </form>
        <p style={{color:'#64748b', fontSize:'0.8em', marginTop:'20px'}}>
          Defaults:<br/>Dealer: DLR_TATA / admin<br/>User: rahul / 123
        </p>
      </div>
    </div>
  )

  // ================= VIEW: DEALER DASHBOARD =================
  if (role === "dealer") return (
    <div style={styles.base}>
      <div style={{display:'flex', justifyContent:'space-between', marginBottom:'20px'}}>
        <h1>🏢 {session.name} <span style={{fontSize:'0.5em', color:'#94a3b8'}}>DEALER PORTAL</span></h1>
        <button onClick={()=>setSession(null)} style={{...styles.btn, background:'#dc2626'}}>Logout</button>
      </div>

      {/* TABS */}
      <div style={{marginBottom:'20px'}}>
        <button style={{...styles.btn, background: activeTab==='inventory'?'#2563eb':'#334155', marginRight:'10px'}} onClick={()=>setActiveTab('inventory')}>📦 Unassigned Stock</button>
        <button style={{...styles.btn, background: activeTab==='sold'?'#2563eb':'#334155'}} onClick={()=>setActiveTab('sold')}>🤝 Sales History</button>
      </div>

      {activeTab === 'inventory' && (
        <div style={styles.card}>
          <h3>Add New Vehicle Stock</h3>
          <div style={{display:'flex', gap:'10px', marginBottom:'20px'}}>
            <input style={styles.input} value={newVin} onChange={e=>setNewVin(e.target.value)} placeholder="Enter VIN (e.g. MH-101)" />
            <select style={styles.input} value={newModel} onChange={e=>setNewModel(e.target.value)}>
              <option>Tata Nexon EV</option>
              <option>Tata Harrier</option>
              <option>Tata Punch</option>
            </select>
            <button style={{...styles.btn, background:'#10b981'}} onClick={addStock}>+ ADD TO STOCK</button>
          </div>

          <h3>Available Inventory</h3>
          <table style={styles.table}>
            <thead><tr><th style={styles.th}>VIN</th><th style={styles.th}>Model</th><th style={styles.th}>Action</th></tr></thead>
            <tbody>
              {session.inventory.map(car => (
                <tr key={car.id}>
                  <td style={styles.td}>{car.id}</td>
                  <td style={styles.td}>{car.model}</td>
                  <td style={styles.td}>
                    Assign to: <input style={{...styles.input, padding:'5px', width:'80px'}} value={assignTarget} onChange={e=>setAssignTarget(e.target.value)} />
                    <button style={{...styles.btn, padding:'5px 10px', fontSize:'0.8em'}} onClick={()=>assignCar(car.id)}>SELL</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {session.inventory.length === 0 && <p style={{color:'#64748b'}}>No stock available. Add some above.</p>}
        </div>
      )}

      {activeTab === 'sold' && (
        <div style={styles.card}>
          <h3>Sold Vehicles (Service CRM)</h3>
          <table style={styles.table}>
            <thead><tr><th style={styles.th}>VIN</th><th style={styles.th}>Model</th><th style={styles.th}>Owner Name</th><th style={styles.th}>Contact</th><th style={styles.th}>Date</th></tr></thead>
            <tbody>
              {session.sold_vehicles.map(sale => (
                <tr key={sale.id}>
                  <td style={styles.td}>{sale.id}</td>
                  <td style={styles.td}>{sale.model}</td>
                  <td style={styles.td}><span style={{color:'#4ade80', fontWeight:'bold'}}>{sale.owner_name}</span></td>
                  <td style={styles.td}>{sale.owner_phone}</td>
                  <td style={styles.td}>{sale.sale_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ManagerBookings centerId={centerId} onCenterChange={setCenterId} serviceCenters={serviceCenters} styles={styles} />

      <div style={styles.card}>
        <h3>🛡️ UEBA Security Center</h3>
        <div style={{fontSize:'0.9em', color:'#94a3b8'}}>Recent web/behavior alerts</div>
        <table style={styles.table}>
          <thead><tr><th style={styles.th}>Path</th><th style={styles.th}>Method</th><th style={styles.th}>IP</th><th style={styles.th}>Score</th><th style={styles.th}>Findings</th></tr></thead>
          <tbody>
            {securityLogs.slice(-20).reverse().map((log, idx) => (
              <tr key={idx}>
                <td style={styles.td}>{log.path}</td>
                <td style={styles.td}>{log.method}</td>
                <td style={styles.td}>{log.ip}</td>
                <td style={styles.td}>{log.score}</td>
                <td style={styles.td}>{(log.findings || []).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {securityLogs.length === 0 && <p style={{color:'#64748b'}}>No security alerts logged.</p>}
      </div>
    </div>
  )

  // ================= VIEW: USER DASHBOARD =================
  return (
    <div style={styles.base}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h1>🚗 My Garage <span style={{fontSize:'0.5em', color:'#94a3b8'}}>Welcome, {session.name}</span></h1>
        <div>
          <button style={{...styles.btn, marginRight:'10px', background:attackMode?'#dc2626':'#475569'}} onClick={toggleAttack}>{attackMode?'STOP SIM':'SIMULATE ISSUE'}</button>
          <button onClick={()=>setSession(null)} style={{...styles.btn, background:'#334155'}}>Logout</button>
        </div>
      </div>

      {session.vehicles.length === 0 ? (
        <div style={{...styles.card, textAlign:'center', marginTop:'50px'}}>
          <h2>Empty Garage 😢</h2>
          <p>You haven't bought any cars yet.</p>
          <p>Ask your dealer to assign a vehicle to username: <strong>{loginUser}</strong></p>
        </div>
      ) : (
        <div style={{display:'flex', gap:'20px'}}>
          {/* CAR SELECTOR */}
          <div style={{width:'250px'}}>
             {session.vehicles.map(v => (
               <div key={v.id} onClick={()=>{setSelectedCar(v); setTicket(null)}} style={{...styles.card, cursor:'pointer', border: selectedCar?.id===v.id?'2px solid #2563eb':'1px solid #334155'}}>
                 <div style={{fontWeight:'bold'}}>{v.model}</div>
                 <div style={{fontSize:'0.8em', color:'#94a3b8'}}>{v.id}</div>
               </div>
             ))}
          </div>
          
          {/* MAIN DASHBOARD */}
          <div style={{flex:1}}>
            {telemetry ? (
              <div style={styles.card}>
                 <div style={{display:'flex', justifyContent:'space-between'}}>
                    <h2>Live Monitor: {selectedCar.model}</h2>
                    <h2 style={{color: telemetry.risk_score==='HIGH_RISK'?'#ef4444':'#4ade80'}}>{telemetry.risk_score}</h2>
                 </div>
                 
                 <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:'10px', marginTop:'20px'}}>
                    <div style={{background:'#0f172a', padding:'20px', textAlign:'center', borderRadius:'8px'}}>
                       <div style={{color:'#94a3b8'}}>TEMP</div>
                       <div style={{fontSize:'2em'}}>{telemetry.temperature}°C</div>
                    </div>
                    <div style={{background:'#0f172a', padding:'20px', textAlign:'center', borderRadius:'8px'}}>
                       <div style={{color:'#94a3b8'}}>VIBRATION</div>
                       <div style={{fontSize:'2em'}}>{telemetry.vibration}</div>
                    </div>
                    <div style={{background:'#0f172a', padding:'20px', textAlign:'center', borderRadius:'8px'}}>
                       <div style={{color:'#94a3b8'}}>RPM</div>
                       <div style={{fontSize:'2em'}}>{telemetry.rpm}</div>
                    </div>
                 </div>

                 {telemetry.ueba && (
                   <div style={{marginTop:'10px', padding:'14px', background:'#1f2937', borderRadius:'8px', border:'1px solid #334155'}}>
                     <div style={{display:'flex', justifyContent:'space-between'}}>
                        <div style={{fontWeight:'bold'}}>Data Integrity Status</div>
                        <div style={{color: telemetry.ueba.ueba_status === 'CRITICAL' ? '#ef4444' : telemetry.ueba.ueba_status === 'SUSPICIOUS' ? '#f59e0b' : '#4ade80'}}>
                          {telemetry.ueba.ueba_status}
                        </div>
                     </div>
                     <div style={{color:'#94a3b8', marginTop:'6px'}}>Score: {telemetry.ueba.ueba_score}</div>
                     <ul style={{marginTop:'6px', paddingLeft:'18px', color:'#cbd5e1'}}>
                       {(telemetry.ueba.ueba_findings || []).map((f,i)=><li key={i}>{f}</li>)}
                     </ul>
                   </div>
                 )}

                 {/* Extended Telemetry (additive) */}
                 <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:'10px', marginTop:'10px'}}>
                    {telemetry.vehicle_type && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>Type</div>
                        <div style={{fontSize:'1.1em'}}>{telemetry.vehicle_type}</div>
                      </div>
                    )}
                    {telemetry.ev_battery_temp_C !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>EV Batt Temp</div>
                        <div>{telemetry.ev_battery_temp_C}°C</div>
                      </div>
                    )}
                    {telemetry.ev_voltage_stability !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>EV Volt Stability</div>
                        <div>{telemetry.ev_voltage_stability}</div>
                      </div>
                    )}
                    {telemetry.petrol_knock_index !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>Knock Index</div>
                        <div>{telemetry.petrol_knock_index}</div>
                      </div>
                    )}
                    {telemetry.truck_axle_load_imbalance !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>Axle Imbalance</div>
                        <div>{telemetry.truck_axle_load_imbalance}</div>
                      </div>
                    )}
                    {telemetry.ambulance_high_rpm_flag !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>Amb High RPM</div>
                        <div>{telemetry.ambulance_high_rpm_flag ? "Yes" : "No"}</div>
                      </div>
                    )}
                    {telemetry.motorcycle_vibration !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>Moto Vib</div>
                        <div>{telemetry.motorcycle_vibration}</div>
                      </div>
                    )}
                    {telemetry.truck_exhaust_temp_C !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>Exhaust Temp</div>
                        <div>{telemetry.truck_exhaust_temp_C}°C</div>
                      </div>
                    )}
                    {telemetry.ev_cell_delta_V !== undefined && (
                      <div style={{background:'#0f172a', padding:'14px', borderRadius:'8px'}}>
                        <div style={{color:'#94a3b8'}}>Cell ΔV</div>
                        <div>{telemetry.ev_cell_delta_V} V</div>
                      </div>
                    )}
                 </div>

                 {/* RCA / BOOKING SECTION */}
                 {telemetry.repair_recommendation && (
                   <div style={{marginTop:'20px', padding:'20px', background:'#1e3a8a', borderRadius:'8px', border:'1px solid #3b82f6'}}>
                      <h3>🔧 Issue Detected: {telemetry.repair_recommendation.issue}</h3>
                      <p>Fix: {telemetry.repair_recommendation.action}</p>
                      <hr style={{borderColor:'#3b82f6', margin:'15px 0'}}/>
                      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                         <div>
                            <div style={{fontSize:'0.8em', opacity:0.7}}>SERVICE PARTNER</div>
                            <strong>{selectedCar.dealer.name}</strong>
                            <div style={{marginTop:'8px'}}>
                              <select style={styles.input} value={centerId} onChange={e=>{setCenterId(e.target.value); setTicket(null)}}>
                                {serviceCenters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                              </select>
                            </div>
                         </div>
                         {ticket ? (
                           <div style={{background:'#064e3b', padding:'10px', borderRadius:'5px'}}>✅ Ticket: {ticket}</div>
                         ) : (
                           <button onClick={bookService} style={{...styles.btn, background:'#10b981'}}>BOOK SERVICE APPOINTMENT</button>
                         )}
                      </div>
                   </div>
                 )}
              </div>
            ) : <p>Connecting to satellite...</p>}
            <ChatbotWidget vehicleId={selectedCar?.id} styles={styles} />
          </div>
        </div>
      )}
    </div>
  )
}

export default App