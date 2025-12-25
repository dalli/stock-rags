import { create } from 'zustand'

interface AppState {
  // Models
  llmModels: Record<string, string[]>
  embeddingModels: Record<string, string[]>
  defaultLLMProvider: string
  defaultLLMModel: string
  defaultEmbeddingProvider: string
  defaultEmbeddingModel: string
  setModels: (llm: Record<string, string[]>, embedding: Record<string, string[]>) => void
  setDefaultLLM: (provider: string, model: string) => void
  setDefaultEmbedding: (provider: string, model: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  llmModels: {},
  embeddingModels: {},
  defaultLLMProvider: 'gemini',
  defaultLLMModel: 'gemini-1.5-pro',
  defaultEmbeddingProvider: 'ollama',
  defaultEmbeddingModel: 'nomic-embed-text',

  setModels: (llm, embedding) =>
    set({
      llmModels: llm,
      embeddingModels: embedding,
    }),

  setDefaultLLM: (provider, model) =>
    set({
      defaultLLMProvider: provider,
      defaultLLMModel: model,
    }),

  setDefaultEmbedding: (provider, model) =>
    set({
      defaultEmbeddingProvider: provider,
      defaultEmbeddingModel: model,
    }),
}))
