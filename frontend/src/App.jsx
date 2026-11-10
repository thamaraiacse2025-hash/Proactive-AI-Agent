
import { useEffect, useState } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState({
    total_jobs: 0,
    jobs_with_descriptions: 0,
  })

  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('All')
  const [selectedJob, setSelectedJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Fetch actual internships and statistics from FastAPI
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        setError('')

        const [jobsResponse, statsResponse] = await Promise.all([
          fetch(`${API_URL}/jobs`),
          fetch(`${API_URL}/stats`),
        ])

        if (!jobsResponse.ok || !statsResponse.ok) {
          throw new Error('Unable to fetch dashboard data.')
        }

        const jobsData = await jobsResponse.json()
        const statsData = await statsResponse.json()

        setJobs(jobsData.jobs || [])
        setStats(statsData)
      } catch (err) {
        console.error('Dashboard error:', err)
        setError(
          'Cannot connect to backend. Please make sure FastAPI is running.'
        )
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  // Categorize internships based on their titles
  const getCategory = (job) => {
    const title = (job.job_title || '').toLowerCase()

    if (title.includes('machine learning') || title.includes('ml ')) {
      return 'Machine Learning'
    }

    if (title.includes('python')) {
      return 'Python'
    }

    if (
      title.includes('software') ||
      title.includes('developer') ||
      title.includes('engineer')
    ) {
      return 'Software Development'
    }

    return 'Other'
  }

  // Search and filter actual database records
  const filteredJobs = jobs.filter((job) => {
    const searchText = search.toLowerCase()

    const matchesSearch = [
      job.job_title,
      job.company,
      job.location,
      job.description,
    ].some((value) => (value || '').toLowerCase().includes(searchText))

    const matchesFilter =
      filter === 'All' || getCategory(job) === filter

    return matchesSearch && matchesFilter
  })

  return (
    <div className="dashboard">

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">✦</span>
          <span>ProActive AI</span>
        </div>

        <p className="menu-label">MENU</p>

        <nav>
          <a className="nav-link active" href="#dashboard">
            ◫ <span>Dashboard</span>
          </a>

          <a className="nav-link" href="#internships">
            ▤ <span>Internships</span>
          </a>

          <a className="nav-link" href="#profile">
            ◉ <span>My Profile</span>
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="agent-status">
            <span className="status-dot"></span>
            <div>
              <strong>AI Agent Active</strong>
              <small>Monitoring opportunities</small>
            </div>
          </div>

          <p>Proactive Internship Agent</p>
          <small>Version 1.0</small>
        </div>
      </aside>

      <main className="main-content" id="dashboard">

        <header className="topbar">
          <div>
            <p className="breadcrumb">Workspace / Dashboard</p>
            <h1>Dashboard</h1>
            <p className="subtitle">
              Your personalized internship opportunities at a glance.
            </p>
          </div>

          <div className="profile">
            <div className="avatar">T</div>
            <div>
              <strong>Thamarai</strong>
              <small>Student</small>
            </div>
          </div>
        </header>

        <section className="welcome-banner">
          <div>
            <p>YOUR CAREER JOURNEY</p>
            <h2>Find opportunities that match you.</h2>
            <span>
              Your AI agent continuously looks for relevant opportunities.
            </span>
          </div>

          <div className="banner-icon">✦</div>
        </section>

        <section className="stats-grid">

          <div className="stat-card">
            <span className="stat-icon purple">▤</span>
            <p>Total Internships</p>
            <h2>{stats.total_jobs}</h2>
            <small>Stored in database</small>
          </div>

          <div className="stat-card">
            <span className="stat-icon blue">✦</span>
            <p>With Descriptions</p>
            <h2>{stats.jobs_with_descriptions}</h2>
            <small>Detailed job information</small>
          </div>

          <div className="stat-card">
            <span className="stat-icon green">⌕</span>
            <p>Search Results</p>
            <h2>{filteredJobs.length}</h2>
            <small>Currently displayed</small>
          </div>

          <div className="stat-card">
            <span className="stat-icon orange">◷</span>
            <p>Search Frequency</p>
            <h2>6 Hours</h2>
            <small>Automatic schedule</small>
          </div>

        </section>

        <section className="jobs-section" id="internships">

          <div className="section-heading">
            <div>
              <h2>Internship Opportunities</h2>
              <p>
                Actual opportunities collected and stored by your AI agent.
              </p>
            </div>

            <span className="demo-label">Live Database</span>
          </div>

          <div className="search-bar">
            <span>⌕</span>

            <input
              type="text"
              placeholder="Search by job title, company or location..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="filter-row">
            {[
              'All',
              'Python',
              'Machine Learning',
              'Software Development',
              'Other',
            ].map((item) => (
              <button
                key={item}
                className={
                  filter === item ? 'filter active-filter' : 'filter'
                }
                onClick={() => setFilter(item)}
              >
                {item}
              </button>
            ))}
          </div>

          <div className="job-list">

            {loading && (
              <p className="empty-state">
                Loading internships from database...
              </p>
            )}

            {error && (
              <p className="empty-state">{error}</p>
            )}

            {!loading && !error && filteredJobs.map((job) => (
              <article className="job-card" key={job.id}>

                <div className="company-logo">
                  {(job.company || 'C').charAt(0).toUpperCase()}
                </div>

                <div className="job-info">
                  <h3>{job.job_title}</h3>
                  <p>{job.company}</p>

                  <div className="job-meta">
                    <span>⌖ {job.location || 'Location not specified'}</span>
                    <span>{getCategory(job)}</span>
                  </div>
                </div>

                <div className="job-score">
                  <small>
                    Found: {job.date_found || 'N/A'}
                  </small>

                  <button onClick={() => setSelectedJob(job)}>
                    View Details
                  </button>
                </div>

              </article>
            ))}

            {!loading && !error && filteredJobs.length === 0 && (
              <p className="empty-state">
                No matching internships found.
              </p>
            )}

          </div>
        </section>

        <footer>
          ProActive AI · Personalized Internship Discovery System
        </footer>

      </main>

      {selectedJob && (
        <div
          className="modal-overlay"
          onClick={() => setSelectedJob(null)}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()}>

            <button
              className="close-button"
              onClick={() => setSelectedJob(null)}
            >
              ×
            </button>

            <h2>{selectedJob.job_title}</h2>
            <p>{selectedJob.company}</p>

            <hr />

            <p>
              <strong>Location:</strong> {selectedJob.location || 'Not specified'}
            </p>

            <p>
              <strong>Date Found:</strong> {selectedJob.date_found || 'N/A'}
            </p>

            <p>
              <strong>Category:</strong> {getCategory(selectedJob)}
            </p>

            <h3>Job Description</h3>

            <p className="job-description">
              {selectedJob.description || 'Description not available.'}
            </p>

            {selectedJob.apply_link && (
              <a
                href={selectedJob.apply_link}
                target="_blank"
                rel="noopener noreferrer"
                className="apply-button"
              >
                Apply Now ↗
              </a>
            )}

          </div>
        </div>
      )}

    </div>
  )
}

export default App
