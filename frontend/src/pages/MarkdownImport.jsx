import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useNotification } from '../components/NotificationProvider'

function MarkdownImport() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showError, showSuccess, showWarning } = useNotification()
  
  const [markdownContent, setMarkdownContent] = useState('')
  const [validationResult, setValidationResult] = useState(null)
  const [importMethod, setImportMethod] = useState('textarea') // 'textarea' or 'file'

  // Validation mutation
  const validateMutation = useMutation({
    mutationFn: async (content) => {
      const response = await fetch('/api/import/markdown/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'text/markdown',
        },
        body: content
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Validation failed')
      }
      
      return response.json()
    },
    onSuccess: (data) => {
      setValidationResult(data)
      if (data.valid) {
        showSuccess(`Validation successful! Found ${data.issues_count} issues`)
      } else {
        showError('Validation failed - check errors below')
      }
      
      // Show warnings if any
      if (data.warnings && data.warnings.length > 0) {
        data.warnings.forEach(warning => showWarning(warning))
      }
    },
    onError: (error) => {
      showError(`Validation failed: ${error.message}`)
      setValidationResult(null)
    }
  })

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async (content) => {
      const response = await fetch('/api/import/markdown/', {
        method: 'POST',
        headers: {
          'Content-Type': 'text/markdown',
        },
        body: content
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail?.message || error.detail || 'Import failed')
      }
      
      return response.json()
    },
    onSuccess: (data) => {
      showSuccess(`Import completed! ${data.statistics.issues_created} created, ${data.statistics.issues_updated} updated`)
      
      // Show warnings if any
      if (data.warnings && data.warnings.length > 0) {
        data.warnings.forEach(warning => showWarning(warning))
      }
      
      // Clear form and refresh issues list
      setMarkdownContent('')
      setValidationResult(null)
      queryClient.invalidateQueries({ queryKey: ['issues'] })
      
      // Navigate back to issues list
      navigate('/')
    },
    onError: (error) => {
      showError(`Import failed: ${error.message}`)
    }
  })

  const handleFileUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      if (file.type !== 'text/markdown' && !file.name.endsWith('.md')) {
        showWarning('Please select a Markdown file (.md)')
        return
      }
      
      const reader = new FileReader()
      reader.onload = (e) => {
        setMarkdownContent(e.target.result)
        setValidationResult(null)
      }
      reader.onerror = () => {
        showError('Failed to read file')
      }
      reader.readAsText(file)
    }
  }

  const handleValidate = () => {
    if (!markdownContent.trim()) {
      showError('Please enter markdown content or upload a file')
      return
    }
    
    validateMutation.mutate(markdownContent)
  }

  const handleImport = () => {
    if (!validationResult || !validationResult.valid) {
      showError('Please validate the markdown first')
      return
    }
    
    if (window.confirm(`Import ${validationResult.issues_count} issues? This will overwrite existing issues with the same markdown IDs.`)) {
      importMutation.mutate(markdownContent)
    }
  }

  const handleClear = () => {
    setMarkdownContent('')
    setValidationResult(null)
  }

  const exampleMarkdown = `# Issues Structure
- [platform] Platform Foundation, t=Epic, p=0
    - [auth] Authentication Service, t=Feature, p=0, deps=[platform]
        - [oauth] OAuth Implementation, t=Task, p=0, deps=[auth]
        - [jwt] JWT Token Management, t=Task, p=1, deps=[oauth]
    - [api] REST API Framework, t=Feature, p=1, deps=[platform]
        - [routes] API Routes, t=Task, p=0, deps=[api]
    - [docs] Documentation, t=Chore, p=2, deps=[auth,api]

# Detailed Content
## platform
### description
Foundation epic for our new platform architecture.
This establishes core services and deployment infrastructure.

### acceptance_criteria
- [ ] Core services deployed
- [ ] CI/CD pipeline working
- [ ] Monitoring in place

## auth
### description
Complete authentication and authorization system.

### design
**Architecture:**
- OAuth2 with JWT tokens
- Multi-provider support
- Session management`

  return (
    <div className="markdown-import-page">
      <div className="page-header">
        <div>
          <h1>Markdown Import</h1>
          <p>Import issues from structured Markdown with logical IDs and dependencies</p>
        </div>
        <div className="page-actions">
          <button onClick={() => navigate('/')} className="btn btn-secondary">
            Back to Issues
          </button>
          <a 
            href="/docs/MARKDOWN_IMPORT.md" 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn btn-secondary"
          >
            📖 Documentation
          </a>
        </div>
      </div>

      <div className="import-content">
        <div className="import-input-section">
          <div className="input-method-selector">
            <label className="method-option">
              <input
                type="radio"
                value="textarea"
                checked={importMethod === 'textarea'}
                onChange={(e) => setImportMethod(e.target.value)}
              />
              <span>Type/Paste Markdown</span>
            </label>
            <label className="method-option">
              <input
                type="radio"
                value="file"
                checked={importMethod === 'file'}
                onChange={(e) => setImportMethod(e.target.value)}
              />
              <span>Upload File</span>
            </label>
          </div>

          {importMethod === 'file' && (
            <div className="file-upload-section">
              <input
                type="file"
                accept=".md,.markdown,text/markdown"
                onChange={handleFileUpload}
                className="file-input"
                id="markdown-file"
              />
              <label htmlFor="markdown-file" className="file-upload-label">
                📁 Choose Markdown File (.md)
              </label>
            </div>
          )}

          <div className="markdown-editor">
            <div className="editor-header">
              <span>Markdown Content</span>
              <div className="editor-actions">
                <button
                  onClick={() => setMarkdownContent(exampleMarkdown)}
                  className="btn btn-sm btn-secondary"
                  type="button"
                >
                  Load Example
                </button>
                <button
                  onClick={handleClear}
                  className="btn btn-sm btn-secondary"
                  type="button"
                >
                  Clear
                </button>
              </div>
            </div>
            <textarea
              value={markdownContent}
              onChange={(e) => {
                setMarkdownContent(e.target.value)
                setValidationResult(null)
              }}
              placeholder="Enter your markdown content here or upload a file..."
              className="markdown-textarea"
              rows="20"
              disabled={importMethod === 'file' && !markdownContent}
            />
          </div>

          <div className="import-actions">
            <button
              onClick={handleValidate}
              disabled={!markdownContent.trim() || validateMutation.isPending}
              className="btn btn-primary"
            >
              {validateMutation.isPending ? 'Validating...' : '✓ Validate'}
            </button>
            <button
              onClick={handleImport}
              disabled={!validationResult?.valid || importMutation.isPending}
              className="btn btn-success"
            >
              {importMutation.isPending ? 'Importing...' : '📥 Import Issues'}
            </button>
          </div>
        </div>

        {validationResult && (
          <div className="validation-results">
            <h3>Validation Results</h3>
            
            <div className={`validation-status ${validationResult.valid ? 'success' : 'error'}`}>
              <span className="status-icon">
                {validationResult.valid ? '✅' : '❌'}
              </span>
              <span className="status-text">
                {validationResult.valid 
                  ? `Valid - ${validationResult.issues_count} issues found`
                  : 'Validation failed'
                }
              </span>
            </div>

            {validationResult.errors && validationResult.errors.length > 0 && (
              <div className="errors-section">
                <h4>Errors</h4>
                <ul className="error-list">
                  {validationResult.errors.map((error, index) => (
                    <li key={index} className="error-item">{error}</li>
                  ))}
                </ul>
              </div>
            )}

            {validationResult.warnings && validationResult.warnings.length > 0 && (
              <div className="warnings-section">
                <h4>Warnings</h4>
                <ul className="warning-list">
                  {validationResult.warnings.map((warning, index) => (
                    <li key={index} className="warning-item">{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {validationResult.valid && validationResult.issues_summary && (
              <div className="issues-preview">
                <h4>Issues Preview</h4>
                <div className="issues-tree">
                  {validationResult.issues_summary.map((issue) => (
                    <div key={issue.logical_id} className="issue-preview-item">
                      <div className="issue-preview-header">
                        <span className="logical-id">[{issue.logical_id}]</span>
                        <span className="issue-title">{issue.title}</span>
                        <span className={`badge badge-type ${issue.type}`}>{issue.type}</span>
                        <span className={`badge badge-priority p-${issue.priority}`}>P{issue.priority}</span>
                      </div>
                      {issue.dependencies && issue.dependencies.length > 0 && (
                        <div className="issue-dependencies">
                          <span className="deps-label">Dependencies:</span>
                          {issue.dependencies.map((dep, idx) => (
                            <span key={idx} className="dependency-tag">{dep}</span>
                          ))}
                        </div>
                      )}
                      {issue.parent && (
                        <div className="issue-parent">
                          <span className="parent-label">Parent:</span>
                          <span className="parent-tag">{issue.parent}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default MarkdownImport