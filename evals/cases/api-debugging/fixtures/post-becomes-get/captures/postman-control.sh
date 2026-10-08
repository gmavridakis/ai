# Postman > Code snippet > cURL. Returns 201 with {"id":"pay_01J9...","status":"pending"}.
curl --location 'https://api.partner-pay.example/v2/payments' \
  --header 'Authorization: Bearer <redacted>' \
  --header 'Content-Type: application/json' \
  --data '{"amount":1250,"currency":"EUR","reference":"INV-2026-0931"}'
