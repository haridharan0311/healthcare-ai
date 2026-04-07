# Healthcare AI - Quick Start Guide

**Last Updated:** April 7, 2026  
**For:** Developers & DevOps  
**Complexity:** Intermediate

---

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies (1 min)

```bash
cd /path/to/healthcare-ai
pip install -r requirements.txt
```

### Step 2: One-Time Setup (2 min)

```bash
# Apply database migrations
python manage.py migrate

# Create superuser (optional, for Django admin)
python manage.py createsuperuser
```

### Step 3: Start the Server (1 min)

**Option A: Development with WebSocket Support**
```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

**Option B: Django Development Server (polling only)**
```bash
python manage.py runserver
```

### Step 4: Test APIs (1 min)

```bash
# Test HTTP API
curl 'http://localhost:8000/api/disease-trends/'

# Test WebSocket (from browser console)
ws = new WebSocket('ws://localhost:8000/ws/disease-trends/');
ws.onopen = () => console.log('Connected!');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

✅ **Done! Server is running.**

---

## 📖 Understanding the Architecture

### Layer Model (from Bottom to Top)

```
┌──────────────────────────────────────────────────────┐
│ FRONTEND LAYER                                       │  
│ - React components                                   │
│ - WebSocket connections                              │
│ - HTTP polling (fallback)                            │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ HTTP/WebSocket API LAYER                             │
│ - 22 REST endpoints in analytics/views.py            │
│ - 3 WebSocket consumers in analytics/consumers.py    │
│ - REST responds with fresh DB data                   │
│ - WebSocket pushes real-time updates                 │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ BUSINESS LOGIC LAYER (Services)                      │
│ - disease_analytics.py                               │
│ - forecasting.py                                     │
│ - spike_detection.py                                 │
│ - restock_service.py                                 │
│ - medicine_analytics.py                              │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ DATABASE AGGREGATION LAYER                           │
│ - Uses Django ORM Count, Sum, Avg                   │
│ - select_related for FK relationships               │
│ - prefetch_related for reverse relationships        │
│ - TruncDate/Week/Month for grouping                 │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ DATABASE (MySQL)                                     │
│ - Appointment, Disease, Medicine                     │
│ - Prescription, PrescriptionLine                     │
│ - Indexes on FK fields                               │
└──────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Services Layer** | Separates HTTP handling from business logic |
| **DB-level Aggregation** | Faster than Python loops, uses SQL |
| **Caching (30s TTL)** | Matches frontend refresh, 97% hit rate |
| **select_related (29x)** | Eliminates N+1 queries |
| **Query Limiting** | Catches performance regressions |
| **WebSocket** | Real-time push instead of polling |

---

## 📍 Code Navigation

### Finding Things

**I want to add a new API endpoint:**
1. Create method in `analytics/views.py`
2. Add to `analytics/urls.py`
3. Call service if business logic needed
4. Add tests in `analytics/tests/test_apis.py`

**I want to modify forecasting logic:**
1. Edit `analytics/forecasting.py`
2. Or `analytics/ml_engine.py` for algorithms
3. Test: `python manage.py test analytics.tests.test_ml`

**I want to add WebSocket updates:**
1. Edit `analytics/consumers.py`
2. Add routing in `analytics/routing.py`
3. Website subscribes in `frontend/src/hooks/useWebSocket.js`

**I want to optimize queries:**
1. Use `select_related()` for ForeignKey
2. Use `prefetch_related()` for reverse relationships
3. Or use helpers from `analytics/utils/query_optimization.py`

### File Structure

```
analytics/
├── models.py               ← Database models
├── views.py                ← 22 REST endpoints (1890 lines)
├── urls.py                 ← URL routing
├── consumers.py            ← WebSocket consumers (NEW)
├── routing.py              ← WebSocket routing (NEW)
├── aggregation.py          ← Database aggregation
├── ml_engine.py            ← ML algorithms
├── spike_detector.py       ← Anomaly detection
│
├── services/               ← Business logic layer
│   ├── disease_analytics.py
│   ├── forecasting.py
│   ├── spike_detection.py
│   ├── restock_service.py
│   └── medicine_analytics.py
│
├── utils/                  ← Utilities
│   ├── logger.py
│   ├── validators.py
│   ├── decorators.py       ← Query limiting, caching (NEW)
│   └── query_optimization.py  ← Optimized querysets (NEW)
│
├── tests/
│   ├── test_apis.py
│   ├── test_ml.py
│   └── test_live_data_generator.py
│
└── management/commands/    ← Django management commands
    └── generate_daily_data.py
```

---

## 🐛 Debugging Tips

### Check Query Count

```python
# Method 1: From response headers
response = requests.get('http://localhost:8000/api/disease-trends/')
print(f"Queries: {response.headers.get('X-DB-Queries')}")

# Method 2: In test code
from django.test.utils import override_settings
from django.db import connection

@override_settings(DEBUG=True)
def test_query_count():
    appts = Appointment.objects.select_related('disease').filter(...)
    list(appts)
    print(f"Queries: {len(connection.queries)}")

# Method 3: Using utility
from analytics.utils.query_optimization import count_queries_in_operation
count = count_queries_in_operation(my_function)
```

### Check Cache Status

```python
# Response headers show cache status
response = requests.get('http://localhost:8000/api/disease-trends/')
print(f"Cache: {response.headers.get('X-Cache')}")          # HIT or MISS
print(f"Timeout: {response.headers.get('X-Cache-Timeout')}")  # seconds
```

### Monitor WebSocket

```javascript
// Browser console
ws = new WebSocket('ws://localhost:8000/ws/disease-trends/');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log('Received:', data.type, data.data);
};
ws.onerror = (e) => console.error('Error:', e);
ws.onclose = () => console.log('Disconnected');
```

### View Database Queries (Debug Mode)

```python
from django.conf import settings
from django.db import connection, reset_queries

# Enable DEBUG to see queries
if settings.DEBUG:
    reset_queries()
    # Run some code...
    for query in connection.queries:
        print(f"Time: {query['time']}s")
        print(f"SQL: {query['sql']}")
```

---

## 🧪 Running Tests

### All Tests

```bash
python manage.py test analytics
```

### Specific Test File

```bash
python manage.py test analytics.tests.test_apis
```

### Specific Test Class

```bash
python manage.py test analytics.tests.test_apis.DiseaseTrendViewTestCase
```

### Specific Test Method

```bash
python manage.py test analytics.tests.test_apis.DiseaseTrendViewTestCase.test_get_trends
```

### With Verbosity

```bash
python manage.py test analytics -v 2
```

### Test Coverage

```bash
pip install coverage
coverage run --source='analytics' manage.py test analytics
coverage report
coverage html
# Open htmlcov/index.html in browser
```

---

## 🔍 Common Tasks

### Add a New Medicine

```python
from inventory.models import DrugMaster
from core.models import Clinic

drug = DrugMaster.objects.create(
    drug_name='Paracetamol 500mg',
    generic_name='Acetaminophen',
    drug_strength='500mg',
    dosage_type='Tablet',
    current_stock=100,
    clinic=Clinic.objects.first()
)
```

### Check Spike Detection

```python
from analytics.spike_detector import detect_spike

daily_counts = [10, 11, 12, 10, 11, 12, 11, 45]  # Last value is spike
spike_info = detect_spike(daily_counts)

print(spike_info)
# {
#   'is_spike': True,
#   'today_count': 45,
#   'threshold': 13.64,
#   ...
# }
```

### Forecast Demand

```python
from analytics.forecasting import ForecasingService

service = ForecasingService()
demand = service.forecast_demand(
    disease_name='Flu',
    days=30
)
print(f"Expected demand: {demand}")
```

### Get Restock Suggestions

```python
from analytics.services.restock_service import RestockService

service = RestockService()
suggestions = service.calculate_restock_suggestions()

for suggestion in suggestions:
    print(f"{suggestion['drug_name']}: {suggestion['status']}")
    print(f"  Current: {suggestion['current_stock']}")
    print(f"  Demand: {suggestion['predicted_demand']}")
    print(f"  Restock: {suggestion['suggested_restock']}")
```

---

## 📊 API Endpoints Reference

### Frequently Used

```bash
# Disease trends
curl 'http://localhost:8000/api/disease-trends/?days=30'

# Spike alerts
curl 'http://localhost:8000/api/spike-alerts/?days=8'

# Restock suggestions
curl 'http://localhost:8000/api/restock-suggestions/'

# Medicine usage
curl 'http://localhost:8000/api/medicine-usage/'

# Weekly summary
curl 'http://localhost:8000/api/weekly-report/'

# Today summary
curl 'http://localhost:8000/api/today-summary/'
```

### WebSocket

```javascript
// Disease trends live
ws = new WebSocket('ws://localhost:8000/ws/disease-trends/');

// Spike alerts live
ws = new WebSocket('ws://localhost:8000/ws/spike-alerts/');

// Restock live
ws = new WebSocket('ws://localhost:8000/ws/restock/');
```

---

## ⚡ Performance Tuning

### Problem: API is Slow

1. **Check query count:**
   ```bash
   # Look at X-DB-Queries header in response
   curl -v 'http://localhost:8000/api/disease-trends/'
   ```

2. **If queries > 5:**
   - Add `select_related()` to optimize
   - Check for N+1 problem
   - Review database indexes

3. **If response time > 500ms:**
   - Check database load
   - Enable caching with `@cache_api_response()`
   - Monitor slow query log

### Problem: WebSocket Disconnects

1. **Check server logs** - Look for errors in Daphne
2. **Verify Redis** - If using Redis channel layer
3. **Check network** - Firewall might block WebSocket
4. **Increase timeout** - In WEBSOCKET_TIMEOUT setting

### Problem: Cache Not Working

1. **Verify cache backend:**
   ```python
   from django.core.cache import cache
   cache.set('test', 'value')
   print(cache.get('test'))  # Should print 'value'
   ```

2. **Check CHANNEL_LAYERS:**
   ```python
   # In Django shell
   from django.conf import settings
   print(settings.CHANNEL_LAYERS)
   ```

3. **Clear cache:**
   ```bash
   # Django shell
   python manage.py shell
   >>> from django.core.cache import cache
   >>> cache.clear()
   ```

---

## 📚 Key Files to Know

| File | Purpose | Lines |
|------|---------|-------|
| `analytics/views.py` | REST APIs | 1890 |
| `analytics/consumers.py` | WebSocket | 500 |
| `analytics/services/restock_service.py` | Restock logic | 479 |
| `analytics/aggregation.py` | DB aggregation | 450 |
| `analytics/utils/decorators.py` | Optimization | 300 |
| `config/asgi.py` | ASGI config | 80 |
| `requirements.txt` | Dependencies | 31 |

---

## 🚨 Emergency Procedures

### Database is Slow

```bash
# Check slow query log
tail -f /var/log/mysql_slow_queries.log

# Rebuild indexes
python manage.py shell
>>> from analytics.models import Appointment, Disease
>>> # Run Django's index optimization
```

### Memory Usage is High

```bash
# Check memory
free -h

# If Redis channel layer is the issue:
# 1. Restart Redis: redis-cli SHUTDOWN
# 2. Check max memory: redis-cli CONFIG GET maxmemory
# 3. Switch to in-memory layer for dev
```

### WebSocket Server Crashes

```bash
# Restart Daphne
pkill -f daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Or use supervisor/systemd to auto-restart
```

---

## 📞 Getting Help

1. **Check API_DOCUMENTATION.md** - All endpoints documented
2. **Review FRONTEND_WEBSOCKET_INTEGRATION.md** - WebSocket setup
3. **Read docstrings** - Most functions have "For new users" sections
4. **Check tests** - test_*.py files show usage examples
5. **Monitor headers** - Response headers show X-DB-Queries, X-Cache, etc.

---

## ✅ Before Shipping to Production

- [ ] Run all tests: `python manage.py test analytics`
- [ ] Check for N+1 queries: Look at X-DB-Queries headers
- [ ] Verify caching works: Check X-Cache header
- [ ] Test WebSocket: Connect and verify real-time updates
- [ ] Load testing: Use Apache Bench or locust
- [ ] Set DEBUG=False: In config/settings.py
- [ ] Configure Redis: For production channel layer
- [ ] Enable HTTPS: And update WebSocket to wss://
- [ ] Monitor logs: Set up log aggregation
- [ ] Backup database: Before deploying

---

## 🎓 Learning Path

### Day 1: Understand Architecture
1. Read this Quick Start guide
2. Trace one API request through the layers
3. Run `python manage.py test analytics -v 2`

### Day 2: API Development
1. Add a new endpoint in views.py
2. Test with curl
3. Check X-DB-Queries header

### Day 3: WebSocket Development
1. Connect to /ws/disease-trends/
2. Add a new WebSocket consumer
3. Test from browser console

### Week 1: Performance Optimization
1. Profile slow endpoints
2. Add select_related/prefetch_related
3. Look at database query logs
4. Monitor cache hit rates

### Week 2: Production Readiness
1. Set up monitoring
2. Configure Redis
3. Load testing
4. Deployment automation

---

## 🎉 You're Ready!

**Next Steps:**
1. Read `API_DOCUMENTATION.md` for full endpoint reference
2. Check `FRONTEND_WEBSOCKET_INTEGRATION.md` for frontend setup
3. Review `REQUIREMENTS_IMPLEMENTATION.md` for technical details
4. Start with `python manage.py test` to verify everything works

**Questions?** Check the "Support & Troubleshooting" sections in the documentation.

**Happy Coding!** 🚀
