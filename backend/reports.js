const express = require('express');
const router = express.Router();

// In‑memory stores (replace with a DB for production)
const reports = []; // {id, postId, reason, reporter, timestamp}
const hiddenPosts = new Set(); // postIds automatically hidden after a report
const removedPosts = new Set(); // postIds removed by a moderator
const actionLog = []; // {reportId, action, moderator, timestamp}

let nextReportId = 1;

/**
 * POST /api/report
 * Body: { postId, reason, reporter? }
 * Creates a report and auto‑hides the post.
 */
router.post('/report', (req, res) => {
  const { postId, reason, reporter } = req.body;
  if (!postId || !reason) {
    return res.status(400).json({ error: 'postId and reason are required' });
  }
  const report = {
    id: nextReportId++,
    postId,
    reason,
    reporter: reporter || 'anonymous',
    timestamp: Date.now()
  };
  reports.push(report);
  hiddenPosts.add(postId); // auto‑hide the reported post
  res.status(201).json({ report });
});

/**
 * GET /api/reports
 * Returns all pending reports. In a real app this would be protected.
 */
router.get('/reports', (req, res) => {
  // TODO: add moderator authentication
  res.json({ reports });
});

/**
 * POST /api/moderate
 * Body: { reportId, action: 'keep'|'remove', moderator? }
 * Executes the moderator's decision and logs it.
 */
router.post('/moderate', (req, res) => {
  const { reportId, action, moderator } = req.body;
  const report = reports.find(r => r.id === Number(reportId));
  if (!report) {
    return res.status(404).json({ error: 'Report not found' });
  }

  if (action === 'remove') {
    removedPosts.add(report.postId);
    hiddenPosts.delete(report.postId);
  } else if (action === 'keep') {
    hiddenPosts.delete(report.postId);
  } else {
    return res.status(400).json({ error: 'Invalid action' });
  }

  actionLog.push({
    reportId: report.id,
    action,
    moderator: moderator || 'unknown',
    timestamp: Date.now()
  });

  // Remove the processed report from the pending list
  const idx = reports.findIndex(r => r.id === report.id);
  if (idx !== -1) reports.splice(idx, 1);

  res.json({ status: 'ok' });
});

module.exports = router;
