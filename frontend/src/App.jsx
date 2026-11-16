
import { useEffect, useState } from 'react';
import './App.css';

import { Country, State, City } from 'country-state-city';

const API_URL = 'http://127.0.0.1:8000';

const countries = Country.getAllCountries();

const skillOptions = [
  'Python', 'Java', 'JavaScript', 'C', 'C++', 'SQL',
  'Machine Learning', 'Deep Learning', 'Artificial Intelligence',
  'Full Stack Development', 'HTML', 'CSS', 'React',
  'FastAPI', 'Data Science', 'Cloud Computing', 'MySQL',
  'MongoDB', 'Data Analysis'
];

const roleOptions = [
  'Software Developer Intern',
  'Python Developer Intern',
  'Java Developer Intern',
  'Machine Learning Intern',
  'AI Intern',
  'Data Science Intern',
  'Web Developer Intern',
  'Full Stack Developer Intern',
  'Cloud Computing Intern',
  'Data Analyst Intern'
];

const emptyProfile = {
  name: '',
  email: '',
  skills: [],
  preferred_location: '',
  preferred_roles: [],
  work_mode: 'Any',
  notification_threshold: 0.25
};

function findByName(list, name) {
  if (!name) return null;
  return list.find(
    item => item.name.toLowerCase() === name.toLowerCase()
  ) || null;
}

function parseSavedLocation(savedLocation) {
  const parts = (savedLocation || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean);

  const savedCountry = parts
    .map(part => findByName(countries, part))
    .find(Boolean);

  const country = savedCountry || findByName(countries, 'India');

  if (!country) {
    return {
      countryCode: '', country: '', stateCode: '',
      state: '', city: '', area: ''
    };
  }

  const states = State.getStatesOfCountry(country.isoCode);

  const savedState = parts
    .map(part => findByName(states, part))
    .find(Boolean);

  const state = savedState || null;

  const cities = state
    ? City.getCitiesOfState(country.isoCode, state.isoCode)
    : [];

  const savedCity = [...parts]
    .reverse()
    .map(part => findByName(cities, part))
    .find(Boolean);

  const city = savedCity ? savedCity.name : '';

  const ignoredNames = [
    country.name, state?.name, city
  ].filter(Boolean).map(name => name.toLowerCase());

  const area = parts
    .filter(part => !ignoredNames.includes(part.toLowerCase()))
    .join(', ');

  return {
    countryCode: country.isoCode,
    country: country.name,
    stateCode: state?.isoCode || '',
    state: state?.name || '',
    city,
    area
  };
}

function App() {
  const [activePage, setActivePage] = useState('dashboard');

  const [jobs, setJobs] = useState([]);
  const [recommendedJobs, setRecommendedJobs] = useState([]);
  const [recommendationError, setRecommendationError] = useState('');
  const [stats, setStats] = useState({});
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recommendationsLoading, setRecommendationsLoading] = useState(false);
  const [error, setError] = useState('');

  const [token, setToken] = useState(
    localStorage.getItem('proactive_agent_token') || ''
  );
  const [userId, setUserId] = useState(
    localStorage.getItem('proactive_agent_user_id') || ''
  );
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [authMode, setAuthMode] = useState('login');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  const [authForm, setAuthForm] = useState({
    name: '', email: '', password: ''
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [profile, setProfile] = useState(emptyProfile);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');
  const [profileError, setProfileError] = useState('');

  const [location, setLocation] = useState({
    countryCode: 'IN',
    country: 'India',
    stateCode: '',
    state: '',
    city: '',
    area: ''
  });

  const availableStates = location.countryCode
    ? State.getStatesOfCountry(location.countryCode)
    : [];

  const availableCities =
    location.countryCode && location.stateCode
      ? City.getCitiesOfState(location.countryCode, location.stateCode)
      : [];

  useEffect(() => {
    async function verifySession() {
      if (!token) {
        setIsAuthenticated(false);
        setAuthChecking(false);
        return;
      }

      setAuthChecking(true);

      try {
        const response = await fetch(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!response.ok) {
          throw new Error('Your session has expired. Please log in again.');
        }

        const user = await response.json();

        setUserId(String(user.id));
        localStorage.setItem('proactive_agent_user_id', String(user.id));

        setProfile(previous => ({
          ...previous,
          name: user.name || '',
          email: user.email || ''
        }));

        setIsAuthenticated(true);

        await Promise.all([
          fetchJobs(),
          fetchStats(),
          fetchRecommendations()
        ]);
      } catch (err) {
        localStorage.removeItem('proactive_agent_token');
        localStorage.removeItem('proactive_agent_user_id');

        setToken('');
        setUserId('');
        setIsAuthenticated(false);
        setAuthError(err.message || 'Please log in again.');
      } finally {
        setAuthChecking(false);
      }
    }

    verifySession();
  }, [token]);

  useEffect(() => {
    if (activePage === 'profile' && userId && token && isAuthenticated) {
      loadProfile();
    }
  }, [activePage, userId, token, isAuthenticated]);

  async function handleForgotPassword(event) {
    event.preventDefault();
    setAuthError('');

    if (!forgotEmail.trim()) {
      setAuthError('Please enter your registered email.');
      return;
    }

    try {
      setAuthLoading(true);

      const response = await fetch(`${API_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail.trim() })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to send OTP.');
      }

      setAuthError('');
      setAuthMode('reset');
    } catch (err) {
      setAuthError(err.message || 'Unable to send OTP.');
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleResetPassword(event) {
    event.preventDefault();
    setAuthError('');

    if (!/^\d{6}$/.test(otp.trim())) {
      setAuthError('Please enter the valid 6-digit OTP.');
      return;
    }

    if (newPassword.length < 8) {
      setAuthError('Password must contain at least 8 characters.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setAuthError('Passwords do not match.');
      return;
    }

    try {
      setAuthLoading(true);

      const response = await fetch(`${API_URL}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: forgotEmail.trim(),
          otp: otp.trim(),
          new_password: newPassword
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to reset password.');
      }

      setAuthMode('login');
      setAuthForm({
        name: '',
        email: forgotEmail.trim(),
        password: ''
      });

      setOtp('');
      setNewPassword('');
      setConfirmPassword('');
      setShowPassword(false);
      setShowNewPassword(false);
      setShowConfirmPassword(false);
      setAuthError('');

      alert('Password reset successful! Please login with your new password.');
    } catch (err) {
      setAuthError(err.message || 'Unable to reset password.');
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthError('');

    if (authMode === 'register' && !authForm.name.trim()) {
      setAuthError('Please enter your full name.');
      return;
    }

    if (!authForm.email.trim() || !authForm.password) {
      setAuthError('Please enter your email and password.');
      return;
    }

    if (authMode === 'register' && authForm.password.length < 8) {
      setAuthError('Password must contain at least 8 characters.');
      return;
    }

    try {
      setAuthLoading(true);

      const endpoint = authMode === 'register'
        ? '/auth/register'
        : '/auth/login';

      const payload = authMode === 'register'
        ? {
            name: authForm.name.trim(),
            email: authForm.email.trim(),
            password: authForm.password
          }
        : {
            email: authForm.email.trim(),
            password: authForm.password
          };

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed.');
      }

      localStorage.setItem('proactive_agent_token', data.access_token);
      localStorage.setItem('proactive_agent_user_id', String(data.user_id));

      setUserId(String(data.user_id));

      setProfile(previous => ({
        ...previous,
        name: data.name || '',
        email: data.email || authForm.email.trim()
      }));

      setAuthForm({ name: '', email: '', password: '' });
      setAuthChecking(true);
      setToken(data.access_token);
    } catch (err) {
      setAuthError(err.message || 'Unable to authenticate. Please try again.');
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem('proactive_agent_token');
    localStorage.removeItem('proactive_agent_user_id');

    setToken('');
    setUserId('');
    setIsAuthenticated(false);
    setProfile(emptyProfile);
    setJobs([]);
    setRecommendedJobs([]);
    setStats({});
    setActivePage('dashboard');
    setAuthMode('login');
    setAuthError('');
    setRecommendationError('');
  }

  async function fetchJobs() {
    try {
      setLoading(true);
      setError('');

      const response = await fetch(`${API_URL}/jobs`);

      if (!response.ok) {
        throw new Error('Unable to load internships');
      }

      const data = await response.json();

      // API returns { total_jobs, jobs: [...] }
      setJobs(Array.isArray(data) ? data : data.jobs || []);
    } catch (err) {
      setError(
        'Unable to connect to backend. Check whether the API is running.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function fetchRecommendations() {
    if (!token) return;

    try {
      setRecommendationsLoading(true);
      setRecommendationError('');

      const response = await fetch(`${API_URL}/my/recommendations`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load AI recommendations.');
      }

      setRecommendedJobs(
        Array.isArray(data.recommendations) ? data.recommendations : []
      );
    } catch (err) {
      setRecommendedJobs([]);
      setRecommendationError(err.message || 'Unable to load recommendations.');
    } finally {
      setRecommendationsLoading(false);
    }
  }

  async function fetchStats() {
    try {
      const response = await fetch(`${API_URL}/stats`);

      if (response.ok) {
        setStats(await response.json());
      }
    } catch (err) {
      console.error('Stats loading failed:', err);
    }
  }

  async function loadProfile() {
    try {
      setProfileLoading(true);
      setProfileError('');

      const response = await fetch(`${API_URL}/profiles/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.status === 404) {
        setProfile(previous => ({
          ...emptyProfile,
          name: previous.name,
          email: previous.email
        }));
        return;
      }

      if (!response.ok) {
        throw new Error('Unable to load profile');
      }

      const data = await response.json();

      setProfile({
        name: data.name || '',
        email: data.email || '',
        skills: data.skills || [],
        preferred_location: data.preferred_location || '',
        preferred_roles: data.preferred_roles || [],
        work_mode: data.work_mode || 'Any',
        notification_threshold: data.notification_threshold ?? 0.25
      });

      setLocation(parseSavedLocation(data.preferred_location));
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfileLoading(false);
    }
  }

  function updateProfile(field, value) {
    setProfile(previous => ({ ...previous, [field]: value }));
  }

  function toggleMultiValue(field, value, checked) {
    setProfile(previous => ({
      ...previous,
      [field]: checked
        ? [...previous[field], value]
        : previous[field].filter(item => item !== value)
    }));
  }

  async function saveProfile(event) {
    event.preventDefault();

    setProfileMessage('');
    setProfileError('');

    const selectedLocation = [
      location.area,
      location.city,
      location.state,
      location.country
    ].filter(Boolean).join(', ');

    const payload = {
      name: profile.name.trim(),
      email: profile.email.trim(),
      skills: profile.skills,
      preferred_location: selectedLocation,
      preferred_roles: profile.preferred_roles,
      work_mode: profile.work_mode,
      notification_threshold: 0.25
    };

    if (!payload.name || !payload.email) {
      setProfileError('Please enter your name and email.');
      return;
    }

    if (!payload.skills.length) {
      setProfileError('Please select at least one skill.');
      return;
    }

    if (!payload.preferred_roles.length) {
      setProfileError('Please select at least one preferred role.');
      return;
    }

    if (!location.countryCode || !location.stateCode || !location.city) {
      setProfileError('Please select your country, state and city.');
      return;
    }

    try {
      setProfileLoading(true);

      const isEditing = Boolean(userId);
      const url = isEditing
        ? `${API_URL}/profiles/${userId}`
        : `${API_URL}/profiles`;

      const response = await fetch(url, {
        method: isEditing ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to save profile');
      }

      if (!isEditing && data.user_id) {
        localStorage.setItem(
          'proactive_agent_user_id',
          String(data.user_id)
        );
        setUserId(String(data.user_id));
      }

      setProfileMessage(
        isEditing
          ? 'Profile updated successfully!'
          : 'Profile saved successfully!'
      );
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfileLoading(false);
    }
  }

  // Newest internships first using the date saved by the agent.
  // The database ID is the fallback when dates are equal or unavailable.
  function compareNewestFirst(a, b) {
    const dateA = Date.parse(a.date_found || a.created_at || '') || 0;
    const dateB = Date.parse(b.date_found || b.created_at || '') || 0;

    if (dateA !== dateB) {
      return dateB - dateA;
    }

    const idA = Number(a.id);
    const idB = Number(b.id);

    if (Number.isFinite(idA) && Number.isFinite(idB)) {
      return idB - idA;
    }

    return 0;
  }

  const filteredJobs = jobs
    .filter(job => {
      const keyword = search.toLowerCase();

      const matchesSearch =
        (job.job_title || '').toLowerCase().includes(keyword) ||
        (job.company || '').toLowerCase().includes(keyword) ||
        (job.location || '').toLowerCase().includes(keyword);

      const matchesFilter =
        filter === 'All' ||
        (job.location || '').toLowerCase().includes(filter.toLowerCase());

      return matchesSearch && matchesFilter;
    })
    .sort(compareNewestFirst);

  const filteredRecommendedJobs = recommendedJobs
    .filter(job => {
      const keyword = search.toLowerCase();

      const matchesSearch =
        (job.job_title || '').toLowerCase().includes(keyword) ||
        (job.company || '').toLowerCase().includes(keyword) ||
        (job.location || '').toLowerCase().includes(keyword);

      const matchesFilter =
        filter === 'All' ||
        (job.location || '').toLowerCase().includes(filter.toLowerCase());

      return matchesSearch && matchesFilter;
    })
    .sort((a, b) => {
      const dateA = Date.parse(a.date_found || a.created_at || '') || 0;
      const dateB = Date.parse(b.date_found || b.created_at || '') || 0;

      if (dateA !== dateB) return dateB - dateA;

      const scoreDifference =
        (Number(b.final_score) || 0) - (Number(a.final_score) || 0);
      if (scoreDifference !== 0) return scoreDifference;

      return compareNewestFirst(a, b);
    });

  function renderJobCards(jobList, showMatch = false, limit = null) {
    const displayedJobs = limit ? jobList.slice(0, limit) : jobList;

    if (!displayedJobs.length) {
      return <p className="empty-state">No internships found.</p>;
    }

    return (
      <div className="jobs-grid">
        {displayedJobs.map((job, index) => (
          <article className="job-card" key={job.id || job.apply_link || index}>
            <div className="job-card-top">
              <div className="company-avatar">
                {(job.company || 'C').charAt(0).toUpperCase()}
              </div>

              {showMatch ? (
                <span className="job-tag">
                  {`${Math.round((Number(job.final_score) || 0) * 100)}% Match`}
                </span>
              ) : (
                <span className="job-tag">Internship</span>
              )}
            </div>

            <h3>{job.job_title || 'Internship Opportunity'}</h3>

            <p className="company-name">
              {job.company || 'Company not specified'}
            </p>

            <p className="job-location">
              ⌖ {job.location || 'Location not specified'}
            </p>

            {showMatch && job.matched_skills?.length > 0 && (
              <p className="job-location">
                Matched skills: {job.matched_skills.join(', ')}
              </p>
            )}

            <div className="job-card-footer">
              <button
                className="details-button"
                onClick={() => setSelectedJob(job)}
              >
                View Details
              </button>

              <a
                className="apply-button"
                href={job.apply_link || '#'}
                target="_blank"
                rel="noreferrer"
              >
                Apply Now ↗
              </a>
            </div>
          </article>
        ))}
      </div>
    );
  }

  if (authChecking) {
    return (
      <div className="auth-screen">
        <div className="auth-card auth-loading">
          <div className="brand-icon">✦</div>
          <h2>Proactive AI</h2>
          <p>Checking your secure session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="auth-brand">
            <div className="brand-icon">✦</div>
            <span>Proactive AI</span>
          </div>

          <p className="section-eyebrow">PERSONALIZED CAREER ASSISTANT</p>

          <h1>
            {authMode === 'login'
              ? 'Welcome back'
              : authMode === 'register'
              ? 'Create your account'
              : authMode === 'forgot'
              ? 'Forgot password?'
              : 'Reset password'}
          </h1>

          <p className="auth-description">
            {authMode === 'login'
              ? 'Log in to continue to your personalized internship dashboard.'
              : authMode === 'register'
              ? 'Create an account to start discovering opportunities with your AI agent.'
              : authMode === 'forgot'
              ? 'Enter your registered email address. We will send you a password reset OTP.'
              : 'Enter the OTP sent to your email and create your new password.'}
          </p>

          {(authMode === 'login' || authMode === 'register') && (
            <form className="auth-form" onSubmit={handleAuthSubmit}>
              {authMode === 'register' && (
                <div className="form-group">
                  <label>Full Name</label>
                  <input
                    className="profile-input"
                    type="text"
                    value={authForm.name}
                    onChange={e => setAuthForm(previous => ({
                      ...previous, name: e.target.value
                    }))}
                    placeholder="Enter your full name"
                    autoComplete="name"
                    required
                  />
                </div>
              )}

              <div className="form-group">
                <label>Email Address</label>
                <input
                  className="profile-input"
                  type="email"
                  value={authForm.email}
                  onChange={e => setAuthForm(previous => ({
                    ...previous, email: e.target.value
                  }))}
                  placeholder="Enter your email"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="form-group">
                <label>Password</label>
                <div className="password-input-wrapper">
                  <input
                    className="profile-input"
                    type={showPassword ? 'text' : 'password'}
                    value={authForm.password}
                    onChange={e => setAuthForm(previous => ({
                      ...previous, password: e.target.value
                    }))}
                    placeholder={
                      authMode === 'register'
                        ? 'At least 8 characters'
                        : 'Enter your password'
                    }
                    autoComplete={
                      authMode === 'login'
                        ? 'current-password'
                        : 'new-password'
                    }
                    minLength={authMode === 'register' ? 8 : undefined}
                    required
                  />

                  <button
                    className="password-toggle"
                    type="button"
                    onClick={() => setShowPassword(previous => !previous)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>

              {authMode === 'login' && (
                <div className="forgot-password-row">
                  <button
                    type="button"
                    onClick={() => {
                      setForgotEmail(authForm.email);
                      setAuthMode('forgot');
                      setAuthError('');
                    }}
                  >
                    Forgot Password?
                  </button>
                </div>
              )}

              {authError && (
                <div className="profile-message error">{authError}</div>
              )}

              <button
                className="profile-submit auth-submit"
                type="submit"
                disabled={authLoading}
              >
                {authLoading
                  ? 'Please wait...'
                  : authMode === 'login'
                  ? 'Login →'
                  : 'Create Account →'}
              </button>
            </form>
          )}

          {authMode === 'forgot' && (
            <form className="auth-form" onSubmit={handleForgotPassword}>
              <div className="form-group">
                <label>Registered Email Address</label>
                <input
                  className="profile-input"
                  type="email"
                  value={forgotEmail}
                  onChange={e => setForgotEmail(e.target.value)}
                  placeholder="Enter your registered email"
                  autoComplete="email"
                  required
                />
              </div>

              {authError && (
                <div className="profile-message error">{authError}</div>
              )}

              <button
                className="profile-submit auth-submit"
                type="submit"
                disabled={authLoading}
              >
                {authLoading ? 'Sending OTP...' : 'Send OTP →'}
              </button>
            </form>
          )}

          {authMode === 'reset' && (
            <form className="auth-form" onSubmit={handleResetPassword}>
              <div className="form-group">
                <label>6-Digit OTP</label>
                <input
                  className="profile-input"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="Enter OTP"
                  required
                />
              </div>

              <div className="form-group">
                <label>New Password</label>
                <div className="password-input-wrapper">
                  <input
                    className="profile-input"
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    minLength={8}
                    autoComplete="new-password"
                    required
                  />
                  <button
                    className="password-toggle"
                    type="button"
                    onClick={() => setShowNewPassword(previous => !previous)}
                    aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                  >
                    {showNewPassword ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label>Confirm New Password</label>
                <div className="password-input-wrapper">
                  <input
                    className="profile-input"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter new password"
                    autoComplete="new-password"
                    required
                  />
                  <button
                    className="password-toggle"
                    type="button"
                    onClick={() => setShowConfirmPassword(previous => !previous)}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>

              {authError && (
                <div className="profile-message error">{authError}</div>
              )}

              <button
                className="profile-submit auth-submit"
                type="submit"
                disabled={authLoading}
              >
                {authLoading ? 'Resetting...' : 'Reset Password →'}
              </button>
            </form>
          )}

          <p className="auth-switch">
            {authMode === 'login' ? (
              <>
                Don't have an account?
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('register');
                    setAuthError('');
                    setShowPassword(false);
                  }}
                >
                  Create account
                </button>
              </>
            ) : authMode === 'register' ? (
              <>
                Already have an account?
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('login');
                    setAuthError('');
                    setShowPassword(false);
                  }}
                >
                  Login
                </button>
              </>
            ) : (
              <>
                Remember your password?
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('login');
                    setAuthError('');
                    setOtp('');
                    setNewPassword('');
                    setConfirmPassword('');
                  }}
                >
                  Back to Login
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <span>Proactive AI</span>
        </div>

        <p className="nav-label">MENU</p>

        <nav className="navigation">
          <button
            className={activePage === 'dashboard' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActivePage('dashboard')}
          >
            <span>▦</span> Dashboard
          </button>

          <button
            className={activePage === 'internships' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActivePage('internships')}
          >
            <span>⌕</span> Internships
          </button>

          <button
            className={activePage === 'profile' ? 'nav-item active' : 'nav-item'}
            onClick={() => setActivePage('profile')}
          >
            <span>◉</span> My Profile
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span>✦</span>
            <p>Your AI agent is working to find opportunities for you.</p>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="topbar-subtitle">PERSONALIZED CAREER ASSISTANT</p>
            <h2>
              {activePage === 'profile'
                ? 'My Profile'
                : activePage === 'internships'
                ? 'Internships'
                : 'Dashboard'}
            </h2>
          </div>

          <div className="user-info">
            <div className="avatar">
              {profile.name ? profile.name.charAt(0).toUpperCase() : 'S'}
            </div>

            <div>
              <strong>{profile.name || 'Student'}</strong>
              <small>{profile.email || 'Your career journey'}</small>
            </div>

            <button className="logout-button" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </header>

        {activePage === 'profile' ? (
          <section className="profile-section">
            <div className="profile-header">
              <div>
                <p className="section-eyebrow">PERSONALIZE YOUR AI AGENT</p>
                <h2>Build your career profile</h2>
                <p>
                  Tell us about your skills and preferences to discover
                  relevant opportunities.
                </p>
              </div>
              <div className="profile-symbol">◉</div>
            </div>

            {profileLoading && (
              <p className="profile-help">Loading profile...</p>
            )}

            <form className="profile-form" onSubmit={saveProfile}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    className="profile-input"
                    value={profile.name}
                    onChange={e => updateProfile('name', e.target.value)}
                    placeholder="Enter your name"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Email Address *</label>
                  <input
                    className="profile-input"
                    type="email"
                    value={profile.email}
                    onChange={e => updateProfile('email', e.target.value)}
                    placeholder="Enter your email"
                    required
                  />
                </div>

                <div className="form-group full-width">
                  <label>Skills *</label>
                  <details className="multi-select">
                    <summary>
                      {profile.skills.length
                        ? `${profile.skills.length} skills selected`
                        : 'Choose your skills'}
                    </summary>

                    <div className="multi-select-options">
                      {skillOptions.map(skill => (
                        <label key={skill}>
                          <input
                            type="checkbox"
                            checked={profile.skills.includes(skill)}
                            onChange={e => toggleMultiValue(
                              'skills', skill, e.target.checked
                            )}
                          />
                          {skill}
                        </label>
                      ))}
                    </div>
                  </details>
                </div>

                <div className="form-group">
                  <label>Country *</label>
                  <select
                    className="profile-input"
                    value={location.countryCode}
                    onChange={e => {
                      const selected = countries.find(
                        country => country.isoCode === e.target.value
                      );

                      setLocation({
                        countryCode: selected?.isoCode || '',
                        country: selected?.name || '',
                        stateCode: '',
                        state: '',
                        city: '',
                        area: ''
                      });
                    }}
                  >
                    <option value="">Select Country</option>
                    {countries.map(country => (
                      <option key={country.isoCode} value={country.isoCode}>
                        {country.flag} {country.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>State *</label>
                  <select
                    className="profile-input"
                    value={location.stateCode}
                    onChange={e => {
                      const selected = availableStates.find(
                        state => state.isoCode === e.target.value
                      );

                      setLocation(previous => ({
                        ...previous,
                        stateCode: selected?.isoCode || '',
                        state: selected?.name || '',
                        city: '',
                        area: ''
                      }));
                    }}
                    disabled={!location.countryCode}
                  >
                    <option value="">Select State</option>
                    {availableStates.map(state => (
                      <option key={state.isoCode} value={state.isoCode}>
                        {state.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>City *</label>
                  <select
                    className="profile-input"
                    value={location.city}
                    onChange={e => setLocation(previous => ({
                      ...previous, city: e.target.value, area: ''
                    }))}
                    disabled={!location.stateCode}
                  >
                    <option value="">Select City</option>
                    {availableCities.map((city, index) => (
                      <option key={`${city.name}-${index}`} value={city.name}>
                        {city.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Area / Locality (Optional)</label>
                  <input
                    className="profile-input"
                    value={location.area}
                    onChange={e => setLocation(previous => ({
                      ...previous, area: e.target.value
                    }))}
                    placeholder="Enter your area or locality"
                  />
                </div>

                <div className="form-group full-width">
                  <label>Preferred Roles *</label>
                  <details className="multi-select">
                    <summary>
                      {profile.preferred_roles.length
                        ? `${profile.preferred_roles.length} roles selected`
                        : 'Choose your preferred roles'}
                    </summary>

                    <div className="multi-select-options">
                      {roleOptions.map(role => (
                        <label key={role}>
                          <input
                            type="checkbox"
                            checked={profile.preferred_roles.includes(role)}
                            onChange={e => toggleMultiValue(
                              'preferred_roles', role, e.target.checked
                            )}
                          />
                          {role}
                        </label>
                      ))}
                    </div>
                  </details>
                </div>

                <div className="form-group">
                  <label>Work Mode</label>
                  <select
                    className="profile-input"
                    value={profile.work_mode}
                    onChange={e => updateProfile('work_mode', e.target.value)}
                  >
                    <option value="Any">Any</option>
                    <option value="Remote">Remote</option>
                    <option value="Hybrid">Hybrid</option>
                    <option value="On-site">On-site</option>
                  </select>
                </div>
              </div>

              {profileError && (
                <div className="profile-message error">{profileError}</div>
              )}

              {profileMessage && (
                <div className="profile-message success">{profileMessage}</div>
              )}

              <button
                className="profile-submit"
                type="submit"
                disabled={profileLoading}
              >
                {profileLoading
                  ? 'Saving...'
                  : userId
                  ? 'Update Profile →'
                  : 'Save Profile →'}
              </button>
            </form>
          </section>
        ) : (
          <>
            {activePage === 'dashboard' && (
              <section className="welcome-banner">
                <div>
                  <p className="section-eyebrow">YOUR CAREER JOURNEY</p>
                  <h1>Discover opportunities made for you.</h1>
                  <p>
                    Your proactive AI agent continuously finds and matches
                    internships based on your profile.
                  </p>

                  <button
                    className="banner-button"
                    onClick={() => setActivePage('internships')}
                  >
                    Explore Internships →
                  </button>
                </div>

                <div className="banner-art">✦</div>
              </section>
            )}

            <section className="stats-grid">
              <div className="stat-card">
                <span className="stat-icon purple">▦</span>
                <p>Total Internships</p>
                <h2>{stats.total_jobs ?? jobs.length}</h2>
              </div>

              <div className="stat-card">
                <span className="stat-icon green">✓</span>
                <p>Available Opportunities</p>
                <h2>{stats.total_jobs ?? jobs.length}</h2>
              </div>

              <div className="stat-card">
                <span className="stat-icon orange">✦</span>
                <p>AI Recommendations</p>
                <h2>{recommendedJobs.length}</h2>
              </div>
            </section>

            <div className="search-toolbar">
              <input
                className="search-input"
                placeholder="Search by role, company or location..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />

              <select
                className="filter-select"
                value={filter}
                onChange={e => setFilter(e.target.value)}
              >
                <option value="All">All Locations</option>
                <option value="Chennai">Chennai</option>
                <option value="Bangalore">Bangalore</option>
                <option value="Remote">Remote</option>
              </select>
            </div>

            <section className="internship-section">
              <div className="section-heading">
                <div>
                  <p className="section-eyebrow">AI-POWERED MATCHING</p>
                  <h2>Recommended for You</h2>
                  <p>Internships matched independently to your profile.</p>
                </div>

                <button
                  className="view-all"
                  onClick={fetchRecommendations}
                  disabled={recommendationsLoading}
                >
                  {recommendationsLoading ? 'Refreshing...' : 'Refresh ↻'}
                </button>
              </div>

              {recommendationsLoading ? (
                <p className="empty-state">Finding your best matches...</p>
              ) : recommendationError ? (
                <p className="empty-state error-text">
                  {recommendationError}
                </p>
              ) : filteredRecommendedJobs.length === 0 ? (
                <p className="empty-state">
                  No AI recommendations available yet. Your agent may need
                  to complete its next matching run.
                </p>
              ) : (
                renderJobCards(
                  filteredRecommendedJobs,
                  true,
                  activePage === 'dashboard' ? 6 : null
                )
              )}
            </section>

            <section className="internship-section">
              <div className="section-heading">
                <div>
                  <p className="section-eyebrow">COMMON JOB DATABASE</p>
                  <h2>
                    {activePage === 'internships'
                      ? 'All Internships'
                      : 'Explore All Internships'}
                  </h2>
                  <p>
                    Browse all opportunities collected by the agent,
                    not just your personalized matches.
                  </p>
                </div>

                {activePage === 'dashboard' && (
                  <button
                    className="view-all"
                    onClick={() => setActivePage('internships')}
                  >
                    View all →
                  </button>
                )}
              </div>

              {loading ? (
                <p className="empty-state">Loading internships...</p>
              ) : error ? (
                <p className="empty-state error-text">{error}</p>
              ) : (
                renderJobCards(
                  filteredJobs,
                  false,
                  activePage === 'dashboard' ? 6 : null
                )
              )}
            </section>
          </>
        )}
      </main>

      {selectedJob && (
        <div
          className="modal-overlay"
          onClick={() => setSelectedJob(null)}
        >
          <div className="modal" onClick={e => e.stopPropagation()}>
            <button
              className="modal-close"
              onClick={() => setSelectedJob(null)}
            >
              ×
            </button>

            <p className="section-eyebrow">INTERNSHIP DETAILS</p>
            <h2>{selectedJob.job_title}</h2>
            <p className="company-name">{selectedJob.company}</p>
            <p className="job-location">⌖ {selectedJob.location}</p>

            {selectedJob.final_score !== undefined && (
              <p className="job-location">
                AI Match: {Math.round(Number(selectedJob.final_score) * 100)}%
              </p>
            )}

            {selectedJob.matched_skills?.length > 0 && (
              <p className="job-location">
                Matched skills: {selectedJob.matched_skills.join(', ')}
              </p>
            )}

            <div className="job-description">
              {selectedJob.description || 'No description available.'}
            </div>

            <a
              className="apply-button modal-apply"
              href={selectedJob.apply_link || '#'}
              target="_blank"
              rel="noreferrer"
            >
              Apply Now ↗
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
