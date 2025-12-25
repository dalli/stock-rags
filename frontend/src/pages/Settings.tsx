import React, { useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Stack,
  Divider,
} from '@mui/material'
import { MainLayout } from '@/components/Layout/MainLayout'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorAlert } from '@/components/ErrorAlert'
import { useAppStore } from '@/store/app'
import { modelsApi } from '@/api/models'

export const SettingsPage: React.FC = () => {
  React.useEffect(() => {
    console.log('SettingsPage mounted')
  }, [])

  const {
    llmModels,
    embeddingModels,
    defaultLLMProvider,
    defaultLLMModel,
    defaultEmbeddingProvider,
    defaultEmbeddingModel,
    setModels,
    setDefaultLLM,
    setDefaultEmbedding,
  } = useAppStore()

  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState(false)

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      setLoading(true)
      const data = await modelsApi.getAvailableModels()
      console.log('Settings: Loaded models from API:', data)
      setModels(data.llm_models, data.embedding_models)
      console.log('Settings: Store updated with:', { llm: data.llm_models, embedding: data.embedding_models })
      setError(null)
    } catch (err) {
      setError('Failed to load models')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveLLM = async () => {
    try {
      setSaving(true)
      await modelsApi.setDefaultModel(defaultLLMProvider, defaultLLMModel)
    } catch (err) {
      setError('Failed to save LLM settings')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveEmbedding = async () => {
    try {
      setSaving(true)
      await modelsApi.setDefaultModel(defaultEmbeddingProvider, defaultEmbeddingModel)
    } catch (err) {
      setError('Failed to save embedding settings')
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <MainLayout>
        <LoadingSpinner message="Loading settings..." />
      </MainLayout>
    )
  }

  return (
    <MainLayout>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          ⚙️ Settings
        </Typography>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Configure LLM and embedding providers
        </Typography>
      </Box>

      {error && <ErrorAlert message={error} />}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            🤖 LLM Provider
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={2}>
            <FormControl fullWidth>
              <InputLabel>Provider</InputLabel>
              <Select
                value={defaultLLMProvider}
                label="Provider"
                onChange={(e) => setDefaultLLM(e.target.value, defaultLLMModel)}
              >
                {Object.keys(llmModels || {}).map((provider) => (
                  <MenuItem key={provider} value={provider}>
                    {provider}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Model</InputLabel>
              <Select
                value={defaultLLMModel}
                label="Model"
                onChange={(e) => setDefaultLLM(defaultLLMProvider, e.target.value)}
              >
                {(llmModels || {})[defaultLLMProvider]?.map((model) => (
                  <MenuItem key={model} value={model}>
                    {model}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="contained"
              onClick={handleSaveLLM}
              disabled={saving}
            >
              Save LLM Settings
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            🔍 Embedding Provider
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Stack spacing={2}>
            <FormControl fullWidth>
              <InputLabel>Provider</InputLabel>
              <Select
                value={defaultEmbeddingProvider}
                label="Provider"
                onChange={(e) => setDefaultEmbedding(e.target.value, defaultEmbeddingModel)}
              >
                {Object.keys(embeddingModels || {}).map((provider) => (
                  <MenuItem key={provider} value={provider}>
                    {provider}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Model</InputLabel>
              <Select
                value={defaultEmbeddingModel}
                label="Model"
                onChange={(e) => setDefaultEmbedding(defaultEmbeddingProvider, e.target.value)}
              >
                {(embeddingModels || {})[defaultEmbeddingProvider]?.map((model) => (
                  <MenuItem key={model} value={model}>
                    {model}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="contained"
              onClick={handleSaveEmbedding}
              disabled={saving}
            >
              Save Embedding Settings
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </MainLayout>
  )
}
