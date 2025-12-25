import React from 'react'
import { Box, CircularProgress, Typography } from '@mui/material'

interface LoadingSpinnerProps {
  message?: string
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        py: 4,
      }}
    >
      <CircularProgress />
      {message && <Typography variant="body2" color="textSecondary">{message}</Typography>}
    </Box>
  )
}
