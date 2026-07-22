'use strict';

/**
 * Checkout pricing helpers.
 */

/**
 * Applies a percentage discount to a price.
 *
 * @param {number} price - unit price in cents
 * @param {number} percent - discount percentage, 0..100 (e.g. 20 means 20% off)
 * @returns {number} discounted price in cents, rounded to the nearest cent
 */
function applyDiscount(price, percent) {
  if (percent < 0 || percent > 100) {
    throw new RangeError('percent must be between 0 and 100');
  }
  return Math.round(price - price * percent);
}

/**
 * Total for a cart of {price, quantity} line items after a cart-wide discount.
 */
function cartTotal(items, discountPercent) {
  const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  return applyDiscount(subtotal, discountPercent);
}

module.exports = { applyDiscount, cartTotal };
