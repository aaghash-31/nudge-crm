import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL

function ConfidenceScore({ score }) {
  const [displayed, setDisplayed] = useState(0)

  useEffect(() => {
    let current = 0
    const timer = setInterval(() => {
      current += 2
      if (current >= score) {
        setDisplayed(score)
        clearInterval(timer)
      } else {
        setDisplayed(current)
      }
    }, 20)
    return () => clearInterval(timer)
  }, [score])

  const color = score >= 70
    ? 'text-green-600 border-green-500'
    : score >= 40
    ? 'text-yellow-600 border-yellow-500'
    : 'text-red-600 border-red-500'

  return (
    <div className={`w-32 h-32 rounded-full border-8 flex flex-col items-center justify-center ${color}`}>
      <span className="text-4xl font-bold">{displayed}</span>
      <span className="text-xs font-medium">CONFIDENCE</span>
    </div>
  )
}

function ConfidenceCard({ card, campaignId, sampleProfiles }) {
  const [approving, setApproving] = useState(false)
  const navigate = useNavigate()

  async function handleApprove() {
    setApproving(true)
    try {
      await axios.post(`${API}/campaigns/${campaignId}/send`)
      navigate(`/campaigns/${campaignId}/live`)
    } catch (e) {
      alert('Failed to send campaign')
      setApproving(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 mt-6 border border-gray-100">
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Campaign Confidence Card</h2>
          <p className="text-gray-600">{card.segment_description}</p>
        </div>
        <div className="ml-6">
          <ConfidenceScore score={card.confidence_score} />
        </div>
      </div>

      {/* Channel reasoning */}
      <div className="bg-blue-50 rounded-xl p-4 mb-6">
        <p className="text-sm font-semibold text-blue-800 mb-1">Channel Recommendation</p>
        <p className="text-sm text-blue-700">{card.channel_reasoning}</p>
      </div>

      {/* Predictions */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">
            {(card.predicted_open_rate * 100).toFixed(0)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">Predicted Open Rate</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">
            {(card.predicted_click_rate * 100).toFixed(0)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">Predicted Click Rate</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">
            ₹{card.predicted_revenue?.toLocaleString('en-IN')}
          </p>
          <p className="text-xs text-gray-500 mt-1">Predicted Revenue</p>
        </div>
      </div>

      {/* Confidence factors */}
      {card.confidence_factors?.length > 0 && (
        <div className="mb-6">
          <p className="text-sm font-semibold text-gray-700 mb-3">Confidence Breakdown</p>
          <div className="space-y-3">
            {card.confidence_factors.map((f, i) => (
              <div key={i}>
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                  <span>{f.factor}</span>
                  <span>{f.score}/{f.max_score}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-indigo-500 h-2 rounded-full transition-all duration-700"
                    style={{ width: `${(f.score / f.max_score) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">{f.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sample customers */}
        {sampleProfiles?.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <p className="text-xs font-bold text-gray-500 uppercase mb-3">
            Who are these customers?
            </p>
            <div className="space-y-2">
            {sampleProfiles.map((p, i) => (
                <div key={i} className="flex items-center gap-3">
                <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-sm font-bold text-indigo-600">
                    {p.name[0]}
                </div>
                <div>
                    <p className="text-sm font-medium text-gray-800">{p.name}</p>
                    <p className="text-xs text-gray-400">
                    Last bought {p.last_product} · {p.days_inactive} days ago · {p.tier} tier
                    </p>
                </div>
                </div>
            ))}
            </div>
        </div>
        )}
    
      {/* Message variants */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="border border-orange-200 bg-orange-50 rounded-xl p-4">
          <p className="text-xs font-bold text-orange-700 uppercase mb-2">
            Variant A — {card.message_variant_a?.tone}
          </p>
          <p className="text-sm text-gray-700">{card.message_variant_a?.text}</p>
        </div>
        <div className="border border-purple-200 bg-purple-50 rounded-xl p-4">
          <p className="text-xs font-bold text-purple-700 uppercase mb-2">
            Variant B — {card.message_variant_b?.tone}
          </p>
          <p className="text-sm text-gray-700">{card.message_variant_b?.text}</p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleApprove}
          disabled={approving}
          className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-semibold py-3 px-6 rounded-xl transition-colors"
        >
          {approving ? 'Sending...' : '✓ Approve & Send'}
        </button>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-3 border border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-colors"
        >
          Revise
        </button>
        <button
          onClick={handleApprove}
          disabled={approving}
          className="px-6 py-3 border border-red-300 text-red-600 font-semibold rounded-xl hover:bg-red-50 transition-colors"
        >
          Override
        </button>
      </div>
    </div>
  )
}

export default function CampaignCreator() {
  const [intent, setIntent] = useState('')
  const [channel, setChannel] = useState('WhatsApp')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [pastCampaigns, setPastCampaigns] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    axios.get(`${API}/campaigns`).then(r => {
      setPastCampaigns(r.data.campaigns || [])
    }).catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!intent.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const r = await axios.post(`${API}/campaigns`, { intent, channel })
      setResult(r.data.campaign)
    } catch (e) {
      setError('Failed to generate confidence card. Check your GROQ_API_KEY.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">N</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Nudge</h1>
            <p className="text-xs text-gray-500">AI Campaign Confidence Engine</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Know before you send.
          </h2>
          <p className="text-gray-500 text-lg">
            Describe your campaign goal. Nudge predicts the outcome before you send a single message.
          </p>
        </div>

        {/* Campaign form */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                What do you want to achieve?
              </label>
              <textarea
                value={intent}
                onChange={e => setIntent(e.target.value)}
                placeholder="e.g. Win back customers who bought face wash but haven't returned in 60 days..."
                className="w-full border border-gray-200 rounded-xl p-4 text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
                rows={3}
              />
            </div>
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <label className="block text-sm font-semibold text-gray-700 mb-2">Channel</label>
                <select
                  value={channel}
                  onChange={e => setChannel(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl p-3 text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                >
                  <option>WhatsApp</option>
                  <option>Email</option>
                  <option>SMS</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={loading || !intent.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-semibold py-3 px-8 rounded-xl transition-colors"
              >
                {loading ? 'Analysing...' : 'Generate Confidence Card →'}
              </button>
            </div>
          </form>

          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
              {error}
            </div>
          )}

          {loading && (
            <div className="mt-6 text-center py-8">
              <div className="inline-block w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
              <p className="text-gray-500 mt-3">Nudge is building your confidence card...</p>
            </div>
          )}
        </div>

        {/* Confidence card */}
        {result && (
          <ConfidenceCard
            card={result.confidence_card}
            campaignId={result.id}
            sampleProfiles={result.sample_profiles}
          />
        )}

        {/* Past campaigns */}
        {pastCampaigns.length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Past Campaigns</h3>
            <div className="space-y-3">
              {pastCampaigns.map(c => (
                <div
                  key={c.id}
                  className="bg-white rounded-xl border border-gray-100 p-4 flex items-center justify-between hover:shadow-sm transition-shadow"
                >
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-800">{c.name || c.intent}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {c.channel} · {c.total_sent} sent · {new Date(c.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    <div className={`text-lg font-bold ${
                      c.confidence_score >= 70 ? 'text-green-600' :
                      c.confidence_score >= 40 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {c.confidence_score}
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                      c.status === 'active' ? 'bg-green-100 text-green-700' :
                      c.status === 'completed' ? 'bg-gray-100 text-gray-600' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {c.status}
                    </span>
                    {c.status === 'active' && (
                      <button
                        onClick={() => navigate(`/campaigns/${c.id}/live`)}
                        className="text-xs bg-indigo-50 text-indigo-600 px-3 py-1 rounded-lg hover:bg-indigo-100"
                      >
                        View Live →
                      </button>
                    )}
                    {c.total_sent > 0 && (
                      <button
                        onClick={() => navigate(`/campaigns/${c.id}/postmortem`)}
                        className="text-xs bg-gray-50 text-gray-600 px-3 py-1 rounded-lg hover:bg-gray-100"
                      >
                        Post-Mortem →
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}