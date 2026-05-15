import type { components, operations } from './generated/schema';

export type Scan = components['schemas']['Scan'];
export type ExtractedFields = components['schemas']['ExtractedFields'];
export type Hotel = components['schemas']['Hotel'];
export type ScanStatus = Scan['status'];

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API ${init?.method ?? 'GET'} ${path} → ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function createScan(image: Blob, hotelId: string): Promise<Scan> {
  const form = new FormData();
  form.append('image', image, 'id.jpg');
  form.append('hotelId', hotelId);
  const res = await fetch(`${BASE_URL}/scans`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`createScan → ${res.status}`);
  return res.json() as Promise<Scan>;
}

export function getScan(id: string): Promise<Scan> {
  return apiFetch<Scan>(`/scans/${id}`);
}

export function updateScan(id: string, fields: ExtractedFields): Promise<Scan> {
  return apiFetch<Scan>(`/scans/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  });
}

export function getMyHotel(): Promise<Hotel> {
  return apiFetch<Hotel>('/hotels/me');
}
