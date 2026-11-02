import { test, expect } from '@playwright/test';

test('synthetic fixture: deep department link, search, hidden labs, student filter and XML reader', async ({
  page,
}) => {
  test.skip(process.env.ATLAS_FIXTURE !== '1', 'Run with the synthetic CI bundle');
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/cs-departments.html?school=fixture&dept=Computer%20Science');
  await expect(page).toHaveURL(/dept=Computer\+Science|dept=Computer%20Science/);
  await expect(page.locator('#csd-rows tr[data-i]')).toHaveCount(1);
  await expect(page.locator('#csd-rows')).not.toContainText('Hidden empty lab');
  await page.locator('#csd-search').fill('no-match-123456');
  await expect(page.locator('#csd-rows')).toContainText('No labs.');
  await page.locator('#csd-search').fill('Fixture Student');
  await page.locator('#csd-rows tr[data-i]').first().press('Enter');
  await page.locator('[data-st]').click();
  await expect(page.locator('#csd-clear')).toBeVisible();
  await page.getByRole('button', { name: 'Read here · stored full text' }).click();
  await expect(page.getByRole('dialog')).toContainText('Synthetic full text for browser tests.');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
  expect(errors).toEqual([]);
});
