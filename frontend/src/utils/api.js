import axios from "axios";

const API = axios.create({ baseURL: "http://localhost:8000" });

API.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

export const authAPI = {
    signup: (formData) => API.post("/auth/signup", formData),
    login: (data) => API.post("/auth/login", data),
};

export const alertsAPI = {
    getAlerts: (limit = 20) => API.get(`/alerts?limit=${limit}`),
    getAlertDetail: (id) => API.get(`/alerts/${id}`),
    deleteAlert: (id) => API.delete(`/alerts/${id}`),
};

export default API;