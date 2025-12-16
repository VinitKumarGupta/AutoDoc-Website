import { useState, useEffect } from 'react'
import axios from 'axios'

export default function ChatbotWidget({ vehicleId, styles }) {
  const [question, setQuestion] = useState("How is my vehicle health?")
  const [answer, setAnswer] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(false)
  const quickQuestions = [
    "Explain my current alert",
    "Is my vehicle safe to drive?",
    "What maintenance is due soon?",
    "Summarize all sensor issues",
  ]

  const fetchAlerts = async () => {
    try {
      const res = await axios.get("http://localhost:8001/alerts/active")
      setAlerts(res.data.alerts || [])
    } catch (e) {
      console.error("Failed to load alerts", e)
    }
  }

  const ask = async (overrideQuestion) => {
    if (!vehicleId) return
    const q = overrideQuestion ?? question
    if (overrideQuestion) setQuestion(overrideQuestion)
    setLoading(true)
    try {
      const res = await axios.post("http://localhost:8001/chatbot/query", {
        vehicle_id: vehicleId,
        question: q,
      })
      setAnswer(res.data)
      fetchAlerts()
    } catch (e) {
      console.error("Chatbot query failed", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlerts()
  }, [])

  return (
    <div style={{...styles.card, marginTop:'20px'}}>
      <h3>🤖 Vehicle Assistant</h3>
      <div style={{display:'flex', gap:'8px', flexWrap:'wrap', marginBottom:'8px'}}>
        {quickQuestions.map(q => (
          <button key={q} style={{...styles.btn, background:'#334155', padding:'6px 10px'}} onClick={()=>ask(q)} disabled={loading || !vehicleId}>{q}</button>
        ))}
      </div>
      <div style={{display:'flex', gap:'10px', marginBottom:'10px'}}>
        <input style={{...styles.input, flex:1}} value={question} onChange={e=>setQuestion(e.target.value)} />
        <button style={styles.btn} onClick={ask} disabled={loading || !vehicleId}>{loading ? "..." : "Ask"}</button>
      </div>
      {answer && (
        <div style={{background:'#0f172a', padding:'10px', borderRadius:'8px'}}>
          <div style={{fontWeight:'bold'}}>Answer:</div>
          <div style={{marginBottom:'8px'}}>{answer.answer || answer.explanation}</div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:'6px', marginTop:'10px'}}>
            <div style={{color:'#94a3b8'}}>Cause</div><div>{answer.most_likely_cause}</div>
            <div style={{color:'#94a3b8'}}>Action</div><div>{answer.recommended_action}</div>
            <div style={{color:'#94a3b8'}}>Urgency</div><div style={{color: answer.urgency === 'critical' ? '#ef4444' : '#f59e0b'}}>{answer.urgency}</div>
            <div style={{color:'#94a3b8'}}>Risk</div><div>{answer.risk_level}</div>
          </div>
          {answer.subsystem && (
            <div style={{marginTop:'8px', fontSize:'0.9em', color:'#94a3b8'}}>
              Subsystem: {answer.subsystem}
            </div>
          )}
        </div>
      )}
      <div style={{marginTop:'10px'}}>
        <div style={{fontWeight:'bold', marginBottom:'5px'}}>Active Alerts</div>
        {alerts.length === 0 && <div style={{color:'#64748b'}}>None</div>}
        {alerts.map(a => (
          <div key={a.vehicle_id} style={{background:'#1e293b', padding:'8px', borderRadius:'6px', marginBottom:'6px'}}>
            <div style={{fontWeight:'bold'}}>{a.predicted_failure_type}</div>
            <div style={{fontSize:'0.9em', color:'#94a3b8'}}>Sensor: {a.root_cause_sensor} | Risk: {a.risk_score}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

