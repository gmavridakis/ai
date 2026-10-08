import axios from "axios";

const client = axios.create({
  baseURL: process.env.PARTNER_BASE_URL,
  timeout: 10000,
  headers: { Authorization: `Bearer ${process.env.PARTNER_KEY}` },
});

export async function createPayment(payment) {
  const { data } = await client.post("/payments", payment);
  return data;
}
