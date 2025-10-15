import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

function IssueList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['issues'],
    queryFn: async () => {
      const response = await axios.get('/api/issues')
      return response.data
    }
  })

  if (isLoading) {
    return <div className="loading">Loading issues...</div>
  }

  if (error) {
    return <div className="card">Error loading issues: {error.message}</div>
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Issues</h1>
      </div>
      
      <div className="placeholder">
        <h3>Issue List Placeholder</h3>
        <p>API Response: {JSON.stringify(data, null, 2)}</p>
        <p>This will be replaced with actual issue list in Phase 4</p>
      </div>
    </div>
  )
}

export default IssueList