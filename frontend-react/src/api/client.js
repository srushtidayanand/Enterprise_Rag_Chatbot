import axios from "axios";

const SERVER_HOST =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
    ? "127.0.0.1"
    : window.location.hostname;

export const API_BASE = `http://${SERVER_HOST}:8000`;

const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const loginUser        = (creds)           => api.post("/login", creds);
export const logoutUser       = ()                => api.post("/logout");
export const askQuestion      = (question)        => api.post("/ask", { question });
export const getSuggestions   = (question)        => api.post("/suggestions", { question });
export const submitFeedback   = (query_id, value) => api.post("/feedback", { query_id, feedback: value });
export const getChatHistory   = (limit = 50)      => api.get(`/chat/history?limit=${limit}`);
export const getDocumentList  = ()                => api.get("/documents/list");
export const getEvalMetrics   = ()                => api.get("/metrics/evaluation");
export const getStats         = (days = 30)       => api.get(`/analytics/stats?days=${days}`);

export default api;
