import { SearchInterface } from './components/SearchInterface'

function App() {
  return (
    <div className="min-h-screen bg-background">
      {/* Skip link for accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 bg-background border-b border-border z-50">
        <div className="container mx-auto px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div>
              <span className="text-sm font-semibold tracking-wider">CAR HELPER</span>
            </div>

            {/* Meta */}
            <div className="text-right">
              <span className="text-sm font-medium">40,912 cars</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="pt-16" id="main-content" role="main">
        <SearchInterface />
      </main>
    </div>
  )
}

export default App
