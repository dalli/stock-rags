import client from './client'
import { Entity, Timeline } from './types'

export const graphApi = {
  searchEntities: async (query: string, type?: string) => {
    const response = await client.get<Entity[]>('/graph/entities', {
      params: { query, type },
    })
    return response.data
  },

  getCompanyTimeline: async (ticker: string) => {
    const response = await client.get<Timeline>(`/graph/companies/${ticker}/timeline`)
    return response.data
  },
}
