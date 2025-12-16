import { useEffect, useState } from 'react'
import axios from 'axios'

export default function ManagerBookings({ centerId, serviceCenters, styles, onCenterChange }) {
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchBookings = async (cid) => {
    if (!cid) return
    setLoading(true)
    try {
      const res = await axios.get(`http://localhost:8001/manager/bookings`, { params: { center_id: cid } })
      setBookings(res.data.bookings || [])
    } catch (e) {
      console.error("Failed to load bookings", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBookings(centerId)
  }, [centerId])

  return (
    <div style={{...styles.card, marginTop:'20px'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h3>📅 Service Appointments</h3>
        <div>
          <select style={styles.input} value={centerId} onChange={e => { onCenterChange(e.target.value); fetchBookings(e.target.value); }}>
            {serviceCenters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
      </div>
      {loading ? <p>Loading...</p> : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Ticket</th>
              <th style={styles.th}>Vehicle</th>
              <th style={styles.th}>Owner</th>
              <th style={styles.th}>Issue</th>
              <th style={styles.th}>Center</th>
              <th style={styles.th}>Created</th>
            </tr>
          </thead>
          <tbody>
            {bookings.map(b => (
              <tr key={b.ticket_id || b.vehicle_id + b.created_at}>
                <td style={styles.td}>{b.ticket_id}</td>
                <td style={styles.td}>{b.vehicle_id}</td>
                <td style={styles.td}>{b.owner_name}</td>
                <td style={styles.td}>{b.issue}</td>
                <td style={styles.td}>{b.service_center}</td>
                <td style={styles.td}>{b.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {(!loading && bookings.length === 0) && <p style={{color:'#64748b'}}>No bookings yet for this center.</p>}
    </div>
  )
}

