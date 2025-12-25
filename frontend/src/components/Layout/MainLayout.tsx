import React from 'react'
import { Box, Container } from '@mui/material'
import { Header } from './Header'

interface MainLayoutProps {
  children: React.ReactNode
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />
      <Container
        maxWidth="lg"
        sx={{
          flex: 1,
          py: 4,
        }}
      >
        {children}
      </Container>
    </Box>
  )
}
