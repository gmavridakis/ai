import "dotenv/config";
import { createPayment } from "./partner.js";

const payment = { amount: 1250, currency: "EUR", reference: "INV-2026-0931" };
createPayment(payment)
  .then((r) => console.log("created", r.id))
  .catch((e) => {
    console.error("payment failed:", e.message);
    process.exit(1);
  });
