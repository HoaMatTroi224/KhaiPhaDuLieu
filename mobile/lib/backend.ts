import { supabase } from '@/lib/supabase';

const API_BASE_URL = 'https://khaiphadulieu-backend-954130532427.us-central1.run.app/?fbclid=IwY2xjawR1RAdleHRuA2FlbQIxMABicmlkETE1T3RwSGxraEV2cWo5Tjl0c3J0YwZhcHBfaWQQMjIyMDM5MTc4ODIwMDg5MgABHuzbbZdFOhYbDk21L_OTqAX5FvGGc_01-emydANgudRtvz2GQM9Yev1f1Y6x_aem_GoDzlTzsIKJR-wc_PGex5w';

function buildApiUrl(path: string) {
  return new URL(path, API_BASE_URL).toString();
}

async function getAuthHeaders() {
  const { data: { session } } = await supabase.auth.getSession();
  const access_token = session?.access_token;
  if (!access_token) {
    throw new Error('Missing authentication token. Please sign in again.');
  }

  return {
    Authorization: `Bearer ${access_token}`,
    'Content-Type': 'application/json',
  };
}

export async function initializeProject() {
  const headers = await getAuthHeaders();
  const response = await fetch(buildApiUrl('projects/initialize'), {
    method: 'POST',
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to initialize project');
  }

  return response.json();
}

export async function finalizeProject(projectId: string, payload: { name: string; domain: string | null; documents: Array<{ file_name: string; file_path: string; file_url: string; file_type: 'pdf' | 'txt'; file_size: number; }>; }) {
  const headers = await getAuthHeaders();
  const response = await fetch(buildApiUrl(`projects/${projectId}/finalize`), {
    method: 'PUT',
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const json = await response.json().catch(() => null);
    const message = json?.detail || json?.message || await response.text();
    throw new Error(message || 'Failed to finalize project');
  }

  return response.json();
}

export async function getRecentProjects() {
  const headers = await getAuthHeaders();
  const response = await fetch(buildApiUrl('projects/recent'), {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to fetch recent projects');
  }

  return response.json();
}

export async function getChatHistory(projectId: string) {
  const headers = await getAuthHeaders();
  const url = new URL(buildApiUrl('chat/history'));
  url.searchParams.set('project_id', projectId);

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to fetch chat history');
  }

  return response.json();
}

export async function answerChatQuestion(projectId: string, threadId: string, question: string) {
  const headers = await getAuthHeaders();
  const url = new URL(buildApiUrl('chat/answer'));
  url.searchParams.set('project_id', projectId);
  url.searchParams.set('thread_id', threadId);
  url.searchParams.set('question', question);

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers,
  });

  if (!response.ok) {
    const json = await response.json().catch(() => null);
    const message = json?.detail || json?.message || await response.text();
    throw new Error(message || 'Failed to fetch chat answer');
  }

  return response.json();
}

export async function getAllProjects() {
  const headers = await getAuthHeaders();
  const response = await fetch(buildApiUrl('projects/'), {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to fetch projects');
  }

  return response.json();
}

export async function getProjectDocuments(projectId: string) {
  const headers = await getAuthHeaders();
  const url = new URL(buildApiUrl('documents/'));
  url.searchParams.set('project_id', projectId);

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to fetch documents');
  }

  return response.json();
}

export async function getSummary(summaryId: string) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/summaries/${summaryId}`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || 'Failed to fetch summary');
  }

  return response.json();
}
