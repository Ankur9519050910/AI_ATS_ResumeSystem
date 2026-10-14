
import { Link } from 'react-router-dom'
import './AnalysisResult.css'

function ScoreRing({ score }) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0))
  const circumference = 2 * Math.PI * 43
  const offset = circumference * (1 - safeScore / 100)

  return (
    <div className="result-score-ring">
      <svg viewBox="0 0 100 100" aria-label={`ATS score ${safeScore}`}>
        <circle className="result-ring-track" cx="50" cy="50" r="43" />
        <circle
          className="result-ring-value"
          cx="50"
          cy="50"
          r="43"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="result-ring-label">
        <strong>{safeScore.toFixed(1)}</strong>
        <span>out of 100</span>
      </div>
    </div>
  )
}

function AnalysisResult({ result }) {
  const components = result.component_scores || {}
  const jdMatch = result.jd_match_analysis || {}
  const validation = result.skill_validation_details || {}

  const componentLabels = {
    formatting: 'Formatting',
    keywords: 'Keywords',
    content: 'Content',
    skill_validation: 'Skill validation',
    ats_compatibility: 'ATS compatibility',
  }

  const componentEntries = Object.entries(components)

  return (
    <main className="results-page">
      <header className="results-navbar">
        <Link to="/dashboard" className="results-brand">
          <span className="results-brand-icon">R</span>
          ResumeAI
        </Link>

        <Link to="/dashboard" className="results-back-link">
          ← Dashboard
        </Link>
      </header>

      <div className="results-container">
        <div className="results-heading">
          <p className="results-eyebrow">YOUR ANALYSIS REPORT</p>
          <h1>Resume analysis results</h1>
          <p>
            Review your resume score, job match, and recommended
            improvements.
          </p>
        </div>

        <section className="results-overview">
          <div className="results-overview-copy">
            <p className="results-card-label">OVERALL ATS SCORE</p>

            <h2>{Number(result.ats_score ?? 0).toFixed(1)}<span>/100</span></h2>

            <p className="results-interpretation">
              {result.interpretation || 'Analysis completed.'}
            </p>

            <p className="results-muted">
              Use the feedback below to identify areas for improvement.
            </p>
          </div>

          <ScoreRing score={result.ats_score} />
        </section>

        <section className="results-section">
          <div className="results-section-heading">
            <h2>Score breakdown</h2>
            <p>Scores returned by your analysis model.</p>
          </div>

          <div className="component-score-grid">
            {componentEntries.map(([key, value]) => (
              <article className="component-score-card" key={key}>
                <div className="component-score-top">
                  <span>{componentLabels[key] || key.replaceAll('_', ' ')}</span>
                  <strong>{value}</strong>
                </div>

                <div
                  className="component-progress-track"
                  role="progressbar"
                  aria-label={componentLabels[key] || key}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.min(100, Math.max(0, Number(value) || 0))}
                >
                  <div
                    className="component-progress-value"
                    style={{
                      width: `${Math.min(100, Math.max(0, Number(value) || 0))}%`,
                    }}
                  />
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="results-section">
          <div className="results-section-heading">
            <h2>Job description match</h2>
            <p>How closely your resume matches the supplied job description.</p>
          </div>

          <div className="match-summary-card">
            <div>
              <span className="results-card-label">MATCH PERCENTAGE</span>
              <strong className="match-percentage">
                {Number(jdMatch.match_percentage ?? result.keyword_match ?? 0).toFixed(1)}%
              </strong>
            </div>

            <div className="match-detail">
              <span>Semantic similarity</span>
              <strong>
                {jdMatch.semantic_similarity != null
                  ? `${(Number(jdMatch.semantic_similarity) * 100).toFixed(1)}%`
                  : 'Not available'}
              </strong>
            </div>

            <div className="match-detail">
              <span>Validated skills</span>
              <strong>
                {validation.validated_count ?? validation.validated?.length ?? 0}
                {' / '}
                {validation.total ?? result.skills?.length ?? 0}
              </strong>
            </div>
          </div>
        </section>

        <section className="results-section">
          <div className="results-section-heading">
            <h2>Strengths</h2>
            <p>Positive findings identified in your resume.</p>
          </div>

          {result.strengths?.length ? (
            <ul className="results-strength-list">
              {result.strengths.map((strength, index) => (
                <li key={`${strength}-${index}`}>
                  <span aria-hidden="true">✓</span>
                  {strength}
                </li>
              ))}
            </ul>
          ) : (
            <p className="results-empty">No strengths were returned.</p>
          )}
        </section>

        <section className="results-section">
          <div className="results-section-heading">
            <h2>Issues to address</h2>
            <p>Review these findings and follow the suggested fixes.</p>
          </div>

          <div className="feedback-list">
            {(result.detailed_feedback || []).map((item, index) => (
              <article className="feedback-card" key={`${item.issue_title}-${index}`}>
                <div className="feedback-card-heading">
                  <div>
                    <span className="feedback-index">
                      ISSUE {String(index + 1).padStart(2, '0')}
                    </span>
                    <h3>{item.issue_title}</h3>
                  </div>

                  <span className={`severity-pill ${String(item.severity_level || '').toLowerCase()}`}>
                    {item.severity_level || 'Review'}
                  </span>
                </div>

                <p className="feedback-explanation">{item.explanation}</p>

                {item.where_it_appears && (
                  <div className="feedback-detail">
                    <strong>Where it appears</strong>
                    <p>{item.where_it_appears}</p>
                  </div>
                )}

                {item.how_to_fix && (
                  <div className="feedback-detail">
                    <strong>How to improve</strong>
                    <p>{item.how_to_fix}</p>
                  </div>
                )}

                {item.action_items?.length > 0 && (
                  <div className="feedback-detail">
                    <strong>Action items</strong>
                    <ul>
                      {item.action_items.map((action, actionIndex) => (
                        <li key={`${action}-${actionIndex}`}>{action}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {item.example_improvement && (
                  <div className="feedback-example">
                    <strong>Example improvement</strong>
                    <pre>{item.example_improvement}</pre>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>

        <section className="results-section">
          <div className="results-section-heading">
            <h2>Keyword analysis</h2>
            <p>Compare detected keywords with the job description.</p>
          </div>

          <div className="keyword-grid">
            <div className="keyword-card">
              <h3>Matched keywords</h3>
              <div className="keyword-list">
                {(jdMatch.matched_keywords || result.matched_keywords || []).map(
                  (keyword, index) => (
                    <span className="keyword-tag matched" key={`${keyword}-${index}`}>
                      {keyword}
                    </span>
                  ),
                )}
              </div>
            </div>

            <div className="keyword-card">
              <h3>Missing keywords</h3>
              <div className="keyword-list">
                {(jdMatch.missing_keywords || result.missing_keywords || []).map(
                  (keyword, index) => (
                    <span className="keyword-tag missing" key={`${keyword}-${index}`}>
                      {keyword}
                    </span>
                  ),
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="results-section">
          <div className="results-section-heading">
            <h2>Skill validation</h2>
            <p>Skills the model found evidence for in your projects.</p>
          </div>

          <div className="skill-validation-grid">
            <div className="keyword-card">
              <h3>Validated skills</h3>

              {(validation.validated || []).length ? (
                validation.validated.map((item, index) => (
                  <div className="validated-skill" key={`${item.skill}-${index}`}>
                    <strong>{item.skill}</strong>
                    <span>
                      Evidence: {(item.projects || []).join(', ') || 'Not specified'}
                    </span>
                  </div>
                ))
              ) : (
                <p className="results-empty">No validated skills returned.</p>
              )}
            </div>

            <div className="keyword-card">
              <h3>Unvalidated skills</h3>
              <div className="keyword-list">
                {(validation.unvalidated || []).map((skill, index) => (
                  <span className="keyword-tag missing" key={`${skill}-${index}`}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {result.critical_issues?.length > 0 && (
          <section className="results-section">
            <div className="results-section-heading">
              <h2>Critical issues</h2>
            </div>
            <ul>
              {result.critical_issues.map((issue, index) => (
                <li key={`${issue}-${index}`}>{issue}</li>
              ))}
            </ul>
          </section>
        )}

        <div className="results-footer-actions">
          <Link to="/analyze" className="results-primary-button">
            Analyze another resume →
          </Link>
          <Link to="/dashboard" className="results-secondary-button">
            Back to dashboard
          </Link>
        </div>
      </div>
    </main>
  )
}

export default AnalysisResult
