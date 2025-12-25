import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  TextField,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Stack,
  Chip,
  Grid,
  IconButton,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import { MainLayout } from '@/components/Layout/MainLayout'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ErrorAlert } from '@/components/ErrorAlert'
import { graphApi } from '@/api/graph'
import { Entity, Timeline } from '@/api/types'

export const GraphExplorerPage: React.FC = () => {
  React.useEffect(() => {
    console.log('GraphExplorerPage mounted')
  }, [])

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null)
  const [entities, setEntities] = useState<Entity[]>([])
  const [timeline, setTimeline] = useState<Timeline | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    try {
      setLoading(true)
      const results = await graphApi.searchEntities(searchQuery)
      setEntities(results)
      setSelectedEntity(null)
      setTimeline(null)
      setError(null)
    } catch (err) {
      setError('Failed to search entities')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectEntity = async (entity: Entity) => {
    setSelectedEntity(entity)

    // Try to load timeline if it's a company
    if (entity.type === 'Company' && entity.properties?.ticker) {
      try {
        const data = await graphApi.getCompanyTimeline(entity.properties.ticker as string)
        setTimeline(data)
      } catch (err) {
        console.error('Failed to load timeline:', err)
      }
    }
  }

  return (
    <MainLayout>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          🌐 Graph Explorer
        </Typography>
        <Typography variant="body2" color="textSecondary" gutterBottom>
          Explore the knowledge graph and relationships
        </Typography>
      </Box>

      {error && <ErrorAlert message={error} />}

      <Grid container spacing={2}>
        {/* Search and Results */}
        <Grid item xs={12} md={5}>
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  placeholder="Search entities (companies, analysts, etc.)"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleSearch()
                    }
                  }}
                />
                <IconButton
                  onClick={handleSearch}
                  color="primary"
                  disabled={!searchQuery.trim() || loading}
                  sx={{ ml: 1 }}
                >
                  <SearchIcon />
                </IconButton>
              </Box>
            </CardContent>
          </Card>

          <Paper>
            {loading ? (
              <LoadingSpinner message="Searching..." />
            ) : (
              <List>
                {entities.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="No entities found" />
                  </ListItem>
                ) : (
                  entities.map((entity) => (
                    <ListItemButton
                      key={entity.id}
                      selected={selectedEntity?.id === entity.id}
                      onClick={() => handleSelectEntity(entity)}
                    >
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <Typography variant="body2">{entity.name}</Typography>
                            <Chip label={entity.type} size="small" />
                          </Box>
                        }
                        secondary={
                          entity.properties
                            ? Object.entries(entity.properties)
                                .map(([k, v]) => `${k}: ${v}`)
                                .join(', ')
                            : ''
                        }
                      />
                    </ListItemButton>
                  ))
                )}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Entity Details */}
        <Grid item xs={12} md={7}>
          {selectedEntity ? (
            <Stack spacing={2}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {selectedEntity.name}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                    <Chip label={selectedEntity.type} color="primary" />
                  </Stack>

                  {selectedEntity.properties && (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        Properties
                      </Typography>
                      <Box
                        component="dl"
                        sx={{
                          display: 'grid',
                          gridTemplateColumns: '100px 1fr',
                          gap: 1,
                        }}
                      >
                        {Object.entries(selectedEntity.properties).map(([key, value]) => (
                          <React.Fragment key={key}>
                            <Typography variant="body2" color="textSecondary">
                              {key}:
                            </Typography>
                            <Typography variant="body2">
                              {String(value)}
                            </Typography>
                          </React.Fragment>
                        ))}
                      </Box>
                    </Box>
                  )}
                </CardContent>
              </Card>

              {timeline && (
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      📈 Investment Opinion Timeline
                    </Typography>
                    <Stack spacing={2}>
                      {timeline.entries.map((entry, idx) => (
                        <Box
                          key={idx}
                          sx={{
                            p: 2,
                            backgroundColor: '#f5f5f5',
                            borderRadius: 1,
                            borderLeft: '4px solid #1976d2',
                          }}
                        >
                          <Typography variant="subtitle2">
                            {new Date(entry.date).toLocaleDateString()}
                          </Typography>
                          <Typography variant="body2">
                            Opinion: <strong>{entry.opinion}</strong>
                          </Typography>
                          {entry.target_price && (
                            <Typography variant="body2">
                              Target Price: ${entry.target_price.toFixed(2)}
                            </Typography>
                          )}
                          {entry.analyst && (
                            <Typography variant="caption" color="textSecondary">
                              by {entry.analyst}
                            </Typography>
                          )}
                        </Box>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              )}
            </Stack>
          ) : (
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 6 }}>
                <Typography color="textSecondary">
                  Select an entity to view details
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </MainLayout>
  )
}
