import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
const CRUD = `${BASE}/crud`;

export const apiInstance = axios.create({
  baseURL: BASE,
  timeout: 120000,
});

apiInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

const api = (url, params = {}) =>
  apiInstance.get(url, { params });

// ── Authentication ────────────────────────────────────────────────────
export const login = (username, password) => 
  axios.post(`${BASE}/token/`, { username, password });

export const fetchMe = () => api('/me/');

// ── Core analytics ────────────────────────────────────────────────────
export const fetchTrends       = (days = 30)  => api('/disease-trends/', { days });
export const fetchTimeSeries   = (days = 7)   => api('/disease-trends/timeseries/', { days });
export const fetchMedicineUsage= (days = 30)  => api('/medicine-usage/', { days });
export const fetchSpikes       = (all = true) => api('/spike-alerts/', { all });
export const fetchRestock      = (days = 30)  => api('/restock-suggestions/', { days });

// ── District restock ──────────────────────────────────────────────────
export const fetchDistricts         = ()                    => api('/district-restock/');
export const fetchDistrictRestock = (district, days = 30) =>
  api('/district-restock/', { district, days });

// ── New features ──────────────────────────────────────────────────────
export const fetchTrendComparison  = (days = 7)    => api('/trend-comparison/', { days });
export const fetchTopMedicines     = (days = 30, limit = 10) =>
  api('/top-medicines/', { days, limit });
export const fetchLowStockAlerts   = (threshold = 50) =>
  api('/low-stock-alerts/', { threshold });
export const fetchSeasonality      = (days = 365)  => api('/seasonality/', { days });
export const fetchDoctorTrends     = (days = 30, limit = 20) =>
  api('/doctor-trends/', { days, limit });
export const fetchWeeklyReport     = (days = 90, period = null)   => api('/reports/weekly/', { days, ...(period ? { period } : {}) });
export const fetchMonthlyReport    = (days = 365, period = null)  => api('/reports/monthly/', { days, ...(period ? { period } : {}) });
export const fetchTodaySummary = () => api('/today-summary/');
export const fetchMedicineDependency = (disease = null, days = 30, min_usage = 0) =>
  api('/medicine-dependency/', {
    ...(disease ? { disease } : {}),
    days,
    min_usage,
  });
export const fetchStockDepletionForecast = (drugName, days = 30, forecastDays = 30) =>
  api('/stock-depletion/', {
    drug_name: drugName,
    days,
    forecast_days: forecastDays,
  });
export const fetchAdaptiveBuffer = (days = 30) => api('/adaptive-buffer/', { days });
export const fetchPlatformStats     = (days = 30) => api('/dashboard/stats/', { days });
export const fetchPlatformTrends    = (days = 30, forecastDays = 14) => 
  api('/dashboard/trends/', { days, forecast_days: forecastDays });
export const fetchPlatformMedicines = (days = 30) => api('/dashboard/medicines/', { days });

// ── Simulator Control ─────────────────────────────────────────────────
export const fetchSimulatorStatus = () => api('/simulator/toggle/');
export const toggleSimulator = (action, interval = 30) => 
  apiInstance.post(`/simulator/toggle/`, { action, interval });


// ── CSV exports ───────────────────────────────────────────────────────
export const getExportUrl = (type, params = {}) => {
  const qstr = new URLSearchParams(params).toString();
  return `${BASE}/export/${type}/${qstr ? '?' + qstr : ''}`;
};

export const downloadFile = async (type, params = {}, filename = 'export.csv') => {
  const url = getExportUrl(type, params);
  const response = await apiInstance.get(url, { responseType: 'blob' });
  const downloadUrl = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

// ── CRUD ──────────────────────────────────────────────────────────────
export const crudApi = {
  list:   (model, page = 1, search = '', pageSize = 20) =>
    axios.get(`${CRUD}/${model}/`, { params: { page, search, page_size: pageSize } }),
  get:    (model, id) => axios.get(`${CRUD}/${model}/${id}/`),
  create: (model, data) => axios.post(`${CRUD}/${model}/`, data),
  update: (model, id, data) => axios.put(`${CRUD}/${model}/${id}/`, data),
  patch:  (model, id, data) => axios.patch(`${CRUD}/${model}/${id}/`, data),
  remove: (model, id) => axios.delete(`${CRUD}/${model}/${id}/`),
};
export const fetchDropdowns = () => axios.get(`${CRUD}/dropdowns/`);

