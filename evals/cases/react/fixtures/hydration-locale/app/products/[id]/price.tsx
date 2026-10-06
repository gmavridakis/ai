'use client';

import { useState } from 'react';

export function Price({ amountCents, currency }: { amountCents: number; currency: string }) {
  const [quantity, setQuantity] = useState(1);
  const formatter = new Intl.NumberFormat(
    typeof navigator === 'undefined' ? 'en-US' : navigator.language,
    { style: 'currency', currency },
  );
  const amount = typeof navigator === 'undefined' ? 0 : (amountCents * quantity) / 100;
  return (
    <div>
      <span data-testid="price">{formatter.format(amount)}</span>
      <button onClick={() => setQuantity((q) => q + 1)}>+</button>
      <button onClick={() => setQuantity((q) => Math.max(1, q - 1))}>-</button>
    </div>
  );
}
