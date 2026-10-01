const express = require('express');
const app = express();
app.use('/report', require('./routes/report'));
app.use((err, req, res, next) => {
  console.error('handler error', err);
  res.status(500).json({ error: 'internal' });
});
app.listen(8080, () => console.log('listening on 8080'));
