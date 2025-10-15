import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { api, handleQueryError } from '../utils/api'
import { useNotification } from '../components/NotificationProvider'

function CreateIssue() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showError, showSuccess } = useNotification()
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'task',
    priority: 2,
    design: '',
    acceptance_criteria: '',
    assignee: '',
    estimated_minutes: '',
    parent_id: ''
  })

  const [showParentDropdown, setShowParentDropdown] = useState(false)
  const [parentSearchTerm, setParentSearchTerm] = useState('')
  
  const [errors, setErrors] = useState({})

  const createIssueMutation = useMutation({
    mutationFn: (issueData) => api.post('/issues', issueData),
    onSuccess: (data) => {
      showSuccess('Issue created successfully')
      queryClient.invalidateQueries({ queryKey: ['issues'] })
      navigate(`/issues/${data.id}`)
    },
    onError: (error) => {
      handleQueryError(error, showError)
      setErrors({ submit: error.message })
    }
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}
    
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required'
    }
    
    if (!formData.description.trim()) {
      newErrors.description = 'Description is required'
    }
    
    if (formData.estimated_minutes && parseInt(formData.estimated_minutes) < 0) {
      newErrors.estimated_minutes = 'Estimated minutes must be positive'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    const issueData = {
      ...formData,
      issue_type: formData.type,
      priority: parseInt(formData.priority),
      estimated_minutes: formData.estimated_minutes ? parseInt(formData.estimated_minutes) : null
    }
    
    // Remove the frontend 'type' field since we're using 'issue_type' for the API
    delete issueData.type
    
    Object.keys(issueData).forEach(key => {
      if (issueData[key] === '') {
        issueData[key] = null
      }
    })

    createIssueMutation.mutate(issueData)
  }

  return (
    <div>
      <h1>Create New Issue</h1>
      
      <form onSubmit={handleSubmit} className="form">
        <div className="form-group">
          <label htmlFor="title" className="form-label">
            Title *
          </label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            className="form-input"
            disabled={createIssueMutation.isPending}
          />
          {errors.title && <div className="form-error">{errors.title}</div>}
        </div>

        <div className="form-group">
          <label htmlFor="description" className="form-label">
            Description *
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            className="form-textarea"
            rows="4"
            disabled={createIssueMutation.isPending}
          />
          {errors.description && <div className="form-error">{errors.description}</div>}
        </div>

        <div className="form-group">
          <label htmlFor="type" className="form-label">
            Type
          </label>
          <select
            id="type"
            name="type"
            value={formData.type}
            onChange={handleChange}
            className="form-select"
            disabled={createIssueMutation.isPending}
          >
            <option value="task">Task</option>
            <option value="feature">Feature</option>
            <option value="bug">Bug</option>
            <option value="epic">Epic</option>
            <option value="chore">Chore</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="priority" className="form-label">
            Priority
          </label>
          <select
            id="priority"
            name="priority"
            value={formData.priority}
            onChange={handleChange}
            className="form-select"
            disabled={createIssueMutation.isPending}
          >
            <option value="0">Critical</option>
            <option value="1">High</option>
            <option value="2">Normal</option>
            <option value="3">Low</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="design" className="form-label">
            Design
          </label>
          <textarea
            id="design"
            name="design"
            value={formData.design}
            onChange={handleChange}
            className="form-textarea"
            rows="3"
            placeholder="Solution design (how)"
            disabled={createIssueMutation.isPending}
          />
        </div>

        <div className="form-group">
          <label htmlFor="acceptance_criteria" className="form-label">
            Acceptance Criteria
          </label>
          <textarea
            id="acceptance_criteria"
            name="acceptance_criteria"
            value={formData.acceptance_criteria}
            onChange={handleChange}
            className="form-textarea"
            rows="3"
            placeholder="Definition of done"
            disabled={createIssueMutation.isPending}
          />
        </div>

        <div className="form-group">
          <label htmlFor="assignee" className="form-label">
            Assignee
          </label>
          <input
            type="text"
            id="assignee"
            name="assignee"
            value={formData.assignee}
            onChange={handleChange}
            className="form-input"
            placeholder="Username"
            disabled={createIssueMutation.isPending}
          />
        </div>

        <div className="form-group">
          <label htmlFor="estimated_minutes" className="form-label">
            Estimated Minutes
          </label>
          <input
            type="number"
            id="estimated_minutes"
            name="estimated_minutes"
            value={formData.estimated_minutes}
            onChange={handleChange}
            className="form-input"
            min="0"
            disabled={createIssueMutation.isPending}
          />
          {errors.estimated_minutes && <div className="form-error">{errors.estimated_minutes}</div>}
        </div>

        {errors.submit && <div className="form-error">{errors.submit}</div>}

        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={createIssueMutation.isPending}
          >
            {createIssueMutation.isPending ? 'Creating...' : 'Create Issue'}
          </button>
          
          <button
            type="button"
            onClick={() => navigate('/')}
            className="btn btn-secondary"
            disabled={createIssueMutation.isPending}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}

export default CreateIssue