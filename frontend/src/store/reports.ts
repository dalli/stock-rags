import { create } from 'zustand'
import { Report } from '@/api/types'

interface ReportsState {
  reports: Report[]
  selectedReport: Report | null
  loading: boolean
  error: string | null
  setReports: (reports: Report[]) => void
  addReport: (report: Report) => void
  removeReport: (reportId: string) => void
  selectReport: (report: Report | null) => void
  updateReportStatus: (reportId: string, status: string) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useReportsStore = create<ReportsState>((set) => ({
  reports: [],
  selectedReport: null,
  loading: false,
  error: null,

  setReports: (reports) => set({ reports }),

  addReport: (report) =>
    set((state) => ({
      reports: [report, ...state.reports],
    })),

  removeReport: (reportId) =>
    set((state) => ({
      reports: state.reports.filter((r) => r.id !== reportId),
    })),

  selectReport: (report) => set({ selectedReport: report }),

  updateReportStatus: (reportId, status) =>
    set((state) => ({
      reports: state.reports.map((r) =>
        r.id === reportId ? { ...r, status: status as any } : r
      ),
    })),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),
}))
