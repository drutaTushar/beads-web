import { useState, useRef, useEffect } from 'react'

const EditableField = ({ 
  value, 
  onSave, 
  placeholder = "Click to edit...",
  multiline = false,
  label,
  className = "",
  disabled = false,
  maxLength,
  required = false
}) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(value || '')
  const [isSaving, setIsSaving] = useState(false)
  const inputRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    setEditValue(value || '')
  }, [value])

  useEffect(() => {
    if (isEditing) {
      const ref = multiline ? textareaRef : inputRef
      if (ref.current) {
        ref.current.focus()
        if (multiline) {
          // For textareas, position cursor at end
          ref.current.setSelectionRange(ref.current.value.length, ref.current.value.length)
        } else {
          // For inputs, select all text
          ref.current.select()
        }
      }
    }
  }, [isEditing, multiline])

  const handleEdit = () => {
    if (disabled) return
    setIsEditing(true)
    setEditValue(value || '')
  }

  const handleSave = async () => {
    if (required && !editValue.trim()) {
      alert(`${label || 'This field'} is required`)
      return
    }

    if (editValue === value) {
      setIsEditing(false)
      return
    }

    setIsSaving(true)
    try {
      await onSave(editValue)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
      // Error handling is done by the parent component via react-query
    } finally {
      setIsSaving(false)
    }
  }

  const handleCancel = () => {
    setEditValue(value || '')
    setIsEditing(false)
  }

  const handleKeyDown = (e) => {
    if (multiline) {
      if (e.key === 'Escape') {
        handleCancel()
      }
      // For multiline, save on Ctrl+Enter
      if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault()
        handleSave()
      }
    } else {
      if (e.key === 'Enter') {
        e.preventDefault()
        handleSave()
      }
      if (e.key === 'Escape') {
        handleCancel()
      }
    }
  }

  const displayValue = value || placeholder
  const isEmpty = !value || value.trim() === ''

  if (isEditing) {
    return (
      <div className={`editable-field editing ${className}`}>
        {label && <label className="editable-field-label">{label}</label>}
        <div className="editable-field-input-container">
          {multiline ? (
            <textarea
              ref={textareaRef}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleSave}
              className="editable-field-textarea"
              placeholder={placeholder}
              maxLength={maxLength}
              disabled={isSaving}
              rows={6}
            />
          ) : (
            <input
              ref={inputRef}
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleSave}
              className="editable-field-input"
              placeholder={placeholder}
              maxLength={maxLength}
              disabled={isSaving}
            />
          )}
          <div className="editable-field-actions">
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || (required && !editValue.trim())}
              className="btn btn-sm btn-primary"
            >
              {isSaving ? 'Saving...' : 'Save'}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              disabled={isSaving}
              className="btn btn-sm btn-secondary"
            >
              Cancel
            </button>
          </div>
          {multiline && (
            <div className="editable-field-hint">
              Press Ctrl+Enter to save, Esc to cancel
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className={`editable-field ${className} ${disabled ? 'disabled' : ''}`}>
      {label && <label className="editable-field-label">{label}</label>}
      <div 
        className={`editable-field-display ${isEmpty ? 'empty' : ''} ${disabled ? 'disabled' : ''}`}
        onClick={handleEdit}
        role="button"
        tabIndex={disabled ? -1 : 0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            handleEdit()
          }
        }}
      >
        {multiline ? (
          <div className="editable-field-multiline">
            {value ? value.split('\n').map((line, index) => (
              <div key={index}>{line || '\u00A0'}</div>
            )) : (
              <div className="placeholder">{placeholder}</div>
            )}
          </div>
        ) : (
          <span className={isEmpty ? 'placeholder' : ''}>
            {displayValue}
          </span>
        )}
        {!disabled && (
          <span className="editable-field-edit-icon">✏️</span>
        )}
      </div>
    </div>
  )
}

export default EditableField