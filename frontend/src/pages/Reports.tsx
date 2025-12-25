import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Button,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Link,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import DeleteIcon from '@mui/icons-material/Delete'
import RefreshIcon from '@mui/icons-material/Refresh'
import IconButton from '@mui/material/IconButton'
import Tooltip from '@mui/material/Tooltip'
import { MainLayout } from '@/components/Layout/MainLayout'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useReportsStore } from '@/store/reports'
import { reportsApi } from '@/api/reports'

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate()

  React.useEffect(() => {
    console.log('[ReportsPage] Component mounted')
  }, [])

  const {
    reports,
    setReports,
    addReport,
    removeReport,
    loading,
    error,
    setLoading,
    setError,
    updateReportStatus,
  } = useReportsStore()

  // Debug: Log reports changes
  React.useEffect(() => {
    console.log('[ReportsPage] Reports state changed:', reports)
    console.log('[ReportsPage] Reports length:', reports?.length)
  }, [reports])

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [reportToDelete, setReportToDelete] = useState<string | null>(null)

  // Load reports on mount
  useEffect(() => {
    console.log('useEffect triggered - loading reports')
    loadReports().catch((err) => {
      console.error('Error loading reports:', err)
      setError('Failed to load reports. Please check your connection.')
    })
  }, [])

  // Poll for status updates
  useEffect(() => {
    if (!reports || reports.length === 0) return
    
    const interval = setInterval(() => {
      reports.forEach((report) => {
        if (report.status === 'pending' || report.status === 'processing') {
          checkReportStatus(report.id)
        }
      })
    }, 2000)
    return () => clearInterval(interval)
  }, [reports])

  const loadReports = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('[ReportsPage] Loading reports...')
      const data = await reportsApi.listReports()
      console.log('[ReportsPage] API Response:', JSON.stringify(data, null, 2))
      
      // Ensure reports is always an array
      const reportsList = data?.reports || (Array.isArray(data) ? data : [])
      console.log('[ReportsPage] Reports list:', reportsList)
      console.log('[ReportsPage] Reports list length:', reportsList?.length)

      if (reportsList && Array.isArray(reportsList) && reportsList.length > 0) {
        console.log('[ReportsPage] Setting reports:', reportsList)
        setReports(reportsList)
        // Force a re-render check
        setTimeout(() => {
          console.log('[ReportsPage] After setReports, store reports:', useReportsStore.getState().reports)
        }, 100)
      } else {
        console.log('[ReportsPage] No reports found, setting empty array')
        setReports([])
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to load reports'
      setError(errorMessage)
      console.error('[ReportsPage] Failed to load reports:', err)
      console.error('[ReportsPage] Error response:', err?.response)
      // Set empty array on error to show empty state
      setReports([])
    } finally {
      setLoading(false)
    }
  }

  const checkReportStatus = async (reportId: string) => {
    try {
      const status = await reportsApi.getReportStatus(reportId)
      updateReportStatus(reportId, status.status)
    } catch (err) {
      console.error('Failed to check status:', err)
    }
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files?.[0]) {
      setSelectedFile(event.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    try {
      setUploading(true)
      const report = await reportsApi.uploadReport(selectedFile)
      console.log('Upload successful, report:', report)
      addReport(report)
      // Reload reports to ensure we have the latest data
      await loadReports()
      setUploadDialogOpen(false)
      setSelectedFile(null)
    } catch (err) {
      setError('Failed to upload report')
      console.error(err)
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteClick = (reportId: string) => {
    setReportToDelete(reportId)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!reportToDelete) return

    try {
      await reportsApi.deleteReport(reportToDelete)
      removeReport(reportToDelete)
      setDeleteDialogOpen(false)
      setReportToDelete(null)
    } catch (err) {
      setError('Failed to delete report')
      console.error(err)
      setDeleteDialogOpen(false)
      setReportToDelete(null)
    }
  }

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false)
    setReportToDelete(null)
  }

  const handleRetry = async (reportId: string) => {
    try {
      const report = await reportsApi.retryReport(reportId)
      console.log('Retry successful, report:', report)
      // Update the report in the store
      updateReportStatus(reportId, report.status)
      // Reload reports to ensure we have the latest data
      await loadReports()
    } catch (err) {
      setError('Failed to retry report processing')
      console.error(err)
    }
  }

  const getStatusColor = (status: string): any => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'parsing_pdf':
      case 'extracting_entities':
      case 'extracting_relationships':
      case 'building_graph':
      case 'storing_embeddings':
        return 'info'
      case 'failed':
        return 'error'
      case 'pending':
        return 'warning'
      default:
        return 'default'
    }
  }

  const getStatusLabel = (status: string): string => {
    const statusMap: Record<string, string> = {
      'pending': '대기 중',
      'parsing_pdf': 'PDF 파싱 중',
      'extracting_entities': '엔티티 추출 중',
      'extracting_relationships': '관계 추출 중',
      'building_graph': '그래프 구축 중',
      'storing_embeddings': '임베딩 저장 중',
      'completed': '완료',
      'failed': '실패',
    }
    return statusMap[status] || status
  }

  return (
    <MainLayout>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          📄 Reports
        </Typography>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Manage and analyze security reports
        </Typography>
      </Box>

      {error && <ErrorAlert message={error} />}

      <Box sx={{ mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<CloudUploadIcon />}
          onClick={() => setUploadDialogOpen(true)}
        >
          Upload Report
        </Button>
      </Box>

      {loading && !(reports || []).length ? (
        <LoadingSpinner message="Loading reports..." />
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                <TableCell>Filename</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Entities</TableCell>
                <TableCell align="right">Chunks</TableCell>
                <TableCell>Uploaded</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reports && reports.length > 0 ? (
                reports.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell>
                      <Link
                        component="button"
                        variant="body2"
                        onClick={() => navigate(`/reports/${report.id}`)}
                        sx={{ cursor: 'pointer', textDecoration: 'none' }}
                      >
                        {report.filename}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getStatusLabel(report.status)}
                        color={getStatusColor(report.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">{report.entity_count}</Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">{report.vector_chunks ?? '-'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {new Date(report.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                        {report.status === 'failed' && (
                          <Tooltip title="재실행">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => handleRetry(report.id)}
                              sx={{ padding: '8px' }}
                            >
                              <RefreshIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title="삭제">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteClick(report.id)}
                            sx={{ padding: '8px' }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ p: 3 }}>
                    <Typography color="textSecondary">No reports yet</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)}>
        <DialogTitle>Upload Report</DialogTitle>
        <DialogContent sx={{ minWidth: 400 }}>
          <Box sx={{ pt: 2 }}>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              style={{ display: 'block', marginBottom: 16 }}
            />
            {selectedFile && (
              <Typography variant="body2" color="success.main">
                Selected: {selectedFile.name}
              </Typography>
            )}
            {uploading && <LinearProgress sx={{ mt: 2 }} />}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpload}
            variant="contained"
            disabled={!selectedFile || uploading}
          >
            Upload
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteDialogOpen} onClose={handleDeleteCancel}>
        <DialogTitle>리포트 삭제 확인</DialogTitle>
        <DialogContent>
          <Typography>
            이 리포트를 삭제하시겠습니까? 이 작업은 되돌릴 수 없으며, 다음 데이터가 모두 삭제됩니다:
          </Typography>
          <Box component="ul" sx={{ mt: 2, pl: 3 }}>
            <li>PDF 파일</li>
            <li>데이터베이스 데이터</li>
            <li>벡터 임베딩 청크</li>
            <li>그래프 데이터</li>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>취소</Button>
          <Button onClick={handleDeleteConfirm} variant="contained" color="error">
            삭제
          </Button>
        </DialogActions>
      </Dialog>
    </MainLayout>
  )
}
