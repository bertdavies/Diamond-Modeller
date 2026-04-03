# Diamond Modeller API Reference

Base URL: `http://localhost:8000` (default)

## Diamonds

### Create Diamond

```
POST /create-diamond
Content-Type: application/x-www-form-urlencoded
```

| Field | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Unique name for the diamond |
| `notes` | string | No | Free-text notes |
| `color` | string | No | Hex colour (default `#4ecdc4`) |
| `adversary_indicators` | string | No | Newline-separated indicator values |
| `victimology_indicators` | string | No | Newline-separated indicator values |
| `capability_indicators` | string | No | Newline-separated indicator values |
| `infrastructure_indicators` | string | No | Newline-separated indicator values |

**Response:** HTML fragment (diamond list). Status 200.

### Get Diamond Summary

```
GET /diamonds/{diamond_id}
```

**Response (JSON):**

```json
{
  "id": 1,
  "label": "Recon",
  "notes": "...",
  "color": "#4ecdc4",
  "created_at": "2026-03-06T12:00:00",
  "updated_at": "2026-03-06T12:00:00"
}
```

### Get Diamond Details

```
GET /diamonds/{diamond_id}/details
```

**Response (JSON):**

```json
{
  "id": 1,
  "label": "Recon",
  "notes": "...",
  "color": "#4ecdc4",
  "created_at": "2026-03-06T12:00:00.000000",
  "updated_at": "2026-03-06T12:00:00.000000",
  "adversary_indicators": ["APT29", "Cozy Bear"],
  "victimology_indicators": ["ACME Corp"],
  "capability_indicators": ["LinkedIn scraping"],
  "infrastructure_indicators": ["cdn-update.com"]
}
```

### Get Diamond for Edit

```
GET /diamonds/{diamond_id}/edit
```

Same as details but indicator lists are newline-joined strings (for form pre-fill).

### List / Search Diamonds

```
GET /diamonds/?query=optional_search_term
```

**Response:** HTML fragment. For structured data use the export or graph endpoints.

### Update Diamond

```
PUT /diamonds/{diamond_id}
Content-Type: application/x-www-form-urlencoded
```

Same fields as create. **Response:** HTML fragment.

### Delete Diamond

```
DELETE /diamonds/{diamond_id}
```

**Response (JSON):**

```json
{
  "message": "Diamond deleted successfully",
  "deleted_id": 1
}
```

### Delete All Diamonds

```
DELETE /diamonds/remove-all/
```

**Response (JSON):**

```json
{
  "message": "All 5 diamonds removed successfully",
  "count": 5
}
```

## Links

### Create Manual Link

```
POST /links/
Content-Type: application/json
```

**Body:**

```json
{
  "src_diamond_id": 1,
  "dst_diamond_id": 2,
  "reason": "Shared C2 infrastructure"
}
```

**Response (JSON):**

```json
{ "message": "Manual link created successfully" }
```

### Regenerate Automatic Links

```
POST /regenerate-links
```

Rebuilds all automatic edges based on current indicator overlaps.

**Response (JSON):**

```json
{ "message": "All automatic links regenerated successfully" }
```

## Graph

### Get Graph Data

```
GET /graph
```

Returns Cytoscape-compatible JSON:

```json
{
  "elements": {
    "nodes": [
      { "data": { "id": "d1", "label": "Recon", "color": "#4ecdc4" } }
    ],
    "edges": [
      { "data": { "id": "e1", "source": "d1", "target": "d2", "label": "Adversary: APT29" } }
    ]
  }
}
```

## Export / Import

### Export Analysis

```
GET /api/export-analysis
```

**Response (JSON):**

```json
{
  "version": "1.1",
  "exported_at": "2026-03-06T12:00:00Z",
  "diamonds": [
    {
      "label": "Recon",
      "notes": "",
      "color": "#4ecdc4",
      "adversary_indicators": ["APT29"],
      "victimology_indicators": ["ACME Corp"],
      "capability_indicators": ["LinkedIn scraping"],
      "infrastructure_indicators": ["cdn-update.com"]
    }
  ],
  "edges": [
    {
      "src_label": "Recon",
      "dst_label": "Delivery",
      "reason": "Adversary: APT29",
      "is_manual": false
    }
  ]
}
```

### Import Analysis

```
POST /api/import-analysis
Content-Type: application/json
```

Send the same JSON structure returned by export. **Replaces all current data.**

**Response (JSON):**

```json
{
  "success": true,
  "imported_diamonds": 5,
  "imported_edges": 3
}
```

## Settings

### Set OpenAI API Key

```
POST /api/settings/openai-api-key
Content-Type: application/json
```

**Body:**

```json
{ "api_key": "sk-..." }
```

**Response (JSON):**

```json
{ "success": true, "message": "OpenAI API key updated and reloaded." }
```

### Check OpenAI API Key Status

```
GET /api/settings/openai-api-key
```

**Response (JSON):**

```json
{ "set": true }
```

## Hypothesis Generation

### Generate Hypotheses

```
POST /conduct-attribution
```

On success returns a PDF file (`Content-Type: application/pdf`) with `Content-Disposition: attachment`.

On failure returns JSON:

```json
{
  "success": false,
  "message": "Error description",
  "stdout": "",
  "stderr": "..."
}
```

## Error Format

All error responses follow FastAPI convention:

```json
{
  "detail": "Diamond not found"
}
```

Or for attribution/service errors:

```json
{
  "success": false,
  "message": "Error description"
}
```

HTTP status codes: `400` (bad request), `404` (not found), `500` (server error).
