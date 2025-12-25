import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { ErrorBoundary } from './components/ErrorBoundary'
import { HomePage } from './pages/Home'
import { ReportsPage } from './pages/Reports'
import { ReportDetailPage } from './pages/ReportDetail'
import { ChatPage } from './pages/Chat'
import { GraphExplorerPage } from './pages/GraphExplorer'
import { SettingsPage } from './pages/Settings'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
})

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/reports/:reportId" element={<ReportDetailPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/graph" element={<GraphExplorerPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

export default App
