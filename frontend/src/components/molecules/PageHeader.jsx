import React from 'react';
import { Box, Typography, Breadcrumbs, Link, Button } from '@mui/material';
import { NavigateNext } from '@mui/icons-material';

const PageHeader = ({ title, subtitle, actions }) => {
  return (
    <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
      <Box>
        <Breadcrumbs 
          separator={<NavigateNext fontSize="small" />} 
          sx={{ mb: 1, '& .MuiTypography-root': { fontSize: '0.875rem' } }}
        >
          <Link underline="hover" color="inherit" href="/">
            Dashboard
          </Link>
          <Typography color="text.primary">{title}</Typography>
        </Breadcrumbs>
        
        <Typography variant="h4" fontWeight={800} color="text.primary" gutterBottom>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="body1" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </Box>

      {actions && (
        <Box sx={{ display: 'flex', gap: 2 }}>
          {actions.map((action, index) => (
            <Button 
              key={index}
              variant={action.variant || 'contained'} 
              startIcon={action.icon}
              onClick={action.onClick}
              sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 600 }}
            >
              {action.label}
            </Button>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default PageHeader;
