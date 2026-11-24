import axios, { type AxiosRequestConfig } from "axios";

const DEFAULT_API_BASE_URL = "/api";
const DEFAULT_TIMEOUT_MS = 15_000;

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
  timeout: DEFAULT_TIMEOUT_MS,
  headers: {
    "Content-Type": "application/json",
  },
});

client.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const payload = error.response?.data as { error?: string } | undefined;
      const message = payload?.error || error.message || "Request failed";
      return Promise.reject(new Error(message));
    }
    return Promise.reject(error instanceof Error ? error : new Error("Unexpected request error"));
  }
);

export interface RequestOptions<TBody = unknown> {
  url: string;
  method?: "GET" | "POST";
  params?: Record<string, string | number | undefined>;
  data?: TBody;
  timeout?: number;
}

export async function appRequest<TResponse, TBody = unknown>({
  url,
  method = "GET",
  params,
  data,
  timeout,
}: RequestOptions<TBody>): Promise<TResponse> {
  const config: AxiosRequestConfig = { url, method, params, data, timeout };
  const response = await client.request<TResponse>(config);
  return response.data;
}
