// All credentials come from localStorage — set by Login page
export interface XtreamCreds {
  baseUrl: string;
  username: string;
  password: string;
}

export function getCreds(): XtreamCreds {
  const raw = localStorage.getItem('xtream_creds');
  if (!raw) throw new Error('Not configured');
  return JSON.parse(raw);
}

export function saveCreds(creds: XtreamCreds) {
  localStorage.setItem('xtream_creds', JSON.stringify(creds));
}

export function clearCreds() {
  localStorage.removeItem('xtream_creds');
}

export async function fetchXtream(action: string, extraParams: Record<string, string | number> = {}) {
  const { baseUrl, username, password } = getCreds();
  const url = new URL(`${baseUrl}/player_api.php`);
  url.searchParams.set('username', username);
  url.searchParams.set('password', password);
  url.searchParams.set('action', action);

  for (const [k, v] of Object.entries(extraParams)) {
    url.searchParams.set(k, String(v));
  }

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API Error: ${res.status}`);
  return res.json();
}

export function getStreamUrl(
  type: 'series' | 'movie',
  streamId: number | string,
  extension = 'mp4'
) {
  const { baseUrl, username, password } = getCreds();
  return `${baseUrl}/${type}/${username}/${password}/${streamId}.${extension}`;
}
