const API_BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res;
}

export async function login(email, password) {
  const res = await request('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  });
  return res.json();
}

export async function signup(email, password) {
  const res = await request('/auth/signup', {
    method: 'POST', body: JSON.stringify({ email, password }),
  });
  return res.json();
}

export async function getPlants(category, search, page = 1, limit = 40) {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (category && category !== 'all') params.set('category', category);
  if (search) params.set('search', search);
  const res = await request(`/plants?${params}`);
  return res.json();
}

export async function uploadGardenImage(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/garden/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
}

/** Cutout placement mode — returns plant positions */
export async function generateDesign(gardenImageId, style, density, plantIds = []) {
  const res = await request('/garden/generate', {
    method: 'POST',
    body: JSON.stringify({ garden_image_id: gardenImageId, style, density, plant_ids: plantIds }),
  });
  return res.json();
}

/** AI Image Generation mode — returns a rendered garden image URL */
export async function generateGardenImage(gardenImageId, style, density) {
  const res = await request('/garden/generate-image', {
    method: 'POST',
    body: JSON.stringify({ garden_image_id: gardenImageId, style, density, plant_ids: [] }),
  });
  return res.json();
}

export async function exportPlantList(placements, format = 'csv') {
  const res = await fetch(`${API_BASE}/garden/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ placements, format }),
  });
  if (!res.ok) throw new Error('Export failed');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `paysagea-garden-plan-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
