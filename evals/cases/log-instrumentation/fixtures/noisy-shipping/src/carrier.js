const CARRIER_URL = process.env.CARRIER_URL || 'https://api.carrier.example/v1/shipments';
const API_KEY = process.env.CARRIER_API_KEY;

export async function createShipment(orderId, items) {
  const payload = { orderId, items };
  console.log('calling carrier with key ' + API_KEY + ' payload ' + JSON.stringify(payload));
  const res = await fetch(CARRIER_URL, {
    method: 'POST',
    headers: { authorization: 'Bearer ' + API_KEY, 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  console.log('carrier status ' + res.status);
  if (!res.ok) {
    throw new Error('carrier returned ' + res.status);
  }
  return res.json();
}
