import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

function ReadyWork() {
  const navigate = useNavigate()

  const { data: readyIssues = [], isLoading, error } = useQuery({
    queryKey: ['ready-work'],
    queryFn: async () => {
      const response = await axios.get('/api/work/ready')
      return response.data
    }
  })

  const getPriorityLabel = (priority) => {
    const labels = { 0: 'critical', 1: 'high', 2: 'normal', 3: 'low' }
    return labels[priority] || 'normal'
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString()
  }

  if (isLoading) {
    return <div className="loading">Loading ready work...</div>
  }

  if (error) {
    return <div className="card">Error loading ready work: {error.message}</div>
  }

  return (
    <div>
      <div className="ready-work-header">
        <h1>Ready Work</h1>
        <p className="ready-work-description">
          Issues that can be started immediately - all dependencies are satisfied
        </p>
      </div>
      
      {readyIssues.length === 0 ? (
        <div className="empty-state">
          <h3>No ready work found</h3>
          <p>
            All issues either have unmet dependencies or are already closed.
            Check the issue list to see what needs to be unblocked.
          </p>
          <button 
            onClick={() => navigate('/')} 
            className="btn btn-primary"
          >
            View All Issues
          </button>
        </div>
      ) : (
        <div className="ready-work-list">
          <div className="ready-work-summary">
            <strong>{readyIssues.length}</strong> issues ready to start
          </div>
          
          {readyIssues.map((issue) => (
            <div
              key={issue.id}
              className="issue-card ready-issue-card"
              onClick={() => navigate(`/issues/${issue.id}`)}
            >
              <div className="issue-header">
                <div>
                  <div className="issue-title">{issue.title}</div>
                  <div className="issue-id">#{issue.id}</div>
                </div>
                <div className="issue-badges">
                  <span className={`badge badge-status ${issue.status}`}>
                    {issue.status}
                  </span>
                  <span className="badge badge-type">
                    {issue.issue_type}
                  </span>
                  <span className={`badge badge-priority ${getPriorityLabel(issue.priority)}`}>
                    {getPriorityLabel(issue.priority)}
                  </span>
                </div>
              </div>
              
              {issue.description && (
                <div className="issue-description">
                  {issue.description.length > 150 
                    ? `${issue.description.substring(0, 150)}...` 
                    : issue.description
                  }
                </div>
              )}
              
              <div className="issue-meta">
                <span>Created: {formatDate(issue.created_at)}</span>
                {issue.assignee && <span>Assignee: {issue.assignee}</span>}
                {issue.estimated_minutes && (
                  <span>Estimate: {issue.estimated_minutes}m</span>
                )}
              </div>
              
              <div className="ready-indicator">
                <span className="ready-badge">✓ Ready to Start</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ReadyWork