# shipping-service

POST /orders/:id/ship creates a shipment at the carrier. Logs go to stdout and are collected by the platform as one JSON line per event when the line parses as JSON; text lines are kept but not indexed.
