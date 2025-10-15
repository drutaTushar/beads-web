import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

function ReadyWork() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ready-work'],
    queryFn: async () => {
      const response = await axios.get('/api/ready')
      return response.data
    }
  })

  if (isLoading) {
    return <div className="loading">Loading ready work...</div>
  }

  if (error) {
    return <div className="card">Error loading ready work: {error.message}</div>
  }

  return (
    <div>
      <h1>Ready Work</h1>
      <div className="placeholder">
        <h3>Ready Work Dashboard Placeholder</h3>
        <p>API Response: {JSON.stringify(data, null, 2)}</p>
        <p>This will be replaced with actual Ready() algorithm results in Phase 5</p>
      </div>
    </div>
  )
}

export default ReadyWork