import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  test.skip(process.env.ATLAS_FIXTURE === '1', 'Full-release tests need a real publication bundle');
  page.on('pageerror', (error) => {
    throw error;
  });
});

test('a slow prior school request cannot replace the selected school', async ({ page }) => {
  await page.goto('/cs-departments.html?school=princeton&dept=Computer%20Science');
  await expect(page.locator('#csd-rows tr[data-i]').first()).toBeVisible();
  await expect(page).toHaveURL(/dept=Computer\+Science|dept=Computer%20Science/);
  await page.route('**/cmu.json.gz', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.continue();
  });
  await page.locator('[data-school="cmu"]').click();
  await page.locator('[data-school="mit"]').click();
  await expect
    .poll(() => page.evaluate(() => window.CSDepartments.getData().school.id))
    .toBe('mit');
  await page.waitForTimeout(2000);
  expect(await page.evaluate(() => window.CSDepartments.getData().school.id)).toBe('mit');
  await expect(page).toHaveURL(/school=mit/);
});

test('atlas loads, switches views, and navigates to departments', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#s-unis')).not.toHaveText('—');
  await expect(page.locator('#error')).toBeHidden();
  for (const tab of ['trends', 'coverage', 'atlas']) {
    await page.locator(`[data-tab="${tab}"]`).click();
    await expect(page.locator(`[data-tab="${tab}"]`)).toHaveClass(/active/);
  }
  await page.getByRole('link', { name: 'CS departments', exact: true }).click();
  await expect(page.locator('#csd-rows tr[data-i]').first()).toBeVisible();
});

test('all six schools load and search filters the labs', async ({ page }) => {
  await page.goto('/cs-departments.html');
  for (const school of ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']) {
    await page.locator(`[data-school="${school}"]`).click();
    await expect(page).toHaveURL(new RegExp('school=' + school));
    await expect(page.locator('#csd-rows tr[data-i]').first()).toBeVisible();
    await expect(page.locator('#csd-error')).toBeHidden();
  }
  await page.locator('#csd-search').fill('this-name-does-not-exist-987654321');
  await expect(page.locator('#csd-rows')).toContainText('No labs.');
  await page.locator('#csd-search').fill('');
  await expect(page.locator('#csd-rows tr[data-i]').first()).toBeVisible();
});

test('keyboard opens a lab, student filters work, and deep links survive reload', async ({
  page,
}) => {
  await page.goto('/cs-departments.html?school=princeton');
  const first = page.locator('#csd-rows tr[data-i]').first();
  await first.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#csd-lab')).toBeVisible();
  const title = await page.locator('#csd-lab h2').textContent();
  await expect(page).toHaveURL(/lab=/);
  await page.reload();
  await expect(page.locator('#csd-lab h2')).toHaveText(title);
  await page.locator('#csd-lab [data-st]').first().click();
  await expect(page.locator('#csd-clear')).toBeVisible();
  await page.locator('#csd-clear').click();
  await expect(page.locator('#csd-clear')).toHaveCount(0);
});

test('paper reader opens, checks bytes, and closes by keyboard', async ({ page }) => {
  await page.goto('/cs-departments.html?school=princeton');
  await page.locator('#csd-rows tr[data-i]').first().click();
  const button = page.getByRole('button', { name: /Read here · stored/ }).first();
  await button.click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('status')).not.toContainText('Loading');
  await expect(dialog.getByRole('status')).not.toContainText(/could not|changed|Invalid|not a PDF/);
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
});

test('downloads work and the mobile page stays within the viewport', async ({ page, request }) => {
  await page.goto('/cs-departments.html');
  await expect(page.locator('#csd-rows tr[data-i]').first()).toBeVisible();
  const headingColor = await page
    .locator('.csd-depts h2')
    .evaluate((el) => getComputedStyle(el).color);
  const sidebarColor = await page
    .locator('.csd-depts')
    .evaluate((el) => getComputedStyle(el).color);
  expect(headingColor).toBe(sidebarColor);
  const countsFit = await page
    .locator('.csd-depts li button span')
    .evaluateAll((elements) =>
      elements.every((el) => el.scrollHeight <= parseFloat(getComputedStyle(el).lineHeight) + 1),
    );
  expect(countsFit).toBe(true);
  const href = await page.getByRole('link', { name: 'Labs · CSV' }).getAttribute('href');
  const response = await request.get('/' + href);
  expect(response.status()).toBe(200);
  expect((await response.body()).length).toBeGreaterThan(100);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(
    true,
  );
});
