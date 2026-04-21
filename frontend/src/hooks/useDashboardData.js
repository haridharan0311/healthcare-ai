import { useQuery } from '@tanstack/react-query';
import { 
  fetchPlatformStats, 
  fetchPlatformTrends, 
  fetchPlatformMedicines,
  fetchTimeSeries,
  fetchDistricts,
  fetchDistrictRestock,
  fetchSeasonality,
  fetchDoctorTrends
} from '../api';

export const usePlatformStats = (days = 30) => {
  return useQuery({
    queryKey: ['platformStats', days],
    queryFn: () => fetchPlatformStats(days).then(res => res.data),
    staleTime: 60000, // 1 minute
  });
};

export const usePlatformTrends = (days = 30, forecastDays = 8) => {
  return useQuery({
    queryKey: ['platformTrends', days, forecastDays],
    queryFn: () => fetchPlatformTrends(days, forecastDays).then(res => res.data),
    staleTime: 300000, // 5 minutes
  });
};

export const usePlatformMedicines = (days = 30) => {
  return useQuery({
    queryKey: ['platformMedicines', days],
    queryFn: () => fetchPlatformMedicines(days).then(res => res.data),
    staleTime: 600000, // 10 minutes
  });
};

export const useTimeSeriesTrends = (days = 30) => {
  return useQuery({
    queryKey: ['timeSeriesTrends', days],
    queryFn: () => fetchTimeSeries(days).then(res => {
      // ... (trimmed for brevity but keeping logic)
      const raw = res.data || [];
      const dateSet = [...new Set(raw.map(r => r.date))].sort();
      const totals = {};
      raw.forEach(r => { totals[r.disease_name] = (totals[r.disease_name] || 0) + r.case_count; });
      const sortedByVolume = Object.keys(totals).sort((a,b) => totals[b] - totals[a]);
      const lookup = {};
      raw.forEach(r => {
        if (!lookup[r.date]) lookup[r.date] = { date: r.date };
        lookup[r.date][r.disease_name] = r.case_count;
      });
      const processedData = dateSet.map(d => {
        const entry = { date: d };
        sortedByVolume.forEach(dis => { entry[dis] = (lookup[d] && lookup[d][dis]) ? lookup[d][dis] : 0; });
        return entry;
      });
      return { chartData: processedData, allDiseases: sortedByVolume };
    }),
    staleTime: 300000, // 5 minutes
  });
};

export const useDistricts = () => {
  return useQuery({
    queryKey: ['districts'],
    queryFn: () => fetchDistricts().then(res => {
      const raw = res.data;
      if (Array.isArray(raw)) return raw;
      if (Array.isArray(raw?.districts)) return raw.districts;
      return [];
    }),
    staleTime: Infinity, // Districts rarely change
  });
};

export const useDistrictRestock = (district, days = 30) => {
  return useQuery({
    queryKey: ['districtRestock', district, days],
    queryFn: () => fetchDistrictRestock(district, days).then(res => res.data),
    enabled: !!district,
    staleTime: 60000,
  });
};

export const useSeasonality = (days = 30) => {
  return useQuery({
    queryKey: ['seasonality', days],
    queryFn: () => fetchSeasonality(days).then(res => res.data),
    staleTime: 86400000, // 24 hours
  });
};

export const useDoctorTrends = (days = 0, limit = 5) => {
  return useQuery({
    queryKey: ['doctorTrends', days, limit],
    queryFn: () => fetchDoctorTrends(days, limit).then(res => res.data?.data || res.data || []),
    staleTime: 300000,
  });
};
