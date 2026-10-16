import { Router } from 'express';
import jwt from 'jsonwebtoken';
import { listByStatus, insert, exportCsv } from '../orders/repo.js';

export const ordersRouter = Router();

function auth(req, res, next) {
  const token = (req.headers.authorization || '').replace('Bearer ', '');
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ error: 'invalid token' });
  }
}

ordersRouter.get('/', auth, async (req, res) => {
  res.json(await listByStatus(req.query.status || 'open'));
});

ordersRouter.post('/', auth, async (req, res) => {
  const id = await insert({ ...req.body, customer_id: req.user.sub });
  res.status(201).json({ id });
});

ordersRouter.get('/export', auth, async (req, res) => {
  await exportCsv(req.query.status);
  res.sendFile(`/tmp/${req.query.status}.csv`);
});
