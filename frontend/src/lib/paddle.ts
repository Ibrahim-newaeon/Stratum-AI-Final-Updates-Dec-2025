/**
 * Paddle.js loader.
 *
 * Unlike Stripe, Paddle has no hosted checkout page to redirect to. The server
 * creates a *transaction*, and the checkout is opened by Paddle.js running on
 * one of our own pages. So the browser has to load Paddle.js before any
 * checkout can appear — a redirect on its own shows the customer a bare page.
 *
 * Configuration comes from `GET /payments/config` rather than a build-time env
 * var, for two reasons: the client token and environment are per-deployment,
 * and the active gateway can be switched server-side (`PAYMENT_GATEWAY`)
 * without rebuilding the frontend.
 *
 * The client token is safe in the browser by design — it is scoped to opening
 * checkouts and reading prices, and cannot read or mutate account data. The
 * server-side API key never reaches here.
 */

import { initializePaddle, type Paddle, type Environments } from '@paddle/paddle-js';

/**
 * Initialization is a singleton promise, not a boolean flag.
 *
 * `initializePaddle` warns and refuses on a second call, and React strict mode
 * plus route remounts make concurrent calls likely. Caching the promise means
 * simultaneous callers await the same load instead of racing it.
 */
let paddlePromise: Promise<Paddle | undefined> | null = null;

export interface PaddleInit {
  clientToken: string;
  environment: 'production' | 'sandbox';
}

export function getPaddle({ clientToken, environment }: PaddleInit): Promise<Paddle | undefined> {
  if (!paddlePromise) {
    paddlePromise = initializePaddle({
      token: clientToken,
      environment: environment as Environments,
    }).catch((error) => {
      // Reset so a later attempt can retry rather than being stuck on a
      // rejected promise for the life of the page — a transient CDN failure
      // should not permanently disable checkout.
      paddlePromise = null;
      throw error;
    });
  }
  return paddlePromise;
}

/**
 * Open the checkout overlay for a transaction the server already created.
 *
 * Takes a transaction id (`txn_...`) rather than a price id: the server decides
 * which price applies — including whether the tenant gets the trial-bearing
 * price — and stamps `custom_data.tenant_id` onto the transaction so the
 * webhook can resolve the tenant. Opening by price id here would bypass both.
 *
 * `successUrl` is where Paddle sends the browser after payment. It is for UX
 * only: entitlement is granted by the `subscription.*` webhook, which is
 * signed, retried, and arrives whether or not the customer's browser survives
 * the redirect.
 */
export async function openPaddleCheckout(
  init: PaddleInit,
  transactionId: string,
  successUrl?: string,
): Promise<void> {
  const paddle = await getPaddle(init);
  if (!paddle) {
    throw new Error('Paddle.js failed to load');
  }
  paddle.Checkout.open({
    transactionId,
    settings: {
      variant: 'one-page',
      ...(successUrl ? { successUrl } : {}),
    },
  });
}
