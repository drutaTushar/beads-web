import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import axios from 'axios'

function IssueDetails() {
  const { issueId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [commentText, setCommentText] = useState('')

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
                    {event.event_type === 'comment' ? 'User' : 'System'}
                  </span>
                  <span className="event-date">{formatDate(event.created_at)}</span>
                </div>
                <div className="event-content">
                  {event.event_type === 'comment' && event.data?.comment}
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