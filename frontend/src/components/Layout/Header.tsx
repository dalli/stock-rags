import React from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  Container,
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import SettingsIcon from '@mui/icons-material/Settings'

export const Header: React.FC = () => {
  return (
    <AppBar position="sticky">
      <Container maxWidth="lg">
        <Toolbar disableGutters>
          <Typography
            variant="h6"
            component={RouterLink}
            to="/"
            sx={{
              flexGrow: 1,
              textDecoration: 'none',
              color: 'inherit',
              fontWeight: 'bold',
            }}
          >
            📊 Stock RAGs
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              color="inherit"
              component={RouterLink}
              to="/reports"
            >
              Reports
            </Button>
            <Button
              color="inherit"
              component={RouterLink}
              to="/chat"
            >
              Chat
            </Button>
            <Button
              color="inherit"
              component={RouterLink}
              to="/graph"
            >
              Graph
            </Button>
            <Button
              color="inherit"
              component={RouterLink}
              to="/settings"
              startIcon={<SettingsIcon />}
            >
              Settings
            </Button>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  )
}
