require('dotenv').config();
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const { supabase } = require('./src/shared/supabase');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Fallback in-memory store in case SQL tables haven't been created yet in Supabase
const memoryFallback = {
  controls: JSON.parse(fs.readFileSync(path.join(__dirname, 'seed', 'controls.json'), 'utf8')),
  users: JSON.parse(fs.readFileSync(path.join(__dirname, 'seed', 'users.json'), 'utf8')),
  reviews: [],
  reviewControls: [],
  auditEvents: []
};

let usingSupabase = false;

function generateId(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`.toUpperCase();
}

async function recordAudit(entityType, entityId, action, actorId, metadata = {}) {
  const audit = {
    audit_id: generateId('AUDIT'),
    entity_type: entityType,
    entity_id: entityId,
    action,
    actor_type: 'USER',
    actor_id: actorId || 'USER-LOD2-001',
    metadata,
    timestamp: new Date().toISOString()
  };

  if (usingSupabase) {
    const { error } = await supabase.from('audit_events').insert(audit);
    if (!error) return audit;
  }
  memoryFallback.auditEvents.push(audit);
  return audit;
}

// ---------------- REVIEWS ----------------
app.post('/reviews', async (req, res) => {
  const actorId = req.headers['x-actor-id'] || 'USER-LOD2-001';
  const { name, type, startDate, endDate, businessUnits, description } = req.body;
  if (!name || !startDate || !endDate) {
    return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'name, startDate, and endDate are required' } });
  }

  const reviewId = generateId('REV');
  const review = {
    review_id: reviewId,
    name,
    type: type || 'AML_KYC',
    start_date: startDate,
    end_date: endDate,
    business_units: businessUnits || [],
    description: description || '',
    status: 'DRAFT',
    created_by: actorId,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  if (usingSupabase) {
    const { error } = await supabase.from('reviews').insert(review);
    if (!error) {
      await recordAudit('REVIEW', reviewId, 'REVIEW_CREATED', actorId, { review });
      return res.status(200).json({
        data: {
          reviewId: review.review_id,
          name: review.name,
          type: review.type,
          startDate: review.start_date,
          endDate: review.end_date,
          businessUnits: review.business_units,
          description: review.description,
          status: review.status,
          createdBy: review.created_by,
          createdAt: review.created_at,
          updatedAt: review.updated_at
        }
      });
    }
  }

  // Fallback
  memoryFallback.reviews.push(review);
  recordAudit('REVIEW', reviewId, 'REVIEW_CREATED', actorId, { review });
  res.status(200).json({
    data: {
      reviewId: review.review_id,
      name: review.name,
      type: review.type,
      startDate: review.start_date,
      endDate: review.end_date,
      businessUnits: review.business_units,
      description: review.description,
      status: review.status,
      createdBy: review.created_by,
      createdAt: review.created_at,
      updatedAt: review.updated_at
    }
  });
});

app.get('/reviews', async (req, res) => {
  if (usingSupabase) {
    let query = supabase.from('reviews').select('*');
    if (req.query.status) query = query.eq('status', req.query.status);
    if (req.query.type) query = query.eq('type', req.query.type);
    const { data, error } = await query;
    if (!error && data) {
      return res.status(200).json({
        data: data.map(r => ({
          reviewId: r.review_id,
          name: r.name,
          type: r.type,
          startDate: r.start_date,
          endDate: r.end_date,
          businessUnits: r.business_units,
          description: r.description,
          status: r.status,
          createdBy: r.created_by,
          createdAt: r.created_at,
          updatedAt: r.updated_at
        }))
      });
    }
  }

  let list = [...memoryFallback.reviews];
  if (req.query.status) list = list.filter(r => r.status === req.query.status);
  if (req.query.type) list = list.filter(r => r.type === req.query.type);
  res.status(200).json({
    data: list.map(r => ({
      reviewId: r.review_id,
      name: r.name,
      type: r.type,
      startDate: r.start_date,
      endDate: r.end_date,
      businessUnits: r.business_units,
      description: r.description,
      status: r.status,
      createdBy: r.created_by,
      createdAt: r.created_at,
      updatedAt: r.updated_at
    }))
  });
});

app.post('/reviews/:reviewId/activate', async (req, res) => {
  const actorId = req.headers['x-actor-id'] || 'USER-LOD2-001';
  let review = null;
  let attached = [];

  if (usingSupabase) {
    const { data: rev } = await supabase.from('reviews').select('*').eq('review_id', req.params.reviewId).single();
    const { data: rcs } = await supabase.from('review_controls').select('*').eq('review_id', req.params.reviewId);
    review = rev;
    attached = rcs || [];
  } else {
    review = memoryFallback.reviews.find(r => r.review_id === req.params.reviewId);
    attached = memoryFallback.reviewControls.filter(rc => rc.review_id === req.params.reviewId);
  }

  if (!review) return res.status(400).json({ error: { code: 'NOT_FOUND', message: 'Review not found' } });

  if (attached.length === 0) {
    return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: 'at least one ReviewControl exists' } });
  }

  for (const rc of attached) {
    if (!rc.owner_id) {
      return res.status(400).json({ error: { code: 'VALIDATION_ERROR', message: `ReviewControl ${rc.review_control_id} missing ownerId` } });
    }
  }

  if (usingSupabase) {
    await supabase.from('reviews').update({ status: 'ACTIVE', updated_at: new Date().toISOString() }).eq('review_id', req.params.reviewId);
  } else {
    review.status = 'ACTIVE';
    review.updated_at = new Date().toISOString();
  }

  await recordAudit('REVIEW', req.params.reviewId, 'REVIEW_ACTIVATED', actorId, { reviewId: req.params.reviewId });
  res.status(200).json({ data: { message: 'Review activated successfully', reviewId: req.params.reviewId, status: 'ACTIVE' } });
});

// ---------------- CONTROLS ----------------
app.get('/controls', async (req, res) => {
  if (usingSupabase) {
    const { data, error } = await supabase.from('controls').select('*');
    if (!error && data && data.length > 0) {
      return res.status(200).json({
        data: data.map(c => ({
          controlId: c.control_id,
          name: c.name,
          description: c.description,
          domain: c.domain,
          riskLevel: c.risk_level,
          frequency: c.frequency,
          requiredEvidenceTypes: c.required_evidence_types,
          status: c.status
        }))
      });
    }
  }
  res.status(200).json({ data: memoryFallback.controls });
});

// ---------------- REVIEW CONTROLS ----------------
app.post('/reviews/:reviewId/controls', async (req, res) => {
  const actorId = req.headers['x-actor-id'] || 'USER-LOD2-001';
  const { controlId, ownerId } = req.body;
  const reviewControlId = generateId('RC');

  const rc = {
    review_control_id: reviewControlId,
    review_id: req.params.reviewId,
    control_id: controlId,
    owner_id: ownerId || 'USER-AML-001',
    status: 'NOT_STARTED',
    risk_level: 'HIGH',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  if (usingSupabase) {
    const { error } = await supabase.from('review_controls').insert(rc);
    if (!error) {
      await recordAudit('REVIEW_CONTROL', reviewControlId, 'CONTROL_ATTACHED', actorId, {
        eventType: 'CONTROL_ATTACHED',
        reviewId: req.params.reviewId,
        reviewControlId,
        controlId
      });
      return res.status(200).json({
        data: {
          reviewControlId: rc.review_control_id,
          reviewId: rc.review_id,
          controlId: rc.control_id,
          ownerId: rc.owner_id,
          status: rc.status
        }
      });
    }
  }

  memoryFallback.reviewControls.push(rc);
  recordAudit('REVIEW_CONTROL', reviewControlId, 'CONTROL_ATTACHED', actorId, {
    eventType: 'CONTROL_ATTACHED',
    reviewId: req.params.reviewId,
    reviewControlId,
    controlId
  });
  res.status(200).json({
    data: {
      reviewControlId: rc.review_control_id,
      reviewId: rc.review_id,
      controlId: rc.control_id,
      ownerId: rc.owner_id,
      status: rc.status
    }
  });
});

app.get('/reviews/:reviewId/controls', async (req, res) => {
  if (usingSupabase) {
    const { data } = await supabase.from('review_controls').select('*').eq('review_id', req.params.reviewId);
    if (data) {
      return res.status(200).json({
        data: data.map(rc => ({
          reviewControlId: rc.review_control_id,
          reviewId: rc.review_id,
          controlId: rc.control_id,
          ownerId: rc.owner_id,
          status: rc.status
        }))
      });
    }
  }
  const list = memoryFallback.reviewControls.filter(rc => rc.review_id === req.params.reviewId);
  res.status(200).json({
    data: list.map(rc => ({
      reviewControlId: rc.review_control_id,
      reviewId: rc.review_id,
      controlId: rc.control_id,
      ownerId: rc.owner_id,
      status: rc.status
    }))
  });
});

// ---------------- USERS ----------------
app.get('/users', async (req, res) => {
  if (usingSupabase) {
    const { data } = await supabase.from('users').select('*');
    if (data && data.length > 0) {
      return res.status(200).json({
        data: data.map(u => ({
          userId: u.user_id,
          name: u.name,
          email: u.email,
          role: u.role,
          businessUnit: u.business_unit,
          active: u.active
        }))
      });
    }
  }
  res.status(200).json({ data: memoryFallback.users });
});

// ---------------- AUDIT ----------------
app.get('/reviews/:reviewId/audit', async (req, res) => {
  if (usingSupabase) {
    const { data } = await supabase.from('audit_events').select('*').eq('entity_id', req.params.reviewId);
    if (data) {
      return res.status(200).json({
        data: data.map(a => ({
          auditId: a.audit_id,
          entityId: a.entity_id,
          action: a.action,
          actorId: a.actor_id,
          timestamp: a.timestamp
        }))
      });
    }
  }
  const list = memoryFallback.auditEvents.filter(a => a.entity_id === req.params.reviewId);
  res.status(200).json({
    data: list.map(a => ({
      auditId: a.audit_id,
      entityId: a.entity_id,
      action: a.action,
      actorId: a.actor_id,
      timestamp: a.timestamp
    }))
  });
});

// ---------------- DASHBOARD UI ----------------
app.get('/', (req, res) => {
  res.send(`
<!DOCTYPE html>
<html>
<head>
  <title>Review & Control Management Dashboard</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 24px; background: #f8fafc; color: #1e293b; max-width: 1100px; margin: 0 auto; }
    h1 { color: #0f172a; margin-bottom: 4px; }
    .status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 9999px; font-size: 13px; font-weight: 600; margin-bottom: 20px; }
    .status-sb { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .status-mem { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
    .card { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid #f1f5f9; font-size: 14px; }
    th { background: #f8fafc; font-weight: 600; color: #475569; }
    button { background: #2563eb; color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 13px; }
    button:hover { background: #1d4ed8; }
    .btn-green { background: #16a34a; }
    .btn-green:hover { background: #15803d; }
    input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; margin-right: 8px; font-size: 14px; }
    .badge { padding: 3px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; }
    .badge-draft { background: #e2e8f0; color: #475569; }
    .badge-active { background: #dcfce7; color: #15803d; }
  </style>
</head>
<body>
  <h1>🏦 Review & Control Management Dashboard</h1>
  <div class="status-badge ${usingSupabase ? 'status-sb' : 'status-mem'}">
    ● Database Mode: ${usingSupabase ? '⚡ Connected to Supabase Cloud' : '🟡 Standby / Fallback (SQL tables pending in Supabase)'}
  </div>

  <div class="card">
    <h2 style="margin-top:0;font-size:18px;">1. Create New Compliance Review</h2>
    <form id="createReviewForm" style="display:flex;gap:8px;flex-wrap:wrap;">
      <input type="text" id="revName" placeholder="Review Name (e.g. AML Q3 2026)" required style="flex:1;min-width:240px;">
      <input type="date" id="revStart" value="2026-07-01" required>
      <input type="date" id="revEnd" value="2026-09-30" required>
      <button type="submit">Create Review</button>
    </form>
  </div>

  <div class="card">
    <h2 style="margin-top:0;font-size:18px;">2. Active Compliance Reviews</h2>
    <table id="reviewsTable">
      <thead>
        <tr><th>Review ID</th><th>Review Name</th><th>Period</th><th>Status</th><th>Actions</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="card">
    <h2 style="margin-top:0;font-size:18px;">3. Regulatory Controls Catalog</h2>
    <table id="controlsTable">
      <thead>
        <tr><th>Control ID</th><th>Control Name</th><th>Risk Level</th><th>Frequency</th><th>Required Evidence</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="card">
    <h2 style="margin-top:0;font-size:18px;">4. Immutable Audit Trail</h2>
    <table id="auditTable">
      <thead>
        <tr><th>Audit ID</th><th>Entity ID</th><th>Action</th><th>Actor</th><th>Timestamp</th></tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <script>
    async function loadData() {
      // Reviews
      const revRes = await fetch('/reviews');
      const revJson = await revRes.json();
      const rBody = document.querySelector('#reviewsTable tbody');
      rBody.innerHTML = (revJson.data && revJson.data.length) ? revJson.data.map(r => \`
        <tr>
          <td><b>\${r.reviewId}</b></td>
          <td>\${r.name}</td>
          <td>\${r.startDate} to \${r.endDate}</td>
          <td><span class="badge \${r.status === 'ACTIVE' ? 'badge-active' : 'badge-draft'}">\${r.status}</span></td>
          <td style="display:flex;gap:6px;">
            <button onclick="attachControl('\${r.reviewId}')">Attach AML-001</button>
            <button class="btn-green" onclick="activateReview('\${r.reviewId}')">Activate Review</button>
          </td>
        </tr>
      \`).join('') : '<tr><td colspan="5" style="color:#64748b;">No reviews created yet.</td></tr>';

      // Controls
      const ctlRes = await fetch('/controls');
      const ctlJson = await ctlRes.json();
      const cBody = document.querySelector('#controlsTable tbody');
      cBody.innerHTML = (ctlJson.data && ctlJson.data.length) ? ctlJson.data.map(c => \`
        <tr>
          <td><b>\${c.controlId}</b></td>
          <td>\${c.name}</td>
          <td>\${c.riskLevel}</td>
          <td>\${c.frequency}</td>
          <td>\${Array.isArray(c.requiredEvidenceTypes) ? c.requiredEvidenceTypes.join(', ') : ''}</td>
        </tr>
      \`).join('') : '<tr><td colspan="5">Loading controls...</td></tr>';

      // Audit
      const auditRows = [];
      if (revJson.data) {
        for (const r of revJson.data) {
          const aRes = await fetch('/reviews/' + r.reviewId + '/audit');
          const aJson = await aRes.json();
          if (aJson.data) auditRows.push(...aJson.data);
        }
      }
      const aBody = document.querySelector('#auditTable tbody');
      aBody.innerHTML = auditRows.length ? auditRows.map(a => \`
        <tr>
          <td>\${a.auditId}</td>
          <td><b>\${a.entityId}</b></td>
          <td>\${a.action}</td>
          <td>\${a.actorId}</td>
          <td>\${new Date(a.timestamp).toLocaleTimeString()}</td>
        </tr>
      \`).join('') : '<tr><td colspan="5" style="color:#64748b;">No audit records yet.</td></tr>';
    }

    document.getElementById('createReviewForm').onsubmit = async (e) => {
      e.preventDefault();
      await fetch('/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Actor-Id': 'USER-LOD2-001' },
        body: JSON.stringify({
          name: document.getElementById('revName').value,
          startDate: document.getElementById('revStart').value,
          endDate: document.getElementById('revEnd').value,
          businessUnits: ['RETAIL_BANKING']
        })
      });
      document.getElementById('revName').value = '';
      loadData();
    };

    window.attachControl = async (reviewId) => {
      const res = await fetch('/reviews/' + reviewId + '/controls', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Actor-Id': 'USER-LOD2-001' },
        body: JSON.stringify({ controlId: 'AML-001', ownerId: 'USER-AML-001' })
      });
      const data = await res.json();
      if (data.error) alert(data.error.message);
      else alert('Attached AML-001! (reviewControlId: ' + data.data.reviewControlId + ')');
      loadData();
    };

    window.activateReview = async (reviewId) => {
      const res = await fetch('/reviews/' + reviewId + '/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Actor-Id': 'USER-LOD2-001' }
      });
      const data = await res.json();
      if (data.error) alert('Validation Error: ' + data.error.message);
      else alert('Review Activated Successfully!');
      loadData();
    };

    loadData();
  </script>
</body>
</html>
  `);
});

// Check Supabase table status on startup
async function startServer() {
  const { data, error } = await supabase.from('controls').select('control_id').limit(1);
  if (!error) {
    usingSupabase = true;
    console.log('✅ Supabase connected & tables verified!');
  } else {
    console.log('🟡 Supabase connected! Waiting for tables to be created in SQL Editor.');
  }

  app.listen(PORT, () => {
    console.log(`🚀 Dashboard running at http://localhost:${PORT}`);
  });
}

startServer();
