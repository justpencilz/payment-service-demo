-- Migration 002: Add payment_methods table and link to payments
-- Risk: DDL changes on production tables — requires coordinated deploy

CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'card',
    provider VARCHAR(50) NOT NULL DEFAULT 'stripe',
    token TEXT NOT NULL,
    last_four VARCHAR(4),
    expiry_month INT,
    expiry_year INT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE payments ADD COLUMN payment_method_id INTEGER REFERENCES payment_methods(id);

CREATE INDEX idx_payment_methods_customer ON payment_methods(customer_id);
CREATE INDEX idx_payments_method_id ON payments(payment_method_id);

-- Backfill: set existing payments to first payment method if any
UPDATE payments SET payment_method_id = (
    SELECT MIN(pm.id) FROM payment_methods pm WHERE pm.customer_id = payments.customer_id
) WHERE payment_method_id IS NULL;
