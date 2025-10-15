import { useQuery } from '@tanstack/react-query'
import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, handleQueryError } from '../utils/api'
import { useNotification } from '../components/NotificationProvider'

function IssueList() {
  const navigate = useNavigate()
  const { showError } = useNotification()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['issues'],
    queryFn: () => api.get('/issues')
  })

  // Handle errors with notifications
  useEffect(() => {
    if (error) {
      handleQueryError(error, showError)
    }
  }, [error, showError])

  const filteredIssues = useMemo(() => {
    if (!data || !data.issues) return []
    
    return data.issues.filter(issue => {
      const matchesSearch = searchTerm === '' || 
        issue.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        issue.description.toLowerCase().includes(searchTerm.toLowerCase())
      
      const matchesStatus = statusFilter === '' || issue.status === statusFilter
      const matchesType = typeFilter === '' || issue.issue_type === typeFilter
      
      return matchesSearch && matchesStatus && matchesType
    })
  }, [data, searchTerm, statusFilter, typeFilter])

  const getPriorityLabel = (priority) => {
    const labels = { 0: 'critical', 1: 'high', 2: 'normal', 3: 'low' }
    return labels[priority] || 'normal'
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString()
  }

  if (isLoading) {
    return <div className="loading">Loading issues...</div>
  }

  if (error) {
    return <div className="card">Error loading issues: {error.message}</div>
  }

  return (
    <div>
      <div className="issues-header">
        <h1>Issues</h1>
        <div className="issues-filters">
          <input
            type="search"
            placeholder="Search issues..."
            className="search-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <select
            className="filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>
          <select
            className="filter-select"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="">All Types</option>
            <option value="task">Task</option>
            <option value="feature">Feature</option>
            <option value="bug">Bug</option>
            <option value="epic">Epic</option>
            <option value="chore">Chore</option>
          </select>
        </div>
      </div>
      
      {filteredIssues.length === 0 ? (
        <div className="empty-state">
          <h3>No issues found</h3>
          <p>
            {data?.length === 0 
              ? "No issues have been created yet." 
              : "No issues match your current filters."
            }
          </p>
        </div>
      ) : (
        <div className="issues-list">
          {filteredIssues.map((issue) => (
            <div
              key={issue.id}
              className="issue-card"
              onClick={() => navigate(`/issues/${issue.id}`)}
            >
              <div className="issue-header">
                <div>
                  <div className="issue-title-row">
                    <span className="issue-id">#{issue.id}</span>
                    <span className="issue-title">{issue.title}</span>
                  </div>
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
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default IssueList