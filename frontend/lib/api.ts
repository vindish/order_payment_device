import { request } from "./request";

export type LoginResult = {
  access_token: string;
  token_type: string;
};

export type Device = {
  id: number;
  sn: string;
  name: string | null;
  status: string;
  last_seen_at: string | null;
};

export type Order = {
  id: number;
  user_id: number;
  device_id: number;
  amount: string;
  currency: string;
  status: string;
  retry_count: number;
  created_at: string;
};

export function login(username: string, password: string) {
  return request<LoginResult>("/auth/login", {
    method: "POST",
    body: { username, password }
  });
}

export function listDevices(token: string) {
  return request<Device[]>("/devices", { token });
}

export function createDevice(token: string, data: { sn: string; name?: string }) {
  return request<Device>("/devices", { method: "POST", token, body: data });
}

export function listOrders(token: string) {
  return request<Order[]>("/orders", { token });
}

export function createOrder(token: string, data: { device_sn: string; amount: string }) {
  return request<Order>("/orders", { method: "POST", token, body: data });
}

export function mockPaymentCallback(data: { order_id: number; token: string; provider?: string; trade_no?: string }) {
  return request<{ msg: string; order_id: number; status: string }>("/payments/callback", {
    method: "POST",
    body: data
  });
}
