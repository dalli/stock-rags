import React from 'react'
import { Alert, AlertTitle } from '@mui/material'

interface ErrorAlertProps {
  title?: string
  message: string
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ title, message }) => {
  return (
    <Alert severity="error">
      {title && <AlertTitle>{title}</AlertTitle>}
      {message}
    </Alert>
  )
}
