import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'

// [FIX] Correct Backend URL (FastAPI default is 8000)
const BASE_URL = "http://localhost:8000";

export default function ChatbotWidget({ vehicleId, styles = {} }) {
  // [FIX] 'messages' state for Chat Mode history
  const [messages, setMessages] = useState([
    { role: 'system', content: '🤖 System Online. I can help with diagnostics and maintenance.' }
  ]);
  const [input, setInput] = useState("");
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const quickQuestions = [
    "Explain my current alert",
    "Is my vehicle safe to drive?",
    "What maintenance is due soon?",
    "Summarize all sensor issues",
  ];

  const fetchAlerts = async () => {
    try {
      // [FIX] Use BASE_URL (port 8000)
      const res = await axios.get(`${BASE_URL}/alerts/active`);
      setAlerts(res.data.alerts || []);
    } catch (e) {
      console.warn("Could not fetch alerts (API might be offline)", e);
    }
  };

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const ask = async (overrideQuestion) => {
    // Determine the text to send
    const textToSend = typeof overrideQuestion === 'string' ? overrideQuestion : input;
    
    if (!textToSend.trim()) return;
    if (!vehicleId) {
        setMessages(prev => [...prev, { role: 'system', content: '⚠️ Please select a vehicle first.' }]);
        return;
    }

    // 1. Add User Message to Chat
    setMessages(prev => [...prev, { role: 'user', content: textToSend }]);
    setInput(""); // Clear input
    setLoading(true);

    try {
      // 2. Call Backend
      const res = await axios.post(`${BASE_URL}/chatbot/query`, {
        chassis_number: vehicleId, // [FIX] Backend expects 'chassis_number', not 'vehicle_id'
        question: textToSend,
      });

      // 3. Add AI Response to Chat
      // Backend returns { answer: "...", ... }
      setMessages(prev => [...prev, { role: 'bot', content: res.data.answer }]);
      
      // Refresh alerts in case the chat triggered a fix or check
      fetchAlerts();

    } catch (error) {
      console.error("Chatbot query failed", error);
      
      // [FIX] Handle Error Object gracefully to avoid [object Object] crash
      let errorMsg = "Sorry, I couldn't reach the mechanic server.";
      if (error.response) {
         errorMsg = `Server Error: ${error.response.status}`;
      } else if (error.request) {
         errorMsg = "Connection Refused. Is the backend running on port 8000?";
      }
      
      setMessages(prev => [...prev, { role: 'bot', content: errorMsg }]);
    } finally {
      setLoading(false);
    }
  }

  // Fallback styles if not provided
  const defaultStyles = {
    card: { background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155', color: 'white' },
    btn: { padding: '8px 12px', borderRadius: '6px', border: 'none', background: '#3b82f6', color: 'white', cursor: 'pointer' },
    input: { padding: '10px', borderRadius: '8px', background: '#0f172a', border: '1px solid #334155', color: 'white' }
  };
  
  const s = { ...defaultStyles, ...styles };

  return (
    <div style={{ ...s.card, display: 'flex', flexDirection: 'column', height: '600px' }}>
      
      {/* HEADER */}
      <div style={{ marginBottom: '15px', borderBottom: '1px solid #334155', paddingBottom: '10px' }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            🤖 Vehicle Assistant 
            {vehicleId && <span style={{fontSize:'0.7em', background:'#334155', padding:'2px 6px', borderRadius:'4px'}}>{vehicleId}</span>}
        </h3>
      </div>

      {/* ACTIVE ALERTS SECTION (Preserved from your original design) */}
      {alerts.length > 0 && (
        <div style={{ marginBottom: '15px' }}>
            <div style={{ fontSize: '0.85em', fontWeight: 'bold', color: '#f59e0b', marginBottom: '5px' }}>⚠️ ACTIVE ALERTS</div>
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '5px' }}>
                {alerts.map((a, i) => (
                    <div key={i} style={{ background: '#451a03', padding: '8px', borderRadius: '6px', minWidth: '150px', border: '1px solid #f59e0b' }}>
                        <div style={{ fontWeight: 'bold', fontSize: '0.9em', color: '#fbbf24' }}>{a.predicted_failure_type}</div>
                        <div style={{ fontSize: '0.8em', color: '#fdba74' }}>Sensor: {a.root_cause_sensor}</div>
                    </div>
                ))}
            </div>
        </div>
      )}

      {/* CHAT HISTORY AREA (New "Chat Mode") */}
      <div style={{ 
          flex: 1, 
          overflowY: 'auto', 
          marginBottom: '15px', 
          padding: '10px', 
          background: 'rgba(0,0,0,0.2)', 
          borderRadius: '8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
      }}>
        {messages.map((m, i) => (
            <div key={i} style={{ 
                alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                background: m.role === 'user' ? '#2563eb' : '#334155',
                color: 'white',
                padding: '8px 12px',
                borderRadius: '12px',
                lineHeight: '1.4'
            }}>
                <div style={{ fontSize: '0.75em', opacity: 0.7, marginBottom: '2px' }}>
                    {m.role === 'user' ? 'You' : 'Assistant'}
                </div>
                {m.content}
            </div>
        ))}
        {loading && <div style={{ alignSelf: 'flex-start', color: '#94a3b8', fontSize: '0.9em' }}>Analyzing telemetry...</div>}
        <div ref={chatEndRef} />
      </div>

      {/* QUICK ACTIONS */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
        {quickQuestions.map(q => (
          <button 
            key={q} 
            style={{ ...s.btn, background: '#334155', fontSize: '0.85em', padding: '6px 10px' }} 
            onClick={() => ask(q)}
            disabled={loading}
          >
            {q}
          </button>
        ))}
      </div>

      {/* INPUT AREA */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <input 
            style={{ ...s.input, flex: 1 }} 
            value={input} 
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && ask()}
            placeholder={vehicleId ? "Ask about your car..." : "Select a car to begin"}
            disabled={loading}
        />
        <button style={s.btn} onClick={() => ask()} disabled={loading}>
            {loading ? "..." : "Ask"}
        </button>
      </div>

    </div>
  )
}