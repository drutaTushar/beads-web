import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { api, handleQueryError } from '../utils/api'
import { useNotification } from '../components/NotificationProvider'
import EditableField from '../components/EditableField'

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

  const { data: journalEntries = [], error: journalError } = useQuery({
    queryKey: ['journal-entries', issueId],
    queryFn: () => api.get(`/journal/entries/by-issue/${issueId}`),
    enabled: !!issueId
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

  useEffect(() => {
    if (journalError) handleQueryError(journalError, showError)
  }, [journalError, showError])

  // Dedicated status transition mutations
  const startIssueMutation = useMutation({
    mutationFn: () => api.post(`/issues/${issueId}/start`, {}),
    onSuccess: () => {
      showSuccess('Issue started successfully')
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const blockIssueMutation = useMutation({
    mutationFn: (reason) => api.post(`/issues/${issueId}/block?reason=${encodeURIComponent(reason || '')}`, {}),
    onSuccess: () => {
      showSuccess('Issue blocked successfully')
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const unblockIssueMutation = useMutation({
    mutationFn: () => api.post(`/issues/${issueId}/unblock`, {}),
    onSuccess: () => {
      showSuccess('Issue unblocked successfully')
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const closeIssueMutation = useMutation({
    mutationFn: (reason) => api.delete(`/issues/${issueId}?reason=${encodeURIComponent(reason || '')}`, {}),
    onSuccess: () => {
      showSuccess('Issue closed successfully')
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const reopenIssueMutation = useMutation({
    mutationFn: () => api.post(`/issues/${issueId}/reopen`, {}),
    onSuccess: () => {
      showSuccess('Issue reopened successfully')
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issues'] })
    },
    onError: (error) => handleQueryError(error, showError)
  })

  const deleteIssueMutation = useMutation({
    mutationFn: () => api.delete(`/issues/${issueId}/permanent`),
    onSuccess: () => {
      showSuccess('Issue permanently deleted')
      // Navigate back to issues list since this issue no longer exists
      navigate('/')
    },
    onError: (error) => handleQueryError(error, showError)
  })

  // Legacy status update mutation (keep for backward compatibility)
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

  // Field update mutation for inline editing
  const updateFieldMutation = useMutation({
    mutationFn: (fieldUpdate) => api.put(`/issues/${issueId}`, fieldUpdate),
    onSuccess: (data, variables) => {
      const fieldName = Object.keys(variables)[0]
      showSuccess(`${fieldName.charAt(0).toUpperCase() + fieldName.slice(1)} updated successfully`)
      queryClient.invalidateQueries({ queryKey: ['issue', issueId] })
      queryClient.invalidateQueries({ queryKey: ['issue-events', issueId] })
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

  const handleDeleteIssue = () => {
    const hasChildren = children && children.length > 0
    
    if (hasChildren) {
      alert(`Cannot delete this issue: it has ${children.length} child issues. Please remove all children first.`)
      return
    }
    
    const confirmMessage = `⚠️ PERMANENT DELETE ⚠️\n\nAre you absolutely sure you want to permanently delete this issue?\n\n"${issue.title}"\n\nThis action cannot be undone. The issue and all its data will be permanently removed from the database.`
    
    if (confirm(confirmMessage)) {
      const doubleConfirm = confirm('This is your final confirmation. Delete this issue permanently?')
      if (doubleConfirm) {
        deleteIssueMutation.mutate()
      }
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
          <EditableField
            value={issue.title}
            onSave={(newTitle) => updateFieldMutation.mutateAsync({ title: newTitle })}
            placeholder="Enter issue title..."
            className="issue-title-editable"
            required={true}
            maxLength={500}
          />
          <div className="issue-details-id">#{issue.id}</div>
        </div>
        <div className="issue-details-actions">
          {issue.status === 'open' && (
            <>
              <button
                onClick={() => startIssueMutation.mutate()}
                className="btn btn-primary"
                disabled={startIssueMutation.isPending}
              >
                Start Work
              </button>
              <button
                onClick={() => {
                  const reason = prompt('Reason for blocking (optional):');
                  if (reason !== null) blockIssueMutation.mutate(reason);
                }}
                className="btn btn-warning"
                disabled={blockIssueMutation.isPending}
              >
                Block Issue
              </button>
              <button
                onClick={() => {
                  const reason = prompt('Reason for closing (optional):');
                  if (reason !== null) closeIssueMutation.mutate(reason);
                }}
                className="btn btn-secondary"
                disabled={closeIssueMutation.isPending}
              >
                Close Issue
              </button>
            </>
          )}

          {issue.status === 'in_progress' && (
            <>
              <button
                onClick={() => {
                  const reason = prompt('Reason for blocking (optional):');
                  if (reason !== null) blockIssueMutation.mutate(reason);
                }}
                className="btn btn-warning"
                disabled={blockIssueMutation.isPending}
              >
                Block Issue
              </button>
              <button
                onClick={() => {
                  const reason = prompt('Reason for closing (optional):');
                  if (reason !== null) closeIssueMutation.mutate(reason);
                }}
                className="btn btn-secondary"
                disabled={closeIssueMutation.isPending}
              >
                Close Issue
              </button>
            </>
          )}

          {issue.status === 'blocked' && (
            <>
              <button
                onClick={() => unblockIssueMutation.mutate()}
                className="btn btn-primary"
                disabled={unblockIssueMutation.isPending}
              >
                Unblock Issue
              </button>
              <button
                onClick={() => {
                  const reason = prompt('Reason for closing (optional):');
                  if (reason !== null) closeIssueMutation.mutate(reason);
                }}
                className="btn btn-secondary"
                disabled={closeIssueMutation.isPending}
              >
                Close Issue
              </button>
            </>
          )}

          {issue.status === 'closed' && (
            <button
              onClick={() => reopenIssueMutation.mutate()}
              className="btn btn-primary"
              disabled={reopenIssueMutation.isPending}
            >
              Reopen Issue
            </button>
          )}
        </div>
      </div>

      <div className="issue-details-content">
        <div className="issue-main-content">
          <div className="issue-section">
            <EditableField
              label="Problem Statement (what/why)"
              value={issue.description}
              onSave={(newDescription) => updateFieldMutation.mutateAsync({ description: newDescription })}
              placeholder="Click to add a problem statement..."
              multiline={true}
              className="issue-description-editable"
              maxLength={5000}
            />
          </div>

          <div className="issue-section">
            <EditableField
              label="Solution Design (how)"
              value={issue.design}
              onSave={(newDesign) => updateFieldMutation.mutateAsync({ design: newDesign })}
              placeholder="Click to add solution design..."
              multiline={true}
              className="issue-design-editable"
              maxLength={5000}
            />
          </div>

          <div className="issue-section">
            <EditableField
              label="Acceptance Criteria"
              value={issue.acceptance_criteria}
              onSave={(newCriteria) => updateFieldMutation.mutateAsync({ acceptance_criteria: newCriteria })}
              placeholder="Click to add acceptance criteria..."
              multiline={true}
              className="issue-criteria-editable"
              maxLength={5000}
            />
          </div>

          <div className="issue-section">
            <EditableField
              label="Working Notes"
              value={issue.notes}
              onSave={(newNotes) => updateFieldMutation.mutateAsync({ notes: newNotes })}
              placeholder="Click to add working notes..."
              multiline={true}
              className="issue-notes-editable"
              maxLength={5000}
            />
          </div>
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

          {/* Dangerous Actions */}
          <div className="dangerous-actions">
            <h4>Dangerous Actions</h4>
            <button
              onClick={handleDeleteIssue}
              className="btn btn-danger btn-sm"
              disabled={deleteIssueMutation.isPending}
              title={children && children.length > 0 ? `Cannot delete: has ${children.length} children` : 'Permanently delete this issue'}
            >
              {deleteIssueMutation.isPending ? 'Deleting...' : '🗑️ Delete Permanently'}
            </button>
            <div className="danger-warning">
              ⚠️ Permanent deletion cannot be undone
            </div>
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

            {  whyBlocked && whyBlocked.blocked && (
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
            ) }

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

      {/* Journal Entries Section */}
      <div className="journal-section">
        <h3>📝 Journal Entries</h3>
        <p className="section-description">
          Work progress and insights related to this issue
        </p>
        
        {journalEntries.length === 0 ? (
          <div className="empty-state">
            <p>No journal entries found for this issue.</p>
            <p>Journal entries are created when AI agents complete work related to this issue.</p>
          </div>
        ) : (
          <div className="journal-entries-compact">
            {journalEntries.map((entry) => (
              <div key={entry.id} className="journal-entry-compact">
                <div className="entry-header-compact">
                  <h4 className="entry-title-compact">{entry.title}</h4>
                  <span className="entry-timestamp-compact">
                    {new Date(entry.timestamp).toLocaleDateString()}
                  </span>
                </div>
                
                <div className="entry-summary-compact">
                  {entry.summary.length > 150 
                    ? `${entry.summary.substring(0, 150)}...` 
                    : entry.summary
                  }
                </div>
                
                {entry.files_modified.length > 0 && (
                  <div className="entry-files-compact">
                    <strong>Files:</strong> {entry.files_modified.slice(0, 3).join(', ')}
                    {entry.files_modified.length > 3 && ` +${entry.files_modified.length - 3} more`}
                  </div>
                )}
                
                {entry.issues.length > 1 && (
                  <div className="entry-related-issues">
                    <strong>Also relates to:</strong>{' '}
                    {entry.issues
                      .filter(issue => issue.id !== issueId)
                      .slice(0, 2)
                      .map(issue => (
                        <a 
                          key={issue.id} 
                          href={`/issues/${issue.id}`}
                          className="related-issue-link"
                        >
                          {issue.id}
                        </a>
                      ))
                      .reduce((prev, curr) => [prev, ', ', curr])
                    }
                  </div>
                )}
              </div>
            ))}
            
            <div className="journal-actions">
              <a href={`/journal?issue_id=${issueId}`} className="btn btn-secondary">
                View All Journal Entries for This Issue
              </a>
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
                    `Status changed from ${event.old_value || 'unknown'} to ${event.new_value || 'unknown'}`}
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