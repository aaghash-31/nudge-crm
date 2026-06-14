import { Routes, Route } from 'react-router-dom'
import CampaignCreator from './pages/CampaignCreator'
import LiveFeed from './pages/LiveFeed'
import PostMortem from './pages/PostMortem'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<CampaignCreator />} />
      <Route path="/campaigns/:id/live" element={<LiveFeed />} />
      <Route path="/campaigns/:id/postmortem" element={<PostMortem />} />
    </Routes>
  )
}