import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function HierarchicalIssueList({ hierarchicalIssues, standaloneIssues }) {
  const navigate = useNavigate()
  const [expandedIssues, setExpandedIssues] = useState(new Set())

  const toggleExpanded = (issueId) => {
    const newExpanded = new Set(expandedIssues)
    if (newExpanded.has(issueId)) {
      newExpanded.delete(issueId)
    } else {
      newExpanded.add(issueId)
    }
    setExpandedIssues(newExpanded)
  }

  const getPriorityLabel = (priority) => {
    const labels = { 0: 'Critical', 1: 'High', 2: 'Normal', 3: 'Low' }
    return labels[priority] || 'Normal'
  }

  const getPriorityClass = (priority) => {
    const classes = { 0: 'critical', 1: 'high', 2: 'normal', 3: 'low' }
    return classes[priority] || 'normal'
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString()
  }

  const getStatusSummaryText = (statusSummary) => {
    if (!statusSummary || Object.keys(statusSummary).length === 0) {
      return null
    }

    const total = Object.values(statusSummary).reduce((sum, count) => sum + count, 0)
    const completed = statusSummary.closed || 0
    const inProgress = statusSummary.in_progress || 0
    const blocked = statusSummary.blocked || 0
    const open = statusSummary.open || 0

    return (
      <div className="status-summary">
        <span className="status-summary-item">
          <span className="status-count total">{total}</span>
          <span className="status-label">total</span>
        </span>
        {completed > 0 && (
          <span className="status-summary-item">
            <span className="status-count closed">{completed}</span>
            <span className="status-label">done</span>
          </span>
        )}
        {inProgress > 0 && (
          <span className="status-summary-item">
            <span className="status-count in-progress">{inProgress}</span>
            <span className="status-label">active</span>
          </span>
        )}
        {blocked > 0 && (
          <span className="status-summary-item">
            <span className="status-count blocked">{blocked}</span>
            <span className="status-label">blocked</span>
          </span>
        )}
        {open > 0 && (
          <span className="status-summary-item">
            <span className="status-count open">{open}</span>
            <span className="status-label">open</span>
          </span>
        )}
      </div>
    )
  }

  const renderIssue = (issue, depth = 0) => {
    const isExpanded = expandedIssues.has(issue.id)
    const hasChildren = issue.children && issue.children.length > 0
    const indentStyle = {
      paddingLeft: `${1.5 + (depth * 1.5)}rem`
    }

    return (
      <div key={issue.id} className="hierarchical-issue">
        <div 
          className={`issue-row ${depth > 0 ? 'child-issue' : 'root-issue'}`} 
          style={indentStyle}
        >
          <div className="issue-main">
            <div className="issue-header">
              {hasChildren && (
                <button
                  onClick={() => toggleExpanded(issue.id)}
                  className={`expand-toggle ${isExpanded ? 'expanded' : ''}`}
                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                >
                  {isExpanded ? '▼' : '▶'}
                </button>
              )}
              {!hasChildren && <div className="expand-spacer"></div>}
              
              <div className="issue-info">
                <div className="issue-title-row">
                  <span className="issue-id"></span>
                  <span 
                    className="issue-title"
                    onClick={() => navigate(`/issues/${issue.id}`)}
                  >
                    {issue.title}
                  </span>
                </div>
                
                <div className="issue-meta">
                  <span className={`badge badge-status ${issue.status}`}>
                    {issue.status}
                  </span>
                  <span className="badge badge-type">
                    {issue.issue_type}
                  </span>
                  <span className={`badge badge-priority ${getPriorityClass(issue.priority)}`}>
                    {getPriorityLabel(issue.priority)}
                  </span>
                  {issue.assignee && (
                    <span className="badge badge-assignee">
                      👤 {issue.assignee}
                    </span>
                  )}
                  {issue.estimated_minutes && (
                    <span className="badge badge-estimate">
                      ⏱️ {issue.estimated_minutes}m
                    </span>
                  )}
                  <span className="issue-date">
                    {formatDate(issue.updated_at)}
                  </span>
                </div>
              </div>
            </div>
            
            {hasChildren && getStatusSummaryText(issue.children_status_summary)}
          </div>
        </div>

        {hasChildren && isExpanded && (
          <div className="issue-children">
            {issue.children.map(child => renderIssue(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="hierarchical-issue-list">
      {hierarchicalIssues.length > 0 && (
        <div className="hierarchical-section">
          <div className="section-header">
            <h2>📊 Project Structure</h2>
            <span className="section-count">{hierarchicalIssues.length} epics/features</span>
          </div>
          <div className="issues-container">
            {hierarchicalIssues.map(issue => renderIssue(issue))}
          </div>
        </div>
      )}

      {standaloneIssues.length > 0 && (
        <div className="standalone-section">
          <div className="section-header">
            <h2>📝 Standalone Issues</h2>
            <span className="section-count">{standaloneIssues.length} issues</span>
          </div>
          <div className="issues-container">
            {standaloneIssues.map(issue => renderIssue(issue))}
          </div>
        </div>
      )}

      {hierarchicalIssues.length === 0 && standaloneIssues.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>No Issues Found</h3>
          <p>Create your first issue or import from Markdown to get started</p>
        </div>
      )}
    </div>
  )
}

export default HierarchicalIssueList