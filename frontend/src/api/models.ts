import client from './client'
import { ModelsResponse } from './types'

export const modelsApi = {
  getAvailableModels: async () => {
    const response = await client.get<ModelsResponse>('/models')
    return response.data
  },

  setDefaultModel: async (provider: string, model: string) => {
    const response = await client.put('/models/default', {
      provider,
      model,
    })
    return response.data
  },
}
