import axios from 'axios';

const BASE = 'http://localhost:8000/api';

export const fetchTrends      = (days = 30) => axios.get(`${BASE}/disease-trends/?days=${days}`);
export const fetchTimeSeries  = (days = 7)  => axios.get(`${BASE}/disease-trends/timeseries/?days=${days}`);
export const fetchSpikes      = ()          => axios.get(`${BASE}/spike-alerts/?all=true`);
export const fetchRestock     = ()          => axios.get(`${BASE}/restock-suggestions/`);
export const getExportUrl     = ()          => `${BASE}/export-report/`;