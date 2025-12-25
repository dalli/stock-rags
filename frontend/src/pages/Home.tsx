import React from 'react'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Stack,
  Paper,
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { MainLayout } from '@/components/Layout/MainLayout'

export const HomePage: React.FC = () => {
  return (
    <MainLayout>
      <Box sx={{ mb: 6 }}>
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 'bold' }}>
          📊 Stock RAGs
        </Typography>
        <Typography variant="h6" color="textSecondary" gutterBottom>
          Deep Analysis of Security Reports Using Graph RAG
        </Typography>
      </Box>

      <Grid container spacing={3} sx={{ mb: 6 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ mb: 1 }}>
                📄
              </Typography>
              <Typography variant="h6" gutterBottom>
                Reports
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Upload and manage security reports for analysis
              </Typography>
              <Button
                component={RouterLink}
                to="/reports"
                variant="outlined"
                size="small"
              >
                Go to Reports
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ mb: 1 }}>
                💬
              </Typography>
              <Typography variant="h6" gutterBottom>
                Chat
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Ask questions and get AI-powered answers from reports
              </Typography>
              <Button
                component={RouterLink}
                to="/chat"
                variant="outlined"
                size="small"
              >
                Go to Chat
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ mb: 1 }}>
                🌐
              </Typography>
              <Typography variant="h6" gutterBottom>
                Graph Explorer
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Explore relationships and entities in the knowledge graph
              </Typography>
              <Button
                component={RouterLink}
                to="/graph"
                variant="outlined"
                size="small"
              >
                Go to Graph
              </Button>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ mb: 1 }}>
                ⚙️
              </Typography>
              <Typography variant="h6" gutterBottom>
                Settings
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                Configure LLM and embedding providers
              </Typography>
              <Button
                component={RouterLink}
                to="/settings"
                variant="outlined"
                size="small"
              >
                Go to Settings
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ p: 3, backgroundColor: '#f5f5f5' }}>
        <Typography variant="h6" gutterBottom>
          🚀 Quick Start
        </Typography>
        <Stack component="ol" spacing={1} sx={{ pl: 2 }}>
          <Typography component="li" variant="body2">
            Configure your LLM and embedding providers in Settings
          </Typography>
          <Typography component="li" variant="body2">
            Upload security reports in Reports section
          </Typography>
          <Typography component="li" variant="body2">
            Wait for the reports to be processed
          </Typography>
          <Typography component="li" variant="body2">
            Ask questions about the reports in Chat
          </Typography>
          <Typography component="li" variant="body2">
            Explore relationships in Graph Explorer
          </Typography>
        </Stack>
      </Paper>
    </MainLayout>
  )
}
