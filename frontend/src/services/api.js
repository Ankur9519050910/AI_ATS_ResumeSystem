const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

const API_PREFIX = '/api/v1'

/**
 * Reusable API request handler.
 * Pass a Supabase access token when the endpoint requires authentication.
 */
async function apiRequest(endpoint, options = {}) {
  const {
    token,
    headers: customHeaders = {},
    ...requestOptions
  } = options

  const headers = {
    Accept: 'application/json',
    ...customHeaders,
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(
    `${API_BASE_URL}${API_PREFIX}${endpoint}`,
    {
      ...requestOptions,
      headers,
    },
  )

  if (!response.ok) {
    let message = `Request failed (${response.status})`

    try {
      const errorData = await response.json()
      message =
        errorData.detail ||
        errorData.message ||
        message
    } catch {
      // Keep the default error message if the response is not JSON.
    }

    throw new Error(
      typeof message === 'string'
        ? message
        : JSON.stringify(message),
    )
  }

  if (response.status === 204) {
    return null
  }

  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes('application/pdf')) {
    return response.blob()
  }

  if (contentType.includes('application/json')) {
    return response.json()
  }

  return response.text()
}

/**
 * Check whether the FastAPI backend is running.
 */
export async function checkBackendHealth() {
  return apiRequest('/health')
}

/**
 * Analyze a resume.
 *
 * `formData` should contain the fields expected by your FastAPI endpoint.
 */
export async function analyzeResume(formData, token) {
  return apiRequest('/analyze-resume', {
    method: 'POST',
    token,
    body: formData,
  })
}

/**
 * Fetch the user's analysis history.
 */
export async function getAnalysisHistory(token) {
  return apiRequest('/history', {
    method: 'GET',
    token,
  })
}

/**
 * Delete a specific analysis.
 */
export async function deleteAnalysis(analysisId, token) {
  return apiRequest(`/history/${encodeURIComponent(analysisId)}`, {
    method: 'DELETE',
    token,
  })
}

/**
 * Generate a PDF report from an analysis.
 *
 * The request body must match your backend's expected schema.
 */
export async function generatePdf(analysisData, token) {
  return apiRequest('/generate-pdf', {
    method: 'POST',
    token,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(analysisData),
  })
}

/**
 * Download a PDF for an existing analysis.
 */
export async function downloadAnalysisPdf(analysisId, token) {
  return apiRequest(
    `/history/${encodeURIComponent(analysisId)}/pdf`,
    {
      method: 'GET',
      token,
    },
  )
}

export { API_BASE_URL }