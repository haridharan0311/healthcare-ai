import axios from 'axios';

const BASE = 'http://localhost:8000/api';

export const fetchTrends      = (days = 30) => axios.get(`${BASE}/disease-trends/?days=${days}`);
export const fetchTimeSeries  = (days = 7)  => axios.get(`${BASE}/disease-trends/timeseries/?days=${days}`);
export const fetchSpikes      = ()          => axios.get(`${BASE}/spike-alerts/?all=true`);
export const fetchRestock     = ()          => axios.get(`${BASE}/restock-suggestions/`);
export const getExportUrl     = ()          => `${BASE}/export-report/`;
export const fetchDropdowns   = ()          => axios.get(`${BASE}/crud/dropdowns/`);

const CRUD = 'http://localhost:8000/api/crud';

export const crudApi = {
  list:   (model, page = 1, search = '', pageSize = 20) =>
    axios.get(`${CRUD}/${model}/`, { params: { page, search, page_size: pageSize } }),

  get:    (model, id) =>
    axios.get(`${CRUD}/${model}/${id}/`),

  create: (model, data) =>
    axios.post(`${CRUD}/${model}/`, data),

  update: (model, id, data) =>
    axios.put(`${CRUD}/${model}/${id}/`, data),

  patch:  (model, id, data) =>
    axios.patch(`${CRUD}/${model}/${id}/`, data),

  remove: (model, id) =>
    axios.delete(`${CRUD}/${model}/${id}/`),
};