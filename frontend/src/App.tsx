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
          <div className="grid grid-cols-[auto_1fr_auto] items-center gap-16 h-16">
            {/* Logo */}
            <div>
              <span className="text-sm font-semibold tracking-wider">CAR HELPER</span>
            </div>

            {/* Navigation */}
            <nav role="navigation" aria-label="Main navigation" className="flex gap-8 justify-center">
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground border-b-2 border-foreground pb-1 transition-colors" aria-current="page">
                Search
              </a>
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground border-b-2 border-transparent pb-1 transition-colors">
                Compare
              </a>
              <a href="#" className="text-sm text-muted-foreground hover:text-foreground border-b-2 border-transparent pb-1 transition-colors">
                About
              </a>
            </nav>

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
