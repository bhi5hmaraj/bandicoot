# Frontend UI Design: Bandicoot RMAB Dashboard

**Version:** 1.1
**Status:** Draft
**Last Updated:** 2025-11-23

---

## 1. Overview

### Purpose
Build a simple, multi-page web application with server-side routing to provide Suvita program managers and health workers with:
- Real-time visibility into RMAB recommendations
- Model performance monitoring
- Basic system administration capabilities

### Architecture: Multi-Page Application (MPA)
- **Server-side routing**: FastAPI serves HTML templates via Jinja2
- **Traditional navigation**: Full page loads between routes
- **Progressive enhancement**: Vue 3 for interactive components on each page
- **No client-side routing**: No Vue Router, no SPA shell

### Goals
- **Simplicity**: Traditional web pages, minimal JavaScript
- **Server-rendered**: FastAPI templates with Jinja2
- **Mobile-friendly**: Responsive design for field workers on phones/tablets
- **Fast iteration**: Templates live alongside API code
- **Progressive enhancement**: Works without JavaScript, enhanced with Vue

### Non-Goals (Out of Scope for MVP)
- ❌ Single-page application (SPA) architecture
- ❌ Real-time updates (polling/websockets)
- ❌ User authentication UI (rely on API keys for now)
- ❌ Complex data visualization (charts/graphs)
- ❌ Mobile native app
- ❌ Internationalization (English only)
- ❌ Offline-first architecture

---

## 2. User Personas & Workflows

### Persona 1: Program Manager (Suvita)
**Primary User**, needs strategic overview

**Key Tasks:**
1. **View daily recommendations** - See which caregivers to prioritize today
2. **Monitor model health** - Check if system is trained and operational
3. **Track intervention outcomes** - See how many caregivers were contacted
4. **Trigger retraining** - Manually retrain model when needed

**Dashboard Needs:**
- High-level metrics (recommendations generated, model status)
- Quick access to top-K recommendations
- One-click export (CSV download)
- Simple admin actions (retrain model)

---

### Persona 2: Health Worker / Field Coordinator
**Secondary User**, needs actionable lists

**Key Tasks:**
1. **Get today's contact list** - See who to call/visit
2. **View caregiver context** - See why each caregiver is prioritized
3. **Update caregiver status** - Mark as contacted/responded
4. **Filter by region** - Focus on specific districts

**Dashboard Needs:**
- Clean, scrollable list of caregivers
- Priority scores and reasons
- District/region filters
- Mobile-friendly interface

---

## 3. Routes & Pages

All routes are server-side FastAPI routes that render Jinja2 templates.

### 3.1 Main Dashboard (Home)

**Route:** `GET /` or `GET /dashboard`
**Template:** `templates/dashboard.html`
**Handler:** `app/web/routes.py::dashboard()`

**Layout:**
```
┌─────────────────────────────────────────┐
│  Bandicoot RMAB   [Health: ●] [Retrain]│  ← Header
├─────────────────────────────────────────┤
│                                         │
│  📊 Quick Stats                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │ 1,234│ │  75  │ │ 0.87 │ │ v1.0 │   │
│  │Active│ │Budget│ │Score │ │Model │   │
│  └──────┘ └──────┘ └──────┘ └──────┘   │
│                                         │
├─────────────────────────────────────────┤
│  🎯 Today's Recommendations             │
│                                         │
│  Budget: [50] [Generate] [Export CSV]  │
│                                         │
│  Filters: District [All ▾] State [All ▾]│
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ CG-12345 | Priority 0.87 | ⚠️  │   │
│  │ Unresponsive, Cluster 5         │   │
│  │ Reason: High dropout risk...    │   │
│  │ [Mark Contacted] [Details]      │   │
│  ├─────────────────────────────────┤   │
│  │ CG-67890 | Priority 0.82 | ⚠️  │   │
│  │ ...                             │   │
│  └─────────────────────────────────┘   │
│  Showing 1-20 of 50                     │
│  [Load More]                            │
└─────────────────────────────────────────┘
```

**Server-Side Data:**
- Fetches health status from API
- Pre-loads recent recommendations (if any)
- User context (if authenticated)

**Interactive Components (Vue):**
- `RecommendationForm` - Generate recommendations with Vue reactivity
- `CaregiverList` - Client-side filtering and sorting

**Navigation:**
```html
<a href="/model">Model Info</a>
<a href="/settings">Settings</a>
```

---

### 3.2 Model Info Page

**Route:** `GET /model`
**Template:** `templates/model.html`
**Handler:** `app/web/routes.py::model_info()`

**Purpose:** Show model training details and cluster summaries

**Layout:**
```
┌─────────────────────────────────────────┐
│  ← Back to Dashboard                    │
├─────────────────────────────────────────┤
│  📚 Model Information                   │
│                                         │
│  Training Status                        │
│  ✓ Last trained: 2025-11-23 10:30 UTC  │
│  ✓ Model version: v1.0.0                │
│  ✓ Caregivers: 1,500                    │
│  ✓ Clusters: 20                         │
│  ✓ Silhouette score: 0.65               │
│                                         │
│  [Retrain Model] [Download Model]      │
│                                         │
├─────────────────────────────────────────┤
│  Cluster Summary                        │
│                                         │
│  Cluster | Size | W(R) | W(U) | Retention│
│  ──────────────────────────────────────│
│  0        150    0.35   0.85   82%      │
│  1        120    0.42   0.73   78%      │
│  ...                                    │
│                                         │
└─────────────────────────────────────────┘
```

**Server-Side Data:**
- Cluster summary from API
- Model training metadata
- Last trained timestamp

**Interactive Components (Vue):**
- `RetrainButton` - Trigger retraining with loading state
- `ClusterTable` - Sortable cluster summary

**Navigation:**
```html
<a href="/dashboard">Back to Dashboard</a>
```

---

### 3.3 Settings Page (Admin)

**Route:** `GET /settings`
**Template:** `templates/settings.html`
**Handler:** `app/web/routes.py::settings()`

**Purpose:** Configure model parameters and system settings

**Layout:**
```
┌─────────────────────────────────────────┐
│  ← Back to Dashboard                    │
├─────────────────────────────────────────┤
│  ⚙️ Settings                            │
│                                         │
│  Model Parameters                       │
│  ┌───────────────────────────────────┐ │
│  │ Number of Clusters: [20]          │ │
│  │ Discount Factor (γ): [0.99]       │ │
│  │ Alpha (Dirichlet): [1.0]          │ │
│  │ Min Observations: [10]            │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Recommendation Settings                │
│  ┌───────────────────────────────────┐ │
│  │ Default Budget: [50]              │ │
│  │ Auto-refresh: [Off]               │ │
│  └───────────────────────────────────┘ │
│                                         │
│  [Save Settings] [Reset to Defaults]   │
│                                         │
└─────────────────────────────────────────┘
```

**Server-Side Data:**
- Current settings from config
- Default values

**Interactive Components (Vue):**
- `SettingsForm` - Form with validation and submission

**Form Submission:**
- POST to `/settings` with form data
- Server updates config and re-renders page

**Navigation:**
```html
<a href="/dashboard">Back to Dashboard</a>
```

---

## 4. Template & Component Architecture

### Page-Level Structure

Each page is a Jinja2 template that extends a base layout:

```
templates/
├── base.html                    # Base layout with header/footer
├── dashboard.html               # Extends base, adds dashboard content
├── model.html                   # Extends base, adds model info
└── settings.html                # Extends base, adds settings form
```

### Vue Components Per Page

**Dashboard Page (`dashboard.html`):**
- `RecommendationForm` - Form to generate recommendations
- `CaregiverList` - Interactive list with filtering

**Model Page (`model.html`):**
- `RetrainButton` - Trigger retraining
- `ClusterTable` - Sortable table

**Settings Page (`settings.html`):**
- `SettingsForm` - Parameter configuration form

**Shared Components (all pages):**
- `HealthIndicator` - Shows model health in header
- `LoadingSpinner` - Loading states

### Vue Instance Per Page

Each page creates its own Vue instance:

```javascript
// In dashboard.html
<script>
const { createApp } = Vue;

createApp({
  data() {
    return {
      recommendations: [],
      budget: 50,
      loading: false
    }
  },
  methods: {
    async generateRecommendations() {
      this.loading = true;
      const response = await fetch('/api/v1/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ budget: this.budget })
      });
      this.recommendations = await response.json();
      this.loading = false;
    }
  }
}).mount('#app');
</script>
```

---

## 5. Technology Stack

### Backend Framework
**FastAPI with Jinja2 Templates**
- **Why:** Already using FastAPI, Jinja2 built-in, server-side rendering
- **Templates:** HTML templates with Jinja2 syntax

### Frontend Enhancement
**Vue 3** (via CDN, no build step)
- **Why:** Lightweight, progressive enhancement, works without build tools
- **Usage:** Inline `<script>` tags in templates, one Vue instance per page
- **CDN:** `https://unpkg.com/vue@3/dist/vue.global.js`

### UI Library
**PicoCSS** (classless CSS framework via CDN)
- **Why:** Minimal, semantic HTML, no class names needed
- **Size:** ~10KB gzipped
- **CDN:** `https://unpkg.com/@picocss/pico@latest/css/pico.min.css`

### State Management
**No global state** - each page is independent
- **Why:** Multi-page app, state resets on navigation
- **Per-page state:** Vue reactive data() on each page

### HTTP Client
**Fetch API** (native, no library)
- **Why:** No external dependency, modern browsers only
- **Used in:** Inline JavaScript in templates

### Routing
**Server-side routing** (FastAPI routes)
- **No client-side router:** Traditional `<a href>` links
- **Routes:**
  - `GET /` → `templates/dashboard.html`
  - `GET /model` → `templates/model.html`
  - `GET /settings` → `templates/settings.html`

### Icons
**Unicode Emojis** (no icon library)
- **Why:** Zero dependencies, universal support
- **Examples:** 🐾 📊 ⚙️ ✓ ⚠️

---

## 6. File Structure

```
app/
├── main.py                    # FastAPI app (already exists)
├── web/                       # NEW: Web UI routes
│   ├── __init__.py
│   └── routes.py              # HTML route handlers
├── templates/                 # NEW: Jinja2 templates
│   ├── base.html              # Base layout (header, footer, nav)
│   ├── dashboard.html         # Dashboard page
│   ├── model.html             # Model info page
│   └── settings.html          # Settings page
└── static/                    # NEW: Static assets
    ├── css/
    │   └── custom.css         # Custom styles (in addition to PicoCSS)
    ├── js/
    │   └── utils.js           # Shared JavaScript utilities
    └── images/
        └── logo.svg           # App logo

bandicoot/                     # Core library (already exists)
└── ...

tests/
├── test_api_integration.py    # API tests (already exists)
└── test_web_routes.py         # NEW: Web UI tests
```

**Key Changes from SPA:**
- ❌ No `frontend/` directory
- ❌ No `package.json`, `vite.config.js`, build step
- ✅ Templates live in `app/templates/`
- ✅ Static files in `app/static/`
- ✅ Vue loaded via CDN (no npm install)

---

## 7. Server-Side Rendering & API Integration

### Jinja2 Template Setup

**In `app/main.py`:**
```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")
```

### HTML Route Handlers

**In `app/web/routes.py`:**
```python
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.dependencies import get_recommender

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
async def dashboard(request: Request):
    """Render dashboard page."""
    recommender = get_recommender()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "model_loaded": recommender.is_fitted,
        "page_title": "Dashboard"
    })

@router.get("/model")
async def model_info(request: Request):
    """Render model info page."""
    recommender = get_recommender()

    if recommender.is_fitted:
        cluster_summary = recommender.get_cluster_summary().to_dict('records')
    else:
        cluster_summary = []

    return templates.TemplateResponse("model.html", {
        "request": request,
        "model_loaded": recommender.is_fitted,
        "clusters": cluster_summary,
        "page_title": "Model Info"
    })

@router.get("/settings")
async def settings(request: Request):
    """Render settings page."""
    from app.config import get_settings
    config = get_settings()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": config,
        "page_title": "Settings"
    })
```

### Client-Side API Calls (from templates)

**Inline JavaScript in templates:**
```html
<!-- In dashboard.html -->
<script>
async function generateRecommendations(budget) {
  const response = await fetch('/api/v1/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ budget: budget })
  });

  if (!response.ok) throw new Error('Failed to generate recommendations');

  return await response.json();
}
</script>
```

### Endpoint Usage

| UI Action | API Endpoint | Method | Called From |
|-----------|--------------|--------|-------------|
| Load page | `GET /` | GET | Browser navigation |
| Load health status | `GET /api/v1/health` | GET | Page load (AJAX) |
| Generate recommendations | `POST /api/v1/recommend` | POST | Button click (AJAX) |
| Train model | `POST /api/v1/train_clusters` | POST | Button click (AJAX) |
| Update settings | `POST /settings` | POST | Form submission (page reload) |

---

## 8. Route Priority & Mounting

### Route Order in FastAPI

**In `app/main.py`:**
```python
from app.api import routes as api_routes
from app.web import routes as web_routes

# 1. API routes (highest priority)
app.include_router(api_routes.router, prefix="/api/v1", tags=["API"])

# 2. Web UI routes
app.include_router(web_routes.router, tags=["Web"])

# 3. Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

**Priority:**
1. `/api/v1/*` - API endpoints (JSON responses)
2. `/`, `/model`, `/settings` - HTML pages
3. `/static/*` - CSS, JS, images

**No build step needed:**
- Templates are rendered on-the-fly
- Static assets served directly
- Vue loaded from CDN

---

## 9. Responsive Design

### Breakpoints
- **Mobile:** < 768px (single column, stacked cards)
- **Tablet:** 768px - 1024px (2 columns where appropriate)
- **Desktop:** > 1024px (full layout)

### Mobile Optimizations
- Large tap targets (min 44px)
- Simplified navigation (hamburger menu)
- Reduced data in tables (hide non-essential columns)
- Scroll-friendly lists (infinite scroll or pagination)

---

## 10. Development Workflow

### Local Development

**Single server (FastAPI serves everything):**
```bash
uvicorn app.main:app --reload --port 8000
```

**Access:**
- Web UI: http://localhost:8000/
- API docs: http://localhost:8000/docs
- API endpoints: http://localhost:8000/api/v1/*

**Template changes:**
- Edit `app/templates/*.html` directly
- Refresh browser to see changes
- No build step needed

**CSS/JS changes:**
- Edit `app/static/css/*.css` or `app/static/js/*.js`
- Hard refresh browser (Ctrl+Shift+R) to clear cache

### No Build Step
- ✅ No `npm install`
- ✅ No `npm run build`
- ✅ No `package.json`
- ✅ Templates rendered on-the-fly
- ✅ Static files served directly

---

## 11. Error Handling

### Client-Side Error Display (Vue via CDN)

**Inline in templates:**
```html
<!-- In dashboard.html -->
<div id="app">
  <div v-if="error" class="alert alert-error">
    {{ error }}
    <button @click="retry">Retry</button>
  </div>
</div>

<script>
const { createApp } = Vue;

createApp({
  data() {
    return {
      error: null,
      loading: false
    }
  },
  methods: {
    async loadData() {
      try {
        this.error = null;
        this.loading = true;
        // API call...
      } catch (e) {
        this.error = 'Failed to load data. Please try again.';
      } finally {
        this.loading = false;
      }
    },
    retry() {
      this.loadData();
    }
  }
}).mount('#app');
</script>
```

### Server-Side Error Handling

**In route handlers (`app/web/routes.py`):**
```python
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

@router.get("/dashboard")
async def dashboard(request: Request):
    try:
        recommender = get_recommender()
        # ... fetch data
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "model_loaded": recommender.is_fitted
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "Unable to load dashboard. Please try again."
        })
```

### Loading States
- Spinner during AJAX calls (Vue reactive data)
- Server-side loading indicators for initial page load
- Disabled buttons while processing (`<button :disabled="loading">`)
- Simple CSS animations (no complex skeleton screens)

---

## 12. Performance Considerations

### Asset Size Targets
- **Vue 3 (CDN):** ~34KB gzipped (one-time download, cached)
- **PicoCSS (CDN):** ~10KB gzipped (one-time download, cached)
- **Custom CSS:** < 5KB gzipped
- **Custom JS per page:** < 10KB gzipped
- **Initial load (first visit):** < 2 seconds on 3G
- **Subsequent pages:** < 500ms (CDN assets cached)

### Optimizations (No Build Step)

**Server-Side:**
- Enable HTTP/2 for multiplexing
- Compress HTML responses (gzip/brotli)
- Cache rendered templates (if data is static)
- Use FastAPI's async handlers for concurrency

**Client-Side:**
- Load Vue and PicoCSS from CDN with `crossorigin` attribute
- Use browser cache for static assets (long TTL)
- Defer non-critical JavaScript with `defer` attribute
- Minimize inline JavaScript (extract to `/static/js/utils.js`)

**CDN Configuration:**
```html
<!-- In base.html -->
<link rel="stylesheet"
      href="https://unpkg.com/@picocss/pico@latest/css/pico.min.css"
      crossorigin="anonymous">

<script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"
        crossorigin="anonymous"
        defer></script>
```

**No Code Splitting:**
- Each page loads independently (natural route-based splitting)
- No need for Webpack/Vite code splitting
- Browser navigates to new page, loads only what's needed

**Static Asset Caching:**
```python
# In app/main.py
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Add cache headers in production (nginx/CDN level)
# Cache-Control: public, max-age=31536000
```

---

## 13. Security

### Server-Side Security (Primary)

**Template Rendering (Jinja2):**
- **Auto-escaping enabled** by default (XSS prevention)
- **Never use `| safe` filter** unless absolutely necessary
- **Validate all user input** before rendering
- **Sanitize data** from API responses before passing to templates

```python
# In app/web/routes.py
from markupsafe import escape

@router.get("/dashboard")
async def dashboard(request: Request):
    user_input = request.query_params.get("filter", "")
    safe_input = escape(user_input)  # Escape HTML entities

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "filter": safe_input  # Safe to render
    })
```

**CSRF Protection:**
- Use `POST` for state-changing operations
- Add CSRF tokens to forms (FastAPI middleware available)
- Validate origin headers

### Client-Side Security

**Vue Templates:**
- **XSS prevention** via Vue's automatic escaping (`{{ }}` is safe)
- **Never use `v-html`** with user-generated content
- **Validate forms** client-side before submission (UX)
- **Re-validate server-side** (security)

**Sensitive Data:**
- **No API keys in JavaScript** - handle auth server-side
- **No secrets in localStorage/sessionStorage**
- **No sensitive data in URL parameters**

### API Communication
- **HTTPS only** in production (enforce with HSTS headers)
- **CORS** configured restrictively on FastAPI backend
- **API key authentication** via HTTP-only cookies or headers (not JavaScript-accessible)
- **Rate limiting** on API endpoints (backend responsibility)
- **Content Security Policy (CSP)** headers to prevent XSS

**Example CSP Header:**
```python
# In app/main.py
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://unpkg.com 'unsafe-inline'; "
        "style-src 'self' https://unpkg.com 'unsafe-inline';"
    )
    return response
```

---

## 14. Testing Strategy

### Server-Side Template Tests (pytest)

**Test route handlers and template rendering:**
```python
# In tests/test_web_routes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_dashboard_loads():
    """Test dashboard page renders."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Bandicoot RMAB" in response.content
    assert b"dashboard" in response.content

def test_model_page_before_training():
    """Test model page shows 'not trained' message."""
    response = client.get("/model")
    assert response.status_code == 200
    assert b"Model not yet trained" in response.content or b"No clusters" in response.content

def test_settings_page_loads():
    """Test settings page renders with defaults."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Settings" in response.content
    assert b"Number of Clusters" in response.content
```

### JavaScript Unit Tests (Optional - pytest-js or Jest)

**Test utility functions in `/static/js/utils.js`:**
```javascript
// tests/test_utils.js (if we add Jest later)
import { formatDate, exportToCSV } from '../app/static/js/utils.js';

test('formatDate formats ISO string correctly', () => {
  expect(formatDate('2025-11-23T10:30:00Z')).toBe('Nov 23, 2025');
});

test('exportToCSV generates valid CSV', () => {
  const data = [{ id: 1, name: 'Test' }];
  const csv = exportToCSV(data);
  expect(csv).toContain('id,name');
  expect(csv).toContain('1,Test');
});
```

### E2E Tests (Playwright - Recommended for MVP)

**Test full user workflows:**
```python
# tests/test_e2e.py (using Playwright with Python)
from playwright.sync_api import sync_playwright

def test_recommendation_workflow():
    """Test generating recommendations end-to-end."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate to dashboard
        page.goto("http://localhost:8000/")
        assert "Bandicoot" in page.title()

        # Train model first
        page.goto("http://localhost:8000/model")
        page.click("text=Retrain Model")
        page.wait_for_selector("text=Training complete", timeout=30000)

        # Generate recommendations
        page.goto("http://localhost:8000/")
        page.fill("input[name='budget']", "10")
        page.click("text=Generate")
        page.wait_for_selector(".caregiver-card")

        # Verify recommendations appear
        cards = page.query_selector_all(".caregiver-card")
        assert len(cards) == 10

        browser.close()
```

### Manual Testing Checklist (MVP Priority)

**For each page:**
- [ ] Page loads without errors (check browser console)
- [ ] Mobile responsive (test on phone/tablet)
- [ ] Forms submit correctly
- [ ] Error messages display on API failures
- [ ] Loading states show during async operations
- [ ] Links navigate correctly

**Cross-browser testing:**
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Mobile Chrome (Android)

**For MVP:** Focus on E2E tests and manual testing. Unit tests can be added later as needed.

---

## 15. Future Enhancements (Phase 2+)

### Dashboard Improvements
- 📊 **Charts/Graphs:** Visualize recommendation trends over time (could use Chart.js via CDN)
- 🔄 **Real-time updates:** WebSocket for live recommendation updates
- 🔍 **Advanced filters:** Multi-select, date ranges, custom queries
- 📱 **PWA:** Install as mobile app, offline support
  - ⚠️ **Note:** PWA requires service workers and build process (would need to add Vite/Webpack)
  - Alternative: Keep MPA and use browser "Add to Home Screen" for basic app-like experience

### Caregiver Management
- 👤 **Caregiver profiles:** Detailed view with history (new route: `GET /caregiver/{id}`)
- 📝 **Notes:** Add notes to caregivers (reason for contact, outcome)
- 📞 **Click-to-call:** Direct integration with phone dialer (`<a href="tel:+1234567890">`)

### Analytics
- 📈 **Engagement metrics:** Track intervention outcomes (new page: `GET /analytics`)
- 🎯 **A/B test dashboard:** Compare treatment vs. control groups
- 📊 **Cluster insights:** Deep dive into cluster behavior

### Admin Features
- 👥 **User management:** Multi-user access, role-based permissions
- 📅 **Scheduled retraining:** Auto-retrain on schedule (backend cron job)
- 🔔 **Notifications:** Email/SMS alerts for system events
- 📜 **Audit log:** Track who made what changes (new page: `GET /audit`)

---

## 16. Open Questions

1. **Authentication UI:**
   - Do we need login page or rely on API key?
   - → **Decision:** Start with API key only, add login later if needed

2. **Polling frequency:**
   - How often to refresh recommendations?
   - → **Decision:** Manual refresh for MVP, add auto-refresh in Phase 2

3. **Mobile app:**
   - Native app or PWA?
   - → **Decision:** Responsive web app for MVP, evaluate PWA later

4. **Offline support:**
   - Should UI work offline?
   - → **Decision:** Not for MVP, requires service workers

5. **Localization:**
   - Support multiple languages?
   - → **Decision:** English only for MVP

---

## 17. Success Criteria

### MVP Launch Criteria
- ✅ UI loads in < 2 seconds on 3G
- ✅ All 3 pages functional (Dashboard, Model, Settings)
- ✅ Mobile-friendly (works on phones/tablets)
- ✅ Can generate and export recommendations
- ✅ Can trigger model retraining
- ✅ No console errors or warnings

### User Acceptance
- ✅ Program manager can generate daily recommendations in < 30 seconds
- ✅ Health worker can view and export list on mobile device
- ✅ Admin can retrain model without technical knowledge

---

## 18. Implementation Plan

### Phase 1: Setup & Base Template (2-3 days)
- [ ] Create `app/templates/` and `app/static/` directories
- [ ] Implement `base.html` with header, footer, navigation
- [ ] Add PicoCSS and Vue 3 via CDN to base template
- [ ] Create `app/web/routes.py` with route handlers
- [ ] Mount web routes and static files in `app/main.py`
- [ ] Create basic error template (`error.html`)
- [ ] Test: All routes return 200 and render base layout
- [ ] **Milestone:** Basic MPA structure working

### Phase 2: Dashboard Page (3-4 days)
- [ ] Create `templates/dashboard.html` extending base
- [ ] Implement route handler: `GET /` → dashboard template
- [ ] Add server-side data: health status, recent recommendations
- [ ] Build inline Vue instance for recommendation generation
- [ ] Implement "Generate Recommendations" form with AJAX
- [ ] Add caregiver list rendering with Vue
- [ ] Implement CSV export functionality (client-side JS)
- [ ] Add loading states and error handling
- [ ] Test: Can generate and view recommendations
- [ ] **Milestone:** Functional recommendation workflow

### Phase 3: Model Info Page (2-3 days)
- [ ] Create `templates/model.html` extending base
- [ ] Implement route handler: `GET /model` → model template
- [ ] Add server-side data: cluster summary, training metadata
- [ ] Render cluster summary table with Jinja2
- [ ] Add inline Vue instance for retrain button
- [ ] Implement retrain functionality with AJAX
- [ ] Add loading states for training operation
- [ ] Test: Can view model info and trigger retraining
- [ ] **Milestone:** Model management working

### Phase 4: Settings Page (2-3 days)
- [ ] Create `templates/settings.html` extending base
- [ ] Implement route handlers: `GET /settings` and `POST /settings`
- [ ] Render settings form with current config values
- [ ] Add inline Vue instance for form validation
- [ ] Implement form submission (POST with page reload)
- [ ] Add success/error messages after save
- [ ] Test: Can view and update settings
- [ ] **Milestone:** All pages complete

### Phase 5: Polish & Testing (2-3 days)
- [ ] Mobile responsiveness testing (phone/tablet)
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Add custom CSS for branding (`static/css/custom.css`)
- [ ] Extract shared JS utilities to `static/js/utils.js`
- [ ] Write E2E tests with Playwright (optional)
- [ ] Write template rendering tests with pytest
- [ ] Fix console errors and warnings
- [ ] Add CSP headers and security middleware
- [ ] Test: All success criteria met
- [ ] **Milestone:** Production-ready UI

### Phase 6: Deploy (1 day)
- [ ] Update `Dockerfile` to include templates and static files
- [ ] Test Docker build locally
- [ ] Deploy to Cloud Run (or target platform)
- [ ] Verify all routes work in production
- [ ] Test API + UI integration end-to-end
- [ ] **Milestone:** MVP UI live in production

**Total estimated time:** 12-17 days (2.5-3.5 weeks)

**Dependencies:**
- FastAPI service layer must be complete
- API endpoints must be functional and tested
- Docker deployment infrastructure ready

---

## Appendix A: Color Palette

**Primary Colors:**
- Primary: `#3B82F6` (Blue - actions, links)
- Success: `#10B981` (Green - healthy, completed)
- Warning: `#F59E0B` (Amber - at-risk caregivers)
- Danger: `#EF4444` (Red - errors, unresponsive)

**Neutral Colors:**
- Background: `#FFFFFF` (White)
- Surface: `#F9FAFB` (Light gray)
- Border: `#E5E7EB` (Gray)
- Text: `#111827` (Near black)

---

## Appendix B: Typography

**Font Family:** System font stack
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
             Roboto, "Helvetica Neue", Arial, sans-serif;
```

**Font Sizes:**
- Heading 1: 2rem (32px)
- Heading 2: 1.5rem (24px)
- Body: 1rem (16px)
- Small: 0.875rem (14px)

---

**Document Owner:** Frontend Team
**Reviewers:** Product, Design, Backend
**Next Review:** After MVP UI deployment
