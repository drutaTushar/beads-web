import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { api, handleQueryError } from '../utils/api'
import { useNotification } from '../components/NotificationProvider'

function IssueDetails() {
  const { issueId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showError, showSuccess } = useNotification()
  const [commentText, setCommentText] = useState('')
  const [showDependencyTools, setShowDependencyTools] = useState(false)
  const [newChildId, setNewChildId] = useState('')
  const [showChildDropdown, setShowChildDropdown] = useState(false)
  const [childSearchTerm, setChildSearchTerm] = useState('')
  const [draggedChild, setDraggedChild] = useState(null)
  const [dragOverIndex, setDragOverIndex] = useState(null)

  const { data: issue, isLoading, error } = useQuery({
    queryKey: ['issue', issueId],
    queryFn: () => api.get(`/issues/${issueId}`)
  })

  const { data: events = [], error: eventsError } = useQuery({
    queryKey: ['issue-events', issueId],
    queryFn: () => api.get(`/issues/${issueId}/events`),
    enabled: !!issueId
  })

  const { data: children = [], error: childrenError } = useQuery({
    queryKey: ['issue-children', issueId],
    queryFn: () => api.get(`/issues/${issueId}/children`),
    enabled: !!issueId
  })

  const { data: eligibleChildren = [], error: eligibleChildrenError } = useQuery({
    queryKey: ['eligible-children', issueId],
    queryFn: () => api.get(`/issues/${issueId}/eligible-children`),
    enabled: !!issueId && showChildDropdown
  })

  const { data: dependencyTree, error: treeError } = useQuery({
    queryKey: ['issue-tree', issueId],
    queryFn: () => api.get(`/issues/${issueId}/tree`),
    enabled: !!issueId
  })

  const { data: whyBlocked, error: whyBlockedError } = useQuery({
    queryKey: ['issue-why-blocked', issueId],
    queryFn: () => api.get(`/issues/${issueId}/why-blocked`),
    enabled: !!issueId
  })

  const { data: allIssues = [], error: allIssuesError } = useQuery({
    queryKey: ['all-issues'],
    queryFn: async () => {
      const response = await api.get('/issues/?limit=100')
      return response.issues
    },
    enabled: showDependencyTools
  })

  // Error handling
  useEffect(() => {
    if (error) handleQueryError(error, showError)
  }, [error, showError])

  useEffect(() => {
    if (eventsError) handleQueryError(eventsError, showError)
  }, [eventsError, showError])

  useEffect(() => {
    if (childrenError) handleQueryError(childrenError, showError)
  }, [childrenError, showError])

  useEffect(() => {
    if (eligibleChildrenError) handleQueryError(eligibleChildrenError, showError)
  }, [eligibleChildrenError, showError])

  useEffect(() => {
    if (treeError) handleQueryError(treeError, showError)
  }, [treeError, showError])

  useEffect(() => {
    if (whyBlockedError) handleQueryError(whyBlockedError, showError)
  }, [whyBlockedError, showError])

  useEffect(() => {
    if (allIssuesError) handleQueryError(allIssuesError, showError)
  }, [allIssuesError, showError])

  const updateStatusMutation = useMutation({
    mutationFn: (status) => api.put(`/issues/${issueId}`, { status }),
    onSuccess: () => {
      showSuccess('Issue status updated successfully')
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const addCommentMutation = useMutation({
    mutationFn: (comment) => api.post(`/issues/${issueId}/events`, {
      event_type: 'commented',
      data: { comment }
    }),
    onSuccess: () => {
      showSuccess('Comment added successfully')
      setCommentText('')
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const addChildMutation = useMutation({
    mutationFn: (childId) => api.post(`/issues/${issueId}/children/${childId}`, {}),
    onSuccess: () => {
      showSuccess('Child added successfully')
      setNewChildId('')
      setChildSearchTerm('')
      queryClient.invalidateQueries({ queryKey: ['issue-children', issueId] })
      queryClient.invalidateQueries({ queryKey: ['eligible-children', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-tree', issueId] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const removeChildMutation = useMutation({
    mutationFn: (childId) => api.delete(`/issues/${issueId}/children/${childId}`),
    onSuccess: () => {
      showSuccess('Child removed successfully')
      queryClient.invalidateQueries({ queryKey: ['issue-children', issueId] })
      queryClient.invalidateQueries({ queryKey: ['eligible-children', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-tree', issueId] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const reorderChildrenMutation = useMutation({
    mutationFn: (orderedChildIds) => api.post(`/issues/${issueId}/reorder-children`, { 
      ordered_child_ids: orderedChildIds 
    }),
    onSuccess: () => {
      showSuccess('Children reordered successfully')
      queryClient.invalidateQueries({ queryKey: ['issue-children', issueId] })
    },
    onError: (error) => handleQueryError(error, showError)
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

  // Filter eligible children for display
  const availableIssues = eligibleChildren.filter(issue => {
    // Filter by search term if provided
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

    // Reorder children array locally first for immediate UI feedback
    const newChildren = [...children]
    const [draggedItem] = newChildren.splice(draggedChild.index, 1)
    newChildren.splice(dropIndex, 0, draggedItem)
    
    // Create ordered list of child IDs for the API
    const orderedChildIds = newChildren.map(child => child.issue_id)
    console.log('Reordered children:', orderedChildIds)
    
    setDraggedChild(null)
    
    // Persist the order to the backend
    reorderChildrenMutation.mutate(orderedChildIds)
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

            <div className="dependency-tree-section">
              <h4>Dependency Tree</h4>
              <div className="tree-info">
                {treeError ? (
                  <div className="error-message">
                    Failed to load dependency tree
                  </div>
                ) : dependencyTree ? (
                  renderDependencyTree(dependencyTree, 0)
                ) : (
                  <div className="loading-message">Loading dependency tree...</div>
                )}
              </div>
            </div>
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