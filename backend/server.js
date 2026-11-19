const express = require('express');
const path = require('path');
const bodyParser = require('body-parser');
const reportsRouter = require('./reports');

const app = express();
app.use(bodyParser.json());

// Serve static frontend assets
app.use(express.static(path.join(__dirname, '..', 'web')));

// API routes
app.use('/api', reportsRouter);

// Placeholder protection middleware – replace with real auth in production
function protect(req, res, next) {
  // TODO: verify moderator session / token
  next();
}

// Protect the moderation UI
app.get('/moderate.html', protect, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'web', 'moderate.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
