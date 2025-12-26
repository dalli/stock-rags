import client from './client'
import { Report, ReportStatus, ReportsResponse, GraphVisualizationResponse } from './types'

export const reportsApi = {
  uploadReport: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await client.post<Report>('/reports/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getReportStatus: async (reportId: string) => {
    const response = await client.get<ReportStatus>(`/reports/${reportId}/status`)
    return response.data
  },

  listReports: async () => {
    const response = await client.get<ReportsResponse>('/reports')
    return response.data
  },

  getReport: async (reportId: string) => {
    const response = await client.get<Report>(`/reports/${reportId}`)
    return response.data
  },

  deleteReport: async (reportId: string) => {
    const response = await client.delete(`/reports/${reportId}`)
    return response.data
  },

  retryReport: async (reportId: string) => {
    const response = await client.post<Report>(`/reports/${reportId}/retry`)
    return response.data
  },

  getReportFile: async (reportId: string) => {
    const response = await client.get(`/reports/${reportId}/file`, {
      responseType: 'blob',
    })
    return response.data
  },

  getReportGraph: async (reportId: string) => {
    const response = await client.get(`/reports/${reportId}/graph`)
    return response.data
  },

  getReportVectors: async (reportId: string, limit: number = 100) => {
    const response = await client.get(`/reports/${reportId}/vectors`, {
      params: { limit },
    })
    return response.data
  },

  getReportGraphVisualization: async (reportId: string, limit: number = 500) => {
    const response = await client.get<GraphVisualizationResponse>(
      `/reports/${reportId}/graph/relationships`,
      {
        params: { limit },
      }
    )
    return response.data
  },
}
