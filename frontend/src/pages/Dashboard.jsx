import { useEffect, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/useAuth'

import {

  getAnalysisHistory,

  downloadAnalysisPdf,

  deleteAnalysis,

} from '../services/api'

import './Dashboard.css'

function Dashboard() {

  const navigate = useNavigate()

  const { user, accessToken, loading, signOut } = useAuth()

  const [history, setHistory] = useState([])

  const [historyLoading, setHistoryLoading] = useState(true)

  const [historyError, setHistoryError] = useState('')

  const [downloadError, setDownloadError] = useState('')

  const [downloadingId, setDownloadingId] = useState(null)

  const [signingOut, setSigningOut] = useState(false)

  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {

    if (loading) return

    if (!user) {

      navigate('/login', { replace: true })

      return

    }

    let cancelled = false

    async function loadHistory() {

      setHistoryLoading(true)

      setHistoryError('')

      try {

        const data = await getAnalysisHistory(accessToken)

        if (!cancelled) {

          const items = Array.isArray(data)

            ? data

            : data?.items ?? data?.history ?? []

          setHistory(items)

        }

      } catch (error) {

        if (!cancelled) {

          setHistoryError(

            error.message || 'Unable to load your history.',

          )

        }

      } finally {

        if (!cancelled) {

          setHistoryLoading(false)

        }

      }

    }

    loadHistory()

    return () => {

      cancelled = true

    }

  }, [user, accessToken, loading, navigate])

  const validScores = history
    .map((item) =>
      Number(item.ats_score ?? item.overall_score ?? item.score),
    )
    .filter(
      (score) => Number.isFinite(score) && score >= 0 && score <= 100,
    )

  const totalAnalyses = history.length

  const averageScore =
    validScores.length > 0
      ? (
          validScores.reduce((total, score) => total + score, 0) /
          validScores.length
        ).toFixed(1)
      : '—'

  const highestScore =
    validScores.length > 0 ? Math.max(...validScores).toFixed(1) : '—'

  const latestAnalysis = history.reduce((latest, item) => {
    const date = item.created_at ?? item.date

    if (!date || Number.isNaN(new Date(date).getTime())) {
      return latest
    }

    if (!latest || new Date(date).getTime() > new Date(latest).getTime()) {
      return date
    }

    return latest
  }, null)

  const lastAnalysisDate = latestAnalysis
    ? new Date(latestAnalysis).toLocaleDateString()
    : '—'


async function handleDeleteAnalysis(item) {

  const analysisId = item.id ?? item.analysis_id

  if (analysisId === undefined || analysisId === null) {

    setHistoryError('Unable to identify this analysis.')

    return

  }

  const confirmed = window.confirm(

    'Are you sure you want to delete this analysis? This action cannot be undone.',

  )

  if (!confirmed) return

  setDeletingId(String(analysisId))

  setHistoryError('')

  try {

    await deleteAnalysis(analysisId, accessToken)

    setHistory((currentHistory) =>

      currentHistory.filter(

        (record) =>

          String(record.id ?? record.analysis_id) !==

          String(analysisId),

      ),

    )

  } catch (error) {

    setHistoryError(

      error.message || 'Unable to delete this analysis.',

    )

  } finally {

    setDeletingId(null)

  }

}

  async function handleSignOut() {

    setSigningOut(true)

    try {

      await signOut()

      navigate('/login', { replace: true })

    } catch (error) {

      setHistoryError(error.message || 'Unable to sign out.')

      setSigningOut(false)

    }

  }

  
function handleViewResults(item) {
  const analysisId = item.id ?? item.analysis_id

  if (analysisId === undefined || analysisId === null) {
    setHistoryError('Unable to identify this analysis.')
    return
  }

  navigate(`/saved-results/${encodeURIComponent(analysisId)}`, {
    state: { result: item.analysis_result },
  })
}


  async function handleDownloadPdf(item) {

    const analysisId = item.id ?? item.analysis_id

    if (analysisId === undefined || analysisId === null) {

      setDownloadError('Unable to identify this analysis.')

      return

    }

    setDownloadingId(String(analysisId))

    setDownloadError('')

    try {

      const blob = await downloadAnalysisPdf(

        analysisId,

        accessToken,

      )

      if (!(blob instanceof Blob) || blob.size === 0) {

        throw new Error('The server returned an empty PDF.')

      }

      const url = URL.createObjectURL(blob)

      const link = document.createElement('a')

      link.href = url

      link.download = `ats_report_${analysisId}.pdf`

      document.body.appendChild(link)

      link.click()

      link.remove()

      // Allow the browser to begin downloading before cleanup.

      window.setTimeout(() => URL.revokeObjectURL(url), 1000)

    } catch (error) {

      setDownloadError(

        error.message || 'Unable to download the PDF.',

      )

    } finally {

      setDownloadingId(null)

    }

  }

  if (loading || !user) {

    return (

      <main className="dashboard-loading">

        <p>Loading your dashboard...</p>

      </main>

    )

  }

  const displayName =

    user.user_metadata?.full_name ||

    user.user_metadata?.name ||

    user.email?.split('@')[0] ||

    'there'

  return (

    <main className="dashboard-page">

      <aside className="dashboard-sidebar">

        <Link to="/" className="dashboard-brand">

          <span className="brand-icon">R</span>

          <span>ResumeAI</span>

        </Link>

        <nav

          className="dashboard-nav"

          aria-label="Dashboard navigation"

        >

          <span className="dashboard-nav-label">WORKSPACE</span>

          <Link to="/dashboard" className="dashboard-nav-link active">

            <span aria-hidden="true">▦</span>

            Overview

          </Link>

          <Link to="/analyze" className="dashboard-nav-link">

            <span aria-hidden="true">＋</span>

            Analyze resume

          </Link>

          <a href="#recent-analyses" className="dashboard-nav-link">

            <span aria-hidden="true">◷</span>

            Analysis history

          </a>

        </nav>

        <div className="dashboard-sidebar-bottom">

          <div className="dashboard-user">

            <div className="dashboard-avatar">

              {displayName.charAt(0).toUpperCase()}

            </div>

            <div className="dashboard-user-info">

              <strong>{displayName}</strong>

              <span>{user.email}</span>

            </div>

          </div>

          <button

            type="button"

            className="dashboard-signout"

            onClick={handleSignOut}

            disabled={signingOut}

          >

            {signingOut ? 'Signing out...' : 'Sign out'}

          </button>

        </div>

      </aside>

      <section className="dashboard-main">

        <header className="dashboard-header">

          <div>

            <p className="dashboard-eyebrow">YOUR WORKSPACE</p>

            <h1>Good to see you, {displayName}.</h1>

            <p className="dashboard-subtitle">

              Review your resume progress and prepare for your next

              opportunity.

            </p>

          </div>

          <Link to="/analyze" className="dashboard-primary-button">

            <span aria-hidden="true">＋</span> New analysis

          </Link>

        </header>

        <section className="dashboard-welcome">

          <div className="welcome-copy">

            <span className="welcome-label">

              READY FOR YOUR NEXT STEP?

            </span>

            <h2>Make your next application count.</h2>

            <p>

              Compare your resume with a job description to discover

              relevant skills, missing keywords, and areas to improve.

            </p>

            <Link to="/analyze" className="welcome-button">

              Analyze a resume <span aria-hidden="true">→</span>

            </Link>

          </div>

          <div className="welcome-mark" aria-hidden="true">

            <div className="welcome-document">

              <span></span>

              <span></span>

              <span></span>

              <div className="welcome-document-tags">

                <i></i>

                <i></i>

                <i></i>

              </div>

              <span></span>

              <span></span>

            </div>

          </div>

        </section>

        <section className="dashboard-stats" aria-label="Analysis statistics">
          <article className="dashboard-stat-card">
            <span className="dashboard-stat-icon" aria-hidden="true">▤</span>
            <p>Total analyses</p>
            <h3>{totalAnalyses}</h3>
            <span className="dashboard-stat-caption">Saved resume reports</span>
          </article>

          <article className="dashboard-stat-card">
            <span className="dashboard-stat-icon" aria-hidden="true">↗</span>
            <p>Average ATS score</p>
            <h3>{averageScore}</h3>
            <span className="dashboard-stat-caption">Across scored analyses</span>
          </article>

          <article className="dashboard-stat-card">
            <span className="dashboard-stat-icon" aria-hidden="true">★</span>
            <p>Highest ATS score</p>
            <h3>{highestScore}</h3>
            <span className="dashboard-stat-caption">Best recorded score</span>
          </article>

          <article className="dashboard-stat-card">
            <span className="dashboard-stat-icon" aria-hidden="true">◷</span>
            <p>Last analysis</p>
            <h3 className="dashboard-stat-date">{lastAnalysisDate}</h3>
            <span className="dashboard-stat-caption">Most recent report</span>
          </article>
        </section>

        <section className="dashboard-section" id="recent-analyses">

          <div className="dashboard-section-header">

            <div>

              <h2>Recent analyses</h2>

              <p>Your previous resume analysis results.</p>

            </div>

          </div>

          {downloadError && (

            <p className="dashboard-error" role="alert">

              {downloadError}

            </p>

          )}

          {historyLoading ? (

            <div className="dashboard-empty">

              <p>Loading analysis history...</p>

            </div>

          ) : historyError ? (

            <div className="dashboard-empty">

              <p className="dashboard-error">{historyError}</p>

              <button

                type="button"

                className="dashboard-secondary-button"

                onClick={() => window.location.reload()}

              >

                Try again

              </button>

            </div>

          ) : history.length === 0 ? (

            <div className="dashboard-empty">

              <div className="empty-document" aria-hidden="true">

                ↗

              </div>

              <h3>No analyses yet</h3>

              <p>

                Your completed resume analyses will appear here.

                Start with your first resume to see your results.

              </p>

              <Link

                to="/analyze"

                className="dashboard-secondary-button"

              >

                Start your first analysis

              </Link>

            </div>

          ) : (

            <div className="history-list">

              {history.map((item, index) => {

                const id = item.id ?? item.analysis_id ?? index

                const analysisId = item.id ?? item.analysis_id

                const score =

                  item.ats_score ??

                  item.overall_score ??

                  item.score

                const isDownloading =

                  downloadingId !== null &&

                  downloadingId === String(analysisId)

                return (

                  <article className="history-item" key={id}>

                    <div className="history-document-icon">PDF</div>

                    <div className="history-item-info">

                      <strong>

                        {item.filename ||

                          item.resume_filename ||

                          item.job_title ||

                          `Resume analysis ${index + 1}`}

                      </strong>

                      <span>

                        {item.created_at

                          ? new Date(

                              item.created_at,

                            ).toLocaleDateString()

                          : 'Previous analysis'}

                      </span>

                    </div>

                    <div className="history-score">

                      <span>ATS score</span>

                      <strong>

                        {score !== undefined && score !== null

                          ? `${score}/100`

                          : '—'}

                      </strong>

                    </div>

                    
                    <button
                    type="button"
                    className="dashboard-secondary-button"
                    onClick={() => handleViewResults(item)}
                    >
                    View Results
                    </button>


                    <button

                      type="button"

                      className="dashboard-secondary-button"

                      onClick={() => handleDownloadPdf(item)}

                      disabled={

                        downloadingId !== null ||

                        analysisId === undefined ||

                        analysisId === null

                      }

                    >

                      {isDownloading

                        ? 'Downloading...'

                        : 'Download PDF'}

                    </button>

                    <button

                    type="button"

                    className="dashboard-secondary-button"

                    onClick={() => handleDeleteAnalysis(item)}

                    disabled={deletingId !== null || downloadingId !== null}

                    >

                    {deletingId === String(analysisId)

                        ? 'Deleting...'

                        : 'Delete'}

                    </button>

                  </article>

                )

              })}

            </div>

          )}

        </section>

      </section>

    </main>

  )

}

export default Dashboard
