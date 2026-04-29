import React from 'react';
import { Card, CardContent, Typography, Box, Skeleton } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

const StatCard = ({ title, value, unit, trend, trendValue, icon: Icon, loading }) => {
  if (loading) {
    return (
      <Card sx={{ height: '100%', borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
        <CardContent>
          <Skeleton variant="text" width="60%" height={30} />
          <Skeleton variant="text" width="40%" height={50} />
        </CardContent>
      </Card>
    );
  }

  const isPositiveTrend = trend === 'up';

  return (
    <Card sx={{ 
      height: '100%', 
      borderRadius: 3, 
      boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
      transition: 'transform 0.2s',
      '&:hover': { transform: 'translateY(-4px)' }
    }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
            {title}
          </Typography>
          {Icon && <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'primary.light', color: 'primary.main' }}>
            <Icon fontSize="small" />
          </Box>}
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
          <Typography variant="h4" fontWeight={700}>
            {value}
          </Typography>
          {unit && <Typography variant="body2" color="text.secondary">
            {unit}
          </Typography>}
        </Box>

        {trendValue && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, gap: 0.5 }}>
            {isPositiveTrend ? 
              <TrendingUp fontSize="small" color="success" /> : 
              <TrendingDown fontSize="small" color="error" />
            }
            <Typography variant="caption" color={isPositiveTrend ? 'success.main' : 'error.main'} fontWeight={600}>
              {trendValue}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              vs last period
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default StatCard;
