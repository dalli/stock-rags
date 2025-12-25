import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Paper,
  Grid,
  CircularProgress,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Card,
  CardContent,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import IconButton from '@mui/material/IconButton'
import { MainLayout } from '@/components/Layout/MainLayout'
import { ErrorAlert } from '@/components/ErrorAlert'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { reportsApi } from '@/api/reports'
import { GraphInfo, VectorInfo } from '@/api/types'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  )
}

export const ReportDetailPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [graphInfo, setGraphInfo] = useState<GraphInfo | null>(null)
  const [vectorInfo, setVectorInfo] = useState<VectorInfo | null>(null)
  const [tabValue, setTabValue] = useState(0)

  useEffect(() => {
    if (!reportId) {
      setError('Report ID가 없습니다.')
      setLoading(false)
      return
    }

    loadReportData()
  }, [reportId])

  const loadReportData = async () => {
    if (!reportId) return

    try {
      setLoading(true)
      setError(null)

      // Load PDF file
      const pdfBlob = await reportsApi.getReportFile(reportId)
      const url = URL.createObjectURL(pdfBlob)
      setPdfUrl(url)

      // Load graph info
      try {
        const graph = await reportsApi.getReportGraph(reportId)
        setGraphInfo(graph)
      } catch (err) {
        console.error('Failed to load graph info:', err)
      }

      // Load vector info
      try {
        const vectors = await reportsApi.getReportVectors(reportId)
        setVectorInfo(vectors)
      } catch (err) {
        console.error('Failed to load vector info:', err)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '리포트를 불러오는데 실패했습니다.')
      console.error('Failed to load report:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  if (loading) {
    return (
      <MainLayout>
        <LoadingSpinner message="리포트를 불러오는 중..." />
      </MainLayout>
    )
  }

  if (error) {
    return (
      <MainLayout>
        <ErrorAlert message={error} />
      </MainLayout>
    )
  }

  return (
    <MainLayout>
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/reports')} aria-label="뒤로가기">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4">리포트 상세</Typography>
      </Box>

      <Grid container spacing={3}>
        {/* 왼쪽: PDF 뷰어 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ height: '80vh', overflow: 'auto' }}>
            {pdfUrl ? (
              <iframe
                src={pdfUrl}
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                }}
                title="PDF Viewer"
              />
            ) : (
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '100%',
                }}
              >
                <CircularProgress />
              </Box>
            )}
          </Paper>
        </Grid>

        {/* 오른쪽: 그래프 및 벡터 정보 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ height: '80vh', overflow: 'auto' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={handleTabChange}>
                <Tab label="그래프 정보" />
                <Tab label="벡터 정보" />
              </Tabs>
            </Box>

            <TabPanel value={tabValue} index={0}>
              {graphInfo ? (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    그래프 통계
                  </Typography>
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={6}>
                      <Card>
                        <CardContent>
                          <Typography color="textSecondary" gutterBottom>
                            노드 수
                          </Typography>
                          <Typography variant="h4">{graphInfo.nodes_count}</Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={6}>
                      <Card>
                        <CardContent>
                          <Typography color="textSecondary" gutterBottom>
                            관계 수
                          </Typography>
                          <Typography variant="h4">{graphInfo.relationships_count}</Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>

                  {graphInfo.companies.length > 0 && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="h6" gutterBottom>
                        회사 ({graphInfo.companies.length})
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>이름</TableCell>
                              <TableCell>Ticker</TableCell>
                              <TableCell>산업</TableCell>
                              <TableCell>시장</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {graphInfo.companies.map((company, idx) => (
                              <TableRow key={idx}>
                                <TableCell>{company.name || '-'}</TableCell>
                                <TableCell>
                                  <Chip label={company.ticker || '-'} size="small" />
                                </TableCell>
                                <TableCell>{company.industry || '-'}</TableCell>
                                <TableCell>{company.market || '-'}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  )}

                  {graphInfo.industries.length > 0 && (
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="h6" gutterBottom>
                        산업 ({graphInfo.industries.length})
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>이름</TableCell>
                              <TableCell>상위 산업</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {graphInfo.industries.map((industry, idx) => (
                              <TableRow key={idx}>
                                <TableCell>{industry.name || '-'}</TableCell>
                                <TableCell>{industry.parent_industry || '-'}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  )}

                  {graphInfo.themes.length > 0 && (
                    <Box>
                      <Typography variant="h6" gutterBottom>
                        테마 ({graphInfo.themes.length})
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>이름</TableCell>
                              <TableCell>키워드</TableCell>
                              <TableCell>설명</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {graphInfo.themes.map((theme, idx) => (
                              <TableRow key={idx}>
                                <TableCell>{theme.name || '-'}</TableCell>
                                <TableCell>
                                  {theme.keywords && theme.keywords.length > 0
                                    ? theme.keywords.join(', ')
                                    : '-'}
                                </TableCell>
                                <TableCell>
                                  {theme.description
                                    ? theme.description.substring(0, 100) + '...'
                                    : '-'}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  )}

                  {graphInfo.companies.length === 0 &&
                    graphInfo.industries.length === 0 &&
                    graphInfo.themes.length === 0 && (
                      <Typography color="textSecondary">
                        그래프 정보가 없습니다.
                      </Typography>
                    )}
                </Box>
              ) : (
                <Typography color="textSecondary">그래프 정보를 불러올 수 없습니다.</Typography>
              )}
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              {vectorInfo ? (
                <Box>
                  <Typography variant="h6" gutterBottom>
                    벡터 청크 통계
                  </Typography>
                  <Card sx={{ mb: 3 }}>
                    <CardContent>
                      <Typography color="textSecondary" gutterBottom>
                        총 청크 수
                      </Typography>
                      <Typography variant="h4">{vectorInfo.chunks_count}</Typography>
                    </CardContent>
                  </Card>

                  {vectorInfo.chunks.length > 0 ? (
                    <Box>
                      <Typography variant="h6" gutterBottom>
                        청크 목록
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>인덱스</TableCell>
                              <TableCell>페이지</TableCell>
                              <TableCell>텍스트 미리보기</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {vectorInfo.chunks.map((chunk, idx) => (
                              <TableRow key={idx}>
                                <TableCell>{chunk.chunk_index ?? idx}</TableCell>
                                <TableCell>{chunk.page_number ?? '-'}</TableCell>
                                <TableCell>
                                  <Typography variant="body2" sx={{ maxWidth: 400 }}>
                                    {chunk.text_preview || '-'}
                                  </Typography>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Box>
                  ) : (
                    <Typography color="textSecondary">벡터 청크가 없습니다.</Typography>
                  )}
                </Box>
              ) : (
                <Typography color="textSecondary">벡터 정보를 불러올 수 없습니다.</Typography>
              )}
            </TabPanel>
          </Paper>
        </Grid>
      </Grid>
    </MainLayout>
  )
}

