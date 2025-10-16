import { useQuery } from '@tanstack/react-query'
import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, handleQueryError } from '../utils/api'
import { useNotification } from '../components/NotificationProvider'
import HierarchicalIssueList from '../components/HierarchicalIssueList'

function IssueList() {
  const navigate = useNavigate()
  const { showError } = useNotification()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [viewMode, setViewMode] = useState('hierarchical') // 'hierarchical' or 'flat'

  // Fetch hierarchical data by default, but keep flat data as fallback
  const { data: hierarchicalData, isLoading: hierarchicalLoading, error: hierarchicalError } = useQuery({
    queryKey: ['issues', 'hierarchical'],
    queryFn: () => api.get('/issues/hierarchical'),
    enabled: viewMode === 'hierarchical'
  })

  const { data: flatData, isLoading: flatLoading, error: flatError } = useQuery({
    queryKey: ['issues'],
    queryFn: () => api.get('/issues'),
    enabled: viewMode === 'flat'
  })

  const data = viewMode === 'hierarchical' ? hierarchicalData : flatData
  const isLoading = viewMode === 'hierarchical' ? hierarchicalLoading : flatLoading
  const error = viewMode === 'hierarchical' ? hierarchicalError : flatError

  // Handle errors with notifications
  useEffect(() => {
    if (error) {
      handleQueryError(error, showError)
    }
  }, [error, showError])

  // Filter logic for hierarchical vs flat view
  const filteredData = useMemo(() => {
    if (!data) return { hierarchical_issues: [], standalone_issues: [] }
    
    if (viewMode === 'hierarchical') {
      // Filter hierarchical data
      const filterIssue = (issue) => {
        const matchesSearch = searchTerm === '' || 
          issue.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (issue.description && issue.description.toLowerCase().includes(searchTerm.toLowerCase()))
        
        const matchesStatus = statusFilter === '' || issue.status === statusFilter
        
        return matchesSearch && matchesStatus
      }
      
      const filterHierarchicalIssues = (issues) => {
        return issues.filter(filterIssue).map(issue => ({
          ...issue,
          children: issue.children ? filterHierarchicalIssues(issue.children) : []
        }))
      }
      
      return {
        hierarchical_issues: filterHierarchicalIssues(data.hierarchical_issues || []),
        standalone_issues: (data.standalone_issues || []).filter(filterIssue)
      }
    } else {
      // Filter flat data (fallback)
      if (!data.issues) return { hierarchical_issues: [], standalone_issues: [] }
      
      const filteredIssues = data.issues.filter(issue => {
        const matchesSearch = searchTerm === '' || 
          issue.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          issue.description.toLowerCase().includes(searchTerm.toLowerCase())
        
        const matchesStatus = statusFilter === '' || issue.status === statusFilter
        
        return matchesSearch && matchesStatus
      })
      
      return { hierarchical_issues: [], standalone_issues: filteredIssues }
    }
  }, [data, searchTerm, statusFilter, viewMode])

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
        <div className="header-main">
          <h1>Issues</h1>
          <div className="view-toggle">
            <button 
              className={`toggle-btn ${viewMode === 'hierarchical' ? 'active' : ''}`}
              onClick={() => setViewMode('hierarchical')}
            >
              📊 Hierarchy
            </button>
            <button 
              className={`toggle-btn ${viewMode === 'flat' ? 'active' : ''}`}
              onClick={() => setViewMode('flat')}
            >
              📋 List
            </button>
          </div>
        </div>
        
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
            <option value="in_progress">In Progress</option>
            <option value="blocked">Blocked</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>
      
      {viewMode === 'hierarchical' ? (
        <HierarchicalIssueList 
          hierarchicalIssues={filteredData.hierarchical_issues}
          standaloneIssues={filteredData.standalone_issues}
        />
      ) : (
        // Fallback to flat list view
        <div className="flat-issues-list">
          {filteredData.standalone_issues.length === 0 ? (
            <div className="empty-state">
              <h3>No issues found</h3>
              <p>No issues match your current filters.</p>
            </div>
          ) : (
            <div className="issues-list">
              {filteredData.standalone_issues.map((issue) => (
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
      )}
    </div>
  )
}

export default IssueList