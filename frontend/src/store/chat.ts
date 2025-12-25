import { create } from 'zustand'
import { Message, Conversation } from '@/api/types'

interface ChatState {
  conversations: Conversation[]
  currentConversation: Conversation | null
  loading: boolean
  error: string | null
  setConversations: (conversations: Conversation[]) => void
  setCurrentConversation: (conversation: Conversation | null) => void
  addMessage: (message: Message) => void
  newConversation: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  currentConversation: null,
  loading: false,
  error: null,

  setConversations: (conversations) => set({ conversations }),

  setCurrentConversation: (conversation) => set({ currentConversation: conversation }),

  addMessage: (message) =>
    set((state) => {
      if (!state.currentConversation) return state
      return {
        currentConversation: {
          ...state.currentConversation,
          messages: [...state.currentConversation.messages, message],
        },
      }
    }),

  newConversation: () =>
    set({
      currentConversation: {
        id: '',
        created_at: new Date().toISOString(),
        messages: [],
      },
    }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),
}))
