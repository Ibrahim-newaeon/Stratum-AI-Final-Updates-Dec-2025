import { test, expect } from '@playwright/test'

// Mock contact data
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

const mockTemplates = [
  {
    id: 1,
    name: 'welcome_message',
    language: 'en',
    category: 'MARKETING',
    body_text: 'Welcome to our service!',
    status: 'approved',
    usage_count: 100,
    created_at: '2024-01-01T00:00:00Z',
  },
]

/**
 * Helper to mock authenticated user - uses stratum_auth key that AuthContext expects
 */
async function mockAuth(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    const user = {
      id: '1',
      email: 'admin@company.com',
      name: 'Company Admin',
      role: 'admin',
      organization: 'Acme Corp',
      permissions: ['campaigns', 'analytics', 'users', 'whatsapp'],
      tenant_id: 1,
    }
    localStorage.setItem('stratum_auth', JSON.stringify(user))
  })
}

test.describe('WhatsApp Contact Actions', () => {
  test.beforeEach(async ({ page }) => {
    // Set auth BEFORE any navigation
    await mockAuth(page)

    // Mock API responses
    await page.route('**/api/v1/whatsapp/contacts**', async (route) => {
      const url = route.request().url()
      const method = route.request().method()

      if (method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: mockContacts,
              total: mockContacts.length,
              page: 1,
              page_size: 20,
              total_pages: 1,
            },
          }),
        })
      } else if (method === 'PATCH') {
        // Extract contact ID from URL
        const match = url.match(/\/contacts\/(\d+)/)
        const contactId = match ? parseInt(match[1]) : 1
        const body = JSON.parse(route.request().postData() || '{}')

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              ...mockContacts.find(c => c.id === contactId),
              display_name: body.display_name,
            },
            message: 'Contact updated successfully',
          }),
        })
      } else if (method === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Contact deleted successfully',
          }),
        })
      } else if (method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: mockContacts[0],
            message: 'Contact created successfully',
          }),
        })
      } else {
        await route.continue()
      }
    })

    // Mock opt-in/opt-out endpoints
    await page.route('**/api/v1/whatsapp/contacts/*/opt-in', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { ...mockContacts[1], opt_in_status: 'opted_in' },
          message: 'Contact opted in successfully',
        }),
      })
    })

    await page.route('**/api/v1/whatsapp/contacts/*/opt-out', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Contact opted out successfully',
        }),
      })
    })

    // Mock templates
    await page.route('**/api/v1/whatsapp/templates**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: mockTemplates,
            total: mockTemplates.length,
            page: 1,
            page_size: 20,
            total_pages: 1,
          },
        }),
      })
    })

    // Mock messages
    await page.route('**/api/v1/whatsapp/messages**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [],
            total: 0,
            page: 1,
            page_size: 20,
            total_pages: 0,
          },
        }),
      })
    })

    // Navigate to WhatsApp page (auth is already set via addInitScript)
    await page.goto('/dashboard/whatsapp')
    await page.waitForLoadState('networkidle')

    // Wait for the page to render contacts
    await page.waitForTimeout(1000)
  })

  test('should display contacts list', async ({ page }) => {
    // Check that contacts are displayed
    await expect(page.getByText('John Doe')).toBeVisible()
    await expect(page.getByText('Jane Smith')).toBeVisible()
    await expect(page.getByText('Hans Mueller')).toBeVisible()

    // Check phone numbers
    await expect(page.getByText('+1234567890')).toBeVisible()
    await expect(page.getByText('+9876543210')).toBeVisible()
  })

  test('should display opt-in status badges', async ({ page }) => {
    // Check status badges in table rows (not the filter dropdown options)
    // Find badges by looking within table rows
    const johnRow = page.locator('tr', { has: page.getByText('John Doe') })
    const janeRow = page.locator('tr', { has: page.getByText('Jane Smith') })
    const hansRow = page.locator('tr', { has: page.getByText('Hans Mueller') })

    // John Doe should have "Opted In" badge
    await expect(johnRow.locator('span:text("Opted In")')).toBeVisible()
    // Jane Smith should have "Pending" badge
    await expect(janeRow.locator('span:text("Pending")')).toBeVisible()
    // Hans Mueller should have "Opted Out" badge
    await expect(hansRow.locator('span:text("Opted Out")')).toBeVisible()
  })

  test('should open actions dropdown menu', async ({ page }) => {
    // Click the more options button for the first contact
    const moreButtons = page.locator('button:has(svg.lucide-more-horizontal)')
    await moreButtons.first().click()

    // Check dropdown menu items
    await expect(page.getByText('Edit Contact')).toBeVisible()
    await expect(page.getByText('Opt Out')).toBeVisible() // First contact is opted in
    await expect(page.getByText('Delete Contact')).toBeVisible()
  })

  test('should open edit contact modal', async ({ page }) => {
    // Click the more options button
    const moreButtons = page.locator('button:has(svg.lucide-more-horizontal)')
    await moreButtons.first().click()

    // Click Edit Contact
    await page.getByText('Edit Contact').click()

    // Check modal is open
    await expect(page.getByRole('heading', { name: 'Edit Contact' })).toBeVisible()

    // Check phone number is displayed (readonly)
    await expect(page.locator('input[value="+1234567890"]')).toBeVisible()

    // Check display name input
    const nameInput = page.locator('input[placeholder="Enter display name"]')
    await expect(nameInput).toBeVisible()
    await expect(nameInput).toHaveValue('John Doe')
  })

  test('should update contact name', async ({ page }) => {
    // Open dropdown
    const moreButtons = page.locator('button:has(svg.lucide-more-horizontal)')
    await moreButtons.first().click()

    // Click Edit Contact
    await page.getByText('Edit Contact').click()

    // Update the name
    const nameInput = page.locator('input[placeholder="Enter display name"]')
    await nameInput.clear()
    await nameInput.fill('John Updated')

    // Click Save Changes
    await page.getByRole('button', { name: 'Save Changes' }).click()

    // Modal should close
    await expect(page.getByRole('heading', { name: 'Edit Contact' })).not.toBeVisible()
  })

  test('should close edit modal with cancel button', async ({ page }) => {
    // Open dropdown
    const moreButtons = page.locator('button:has(svg.lucide-more-horizontal)')
    await moreButtons.first().click()

    // Click Edit Contact
    await page.getByText('Edit Contact').click()

    // Click Cancel
    await page.getByRole('button', { name: 'Cancel' }).click()

    // Modal should close
    await expect(page.getByRole('heading', { name: 'Edit Contact' })).not.toBeVisible()
  })

  test('should show Opt In option for pending contact', async ({ page }) => {
    // Find and click the more options for Jane Smith (pending status)
    const janeRow = page.locator('tr', { has: page.getByText('Jane Smith') })
    const moreButton = janeRow.locator('button:has(svg.lucide-more-horizontal)')
    await moreButton.click()

    // Should show "Opt In" option (not "Opt Out")
    await expect(page.getByText('Opt In')).toBeVisible()
  })

  test('should show Opt Out option for opted-in contact', async ({ page }) => {
    // Find and click the more options for John Doe (opted in)
    const johnRow = page.locator('tr', { has: page.getByText('John Doe') })
    const moreButton = johnRow.locator('button:has(svg.lucide-more-horizontal)')
    await moreButton.click()

    // Should show "Opt Out" option
    await expect(page.getByText('Opt Out')).toBeVisible()
  })

  test('should delete contact with confirmation', async ({ page }) => {
    // Set up dialog handler before triggering
    page.on('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm')
      expect(dialog.message()).toContain('Are you sure you want to delete')
      await dialog.accept()
    })

    // Open dropdown
    const moreButtons = page.locator('button:has(svg.lucide-more-horizontal)')
    await moreButtons.first().click()

    // Click Delete Contact
    await page.getByText('Delete Contact').click()

    // Dialog should have been handled and dropdown should close
    await expect(page.getByText('Delete Contact')).not.toBeVisible()
  })

  test('should cancel delete when dismissing confirmation', async ({ page }) => {
    // Set up dialog handler to dismiss
    page.on('dialog', async (dialog) => {
      await dialog.dismiss()
    })

    // Open dropdown
    const moreButtons = page.locator('button:has(svg.lucide-more-horizontal)')
    await moreButtons.first().click()

    // Click Delete Contact
    await page.getByText('Delete Contact').click()

    // Contact should still be visible
    await expect(page.getByText('John Doe')).toBeVisible()
  })

  test('should close dropdown when clicking outside', async ({ page }) => {
    // Open dropdown
    const moreButtons = page.locator('button:has(svg.lucide-more-horizontal)')
    await moreButtons.first().click()

    // Verify dropdown is open
    await expect(page.getByText('Edit Contact')).toBeVisible()

    // Click outside (on the page title)
    await page.getByText('WhatsApp Broadcast').click()

    // Dropdown should close
    await expect(page.getByText('Edit Contact')).not.toBeVisible()
  })

  test('should show send message button only for opted-in contacts', async ({ page }) => {
    // John Doe (opted in) should have send button
    const johnRow = page.locator('tr', { has: page.getByText('John Doe') })
    await expect(johnRow.locator('button:has(svg.lucide-send)')).toBeVisible()

    // Jane Smith (pending) should NOT have send button
    const janeRow = page.locator('tr', { has: page.getByText('Jane Smith') })
    await expect(janeRow.locator('button:has(svg.lucide-send)')).not.toBeVisible()

    // Hans Mueller (opted out) should NOT have send button
    const hansRow = page.locator('tr', { has: page.getByText('Hans Mueller') })
    await expect(hansRow.locator('button:has(svg.lucide-send)')).not.toBeVisible()
  })

  test('should toggle opt-in status', async ({ page }) => {
    // Find Jane Smith (pending) and click opt-in
    const janeRow = page.locator('tr', { has: page.getByText('Jane Smith') })
    const moreButton = janeRow.locator('button:has(svg.lucide-more-horizontal)')
    await moreButton.click()

    // Click Opt In
    await page.getByText('Opt In').click()

    // Dropdown should close after action
    await expect(page.getByText('Opt In')).not.toBeVisible()
  })
})
