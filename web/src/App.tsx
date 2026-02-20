import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { Gavel } from 'lucide-react'

function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto flex items-center gap-2 px-4 py-4">
          <Gavel className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">GoingOnce</h1>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        <p className="text-muted-foreground">Real-time auctions — coming soon.</p>
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
      <Toaster />
    </BrowserRouter>
  )
}

export default App
