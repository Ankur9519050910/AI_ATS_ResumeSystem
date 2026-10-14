
import { useEffect, useState } from 'react'
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
} from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import { getAnalysisHistory } from '../services/api'
import AnalysisResult from './AnalysisResult'

function SavedAnalysisResult() {
  const location = useLocation()
  const navigate = useNavigate()
  const { analysisId } = useParams()
  const { user, accessToken, loading } = useAuth()

  const [result, setResult] = useState(
    location.state?.result ?? null,
  )
  const [pageLoading, setPageLoading] = useState(
    !location.state?.result,
  )
  const [error, setError] = useState('')

  useEffect(() => {
    if (loading) return

    if (!user || !accessToken) {
      navigate('/login', { replace: true })
      return
    }

    let cancelled = false

    async function loadSavedResult() {
      setPageLoading(true)
      setError('')

      try {
        const data = await getAnalysisHistory(accessToken)

        const history = Array.isArray(data)
          ? data
          : data?.items ?? data?.history ?? []

        const savedItem = history.find((item) => {
          const id = item.id ?? item.analysis_id

          return (
            id !== undefined &&
            id !== null &&
            String(id) === String(analysisId)
          )
        })

        if (cancelled) return

        if (!savedItem?.analysis_result) {
          setResult(null)
          setError(
            'Saved results were not found. The analysis may have been deleted.',
          )
          return
        }

        setResult(savedItem.analysis_result)
      } catch (err) {
        if (!cancelled) {
          setError(
            err.message || 'Unable to load the saved analysis.',
          )
        }
      } finally {
        if (!cancelled) {
          setPageLoading(false)
        }
      }
    }

    if (analysisId) {
      loadSavedResult()
    } else if (location.state?.result) {
      setResult(location.state.result)
      setPageLoading(false)
    } else {
      setResult(null)
      setError('No analysis ID was provided.')
      setPageLoading(false)
    }

    return () => {
      cancelled = true
    }
  }, [
    analysisId,
    accessToken,
    user,
    loading,
    navigate,
    location.state,
  ])

  if (loading || pageLoading) {
    return (
      <main className="dashboard-loading">
        <p>Loading saved analysis results...</p>
      </main>
    )
  }

  if (error || !result || typeof result !== 'object') {
    return (
      <main className="dashboard-empty">
        <h2>Analysis results unavailable</h2>
        <p>
          {error || 'The saved analysis could not be loaded.'}
        </p>
        <Link
          to="/dashboard"
          className="dashboard-secondary-button"
        >
          Back to dashboard
        </Link>
      </main>
    )
  }

  return <AnalysisResult result={result} />
}

export default SavedAnalysisResult
