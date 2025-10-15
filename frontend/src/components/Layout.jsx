import { Link, useLocation } from 'react-router-dom'

function Layout({ children }) {
  const location = useLocation()
  
  const isActive = (path) => location.pathname === path
  
  return (
    <div className="layout">
      <header className="header">
        <nav className="nav">
          <h1>AiTrac</h1>
          <ul className="nav-links">
            <li>
              <Link to="/" className={isActive('/') ? 'active' : ''}>
                Issues
              </Link>
            </li>
            <li>
              <Link to="/ready" className={isActive('/ready') ? 'active' : ''}>
                Ready Work
              </Link>
            </li>
            <li>
              <Link to="/create" className="btn btn-primary">
                Create Issue
              </Link>
            </li>
          </ul>
        </nav>
      </header>
      <main className="main">
        {children}
      </main>
    </div>
  )
}

export default Layout