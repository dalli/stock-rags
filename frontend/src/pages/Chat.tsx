import React, { useEffect, useRef } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  TextField,
  Button,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  Chip,
  Stack,
  IconButton,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import mermaid from 'mermaid'
import { MainLayout } from '@/components/Layout/MainLayout'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useChatStore } from '@/store/chat'
import { useAppStore } from '@/store/app'
import { chatApi } from '@/api/chat'
import { Message } from '@/api/types'

export const ChatPage: React.FC = () => {
  React.useEffect(() => {
    console.log('ChatPage mounted')
  }, [])

  const {
    conversations,
    currentConversation,
    error,
    setConversations,
    setCurrentConversation,
    addMessage,
    newConversation,
    setLoading,
    setError,
  } = useChatStore()

  const { defaultLLMProvider, defaultLLMModel } = useAppStore()

  const [query, setQuery] = React.useState('')
  const [sending, setSending] = React.useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize Mermaid
  useEffect(() => {
    mermaid.initialize({ 
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
    })
  }, [])

  // Render Mermaid diagrams after messages update
  useEffect(() => {
    if (currentConversation?.messages) {
      setTimeout(() => {
        mermaid.run({
          querySelector: '.mermaid',
        }).catch((err) => {
          console.error('Mermaid rendering error:', err)
        })
      }, 100)
    }
  }, [currentConversation?.messages])

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentConversation?.messages])

  const loadConversations = async () => {
    try {
      setLoading(true)
      const convs = await chatApi.listConversations()
      setConversations(convs)
      if (convs.length > 0) {
        setCurrentConversation(convs[0])
      }
      setError(null)
    } catch (err) {
      setError('Failed to load conversations')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleNewConversation = () => {
    newConversation()
  }

  const handleSelectConversation = async (convId: string) => {
    try {
      const conv = await chatApi.getConversation(convId)
      setCurrentConversation(conv)
    } catch (err) {
      setError('Failed to load conversation')
      console.error(err)
    }
  }

  const handleDeleteConversation = async (convId: string) => {
    try {
      await chatApi.deleteConversation(convId)
      loadConversations()
    } catch (err) {
      setError('Failed to delete conversation')
      console.error(err)
    }
  }

  const handleSendMessage = async () => {
    if (!query.trim()) return

    try {
      setSending(true)

      // Create user message
      const userMessage: Message = {
        id: '',
        conversation_id: currentConversation?.id || '',
        role: 'user',
        content: query,
        provider: defaultLLMProvider,
        model: defaultLLMModel,
        created_at: new Date().toISOString(),
      }

      // Add user message to current conversation
      if (currentConversation) {
        addMessage(userMessage)
      }

      const response = await chatApi.sendMessage({
        query,
        conversation_id: currentConversation?.id,
        provider: defaultLLMProvider,
        model: defaultLLMModel,
      })

      // Update or create conversation
      const conversationId = response.conversation_id

      // If we have a current conversation, update it
      if (currentConversation && currentConversation.id === conversationId) {
        addMessage(response.message)
      } else {
        // New conversation or different conversation
        // Reload the conversation to get all messages
        const updatedConversation = await chatApi.getConversation(conversationId)
        setCurrentConversation(updatedConversation)

        // Update conversations list
        await loadConversations()
      }

      setQuery('')
    } catch (err) {
      setError('Failed to send message')
      console.error(err)
    } finally {
      setSending(false)
    }
  }

  return (
    <MainLayout>
      <Grid container spacing={2} sx={{ height: 'calc(100vh - 180px)' }}>
        {/* Conversations Sidebar */}
        <Grid item xs={12} sm={3}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ pb: 1 }}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleNewConversation}
                sx={{ mb: 2 }}
              >
                New Chat
              </Button>

              <Typography variant="subtitle2" gutterBottom>
                Recent Chats
              </Typography>
            </CardContent>

            <List sx={{ flex: 1, overflow: 'auto' }}>
              {(Array.isArray(conversations) ? conversations : []).map((conv) => (
                <ListItem
                  key={conv.id}
                  button
                  selected={currentConversation?.id === conv.id}
                  onClick={() => handleSelectConversation(conv.id)}
                  secondaryAction={
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={() => handleDeleteConversation(conv.id)}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  }
                >
                  <ListItemText
                    primary={conv.title || 'Untitled'}
                    secondary={new Date(conv.created_at).toLocaleDateString()}
                    primaryTypographyProps={{ variant: 'body2' }}
                    secondaryTypographyProps={{ variant: 'caption' }}
                  />
                </ListItem>
              ))}
            </List>
          </Card>
        </Grid>

        {/* Chat Area */}
        <Grid item xs={12} sm={9}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
            {error && (
              <Box sx={{ p: 2 }}>
                <ErrorAlert message={error} />
              </Box>
            )}

            {!currentConversation ? (
              <CardContent sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
                <Typography color="textSecondary">
                  Start a new conversation
                </Typography>
              </CardContent>
            ) : (
              <>
                {/* Messages - Scrollable area */}
                <CardContent 
                  sx={{ 
                    flex: 1, 
                    overflow: 'auto',
                    minHeight: 0, // Important for flex scrolling
                    pb: 2
                  }}
                >
                  {(currentConversation.messages || []).length === 0 ? (
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <Typography color="textSecondary">
                        No messages yet. Start the conversation!
                      </Typography>
                    </Box>
                  ) : (
                    <Stack spacing={2}>
                      {(currentConversation.messages || []).map((msg) => (
                        <Box key={msg.id}>
                          <Box
                            sx={{
                              display: 'flex',
                              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            }}
                          >
                            <Paper
                              elevation={0}
                              sx={{
                                p: 2,
                                maxWidth: '70%',
                                backgroundColor: msg.role === 'user' ? '#e3f2fd' : '#f5f5f5',
                                borderRadius: 2,
                              }}
                            >
                              {msg.role === 'assistant' ? (
                                <Box
                                  sx={{
                                    '& h1, & h2, & h3, & h4, & h5, & h6': {
                                      mt: 2,
                                      mb: 1,
                                      fontWeight: 'bold',
                                    },
                                    '& p': {
                                      mb: 1,
                                    },
                                    '& ul, & ol': {
                                      pl: 2,
                                      mb: 1,
                                    },
                                    '& code': {
                                      backgroundColor: 'rgba(0, 0, 0, 0.05)',
                                      padding: '2px 4px',
                                      borderRadius: '3px',
                                      fontFamily: 'monospace',
                                      fontSize: '0.9em',
                                    },
                                    '& pre': {
                                      backgroundColor: 'rgba(0, 0, 0, 0.05)',
                                      padding: 2,
                                      borderRadius: 1,
                                      overflow: 'auto',
                                      mb: 1,
                                    },
                                    '& pre code': {
                                      backgroundColor: 'transparent',
                                      padding: 0,
                                    },
                                    '& blockquote': {
                                      borderLeft: '4px solid #ccc',
                                      pl: 2,
                                      ml: 0,
                                      fontStyle: 'italic',
                                      mb: 1,
                                    },
                                    '& table': {
                                      borderCollapse: 'collapse',
                                      width: '100%',
                                      mb: 1,
                                    },
                                    '& th, & td': {
                                      border: '1px solid #ddd',
                                      padding: '8px',
                                      textAlign: 'left',
                                    },
                                    '& th': {
                                      backgroundColor: '#f2f2f2',
                                      fontWeight: 'bold',
                                    },
                                    '& .mermaid': {
                                      display: 'flex',
                                      justifyContent: 'center',
                                      my: 2,
                                    },
                                  }}
                                >
                                  <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    rehypePlugins={[rehypeRaw]}
                                    components={{
                                      code({ node, inline, className, children, ...props }: any) {
                                        const match = /language-(\w+)/.exec(className || '')
                                        const isMermaid = match && match[1] === 'mermaid'
                                        
                                        if (isMermaid) {
                                          return (
                                            <div className="mermaid" {...props}>
                                              {String(children).replace(/\n$/, '')}
                                            </div>
                                          )
                                        }
                                        
                                        return !inline && match ? (
                                          <pre className={className} {...props}>
                                            <code className={className}>{children}</code>
                                          </pre>
                                        ) : (
                                          <code className={className} {...props}>
                                            {children}
                                          </code>
                                        )
                                      },
                                    }}
                                  >
                                    {msg.content}
                                  </ReactMarkdown>
                                </Box>
                              ) : (
                                <Typography variant="body2">
                                  {msg.content}
                                </Typography>
                              )}
                              {msg.sources && msg.sources.length > 0 && (
                                <Box sx={{ mt: 1 }}>
                                  <Typography variant="caption" color="textSecondary">
                                    Sources:
                                  </Typography>
                                  <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                                    {msg.sources.map((source, idx) => (
                                      <Chip
                                        key={idx}
                                        label={`${source.document} (p${source.page})`}
                                        size="small"
                                        variant="outlined"
                                      />
                                    ))}
                                  </Stack>
                                </Box>
                              )}
                            </Paper>
                          </Box>
                        </Box>
                      ))}
                      <div ref={messagesEndRef} />
                    </Stack>
                  )}
                </CardContent>

                {/* Input - Fixed at bottom */}
                <Box 
                  sx={{ 
                    p: 2, 
                    borderTop: '1px solid #eee',
                    position: 'sticky',
                    bottom: 0,
                    backgroundColor: 'background.paper',
                    zIndex: 1
                  }}
                >
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <TextField
                      fullWidth
                      placeholder="Ask about the reports..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault()
                          handleSendMessage()
                        }
                      }}
                      disabled={sending}
                      multiline
                      maxRows={4}
                    />
                    <Button
                      variant="contained"
                      endIcon={<SendIcon />}
                      onClick={handleSendMessage}
                      disabled={!query.trim() || sending}
                    >
                      Send
                    </Button>
                  </Box>
                </Box>
              </>
            )}
          </Card>
        </Grid>
      </Grid>
    </MainLayout>
  )
}
