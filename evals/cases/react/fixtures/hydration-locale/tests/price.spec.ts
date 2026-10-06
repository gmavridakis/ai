import { expect, test } from '@playwright/test';

test('price is right on first paint', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto('/products/sku-1042');
  await expect(page.getByTestId('price')).toHaveText('12,50 €');
  expect(errors.filter((e) => e.includes('Hydration failed'))).toHaveLength(0);
});
