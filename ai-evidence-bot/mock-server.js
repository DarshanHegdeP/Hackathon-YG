const express = require('express');
const cors = require('cors');
const fs = require('fs');

const PORT = 3000;
const app = express();
app.use(cors());
app.use(express.json());

// In-memory Database
const db = {
  reviews: [],
  controls: JSON.parse(fs.readFileSync('./seed/controls.json', 'utf8')),
  users: JSON.parse(fs.readFileSync('./seed/users.json', 'utf8')),
  reviewControls: [],
  auditEvents: []
};

function generateId(prefix) {
  return prefix + '-' + Math.random().toString(36).substring(2, 10);
}

// ----------------------------------------------------
// Mocked Endpoints mapping logic to in-memory store
// ----------------------------------------------------

// Reviews
app.post('/reviews', (req, res) => {
  const review = {
    reviewId: generateId('REV'),
    name: req.body.name,
    type: req.body.type,
    startDate: req.body.startDate,
    endDate: req.body.endDate,
    businessUnits: req.body.businessUnits || [],
    description: req.body.description || '',
    status: 'DRAFT',
    createdBy: req.headers['x-actor-id'] || 'USER-LOD2-001',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
  db.reviews.push(review);
  db.auditEvents.push({ auditId: generateId('AUDIT'), entityId: review.reviewId, action: 'REVIEW_CREATED' });
  res.json({ data: review });
});

app.get('/reviews', (req, res) => res.json({ data: db.reviews }));
app.get('/reviews/:id', (req, res) => res.json({ data: db.reviews.find(r => r.reviewId === req.params.id) }));

// Users
app.get('/users', (req, res) => res.json({ data: db.users }));

// Controls
app.get('/controls', (req, res) => res.json({ data: db.controls }));

app.post('/reviews/:id/controls', (req, res) => {
  const rc = {
    reviewControlId: generateId('RC'),
    reviewId: req.params.id,
    controlId: req.body.controlId,
    ownerId: req.body.ownerId,
    status: 'NOT_STARTED',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
  db.reviewControls.push(rc);
  res.json({ data: rc });
});

app.get('/reviews/:id/controls', (req, res) => {
  res.json({ data: db.reviewControls.filter(rc => rc.reviewId === req.params.id) });
});

const server = app.listen(PORT, () => {
  console.log('\n=========================================');
  console.log('🚀 MOCK Local Server running on http://localhost:' + PORT);
  console.log('=========================================');
  console.log('Test it out with:');
  console.log('curl http://localhost:' + PORT + '/users');
  console.log('curl http://localhost:' + PORT + '/controls');
});

server.on('error', (e) => {
  if (e.code === 'EADDRINUSE') {
    console.error('Port 3000 is already in use. Retrying on port 3001...');
    server.close();
    app.listen(3001, () => console.log('Server running on port 3001'));
  } else {
    console.error(e);
  }
});
