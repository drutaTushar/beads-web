import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import axios from 'axios'

function IssueDetails() {
  const { issueId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [commentText, setCommentText] = useState('')
  const [showDependencyTools, setShowDependencyTools] = useState(false)
  const [newChildId, setNewChildId] = useState('')
  const [showChildDropdown, setShowChildDropdown] = useState(false)
  const [childSearchTerm, setChildSearchTerm] = useState('')
  const [draggedChild, setDraggedChild] = useState(null)
  const [dragOverIndex, setDragOverIndex] = useState(null)

  const { data: issue, isLoading, error } = useQuery({
    queryKey: ['issue', issueId],
    queryFn: async () => {
      const response = await axios.get(`/api/issues/${issueId}`)
      return response.data
    }
  })

  const { data: events = [] } = useQuery({
    queryKey: ['issue-events', issueId],
    queryFn: async () => {
      const response = await axios.get(`/api/issues/${issueId}/events`)
      return response.data
    },
    enabled: !!issueId
  })

  const { data: children = [] } = useQuery({
    queryKey: ['issue-children', issueId],
    queryFn: async () => {
      const response = await axios.get(`/api/issues/${issueId}/children`)
      return response.data
    },
    enabled: !!issueId
  })

  const { data: dependencyTree } = useQuery({
    queryKey: ['issue-tree', issueId],
    queryFn: async () => {
      const response = await axios.get(`/api/issues/${issueId}/tree`)
      return response.data
    },
    enabled: !!issueId
  })

  const { data: whyBlocked } = useQuery({
    queryKey: ['issue-why-blocked', issueId],
    queryFn: async () => {
      const response = await axios.get(`/api/issues/${issueId}/why-blocked`)
      return response.data
    },
    enabled: !!issueId
  })

  const { data: allIssues = [] } = useQuery({
    queryKey: ['all-issues'],
    queryFn: async () => {
      const response = await axios.get('/api/issues/?limit=100')
      return response.data.issues
    },
    enabled: showDependencyTools
  })

  const updateStatusMutation = useMutation({
    mutationFn: async (status) => {
      const response = await axios.patch(`/api/issues/${issueId}`, { status })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issues'] })
    }
  })

  const addCommentMutation = useMutation({
    mutationFn: async (comment) => {
      const response = await axios.post(`/api/issues/${issueId}/events`, {
        event_type: 'comment',
        data: { comment }
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      setCommentText('')
    }
  })

  const addChildMutation = useMutation({
    mutationFn: async (childId) => {
      const response = await axios.post(`/api/issues/${issueId}/children/${childId}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issue-children', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-tree', issueId] })
      setNewChildId('')
    }
  })

  const removeChildMutation = useMutation({
    mutationFn: async (childId) => {
      const response = await axios.delete(`/api/issues/${issueId}/children/${childId}`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['issue-children', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-tree', issueId] })
    }
  })

  const getPriorityLabel = (priority) => {
    const labels = { 0: 'Critical', 1: 'High', 2: 'Normal', 3: 'Low' }
    return labels[priority] || 'Normal'
  }

  const getPriorityClass = (priority) => {
    const classes = { 0: 'critical', 1: 'high', 2: 'normal', 3: 'low' }
    return classes[priority] || 'normal'
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const handleStatusChange = (newStatus) => {
    updateStatusMutation.mutate(newStatus)
  }

  const handleCommentSubmit = (e) => {
    e.preventDefault()
    if (commentText.trim()) {
      addCommentMutation.mutate(commentText.trim())
    }
  }

  const handleAddChild = (e) => {
    e.preventDefault()
    if (newChildId.trim()) {
      addChildMutation.mutate(newChildId.trim())
    }
  }

  const handleRemoveChild = (childId) => {
    if (confirm(`Remove child relationship with issue ${childId}?`)) {
      removeChildMutation.mutate(childId)
    }
  }

  // Filter available issues for child selection
  const availableIssues = allIssues.filter(issue => {
    // Exclude current issue
    if (issue.id === issueId) return false
    // Exclude already existing children
    if (children.some(child => child.issue_id === issue.id)) return false
    // Filter by search term
    if (childSearchTerm && !issue.title.toLowerCase().includes(childSearchTerm.toLowerCase()) && !issue.id.toLowerCase().includes(childSearchTerm.toLowerCase())) return false
    return true
  })

  const handleChildSelection = (selectedIssue) => {
    setNewChildId(selectedIssue.id)
    setChildSearchTerm(selectedIssue.title)
    setShowChildDropdown(false)
  }

  const handleChildSearchChange = (e) => {
    const value = e.target.value
    setChildSearchTerm(value)
    setNewChildId(value) // Allow manual ID entry as fallback
    setShowChildDropdown(value.length > 0)
  }

  // Drag and drop handlers
  const handleDragStart = (e, child, index) => {
    setDraggedChild({ child, index })
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e, index) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverIndex(index)
  }

  const handleDragLeave = () => {
    setDragOverIndex(null)
  }

  const handleDrop = async (e, dropIndex) => {
    e.preventDefault()
    setDragOverIndex(null)
    
    if (!draggedChild || draggedChild.index === dropIndex) {
      setDraggedChild(null)
      return
    }

    // Reorder children array
    const newChildren = [...children]
    const [draggedItem] = newChildren.splice(draggedChild.index, 1)
    newChildren.splice(dropIndex, 0, draggedItem)
    
    // For now, just update local state (backend ordering support would be needed for persistence)
    // This would require backend API changes to store and update child ordering
    console.log('Reordered children:', newChildren.map(c => c.issue_id))
    
    setDraggedChild(null)
    
    // TODO: Call backend API to persist the new ordering
    // Example: await axios.patch(`/api/issues/${issueId}/children/reorder`, { 
    //   children: newChildren.map(c => c.issue_id) 
    // })
  }

  // Render dependency tree recursively
  const renderDependencyTree = (node, depth) => {
    if (!node) return null

    const indentStyle = {
      marginLeft: `${depth * 20}px`
    }

    return (
      <div key={node.id || node.issue_id} className="tree-node" style={indentStyle}>
        <div className="tree-node-content">
          <div className="tree-node-connector">
            {depth > 0 && (
              <>
                <span className="tree-line">│</span>
                <span className="tree-branch">├─</span>
              </>
            )}
          </div>
          <div className="tree-node-info">
            <div className="tree-node-header">
              <span className="tree-node-id">#{node.id || node.issue_id}</span>
              <span className="tree-node-title">{node.title}</span>
            </div>
            <div className="tree-node-meta">
              {node.status && (
                <span className={`badge badge-status ${node.status}`}>
                  {node.status}
                </span>
              )}
              {node.issue_type && (
                <span className="badge badge-type">
                  {node.issue_type}
                </span>
              )}
              {node.priority !== undefined && (
                <span className={`badge badge-priority ${getPriorityClass(node.priority)}`}>
                  {getPriorityLabel(node.priority)}
                </span>
              )}
            </div>
          </div>
          <div className="tree-node-actions">
            <button
              onClick={() => navigate(`/issues/${node.id || node.issue_id}`)}
              className="btn btn-secondary btn-sm"
            >
              View
            </button>
          </div>
        </div>
        
        {/* Render children/dependencies */}
        {node.children && node.children.length > 0 && (
          <div className="tree-children">
            {node.children.map(child => renderDependencyTree(child, depth + 1))}
          </div>
        )}
        {node.dependencies && node.dependencies.length > 0 && (
          <div className="tree-dependencies">
            {node.dependencies.map(dep => renderDependencyTree(dep, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  if (isLoading) {
    return <div className="loading">Loading issue details...</div>
  }

  if (error) {
    return (
      <div className="card">
        <h2>Error loading issue</h2>
        <p>{error.message}</p>
        <button onClick={() => navigate('/')} className="btn btn-primary">
          Back to Issues
        </button>
      </div>
    )
  }

  if (!issue) {
    return (
      <div className="card">
        <h2>Issue not found</h2>
        <p>The issue you're looking for doesn't exist.</p>
        <button onClick={() => navigate('/')} className="btn btn-primary">
          Back to Issues
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="issue-details-header">
        <div>
          <h1 className="issue-details-title">{issue.title}</h1>
          <div className="issue-details-id">#{issue.id}</div>
        </div>
        <div className="issue-details-actions">
          {issue.status === 'open' ? (
            <button
              onClick={() => handleStatusChange('closed')}
              className="btn btn-secondary"
              disabled={updateStatusMutation.isPending}
            >
              Close Issue
            </button>
          ) : (
            <button
              onClick={() => handleStatusChange('open')}
              className="btn btn-primary"
              disabled={updateStatusMutation.isPending}
            >
              Reopen Issue
            </button>
          )}
        </div>
      </div>

      <div className="issue-details-content">
        <div className="issue-main-content">
          <div className="issue-section">
            <h3>Description</h3>
            <p>{issue.description || 'No description provided.'}</p>
          </div>

          {issue.design && (
            <div className="issue-section">
              <h3>Design</h3>
              <p>{issue.design}</p>
            </div>
          )}

          {issue.acceptance_criteria && (
            <div className="issue-section">
              <h3>Acceptance Criteria</h3>
              <p>{issue.acceptance_criteria}</p>
            </div>
          )}
        </div>

        <div className="issue-sidebar">
          <div className="issue-meta-item">
            <span className="issue-meta-label">Status</span>
            <span className={`badge badge-status ${issue.status}`}>
              {issue.status}
            </span>
          </div>

          <div className="issue-meta-item">
            <span className="issue-meta-label">Type</span>
            <span className="badge badge-type">{issue.issue_type}</span>
          </div>

          <div className="issue-meta-item">
            <span className="issue-meta-label">Priority</span>
            <span className={`badge badge-priority ${getPriorityClass(issue.priority)}`}>
              {getPriorityLabel(issue.priority)}
            </span>
          </div>

          {issue.assignee && (
            <div className="issue-meta-item">
              <span className="issue-meta-label">Assignee</span>
              <span className="issue-meta-value">{issue.assignee}</span>
            </div>
          )}

          {issue.estimated_minutes && (
            <div className="issue-meta-item">
              <span className="issue-meta-label">Estimate</span>
              <span className="issue-meta-value">{issue.estimated_minutes}m</span>
            </div>
          )}

          <div className="issue-meta-item">
            <span className="issue-meta-label">Created</span>
            <span className="issue-meta-value">{formatDate(issue.created_at)}</span>
          </div>

          <div className="issue-meta-item">
            <span className="issue-meta-label">Updated</span>
            <span className="issue-meta-value">{formatDate(issue.updated_at)}</span>
          </div>
        </div>
      </div>

      <div className="dependency-section">
        <h3>Dependencies & Children</h3>
        
        <div className="dependency-tools">
          <button
            onClick={() => setShowDependencyTools(!showDependencyTools)}
            className="btn btn-secondary"
          >
            {showDependencyTools ? 'Hide' : 'Show'} Dependency Tools
          </button>
        </div>

        {showDependencyTools && (
          <div className="dependency-management">
            <div className="child-management">
              <h4>Child Issues</h4>
              <form onSubmit={handleAddChild} className="add-child-form">
                <div className="child-search-container">
                  <input
                    type="text"
                    value={childSearchTerm}
                    onChange={handleChildSearchChange}
                    placeholder="Search issues or enter issue ID..."
                    className="form-input"
                    disabled={addChildMutation.isPending}
                    onFocus={() => setShowChildDropdown(childSearchTerm.length > 0)}
                    onBlur={() => setTimeout(() => setShowChildDropdown(false), 200)}
                  />
                  {showChildDropdown && availableIssues.length > 0 && (
                    <div className="child-dropdown">
                      {availableIssues.slice(0, 10).map((issue) => (
                        <div
                          key={issue.id}
                          className="child-dropdown-item"
                          onClick={() => handleChildSelection(issue)}
                        >
                          <div className="child-dropdown-header">
                            <span className="child-dropdown-id">#{issue.id}</span>
                            <span className="child-dropdown-title">{issue.title}</span>
                          </div>
                          <div className="child-dropdown-meta">
                            <span className={`badge badge-status ${issue.status}`}>
                              {issue.status}
                            </span>
                            <span className="badge badge-type">
                              {issue.issue_type}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={!newChildId.trim() || addChildMutation.isPending}
                >
                  {addChildMutation.isPending ? 'Adding...' : 'Add Child'}
                </button>
              </form>
              
              {children.length > 0 && (
                <div className="children-list">
                  <h5>Children ({children.length})</h5>
                  <div className="drag-hint">
                    💡 Drag and drop to reorder children
                  </div>
                  {children.map((child, index) => (
                    <div
                      key={child.issue_id}
                      className={`child-item ${dragOverIndex === index ? 'drag-over' : ''} ${draggedChild?.index === index ? 'dragging' : ''}`}
                      draggable
                      onDragStart={(e) => handleDragStart(e, child, index)}
                      onDragOver={(e) => handleDragOver(e, index)}
                      onDragLeave={handleDragLeave}
                      onDrop={(e) => handleDrop(e, index)}
                    >
                      <div className="drag-handle">
                        ⋮⋮
                      </div>
                      <div className="child-info">
                        <div className="child-title-row">
                          <span className="child-id">#{child.issue_id}</span>
                          <span className="child-title">{child.title}</span>
                        </div>
                        <div className="child-meta">
                          <span className={`badge badge-status ${child.status}`}>
                            {child.status}
                          </span>
                          <span className="badge badge-type">
                            {child.issue_type}
                          </span>
                          <span className={`badge badge-priority ${getPriorityLabel(child.priority).toLowerCase()}`}>
                            {getPriorityLabel(child.priority)}
                          </span>
                        </div>
                      </div>
                      <div className="child-actions">
                        <button
                          onClick={() => navigate(`/issues/${child.issue_id}`)}
                          className="btn btn-secondary btn-sm"
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleRemoveChild(child.issue_id)}
                          className="btn btn-danger btn-sm"
                          disabled={removeChildMutation.isPending}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {whyBlocked && whyBlocked.blocked && (
              <div className="why-blocked-section">
                <h4>Why Blocked?</h4>
                <div className="blocked-info">
                  <p>{whyBlocked.message}</p>
                  {whyBlocked.blocking_path && whyBlocked.blocking_path.length > 0 && (
                    <div className="blocking-chain">
                      <h5>Blocking Chain:</h5>
                      <ol>
                        {whyBlocked.blocking_path.map((blockingIssue, index) => (
                          <li key={index}>
                            <button
                              onClick={() => navigate(`/issues/${blockingIssue.id}`)}
                              className="link-button"
                            >
                              #{blockingIssue.id}: {blockingIssue.title}
                            </button>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              </div>
            )}

            {dependencyTree && (
              <div className="dependency-tree-section">
                <h4>Dependency Tree</h4>
                <div className="tree-info">
                  {renderDependencyTree(dependencyTree, 0)}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="comments-section">
        <h3>Activity</h3>
        
        <form onSubmit={handleCommentSubmit} className="comment-form">
          <div className="form-group">
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Add a comment..."
              className="form-textarea"
              rows="3"
              disabled={addCommentMutation.isPending}
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!commentText.trim() || addCommentMutation.isPending}
          >
            {addCommentMutation.isPending ? 'Adding...' : 'Add Comment'}
          </button>
        </form>

        <div className="events-list">
          {events.length === 0 ? (
            <p>No activity yet.</p>
          ) : (
            events.map((event) => (
              <div key={event.id} className="event-item">
                <div className="event-header">
                  <span className="event-author">
                    {event.event_type === 'commented' ? 'User' : 'System'}
                  </span>
                  <span className="event-date">{formatDate(event.created_at)}</span>
                </div>
                <div className="event-content">
                  {event.event_type === 'commented' && event.comment}
                  {event.event_type === 'status_changed' && 
                    `Status changed to ${event.data?.new_status}`}
                  {event.event_type === 'created' && 'Issue created'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default IssueDetails