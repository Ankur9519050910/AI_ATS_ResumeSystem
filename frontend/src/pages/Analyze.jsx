
import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import { analyzeResume } from '../services/api'
import './Analyze.css'
import AnalysisResult from './AnalysisResult'

function Analyze() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const { accessToken } = useAuth()

  const [file, setFile] = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0]

    if (!selectedFile) return

    const extension = selectedFile.name
      .split('.')
      .pop()
      ?.toLowerCase()

    if (!['pdf', 'docx'].includes(extension)) {
      setError('Please upload a PDF or DOCX file.')
      setFile(null)
      event.target.value = ''
      return
    }

    if (selectedFile.size > 5 * 1024 * 1024) {
      setError('Your resume must be smaller than 5 MB.')
      setFile(null)
      event.target.value = ''
      return
    }

    setError('')
    setResult(null)
    setFile(selectedFile)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setResult(null)

    if (!file) {
      setError('Please upload your resume first.')
      return
    }

    if (!accessToken) {
      setError('Your session has expired. Please sign in again.')
      return
    }

    setSubmitting(true)

    try {
      const formData = new FormData()

      // These field names match your FastAPI endpoint.
      formData.append('resume', file)
      formData.append('job_description', jobDescription.trim())

      const data = await analyzeResume(formData, accessToken)

      setResult(data)
    } catch (err) {
      setError(
        err.message || 'Resume analysis failed. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="analyze-page">
      <header className="analyze-navbar">
        <Link to="/dashboard" className="analyze-brand">
          <span className="analyze-brand-icon">R</span>
          ResumeAI
        </Link>

        <Link to="/dashboard" className="analyze-back-link">
          ← Back to dashboard
        </Link>
      </header>

      <div className="analyze-container">
        <div className="analyze-heading">
          <p className="analyze-eyebrow">
            AI-POWERED RESUME REVIEW
          </p>

          <h1>Analyze your resume</h1>

          <p>
            Upload your resume and add the job description to discover
            strengths, missing keywords, and areas for improvement.
          </p>
        </div>

        <form className="analyze-form" onSubmit={handleSubmit}>
          <section className="analyze-card">
            <div className="analyze-step-heading">
              <span className="analyze-step-number">01</span>

              <div>
                <h2>Upload your resume</h2>
                <p>PDF or DOCX format, up to 5 MB.</p>
              </div>
            </div>

            <button
              type="button"
              className={`resume-dropzone ${file ? 'has-file' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              disabled={submitting}
            >
              <span className="upload-icon" aria-hidden="true">
                {file ? '✓' : '↑'}
              </span>

              {file ? (
                <>
                  <strong>{file.name}</strong>
                  <span>
                    {(file.size / (1024 * 1024)).toFixed(2)} MB · Click to
                    change file
                  </span>
                </>
              ) : (
                <>
                  <strong>Choose your resume</strong>
                  <span>Click here to browse your files</span>
                </>
              )}
            </button>

            <input
              ref={fileInputRef}
              className="analyze-file-input"
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileChange}
              disabled={submitting}
            />
          </section>

          <section className="analyze-card">
            <div className="analyze-step-heading">
              <span className="analyze-step-number">02</span>

              <div>
                <h2>Job description</h2>
                <p>
                  Paste the job posting you want to target. This field is
                  optional in your backend.
                </p>
              </div>
            </div>

            <label
              className="analyze-label"
              htmlFor="job-description"
            >
              Full job description
            </label>

            <textarea
              id="job-description"
              className="job-description-input"
              placeholder="Paste the job responsibilities, required skills, qualifications, and experience here..."
              value={jobDescription}
              onChange={(event) => {
                setJobDescription(event.target.value)
                setResult(null)
              }}
              rows={9}
              disabled={submitting}
            />

            <p className="character-count">
              {jobDescription.length} characters
            </p>
          </section>

          {error && (
            <p className="analyze-message" role="alert">
              {error}
            </p>
          )}

          <div className="analyze-actions">
            <button
              type="button"
              className="analyze-cancel-button"
              onClick={() => navigate('/dashboard')}
              disabled={submitting}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="analyze-submit-button"
              disabled={submitting}
            >
              {submitting
                ? 'Analyzing resume...'
                : 'Analyze resume →'}
            </button>
          </div>
        </form>

        {submitting && (
          <div className="dashboard-message">
            <p>
              Your resume is being analyzed. This may take a little while.
            </p>
          </div>
        )}

       {result && <AnalysisResult result={result} />}

        <p className="analyze-privacy-note">
          Your resume is used to generate personalized analysis results.
        </p>
      </div>
    </main>
  )
}

export default Analyze
