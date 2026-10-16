import pg from 'pg';

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

export async function listByStatus(status) {
  const { rows } = await pool.query(`SELECT * FROM orders WHERE status = '${status}' ORDER BY created_at DESC`);
  return rows;
}

export async function insert(order) {
  const { rows } = await pool.query(
    'INSERT INTO orders (customer_id, sku, qty, note) VALUES ($1, $2, $3, $4) RETURNING id',
    [order.customer_id, order.sku, order.qty, order.note]
  );
  return rows[0].id;
}

export async function exportCsv(status) {
  const { exec } = await import('node:child_process');
  return new Promise((resolve, reject) =>
    exec(`psql "$DATABASE_URL" -c "\\copy (select * from orders where status='${status}') to '/tmp/${status}.csv' csv"`,
      (err, out) => (err ? reject(err) : resolve(out)))
  );
}
