
import { Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import './App.css'
import Analyze from './pages/Analyze'

import SavedAnalysisResult from './pages/SavedAnalysisResult'

function Home() {
  return (
    <div className="app">
      <nav className="navbar">
        <a href="/" className="brand">
          <span className="brand-icon">R</span>
          <span>ResumeAI</span>
        </a>

        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
        </div>

        <div className="nav-actions">
          <a href="/login" className="btn btn-secondary">
            Sign in
          </a>
          <a href="/register" className="btn btn-primary">
            Get started
          </a>
        </div>
      </nav>

      <main>
        <section className="hero">
          <div className="hero-content">
            <p className="eyebrow">YOUR NEXT OPPORTUNITY STARTS HERE</p>

            <h1>
              Make your resume work
              <span> as hard as you do.</span>
            </h1>

            <p className="hero-description">
              Get an AI-powered resume analysis, identify skill gaps,
              and improve your resume for the roles you want.
            </p>

            <div className="hero-actions">
              <a href="/register" className="btn btn-primary">
                Analyze my resume <span aria-hidden="true">→</span>
              </a>
              <a href="#how-it-works" className="btn btn-secondary">
                See how it works
              </a>
            </div>

            <div className="hero-trust">
              <span className="trust-dot" />
              AI-powered resume insights
              <span className="trust-divider">·</span>
              Clear, actionable feedback
            </div>
          </div>

          <div className="hero-visual" aria-label="Resume analysis preview">
            <div className="resume-preview">
              <div className="preview-topbar">
                <span>Resume analysis</span>
                <span className="preview-status">Completed</span>
              </div>

              <div className="preview-body">
                <div className="preview-profile">
                  <div className="preview-avatar">JD</div>
                  <div>
                    <h3>Jordan Davis</h3>
                    <p>Software Engineer</p>
                  </div>
                </div>

                <div className="preview-score">
                  <div>
                    <p className="preview-label">Overall ATS score</p>
                    <h2>82<span>/100</span></h2>
                    <p className="preview-positive">Strong foundation</p>
                  </div>

                  <div className="score-ring">
                    <svg viewBox="0 0 100 100" role="img"
                      aria-label="82 percent score">
                      <circle cx="50" cy="50" r="40" className="ring-bg" />
                      <circle cx="50" cy="50" r="40" className="ring-progress" />
                    </svg>
                    <span>82%</span>
                  </div>
                </div>

                <div className="preview-metrics">
                  <div className="metric">
                    <span>Keywords</span>
                    <div className="metric-track">
                      <div style={{ width: '86%' }} />
                    </div>
                    <strong>86%</strong>
                  </div>

                  <div className="metric">
                    <span>Experience</span>
                    <div className="metric-track">
                      <div style={{ width: '74%' }} />
                    </div>
                    <strong>74%</strong>
                  </div>

                  <div className="metric">
                    <span>Formatting</span>
                    <div className="metric-track">
                      <div style={{ width: '91%' }} />
                    </div>
                    <strong>91%</strong>
                  </div>
                </div>

                <div className="preview-insight">
                  <span className="insight-icon">✓</span>
                  <div>
                    <strong>One improvement to make</strong>
                    <p>Add measurable results to your project descriptions.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="floating-note">
              <span className="floating-check">✓</span>
              <div>
                <strong>Actionable feedback</strong>
                <p>Know what to improve next</p>
              </div>
            </div>
          </div>
        </section>

        <section className="features-section" id="features">
          <div className="section-heading">
            <p className="eyebrow">BUILT FOR YOUR CAREER</p>
            <h2>More than a score. A clearer path forward.</h2>
            <p>
              Understand how your resume performs and what you can do to
              make it stronger.
            </p>
          </div>

          <div className="features-grid">
            <article className="feature-card">
              <div className="feature-icon">01</div>
              <h3>ATS compatibility</h3>
              <p>
                Identify resume issues that may make it harder for
                applicant tracking systems to read your information.
              </p>
            </article>

            <article className="feature-card">
              <div className="feature-icon">02</div>
              <h3>Skills and keywords</h3>
              <p>
                Find relevant keywords and understand where your resume
                can better reflect the role you are targeting.
              </p>
            </article>

            <article className="feature-card">
              <div className="feature-icon">03</div>
              <h3>Practical suggestions</h3>
              <p>
                Receive structured feedback to help improve clarity,
                experience descriptions, and resume quality.
              </p>
            </article>
          </div>
        </section>

        <section className="how-section" id="how-it-works">
          <div className="section-heading">
            <p className="eyebrow">A SIMPLE PROCESS</p>
            <h2>From resume to actionable insights.</h2>
          </div>

          <div className="steps-grid">
            <div className="step">
              <span>1</span>
              <h3>Upload your resume</h3>
              <p>Start with your existing resume.</p>
            </div>

            <div className="step">
              <span>2</span>
              <h3>Let AI analyze it</h3>
              <p>Review the generated score and feedback.</p>
            </div>

            <div className="step">
              <span>3</span>
              <h3>Make improvements</h3>
              <p>Use the suggestions to strengthen your resume.</p>
            </div>
          </div>

          <div className="final-cta">
            <div>
              <h2>Ready to understand your resume better?</h2>
              <p>Create an account to get started.</p>
            </div>
            <a href="/register" className="btn btn-primary">
              Get started <span aria-hidden="true">→</span>
            </a>
          </div>
        </section>
      </main>

      <footer className="footer">
        <a href="/" className="brand">
          <span className="brand-icon">R</span>
          <span>ResumeAI</span>
        </a>
        <p>Build a stronger resume, one improvement at a time.</p>
      </footer>
    </div>
  )
}

function NotFound() {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>Page not found</h1>
        <p>The page you requested does not exist.</p>
        <a href="/" className="btn btn-primary">
          Back to home
        </a>
      </section>
    </main>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="*" element={<NotFound />} />
      <Route path="/analyze" element={<Analyze />} />

      <Route
        path="/saved-results/:analysisId"
        element={<SavedAnalysisResult />}
      />

    </Routes>
  )
}

export default App
