import { useParams } from 'react-router-dom'

function IssueDetails() {
  const { issueId } = useParams()
  
  return (
    <div>
      <h1>Issue Details: {issueId}</h1>
      <div className="placeholder">
        <h3>Issue Details Placeholder</h3>
        <p>Issue ID: {issueId}</p>
        <p>This will be replaced with actual issue details in Phase 4</p>
      </div>
    </div>
  )
}

export default IssueDetails