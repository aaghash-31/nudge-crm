import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL

const DOT_COLORS = {
  delivered: 'bg-green-500',
  opened: 'bg-blue-500',
  clicked: 'bg-orange-500',
  converted: 'bg-purple-600',
  failed: 'bg-red-500',
  complete: 'bg-gray-400',
}

export default function LiveFeed() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [events, setEvents] = useState([])
  const [stats, setStats] = useState({ total: 0, delivered: 0, opened: 0, clicked: 0, converted: 0, revenue: 0 })
  const [predicted, setPredicted] = useState(null)
  const [complete, setComplete] = useState(false)
  const statsRef = useRef(stats)

  // Load campaign predictions once
  useEffect(() => {
    axios.get(`${API}/campaigns/${id}`).then(r => {
      const c = r.data
      setPredicted({
        open_rate: c.predicted_open_rate,
        click_rate: c.predicted_click_rate,
        revenue: c.predicted_revenue,
        total: c.stats?.total || 0
      })
      setStats(c.stats || stats)
      statsRef.current = c.stats || stats
    }).catch(() => {})
  }, [id])

  // Poll stats every 8 seconds — single source of truth
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await axios.get(`${API}/campaigns/${id}`)
        const s = r.data.stats
        if (!s) return

        // Only update if numbers actually changed
        if (
          s.delivered !== statsRef.current.delivered ||
          s.opened !== statsRef.current.opened ||
          s.clicked !== statsRef.current.clicked ||
          s.converted !== statsRef.current.converted ||
          s.revenue !== statsRef.current.revenue
        ) {
          statsRef.current = s
          setStats(s)

          // Add narrative events for new state changes
          if (s.delivered > 0 && s.delivered !== statsRef.current?.delivered) {
            const pct = Math.round(s.delivered / s.total * 100)
            addEvent('delivered', `✓ ${s.delivered} of ${s.total} messages delivered (${pct}%)`)
          }
          if (s.opened > 0) {
            const pct = Math.round(s.opened / s.total * 100)
            addEvent('opened', `👁 ${s.opened} customers opened — ${pct}% open rate`)
          }
          if (s.clicked > 0) {
            const pct = Math.round(s.clicked / s.total * 100)
            addEvent('clicked', `🔗 ${s.clicked} clicked through — ${pct}% click rate`)
          }
          if (s.converted > 0) {
            addEvent('converted', `🛒 ${s.converted} orders placed — ₹${s.revenue?.toLocaleString('en-IN')} revenue`)
          }
        }

        // Check completion
        const allDone = s.total > 0 && (s.delivered + s.failed) >= s.total
        if (allDone) {
          setComplete(true)
          addEvent('complete', `Campaign complete. ${s.converted} conversions, ₹${s.revenue?.toLocaleString('en-IN')} attributed revenue.`)
        }
      } catch (e) {}
    }

    // Poll immediately then every 8 seconds
    poll()
    const interval = setInterval(poll, 8000)
    return () => clearInterval(interval)
  }, [id])

  const seenNarratives = useRef(new Set())

  const addEvent = (type, narrative) => {
    if (seenNarratives.current.has(narrative)) return
    seenNarratives.current.add(narrative)
    setEvents(prev => [{
      id: Date.now() + Math.random(),
      type,
      narrative,
      time: new Date().toLocaleTimeString()
    }, ...prev])
  }

  const openRate = stats.total > 0 ? ((stats.opened / stats.total) * 100).toFixed(1) : 0
  const clickRate = stats.total > 0 ? ((stats.clicked / stats.total) * 100).toFixed(1) : 0

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-600 text-sm">← Back</button>
            <div className="w-px h-4 bg-gray-200" />
            <div className="w-6 h-6 bg-indigo-600 rounded flex items-center justify-center">
              <span className="text-white font-bold text-xs">N</span>
            </div>
            <span className="font-bold text-gray-900">Live Campaign Feed</span>
          </div>
          {!complete && (
            <div className="flex items-center gap-2 text-sm text-green-600">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Live
            </div>
          )}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6">
        {/* Summary bar */}
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: 'Sent', value: stats.total, color: 'text-gray-700' },
            { label: 'Delivered', value: stats.delivered, color: 'text-green-600' },
            { label: 'Opened', value: stats.opened, color: 'text-blue-600' },
            { label: 'Clicked', value: stats.clicked, color: 'text-orange-600' },
            { label: 'Converted', value: stats.converted, color: 'text-purple-600' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-100 p-4 text-center shadow-sm">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-400 mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Left: Event feed */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-bold text-gray-900">Delivery Events</h2>
              <p className="text-xs text-gray-400 mt-0.5">Real-time callbacks from channel service</p>
            </div>
            <div className="overflow-y-auto" style={{ height: '480px' }}>
              {events.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400">
                  <div className="w-6 h-6 border-2 border-gray-200 border-t-indigo-400 rounded-full animate-spin mb-3" />
                  <p className="text-sm">Waiting for delivery callbacks...</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {events.map(ev => (
                    <div key={ev.id} className="flex items-start gap-3 px-5 py-3">
                      <div className={`w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0 ${DOT_COLORS[ev.type] || 'bg-gray-400'}`} />
                      <div className="flex-1">
                        <p className="text-sm text-gray-800">{ev.narrative}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{ev.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Funnel */}
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
              <h2 className="font-bold text-gray-900 mb-4">Predicted vs Actual</h2>
              {[
                { label: 'Dispatched', actual: stats.total, predicted: predicted?.total || stats.total, color: 'bg-gray-400' },
                { label: 'Delivered', actual: stats.delivered, predicted: Math.round((predicted?.total || stats.total) * 0.92), color: 'bg-green-500' },
                { label: 'Opened', actual: stats.opened, predicted: Math.round((predicted?.total || stats.total) * (predicted?.open_rate || 0.3)), color: 'bg-blue-500' },
                { label: 'Clicked', actual: stats.clicked, predicted: Math.round((predicted?.total || stats.total) * (predicted?.click_rate || 0.1)), color: 'bg-orange-500' },
                { label: 'Converted', actual: stats.converted, predicted: Math.round((predicted?.total || stats.total) * 0.05), color: 'bg-purple-600' },
              ].map(row => (
                <div key={row.label} className="mb-4">
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span className="font-medium">{row.label}</span>
                    <span>
                      <span className="text-gray-400">pred: {row.predicted}</span>
                      <span className="mx-1">·</span>
                      <span className="font-bold text-gray-800">actual: {row.actual}</span>
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3 relative">
                    <div
                      className={`${row.color} h-3 rounded-full opacity-30`}
                      style={{ width: row.predicted > 0 ? `${Math.min((row.predicted / (stats.total || 1)) * 100, 100)}%` : '0%' }}
                    />
                    <div
                      className={`${row.color} h-3 rounded-full absolute top-0 left-0 transition-all duration-500`}
                      style={{ width: row.actual > 0 ? `${Math.min((row.actual / (stats.total || 1)) * 100, 100)}%` : '0%' }}
                    />
                  </div>
                </div>
              ))}

              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex justify-between">
                  <div className="text-center">
                    <p className="text-xl font-bold text-gray-900">{openRate}%</p>
                    <p className="text-xs text-gray-400">Open Rate</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-gray-900">{clickRate}%</p>
                    <p className="text-xs text-gray-400">Click Rate</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-gray-900">₹{stats.revenue?.toLocaleString('en-IN') || 0}</p>
                    <p className="text-xs text-gray-400">Revenue</p>
                  </div>
                </div>
              </div>
            </div>

            {complete && (
              <div className="bg-indigo-600 rounded-2xl p-5 text-white">
                <p className="font-bold text-lg mb-1">Campaign Complete</p>
                <p className="text-indigo-200 text-sm mb-4">All delivery callbacks received.</p>
                <button
                  onClick={() => navigate(`/campaigns/${id}/postmortem`)}
                  className="w-full bg-white text-indigo-600 font-bold py-3 rounded-xl hover:bg-indigo-50 transition-colors"
                >
                  Generate Post-Mortem →
                </button>
              </div>
            )}

            {!complete && (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                <p className="text-sm text-gray-500 text-center">Campaign running · updating every 8 seconds</p>
                <button
                  onClick={() => navigate(`/campaigns/${id}/postmortem`)}
                  className="w-full mt-3 border border-indigo-200 text-indigo-600 font-semibold py-2 rounded-xl hover:bg-indigo-50 text-sm transition-colors"
                >
                  Generate Post-Mortem Early
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}