import client from './client'
import { ChatRequest, ChatResponse, Conversation } from './types'

export const chatApi = {
  sendMessage: async (request: ChatRequest) => {
    const response = await client.post<ChatResponse>('/chat', request)
    return response.data
  },

  listConversations: async () => {
    const response = await client.get<Conversation[]>('/chat/conversations')
    return response.data
  },

  getConversation: async (conversationId: string) => {
    const response = await client.get<Conversation>(`/chat/conversations/${conversationId}`)
    return response.data
  },

  deleteConversation: async (conversationId: string) => {
    const response = await client.delete(`/chat/conversations/${conversationId}`)
    return response.data
  },
}
