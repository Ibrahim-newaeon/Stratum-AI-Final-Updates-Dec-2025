# Decision needed: CRM contact PII and the two missing metrics

Two items were deferred out of #739 as "needs a product and privacy decision":
whether the contact list should show identity fields, and whether to restore the
Avg Deal Size and Conversion Rate tiles. Both were deferred on a premise that
turns out to be false, so this records what is actually in the database and what
the real choices are.

Nothing here is urgent in the sense of an outage. One part of it is a standing
privacy gap that predates the question being asked.

## The premise that was wrong

The deferral said the backend stores only SHA256 hashes of contact identifiers,
so there was no plaintext to show. That is true of the dedicated columns and true
of the API: `CRMContact` has `email_hash` and `phone_hash` and no plaintext
equivalents, and `CRMContactRead` exposes neither.

It is not true of the database. Plaintext arrives by two separate routes.

### 1. `CRMContact.raw_properties` — HubSpot, not exposed, not encrypted

`hubspot_sync.py` asks HubSpot for a fixed property list that includes `email`,
`phone`, `mobilephone`, `firstname` and `lastname`. It hashes email and phone
into the dedicated columns — and then stores the whole dict:

```python
contact_fields = {
    "email_hash": email_hashed,
    "phone_hash": phone_hashed,
    ...
    "raw_properties": properties,   # the entire payload, plaintext included
}
```

`raw_properties` is a plain `JSONB` column. No endpoint or schema returns it, so
this is storage exposure rather than API exposure, but it sits against CLAUDE.md's
requirement to encrypt PII.

Encryption is not missing from this model for want of a pattern. `CRMConnection`
on the same file stores `access_token_enc` and `refresh_token_enc`, twenty lines
above the contact table. The capability is there and was applied to credentials
but not to contact data.

The contradiction is the point: the code takes the trouble to hash the
identifiers and then keeps the plaintext beside them.

### 2. CDP `profile_data` — Pipedrive, exposed and searchable

`pipedrive_sync.py` does not write `raw_properties`. It writes into the CDP
profile instead:

```python
profile_data.update({
    "first_name": person.get("first_name"),
    "last_name":  person.get("last_name"),
    "name":       person.get("name"),
    "org_name":   person.get("org_name"),
})
```

It deliberately skips `email` and `phone` in the custom-field loop that follows,
which reads as intentional. But `profile_data` is returned by the CDP API
(`cdp.py:864`, `cdp.py:1249`) and is free-text searchable:

```python
CDPProfile.profile_data.cast(String).ilike(f"%{query}%")
```

A CDP holding profile attributes is plausibly the intended design; this is noted
so the decision covers both stores rather than one.

## Decision 1: contact identity in the tenant CRM views

Deciding this is not "add a column to a response". It is choosing which of these
the product wants.

**Option A — leave the views as they are.** Contacts render by CRM record id,
lead source, stage, touch count, last touch. Nothing changes. The plaintext in
`raw_properties` stays unread and unexposed, and Decision 3 below still applies
to it.

**Option B — show identity, sourced properly.** Add explicit encrypted columns
for the fields the UI needs, populate them in the sync, expose them through
`CRMContactRead` behind the existing tenant scoping. Cost: a migration, sync
changes, encryption wiring, and a deletion path — a contact deletion request
must now reach these columns, and any export that includes them.

**Option C — show identity by reading `raw_properties`.** Cheapest to build and
the worst of the three. It promotes an accidental store to a load-bearing one,
serves unencrypted PII through the API, and leaves the field set at the mercy of
whatever HubSpot returns. Recorded so it is explicitly rejected rather than
quietly chosen later because it is easy.

Recommendation: **A or B, never C.** B only if a named workflow needs identity in
Stratum rather than in the CRM the data came from — the operator already has
HubSpot or Pipedrive open, and duplicating identity into a second system doubles
the surface that has to honour a deletion request.

## Decision 2: Avg Deal Size and Conversion Rate

These were dropped from the UI in #739 because nothing computed them. That is
still true, but they are not blocked on data — `CRMDeal` already carries
`amount_cents`, `is_won` and `is_closed`, and `get_pipeline_summary` already
aggregates over exactly those rows. This is arithmetic on data in hand, and it
carries no PII implications at all.

The only real question is the conversion-rate denominator:

| Definition | Reads as |
| --- | --- |
| won / all deals | dilutes with a large open pipeline; moves when nothing closed |
| won / closed deals (won + lost) | win rate among decided deals; the usual sales meaning |
| won / contacts | lead-to-customer rate, a different funnel question |

Recommendation: **won / (won + lost)**, labelled "Win Rate" rather than
"Conversion Rate", because that is what it measures and the honest label prevents
it being read as lead conversion. Avg Deal Size should be won-deal value over won
count, not over all deals, for the same reason.

This one does not need a privacy decision. It needs someone to pick the
denominator and it can ship.

## Decision 3: what to do about `raw_properties`

Independent of Decisions 1 and 2, and the one with a deadline attached to it in
the form of a deletion request nobody has sent yet.

**Option A — stop storing it.** Drop `raw_properties` from `contact_fields` and
null the column. Loses the debugging value of having the raw payload, and loses
any field not already mapped to a column.

**Option B — store a filtered subset.** Keep `raw_properties` minus the identity
keys (`email`, `phone`, `mobilephone`, `firstname`, `lastname`). Keeps the
attribution and analytics fields, drops the part that makes it PII.

**Option C — encrypt the column.** Keeps everything, satisfies the encrypt-PII
rule, costs a migration over existing rows and makes the column unsearchable.

**Option D — accept and document it.** Legitimate only if there is a stated
retention and deletion story. Undocumented is the current state and is the one
option that is not a decision.

Recommendation: **B.** It preserves what the column is actually used for and
removes the exposure, without a re-encryption migration. Whichever is chosen,
existing rows need backfilling — the data is already there.

## What is not being claimed

- No evidence this has been exploited or leaked. It is storage that does not
  match the stated policy, found by reading the sync code.
- The CDP `profile_data` behaviour may be entirely intended. It is included so
  the decision covers both stores, not because it is presumed wrong.
- Severity is not assessed here. Whether unencrypted contact PII at rest is a
  finding or an accepted risk depends on commitments made to customers, which
  are not in this repository.
