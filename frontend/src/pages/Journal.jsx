import { useQuery } from '@tanstack/react-query'
import { useState, useMemo, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api, handleQueryError } from '../utils/api'
import { useNotification } from '../components/NotificationProvider'

function Journal() {
  const { showError } = useNotification()
  const [searchTerm, setSearchTerm] = useState('')
  const [issueFilter, setIssueFilter] = useState('')
  const [fileFilter, setFileFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(10)

  // Fetch journal entries
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['journal', 'entries', { search: searchTerm, issue_id: issueFilter, file_path: fileFilter, page: currentPage, limit: pageSize }],
    queryFn: () => {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: pageSize.toString()
      })
      
      if (searchTerm) params.append('search', searchTerm)
      if (issueFilter) params.append('issue_id', issueFilter)
      if (fileFilter) params.append('file_path', fileFilter)
      
      return api.get(`/journal/entries?${params.toString()}`)
    }
  })

  // Handle errors with notifications
  useEffect(() => {
    if (error) {
      handleQueryError(error, showError)
    }
  }, [error, showError])

  const handleSearch = (e) => {
    e.preventDefault()
    setCurrentPage(1) // Reset to first page on new search
    refetch()
  }

  const handleClearFilters = () => {
    setSearchTerm('')
    setIssueFilter('')
    setFileFilter('')
    setCurrentPage(1)
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  const truncateText = (text, maxLength = 200) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  if (isLoading) {
    return (
      <div className="page">
        <div className="page-header">
          <h1>📝 Project Journal</h1>
        </div>
        <div className="loading">Loading journal entries...</div>
      </div>
    )
  }

  const entries = data?.entries || []
  const total = data?.total || 0
  const totalPages = data?.total_pages || 1

  return (
    <div className="page">
      <div className="page-header">
        <h1>📝 Project Journal</h1>
        <p className="page-description">
          Track work progress, decisions, and insights from AI coding agents
        </p>
      </div>

      {/* Search and Filters */}
      <div className="filters-section">
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-row">
            <input
              type="text"
              placeholder="Search in titles, summaries, and issue details..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            <button type="submit" className="btn btn-primary">
              Search
            </button>
          </div>
          
          <div className="filter-row">
            <input
              type="text"
              placeholder="Filter by issue ID (e.g., at-abc123)"
              value={issueFilter}
              onChange={(e) => setIssueFilter(e.target.value)}
              className="filter-input"
            />
            <input
              type="text"
              placeholder="Filter by file path (e.g., src/auth/)"
              value={fileFilter}
              onChange={(e) => setFileFilter(e.target.value)}
              className="filter-input"
            />
            <button type="button" onClick={handleClearFilters} className="btn btn-secondary">
              Clear
            </button>
          </div>
        </form>
      </div>

      {/* Results Summary */}
      <div className="results-summary">
        Showing {entries.length} of {total} journal entries
        {searchTerm && <span> matching "{searchTerm}"</span>}
        {issueFilter && <span> for issue "{issueFilter}"</span>}
        {fileFilter && <span> with file "{fileFilter}"</span>}
      </div>

      {/* Journal Entries List */}
      <div className="journal-entries">
        {entries.length === 0 ? (
          <div className="empty-state">
            <h3>No journal entries found</h3>
            <p>
              {searchTerm || issueFilter || fileFilter
                ? 'Try adjusting your search criteria.'
                : 'No journal entries have been created yet. AI agents will create entries when they complete work.'
              }
            </p>
          </div>
        ) : (
          entries.map((entry) => (
            <div key={entry.id} className="journal-entry">
              <div className="entry-header">
                <h3 className="entry-title">{entry.title}</h3>
                <span className="entry-timestamp">{formatTimestamp(entry.timestamp)}</span>
              </div>
              
              <div className="entry-summary">
                {truncateText(entry.summary)}
              </div>
              
              {entry.issues.length > 0 && (
                <div className="entry-issues">
                  <h4>Related Issues:</h4>
                  <div className="issue-tags">
                    {entry.issues.map((issue) => (
                      <Link
                        key={issue.id}
                        to={`/issues/${issue.id}`}
                        className="issue-tag"
                        title={issue.description}
                      >
                        {issue.id}: {issue.title}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
              
              {entry.files_modified.length > 0 && (
                <div className="entry-files">
                  <h4>Files Modified:</h4>
                  <div className="file-list">
                    {entry.files_modified.slice(0, 5).map((file, index) => (
                      <span key={index} className="file-tag">{file}</span>
                    ))}
                    {entry.files_modified.length > 5 && (
                      <span className="file-count">
                        +{entry.files_modified.length - 5} more files
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="btn btn-secondary"
          >
            Previous
          </button>
          <span className="page-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="btn btn-secondary"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default Journal