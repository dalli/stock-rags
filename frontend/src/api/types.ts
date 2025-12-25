// Models
export interface LLMModel {
  name: string
  provider: string
}

export interface EmbeddingModel {
  name: string
  provider: string
}

export interface ModelsResponse {
  llm_models: Record<string, string[]>
  embedding_models: Record<string, string[]>
}

// Reports
export interface Report {
  id: string
  filename: string
  title?: string
  report_type?: string
  publish_date?: string
  security_firm?: string
  analyst_name?: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  page_count?: number
  entity_count: number
  vector_chunks?: number
  created_at: string
}

export interface ReportStatus {
  report_id: string
  status: string
  progress: number
  error?: string
}

export interface ReportsResponse {
  reports: Report[]
  total: number
}

// Chat
export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  provider?: string
  model?: string
  sources?: Source[]
  graph_data?: GraphData
  created_at: string
}

export interface Source {
  document: string
  page: number
  content: string
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface GraphNode {
  id: string
  label: string
  type: string
  properties?: Record<string, unknown>
}

export interface GraphLink {
  source: string
  target: string
  label: string
  properties?: Record<string, unknown>
}

export interface Conversation {
  id: string
  title?: string
  created_at: string
  messages: Message[]
}

export interface ConversationResponse {
  conversation: Conversation
}

export interface ChatRequest {
  query: string
  conversation_id?: string
  provider?: string
  model?: string
}

export interface ChatResponse {
  conversation_id: string
  message: Message
}

// Graph
export interface Entity {
  id: string
  name: string
  type: string
  properties?: Record<string, unknown>
}

export interface GraphEntity {
  id: string
  name: string
  type: string
  properties: Record<string, unknown>
}

export interface Timeline {
  ticker: string
  entries: TimelineEntry[]
}

export interface TimelineEntry {
  date: string
  opinion: string
  target_price?: number
  analyst?: string
}

// Report Detail
export interface GraphInfo {
  report_id: string
  nodes_count: number
  relationships_count: number
  companies: Array<{
    name?: string
    ticker?: string
    industry?: string
    market?: string
  }>
  industries: Array<{
    name?: string
    parent_industry?: string
  }>
  themes: Array<{
    name?: string
    keywords?: string[]
    description?: string
  }>
}

export interface VectorInfo {
  report_id: string
  chunks_count: number
  chunks: Array<{
    chunk_index?: number
    page_number?: number
    text_preview?: string
  }>
}
