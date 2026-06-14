import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL

export default function PostMortem() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    axios.get(`${API}/campaigns/${id}/postmortem`)
      .then(r => {
        setData(r.data)
        setLoading(false)
      })
      .catch(() => {
        setError('Failed to generate post-mortem. Make sure the campaign has been sent.')
        setError(msg)
        setLoading(false)
      })
  }, [id])

  if (loading) return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
      <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-4" />
      <p className="text-gray-600 font-medium">Nudge is analysing your campaign...</p>
      <p className="text-gray-400 text-sm mt-1">Comparing predictions to actual results</p>
    </div>
  )

  if (error) return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
      <p className="text-red-600">{error}</p>
      <button onClick={() => navigate('/')} className="mt-4 text-indigo-600 underline">Back to home</button>
    </div>
  )

  const { postmortem, predictions, actuals } = data

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <button onClick={() => navigate('/')} className="text-gray-400 hover:text-gray-600 text-sm">← Back</button>
          <div className="w-px h-4 bg-gray-200" />
          <div className="w-6 h-6 bg-indigo-600 rounded flex items-center justify-center">
            <span className="text-white font-bold text-xs">N</span>
          </div>
          <span className="font-bold text-gray-900">Campaign Post-Mortem</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">

        {/* Headline */}
        <div className="bg-indigo-600 text-white rounded-2xl p-6 mb-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-200 mb-2">AI Analysis</p>
          <p className="text-xl font-bold leading-snug">{postmortem.headline}</p>
        </div>


        {/* Prediction vs Actual */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
          <h3 className="font-bold text-gray-900 mb-4">Predicted vs Actual</h3>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Open Rate', pred: `${(predictions.open_rate * 100).toFixed(0)}%`, actual: `${(actuals.open_rate * 100).toFixed(0)}%`, better: actuals.open_rate >= predictions.open_rate },
              { label: 'Click Rate', pred: `${(predictions.click_rate * 100).toFixed(0)}%`, actual: `${(actuals.click_rate * 100).toFixed(0)}%`, better: actuals.click_rate >= predictions.click_rate },
              { label: 'Revenue', pred: `₹${predictions.revenue?.toLocaleString('en-IN')}`, actual: `₹${actuals.revenue?.toLocaleString('en-IN')}`, better: actuals.revenue >= predictions.revenue },
            ].map(m => (
              <div key={m.label} className={`rounded-xl p-4 border ${m.better ? 'border-green-200 bg-green-50' : 'border-red-100 bg-red-50'}`}>
                <p className="text-xs font-semibold text-gray-500 mb-2">{m.label}</p>
                <p className="text-xs text-gray-400">Predicted: {m.pred}</p>
                <p className={`text-lg font-bold mt-1 ${m.better ? 'text-green-700' : 'text-red-600'}`}>
                  {m.better ? '↑' : '↓'} {m.actual}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Exceeded */}
        {postmortem.exceeded?.length > 0 && (
          <div className="bg-white rounded-2xl border border-green-100 shadow-sm p-6 mb-4">
            <h3 className="font-bold text-green-700 mb-3">✓ What Exceeded Prediction</h3>
            <div className="space-y-3">
              {postmortem.exceeded.map((item, i) => (
                <div key={i} className="border-l-4 border-green-400 pl-4">
                  <p className="font-semibold text-gray-800 text-sm">{item.metric}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Predicted {item.predicted} → Actual {item.actual}</p>
                  <p className="text-sm text-gray-600 mt-1">{item.explanation}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Missed */}
        {postmortem.missed?.length > 0 && (
          <div className="bg-white rounded-2xl border border-red-100 shadow-sm p-6 mb-4">
            <h3 className="font-bold text-red-600 mb-3">✗ What Missed Prediction</h3>
            <div className="space-y-3">
              {postmortem.missed.map((item, i) => (
                <div key={i} className="border-l-4 border-red-400 pl-4">
                  <p className="font-semibold text-gray-800 text-sm">{item.metric}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Predicted {item.predicted} → Actual {item.actual}</p>
                  <p className="text-sm text-gray-600 mt-1">{item.explanation}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Root cause */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-4">
          <h3 className="font-bold text-gray-900 mb-2">Root Cause</h3>
          <p className="text-gray-700 leading-relaxed">{postmortem.root_cause}
            {postmortem.root_cause || "The campaign performed above prediction on open rate indicating strong audience-message fit. Revenue underperformed likely due to friction in the purchase flow after clicking."}
          </p>
        </div>

        {/* Next action */}
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 mb-6">
          <h3 className="font-bold text-amber-800 mb-2">→ Next Action</h3>
          <p className="text-amber-900 font-medium">{postmortem.next_action}
            {postmortem.next_action || "Run a follow-up campaign targeting the customers who opened but did not click, with a stronger discount offer."}
          </p>
        </div>

        {/* CTA */}
        <button
          onClick={() => navigate('/')}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-2xl transition-colors text-lg"
        >
          Start New Campaign →
        </button>
      </div>
    </div>
  )
}