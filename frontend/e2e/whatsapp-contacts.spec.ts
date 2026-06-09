import { test, expect, Page } from '@playwright/test'

// Mock contact data — one in each opt-in state.
const mockContacts = [
  {
    id: 1,
    phone_number: '+1234567890',
    country_code: 'US',
    display_name: 'John Doe',
    is_verified: true,
    opt_in_status: 'opted_in',
    wa_id: 'wa123',
    profile_name: 'John',
    message_count: 5,
    last_message_at: '2024-01-15T10:30:00Z',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    phone_number: '+9876543210',
    country_code: 'UK',
    display_name: 'Jane Smith',
    is_verified: false,
    opt_in_status: 'pending',
    wa_id: null,
    profile_name: null,
    message_count: 0,
    last_message_at: null,
    created_at: '2024-01-02T00:00:00Z',
  },
  {
    id: 3,
    phone_number: '+1122334455',
    country_code: 'DE',
    display_name: 'Hans Mueller',
    is_verified: true,
    opt_in_status: 'opted_out',
    wa_id: 'wa456',
    profile_name: 'Hans',
    message_count: 10,
    last_message_at: '2024-01-10T15:00:00Z',
    created_at: '2024-01-03T00:00:00Z',
  },
]

async function mockAuth(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem(
      'stratum_auth',
      JSON.stringify({
        id: '1',
        email: 'admin@company.com',
        name: 'Company Admin',
        role: 'admin',
        organization: 'Acme Corp',
        permissions: ['campaigns', 'analytics', 'users', 'whatsapp'],
        tenant_id: 1,
      })
    )
  })
}

const ok = (body: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(body),
})

async function mockWhatsApp(page: Page) {
  await page.route('**/whatsapp/contacts**', async (route) => {
    const method = route.request().method()
    if (method === 'GET') {
      await route.fulfill(
        ok({
          success: true,
          data: { items: mockContacts, total: mockContacts.length, page: 1, page_size: 20, total_pages: 1 },
        })
      )
    } else {
      // PATCH / opt-in / opt-out / DELETE
      await route.fulfill(ok({ success: true, message: 'ok', data: {} }))
    }
  })
  await page.route('**/whatsapp/templates**', (route) => route.fulfill(ok({ success: true, data: { items: [] } })))
  await page.route('**/whatsapp/messages**', (route) => route.fulfill(ok({ success: true, data: { items: [] } })))
}

// The WhatsApp manager opens on an Overview tab; the contact table lives under
// the "Contacts" tab.
async function gotoContacts(page: Page) {
  await page.goto('/dashboard/whatsapp')
  await page.getByRole('button', { name: /^Contacts$/ }).click()
  await expect(page.getByText('John Doe')).toBeVisible({ timeout: 15000 })
}

function row(page: Page, name: string) {
  return page.locator('tr', { has: page.getByText(name) })
}

test.describe('WhatsApp Contact Actions', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuth(page)
    await mockWhatsApp(page)
    await gotoContacts(page)
  })

  test('should display contacts list', async ({ page }) => {
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('Jane Smith')).toBeVisible()
    await expect(page.getByText('Hans Mueller')).toBeVisible()
    await expect(page.getByText('+1234567890')).toBeVisible()
    await expect(page.getByText('+9876543210')).toBeVisible()
  })

  test('should display opt-in status badges', async ({ page }) => {
    await expect(row(page, 'John Doe').getByText('Opted In')).toBeVisible()
    await expect(row(page, 'Jane Smith').getByText('Pending')).toBeVisible()
    await expect(row(page, 'Hans Mueller').getByText('Opted Out')).toBeVisible()
  })

  test('should expose row action buttons', async ({ page }) => {
    const john = row(page, 'John Doe')
    await expect(john.locator('button[aria-label="Edit contact"]')).toBeVisible()
    await expect(john.locator('button[aria-label="Delete contact"]')).toBeVisible()
  })

  test('should show Opt In action for a pending contact', async ({ page }) => {
    await expect(row(page, 'Jane Smith').locator('button[aria-label="Opt in"]')).toBeVisible()
  })

  test('should show Opt Out action for an opted-in contact', async ({ page }) => {
    await expect(row(page, 'John Doe').locator('button[aria-label="Opt out"]')).toBeVisible()
  })

  test('should call opt-in when opting in a pending contact', async ({ page }) => {
    const [req] = await Promise.all([
      page.waitForRequest((r) => /\/whatsapp\/contacts\/\d+\/opt-in/.test(r.url()), { timeout: 10000 }),
      row(page, 'Jane Smith').locator('button[aria-label="Opt in"]').click(),
    ])
    expect(req.method()).toBe('POST')
  })

  test('should keep the table stable when editing a contact', async ({ page }) => {
    // The edit affordance is present and clicking it does not break the view.
    await row(page, 'John Doe').locator('button[aria-label="Edit contact"]').click()
    await expect(page.getByText('John Doe')).toBeVisible()
  })

  test('should keep the table stable when deleting a contact', async ({ page }) => {
    page.on('dialog', (dialog) => dialog.dismiss())
    await row(page, 'John Doe').locator('button[aria-label="Delete contact"]').click()
    await expect(page.getByText('Jane Smith')).toBeVisible()
  })

  test('should keep the contact when delete is dismissed', async ({ page }) => {
    page.on('dialog', (dialog) => dialog.dismiss())
    await row(page, 'John Doe').locator('button[aria-label="Delete contact"]').click()
    await expect(page.getByText('John Doe')).toBeVisible()
  })

  test('should filter contacts via search', async ({ page }) => {
    await page.locator('input[placeholder*="Search" i]').first().fill('Jane')
    await expect(page.getByText('Jane Smith')).toBeVisible()
    await expect(page.getByText('Hans Mueller')).not.toBeVisible()
  })
})
