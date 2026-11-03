import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
test.beforeEach(() => test.skip(process.env.ATLAS_FIXTURE !== '1', 'synthetic fixture tests'));

test('synthetic fixture: atlas navigation, filters, search and release provenance', async ({
  page,
}) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/');
  await expect(page.locator('#s-unis')).toHaveText('1');
  await expect(page.locator('[data-publication]')).toContainText('Synthetic');
  for (const name of ['trends', 'coverage', 'atlas'])
    await page.locator(`[data-tab="${name}"]`).click();
  await page.locator('#search').fill('Fixture');
  await page.locator('#search-results button').first().click();
  await expect(page.locator('#breadcrumb')).toContainText('Fixture University');
  await page.getByRole('link', { name: 'CS departments', exact: true }).click();
  await expect(page.locator('#csd-rows tr[data-i]')).toHaveCount(1);
  expect(errors).toEqual([]);
});

test('synthetic fixture: a failed school request has a working retry', async ({ page }) => {
  let fail = true;
  await page.route('**/data/cs-hierarchy/fixture.json.gz', (route) =>
    fail ? route.fulfill({ status: 503, body: 'unavailable' }) : route.continue(),
  );
  await page.goto('/cs-departments.html');
  await expect(page.locator('#csd-error')).toBeVisible();
  await expect(page.locator('#csd-rows tr[data-i]')).toHaveCount(0);
  fail = false;
  await page.getByRole('button', { name: 'Retry loading' }).click();
  await expect(page.locator('#csd-rows tr[data-i]')).toHaveCount(1);
});

test('synthetic fixture: unavailable papers give a readable error and dialog can close', async ({
  page,
}) => {
  await page.route('**/papers/**', (route) => route.fulfill({ status: 503, body: 'unavailable' }));
  await page.goto('/cs-departments.html');
  await page.locator('#csd-rows tr[data-i]').first().click();
  await page
    .getByRole('button', { name: /Read here/ })
    .first()
    .click();
  await expect(page.getByRole('dialog').getByRole('status')).not.toContainText('Loading');
  await expect(page.getByRole('dialog')).toContainText(/could not|unavailable|failed/i);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
});

for (const route of ['/', '/cs-departments.html'])
  test('synthetic fixture: accessible ' + route, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator(route === '/' ? '#s-unis' : '#csd-rows')).not.toHaveText(
      route === '/' ? '—' : '',
    );
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(
      results.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
    ).toEqual([]);
  });

test('synthetic fixture: department visual regression', async ({ page }, info) => {
  test.skip(
    info.project.name !== 'desktop' && info.project.name !== 'mobile',
    'Chromium visual baselines',
  );
  await page.goto('/cs-departments.html');
  await expect(page.locator('#csd-rows tr[data-i]')).toHaveCount(1);
  await expect(page.locator('.csd-body')).toHaveScreenshot('departments.png', {
    animations: 'disabled',
    maxDiffPixelRatio: 0.02,
  });
});
