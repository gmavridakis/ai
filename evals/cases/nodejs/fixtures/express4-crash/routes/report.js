const express = require('express');
const db = require('../db');
const router = express.Router();

router.get('/daily', async (req, res) => {
  const day = req.query.day || new Date().toISOString().slice(0, 10);
  const { rows } = await db.query('select * from daily_report where day = $1', [day]); // line 41 in prod build
  res.json(rows);
});

module.exports = router;
