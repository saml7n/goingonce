import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { NamePrompt } from '@/components/NamePrompt'
import { useIdentity } from '@/hooks/useIdentity'
import HomePage from '@/pages/HomePage'
import CreateAuctionPage from '@/pages/CreateAuctionPage'
import AuctionPage from '@/pages/AuctionPage'

function App() {
  const { needsName, setUserName } = useIdentity()

  return (
    <BrowserRouter>
      <NamePrompt open={needsName} onSubmit={setUserName} />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/create" element={<CreateAuctionPage />} />
        <Route path="/auctions/:id" element={<AuctionPage />} />
      </Routes>
      <Toaster richColors position="top-right" />
    </BrowserRouter>
  )
}

export default App
