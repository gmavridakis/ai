import express from 'express';
import cors from 'cors';
import { ordersRouter } from './routes/orders.js';

const app = express();
app.use(cors({ origin: true, credentials: true }));
app.use(express.json());
app.use('/orders', ordersRouter);

app.listen(process.env.PORT || 3000, () => console.log('orders-service listening'));
