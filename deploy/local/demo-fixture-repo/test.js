'use strict';

const assert = require('assert');
const { applyDiscount, cartTotal } = require('./pricing');

// 20% off 1000 cents must be 800 cents.
assert.strictEqual(applyDiscount(1000, 20), 800, `applyDiscount(1000, 20) => ${applyDiscount(1000, 20)}, expected 800`);

// No discount leaves the price unchanged.
assert.strictEqual(applyDiscount(500, 0), 500);

// 100% discount is free.
assert.strictEqual(applyDiscount(500, 100), 0);

// Cart: 2 x 300 + 1 x 400 = 1000, 10% off => 900.
assert.strictEqual(
  cartTotal([{ price: 300, quantity: 2 }, { price: 400, quantity: 1 }], 10),
  900
);

console.log('checkout-pricing: all tests passed');
