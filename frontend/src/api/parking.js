import { http } from "./http";

export const parkingApi = {
  getSpaces: (params) => http.get("/spaces", { params }),
  createSpace: (payload) => http.post("/spaces", payload),
  updateSpace: (id, payload) => http.patch(`/spaces/${id}`, payload),
  deleteSpace: (id) => http.delete(`/spaces/${id}`),
  getZones: (params) => http.get("/zones", { params }),
  getFloors: () => http.get("/zones/floors"),
  getZone: (id) => http.get(`/zones/${id}`),
  createZone: (payload) => http.post("/zones", payload),
  updateZone: (id, payload) => http.patch(`/zones/${id}`, payload),
  deleteZone: (id) => http.delete(`/zones/${id}`),
  getCards: () => http.get("/monthly-cards"),
  createCard: (payload) => http.post("/monthly-cards", payload),
  updateCard: (id, payload) => http.patch(`/monthly-cards/${id}`, payload),
  getOrders: () => http.get("/parking/orders"),
  entry: (payload) => http.post("/parking/entry", payload),
  calculate: (payload) => http.post("/parking/calculate", payload),
  exit: (id, payload) => http.post(`/parking/exit/${id}`, payload),
  getInvoices: () => http.get("/invoices"),
  createInvoice: (payload) => http.post("/invoices", payload),
};
