import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import IssueList from './pages/IssueList'
import IssueDetails from './pages/IssueDetails'
import CreateIssue from './pages/CreateIssue'
import ReadyWork from './pages/ReadyWork'
import { NotificationProvider } from './components/NotificationProvider'
import NotificationContainer from './components/NotificationContainer'

function App() {
  return (
    <NotificationProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<IssueList />} />
          <Route path="/issues/:issueId" element={<IssueDetails />} />
          <Route path="/create" element={<CreateIssue />} />
          <Route path="/ready" element={<ReadyWork />} />
        </Routes>
      </Layout>
      <NotificationContainer />
    </NotificationProvider>
  )
}

export default App