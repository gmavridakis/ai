import { createShipment } from './carrier.js';

export async function shipOrder(orderId, body) {
  console.log('shipOrder ' + orderId + ' ' + JSON.stringify(body));
  const items = body.items || [];
  for (const item of items) {
    console.log('item ' + item.sku + ' qty ' + item.qty);
  }
  const shipment = await createShipment(orderId, items);
  console.log('shipment ' + JSON.stringify(shipment));
  return { orderId, trackingNumber: shipment.trackingNumber };
}
