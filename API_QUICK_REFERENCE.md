# API Quick Reference Guide

## Quick Links to APIs

### Analytics APIs

#### 1. Disease Trends
Returns disease case counts with trend scores over time period
```
GET /api/disease-trends/?days=30
```
**Parameters:**
- `days`: 7, 14, 30 (default: 30)

**Returns:** List of diseases sorted by trend score

---

#### 2. Time Series
Daily case counts for disease trend visualization
```
GET /api/disease-trends/timeseries/?days=7&disease=Flu
```
**Parameters:**
- `days`: 7, 14, 30 (default: 30)
- `disease`: (optional) filter by disease name

**Returns:** Chronologically ordered daily data

---

#### 3. Medicine Usage
Medicine consumption metrics per disease
```
GET /api/medicine-usage/?days=30
```
**Parameters:**
- `days`: 7, 14, 30 (default: 30)

**Returns:** Drug usage statistics with calculated averages

---

#### 4. Spike Detection
Identify unusual disease outbursts
```
GET /api/spike-detection/?days=8&all=false
```
**Parameters:**
- `days`: Baseline window (minimum 8, default: 8)
- `all`: true/false to show all or only spikes (default: false)

**Returns:** Detected spikes with statistical details

---

#### 5. Restock Suggestions
Medicine inventory recommendations
```
GET /api/restock-suggestions/?days=30
```
**Parameters:**
- `days`: 7, 14, 30 (default: 30)

**Returns:** Sorted by status (critical → low → sufficient)

---

#### 6. District Restock
District-level inventory analysis
```
GET /api/district-restock/
GET /api/district-restock/?district=Chennai&days=30
```
**Parameters:**
- `district`: (optional) specific district name
- `days`: 7, 14, 30 (default: 30)

**Returns:** Districts list OR detailed restock data

---

### Export APIs

#### Export Disease Trends
```
GET /api/export/disease-trends/?days=30
```
Returns CSV file download

---

#### Export Spike Alerts
```
GET /api/export/spike-alerts/?days=8
```
Returns CSV file download

---

#### Export Restock
```
GET /api/export/restock/?days=30
```
Returns detailed CSV with DrugMaster level detail

---

#### Export Combined Report
```
GET /api/export-report/?days=30
```
Returns combined CSV with all three sections

---

### CRUD APIs

#### List Records
```
GET /api/crud/{model}/?page=1&page_size=20&search=keyword
```
**Models:** clinics, doctors, patients, diseases, appointments, drugs, prescriptions, prescription-lines

---

#### Get Single Record
```
GET /api/crud/{model}/{id}/
```

---

#### Create Record
```
POST /api/crud/{model}/
```
**Body:** JSON with model fields

---

#### Update Record
```
PUT /api/crud/{model}/{id}/
PATCH /api/crud/{model}/{id}/
```
**Body:** JSON with updated fields

---

#### Delete Record
```
DELETE /api/crud/{model}/{id}/
```

---

#### Get Dropdown Options
```
GET /api/crud/dropdowns/
```
Returns available options for form dropdowns

---

## Response Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 404 | Not Found |
| 500 | Server Error |

---

## Authentication

No authentication currently required. In production:
- Implement token-based authentication
- Use Django REST Framework TokenAuthentication
- Add permissions classes to views

---

## Rate Limiting

Not currently implemented. In production:
- Add rate limiting per IP
- Implement throttling for public APIs
- Use Django REST Framework throttling

---

## Caching

Not currently implemented. Consider:
- Cache disease trend results (5 min TTL)
- Cache spike detection results (1 hour TTL)
- Cache export data if queries are expensive

---

## Error Handling

All endpoints return structured error responses:

```json
{
  "detail": "Specific error message"
}
```

Or for validation errors:

```json
{
  "field_name": ["Error message"]
}
```

---

## Common Filters

All list endpoints support:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `search`: Text search across string fields

Example:
```
GET /api/crud/diseases/?page=2&page_size=10&search=Flu
```

---

## Frontend Integration

The React frontend uses these endpoints:
- `api.js`: Centralized API client
- All URLs configured with `BASE = 'http://localhost:8000/api'`
- Requests include common error handling
- Uses axios for HTTP requests

---

## Testing APIs with curl

### Get Disease Trends
```bash
curl "http://localhost:8000/api/disease-trends/?days=7"
```

### Get Specific Disease Time Series
```bash
curl "http://localhost:8000/api/disease-trends/timeseries/?days=7&disease=Flu"
```

### Get Spike Alerts (show all)
```bash
curl "http://localhost:8000/api/spike-detection/?days=8&all=true"
```

### Create New Disease
```bash
curl -X POST "http://localhost:8000/api/crud/diseases/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Disease",
    "season": "All",
    "category": "Viral",
    "severity": 1,
    "is_active": true
  }'
```

### Export Report
```bash
curl -o report.csv "http://localhost:8000/api/export-report/?days=30"
```

---

## Performance Tips

1. **Use specific date ranges:** `?days=7` is faster than `?days=30`
2. **Limit result sets:** Use pagination `?page_size=20`
3. **Filter when possible:** `?search=keyword` reduces data transfer
4. **Cache JSON responses:** Client-side caching recommended
5. **Batch API calls:** Multiple queries should be combined if possible

---

## Troubleshooting

### 400 Bad Request
Check query parameters are valid (days must be positive integer)

### 404 Not Found
Verify endpoint URL and resource ID are correct

### 500 Server Error
Check Django logs: `python manage.py runserver --verbosity=2`

### Empty Results
Verify date range contains data (check latest appointment date)

### CORS Issues
Check `CORS_ALLOWED_ORIGINS` in `.env` file

---

## Data Field Reference

### Disease Fields
- `id`: UUID
- `name`: Disease name
- `season`: "Summer", "Monsoon", "Winter", "All"
- `category`: Classification
- `severity`: 1-5 scale
- `is_active`: Boolean
- `created_at`: Timestamp

### Appointment Fields
- `id`: UUID
- `appointment_datetime`: ISO timestamp
- `appointment_status`: Status string
- `disease`: FK to Disease
- `clinic`: FK to Clinic
- `doctor`: FK to Doctor
- `patient`: FK to Patient
- `op_number`: Unique appointment number

### DrugMaster Fields
- `id`: UUID
- `drug_name`: Name
- `generic_name`: Chemical name
- `drug_strength`: Dosage strength
- `dosage_type`: "Tablet", "Syrup", etc.
- `current_stock`: Integer quantity
- `clinic`: FK to Clinic

### PrescriptionLine Fields
- `id`: UUID
- `drug`: FK to DrugMaster
- `disease`: FK to Disease
- `quantity`: Integer
- `duration`: Treatment duration
- `instructions`: Admin instructions
- `prescription`: FK to Prescription

---

## Scaling Considerations

For large datasets:

1. **Implement database indexes** on:
   - appointment_datetime
   - disease_id
   - clinic_id
   - drug_name

2. **Use database views** for complex aggregations

3. **Implement caching layer** (Redis recommended)

4. **Use Celery** for heavy calculations:
   - Pre-compute trends periodically
   - Generate export files asynchronously
   - Schedule spike detection

5. **Database optimization**:
   - Partition appointments by date
   - Archive old data
   - Monitor query performance

---

## Security Checklist

- [ ] Enable CSRF protection on POST/PUT/DELETE
- [ ] Implement authentication/authorization
- [ ] Validate all user inputs
- [ ] Use HTTPS in production
- [ ] Implement rate limiting
- [ ] Log security events
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Use environment variables for secrets
- [ ] Implement request signing if needed
