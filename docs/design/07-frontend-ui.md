# Frontend UI Design: Bandicoot RMAB Dashboard

**Version:** 1.0
**Status:** Draft
**Last Updated:** 2025-11-23

---

## 1. Overview

### Purpose
Build a simple, static Vue.js dashboard served from FastAPI to provide Suvita program managers and health workers with:
- Real-time visibility into RMAB recommendations
- Model performance monitoring
- Basic system administration capabilities

### Goals
- **Simplicity**: Single-page application, minimal dependencies
- **Static deployment**: Pre-built Vue app served as static files from FastAPI
- **Mobile-friendly**: Responsive design for field workers on phones/tablets
- **Fast iteration**: No separate backend needed, uses existing FastAPI endpoints
- **Self-contained**: All assets bundled, works offline after initial load

### Non-Goals (Out of Scope for MVP)
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

## 3. Page Structure

### 3.1 Main Dashboard (Home)

**Route:** `/`

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

**Components:**
- `Header` - App title, health indicator, admin actions
- `QuickStats` - 4 metric cards
- `RecommendationPanel` - Form to generate recommendations
- `RecommendationList` - Scrollable list of caregivers
- `CaregiverCard` - Individual caregiver item

---

### 3.2 Model Info Page

**Route:** `/model`

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

**Components:**
- `ModelStats` - Training information
- `ClusterTable` - Table of cluster summaries
- `AdminActions` - Retrain/export buttons

---

### 3.3 Settings Page (Admin)

**Route:** `/settings`

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

**Components:**
- `SettingsForm` - Editable parameter inputs
- `SaveActions` - Save/reset buttons

---

## 4. Component Architecture

### Component Tree
```
App
├── Header
│   ├── AppTitle
│   ├── HealthIndicator
│   └── AdminMenu
├── Router
│   ├── DashboardPage
│   │   ├── QuickStats
│   │   │   └── StatCard (×4)
│   │   ├── RecommendationPanel
│   │   │   ├── BudgetInput
│   │   │   ├── FilterBar
│   │   │   └── ActionButtons
│   │   └── RecommendationList
│   │       └── CaregiverCard (×N)
│   ├── ModelPage
│   │   ├── ModelStats
│   │   ├── ClusterTable
│   │   └── AdminActions
│   └── SettingsPage
│       ├── SettingsForm
│       └── SaveActions
└── Footer
```

### Key Components Detail

#### `Header.vue`
**Props:** None
**State:** `modelHealth` (from API)
**Methods:** `checkHealth()`, `triggerRetrain()`

**Template:**
```vue
<template>
  <header class="app-header">
    <h1>🐾 Bandicoot RMAB</h1>
    <HealthIndicator :status="modelHealth" />
    <button @click="triggerRetrain" class="btn-retrain">
      Retrain Model
    </button>
  </header>
</template>
```

---

#### `QuickStats.vue`
**Props:** None
**State:** `stats` (from API `/health`)
**Computed:** `formattedStats`

**Displays:**
- Total active caregivers
- Today's recommendation budget
- Average priority score
- Model version

---

#### `RecommendationPanel.vue`
**Props:** None
**State:**
- `budget: number = 50`
- `filterDistrict: string = 'All'`
- `filterState: string = 'All'`
- `loading: boolean = false`

**Methods:**
- `generateRecommendations()` - POST to `/recommend`
- `exportCSV()` - Download recommendations as CSV
- `loadMore()` - Pagination

**Emits:** `recommendations-loaded`

---

#### `CaregiverCard.vue`
**Props:**
- `caregiver: Object` - {id, priority, state, cluster, reason}

**Methods:**
- `markContacted()` - POST to `/update_state`
- `viewDetails()` - Navigate to detail page (future)

**Template:**
```vue
<template>
  <div class="caregiver-card" :class="stateClass">
    <div class="card-header">
      <span class="id">{{ caregiver.caregiver_id }}</span>
      <span class="priority">{{ caregiver.priority_score.toFixed(2) }}</span>
      <span class="badge">{{ stateBadge }}</span>
    </div>
    <div class="card-body">
      <p class="cluster">Cluster {{ caregiver.cluster_id }}</p>
      <p class="reason">{{ caregiver.reason }}</p>
    </div>
    <div class="card-actions">
      <button @click="markContacted" class="btn-primary">
        Mark Contacted
      </button>
      <button @click="viewDetails" class="btn-secondary">
        Details
      </button>
    </div>
  </div>
</template>
```

---

## 5. Technology Stack

### Frontend Framework
**Vue 3** (Composition API)
- **Why:** Lightweight, gentle learning curve, excellent docs
- **Alternative considered:** React (more complex, larger bundle)

### Build Tool
**Vite**
- **Why:** Fast dev server, optimized production builds
- **Output:** Static HTML/CSS/JS files

### UI Library
**PicoCSS** (classless CSS framework)
- **Why:** Minimal, semantic HTML, no class names needed
- **Alternative:** Tailwind (more verbose, larger bundle)
- **Size:** ~10KB gzipped

### State Management
**Vue 3 Composition API** (no Vuex/Pinia needed for MVP)
- **Why:** Simple, built-in, sufficient for small app
- **State:** Kept in composables (`useRecommendations`, `useModelHealth`)

### HTTP Client
**Fetch API** (native)
- **Why:** No external dependency, modern browsers only
- **Wrapper:** Simple `api.js` utility

### Routing
**Vue Router 4**
- **Routes:** `/`, `/model`, `/settings`

### Icons
**Unicode Emojis** (no icon library)
- **Why:** Zero dependencies, universal support
- **Examples:** 🐾 📊 ⚙️ ✓ ⚠️

---

## 6. File Structure

```
frontend/                      # Vue app source
├── public/
│   ├── favicon.ico
│   └── robots.txt
├── src/
│   ├── main.js               # App entry point
│   ├── App.vue               # Root component
│   ├── router/
│   │   └── index.js          # Route configuration
│   ├── views/
│   │   ├── DashboardPage.vue
│   │   ├── ModelPage.vue
│   │   └── SettingsPage.vue
│   ├── components/
│   │   ├── Header.vue
│   │   ├── Footer.vue
│   │   ├── QuickStats.vue
│   │   ├── RecommendationPanel.vue
│   │   ├── RecommendationList.vue
│   │   ├── CaregiverCard.vue
│   │   ├── ModelStats.vue
│   │   ├── ClusterTable.vue
│   │   └── SettingsForm.vue
│   ├── composables/
│   │   ├── useApi.js         # API client wrapper
│   │   ├── useRecommendations.js
│   │   └── useModelHealth.js
│   ├── assets/
│   │   ├── main.css          # Global styles
│   │   └── logo.svg
│   └── utils/
│       ├── format.js         # Date/number formatting
│       └── export.js         # CSV export logic
├── package.json
├── vite.config.js
└── README.md

dist/                          # Production build output
└── (served by FastAPI as static files)
```

---

## 7. API Integration

### API Client (`composables/useApi.js`)

```javascript
const API_BASE = '/api/v1';

export function useApi() {
  const get = async (endpoint) => {
    const response = await fetch(`${API_BASE}${endpoint}`);
    if (!response.ok) throw new Error(response.statusText);
    return response.json();
  };

  const post = async (endpoint, data) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(response.statusText);
    return response.json();
  };

  return { get, post };
}
```

### Endpoint Usage

| UI Action | API Endpoint | Method |
|-----------|--------------|--------|
| Load health status | `/health` | GET |
| Generate recommendations | `/recommend` | POST |
| Train model | `/train_clusters` | POST |
| Precompute indices | `/precompute_indices` | POST |
| Update caregiver state | `/update_state` | POST |

---

## 8. Serving from FastAPI

### Static File Serving

**In `app/main.py`:**
```python
from fastapi.staticfiles import StaticFiles

# Mount Vue app
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

**Route Priority:**
1. API routes (`/api/v1/*`) - handled first
2. Static files (`/*`) - fallback to Vue app

**Build & Deploy Workflow:**
```bash
# 1. Build Vue app
cd frontend
npm run build  # → outputs to dist/

# 2. Deploy FastAPI (includes dist/ folder)
docker build -t bandicoot-api .
docker run -p 8080:8080 bandicoot-api

# 3. Access UI
open http://localhost:8080
```

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

**Terminal 1 (Backend):**
```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev  # Vite dev server on port 5173
```

**Frontend proxies API calls to backend:**
```javascript
// vite.config.js
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
```

### Production Build
```bash
cd frontend
npm run build
# Output: dist/ folder ready to serve
```

---

## 11. Error Handling

### API Error Display
```vue
<template>
  <div v-if="error" class="alert alert-error">
    {{ error.message }}
    <button @click="retry">Retry</button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const error = ref(null);

async function loadData() {
  try {
    error.value = null;
    // API call...
  } catch (e) {
    error.value = { message: 'Failed to load data. Please try again.' };
  }
}
</script>
```

### Loading States
- Spinner during API calls
- Skeleton screens for lists
- Disabled buttons while processing

---

## 12. Performance Considerations

### Bundle Size Target
- **Total JS:** < 100KB gzipped
- **Total CSS:** < 20KB gzipped
- **Initial load:** < 2 seconds on 3G

### Optimizations
- Code splitting by route
- Lazy load components not in viewport
- Minify/compress assets in production
- Cache static assets (1 year TTL)

---

## 13. Security

### Client-Side
- **No sensitive data** in localStorage/sessionStorage
- **API key** passed via HTTP headers (not exposed in UI)
- **Input validation** on all forms
- **XSS prevention** via Vue's automatic escaping

### API Communication
- **HTTPS only** in production
- **CORS** configured on FastAPI backend
- **Rate limiting** on API endpoints (backend responsibility)

---

## 14. Testing Strategy

### Unit Tests (Vitest)
- Test composables (`useApi`, `useRecommendations`)
- Test utility functions (`format`, `export`)

### Component Tests (Vue Test Utils)
- Test `CaregiverCard` rendering
- Test `RecommendationPanel` form submission

### E2E Tests (Playwright - Optional)
- Test full recommendation workflow
- Test error handling

**For MVP:** Manual testing sufficient, automate later.

---

## 15. Future Enhancements (Phase 2+)

### Dashboard Improvements
- 📊 **Charts/Graphs:** Visualize recommendation trends over time
- 🔄 **Real-time updates:** WebSocket for live recommendation updates
- 🔍 **Advanced filters:** Multi-select, date ranges, custom queries
- 📱 **PWA:** Install as mobile app, offline support

### Caregiver Management
- 👤 **Caregiver profiles:** Detailed view with history
- 📝 **Notes:** Add notes to caregivers (reason for contact, outcome)
- 📞 **Click-to-call:** Direct integration with phone dialer

### Analytics
- 📈 **Engagement metrics:** Track intervention outcomes
- 🎯 **A/B test dashboard:** Compare treatment vs. control groups
- 📊 **Cluster insights:** Deep dive into cluster behavior

### Admin Features
- 👥 **User management:** Multi-user access, role-based permissions
- 📅 **Scheduled retraining:** Auto-retrain on schedule
- 🔔 **Notifications:** Email/SMS alerts for system events

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

### Week 1: Setup & Core Components
- [ ] Initialize Vite + Vue 3 project
- [ ] Set up router and basic layout
- [ ] Implement Header, Footer, navigation
- [ ] Build API client composable
- [ ] **Milestone:** App skeleton with routing

### Week 2: Dashboard Page
- [ ] Implement QuickStats component
- [ ] Build RecommendationPanel with form
- [ ] Create CaregiverCard component
- [ ] Implement CSV export
- [ ] **Milestone:** Functional recommendation workflow

### Week 3: Model & Settings Pages
- [ ] Build ModelPage with cluster table
- [ ] Implement SettingsPage with form
- [ ] Add retrain functionality
- [ ] **Milestone:** All pages complete

### Week 4: Polish & Deploy
- [ ] Mobile responsiveness testing
- [ ] Error handling and loading states
- [ ] Production build optimization
- [ ] Deploy with FastAPI
- [ ] **Milestone:** MVP UI live

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
