import express from 'express';
import { shipOrder } from './ship.js';

const app = express();
app.use(express.json());

app.post('/orders/:id/ship', async (req, res) => {
  console.log('Processing...');
  try {
    const result = await shipOrder(req.params.id, req.body);
    console.log('Done ' + req.params.id);
    res.status(201).json(result);
  } catch (e) {
    console.log('error: ' + e.message);
    res.status(500).json({ error: 'ship failed' });
  }
});

app.listen(process.env.PORT || 3000, () => console.log('listening'));
