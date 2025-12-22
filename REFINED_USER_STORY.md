# Refined User Story: Login to Cancer Data Commons Hub

## User Story
As a user, I want to successfully log in to the Cancer Data Commons Hub using login.gov with username and TOTP (Time-based One-Time Password) authentication, so that I can access the hub's features.

## Test Flow (with Implicit Wait Requirements)

### Prerequisites
- Valid username: Laxmi_AI_test@yahoo.com
- Valid password: Testnci123456789!
- TOTP secret key: LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX

### Test Steps

**Step 1: Navigate to Hub**
- Action: Navigate to https://hub-stage.datacommons.cancer.gov/
- Expected Result: Page loads and displays the Cancer Data Commons Hub main page
- Wait For: Page to fully load (document.readyState === 'complete' and body has content)
- Validation: URL contains 'hub-stage.datacommons.cancer.gov'

**Step 2: Handle Popup Banner (Conditional)**
- Action: If a popup banner appears, click "Continue" button
- Expected Result: Popup banner is dismissed (if present)
- Wait For: "Continue" button to be visible and clickable (timeout: 10 seconds)
- Validation: If popup exists, it should be dismissed after clicking. If no popup, step passes automatically.

**Step 3: Verify Main Page**
- Action: Verify you are on the main page with login option visible
- Expected Result: Main page is displayed with "Log in" button visible
- Wait For: "Log in" button to be visible in the DOM
- Validation: Page contains "Log in" button or similar login option

**Step 4: Click Log In Button**
- Action: Click on "Log in" button
- Expected Result: User is redirected to the login page (auth.nih.gov or login.gov)
- Wait For: "Log in" button to be visible and clickable (timeout: 10 seconds)
- Validation: URL changes to login page (contains 'auth.nih.gov' or 'login.gov'). This is the expected outcome - we are now on the login page, NOT the hub.

**Step 5: Select Login.gov Option**
- Action: Click on "login.gov" option
- Expected Result: Login form for login.gov is displayed
- Wait For: "login.gov" option/link to be visible and clickable (timeout: 10 seconds)
- Validation: Login form with username and password fields is visible

**Step 6: Enter Username**
- Action: Enter username: Laxmi_AI_test@yahoo.com
- Expected Result: Username field is filled with the provided email
- Wait For: Username input field to be visible and enabled (timeout: 10 seconds)
- Validation: Username field contains the entered email address

**Step 7: Enter Password**
- Action: Enter password: Testnci123456789!
- Expected Result: Password field is filled with the provided password
- Wait For: Password input field to be visible and enabled (timeout: 10 seconds)
- Validation: Password field contains the entered password (may be masked)

**Step 8: Submit Login Form**
- Action: Click on "Submit" button
- Expected Result: Form is submitted and user is redirected to TOTP/2FA page
- Wait For: "Submit" button to be visible and clickable (timeout: 10 seconds)
- Validation: Page navigates to TOTP entry page (URL may change, or TOTP input field appears)

**Step 9: Generate and Enter TOTP Code**
- Action: Generate TOTP code using secret key (LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX) and enter it in the "One-time code" field
- Expected Result: TOTP code is generated and entered into the one-time code input field
- Wait For: "One-time code" input field to be visible and enabled (timeout: 10 seconds)
- Validation: One-time code field contains a 6-digit numeric code

**Step 10: Submit TOTP Code**
- Action: Click "Submit" button to complete login
- Expected Result: TOTP code is submitted and user is navigated to 2FA reminder page or NIH Information Sharing Consent page
- Wait For: "Submit" button to be visible and clickable (timeout: 10 seconds)
- Validation: Page navigates away from TOTP entry page (URL no longer contains 'two_factor/authenticator')

**Step 10.5: Handle 2FA Reminder Page (Conditional)**
- Action: If a page appears asking "Do you want to add another 2FA method?", click "Continue" button
- Expected Result: Page proceeds to the next step (consent page)
- Wait For: "Continue" button to be visible and clickable (timeout: 10 seconds), or page to navigate away automatically
- Validation: If the 2FA reminder page appears (URL contains 'second_mfa_reminder'), click "Continue". If not present, step passes automatically and proceeds to consent page.

**Step 11: Grant Consent (Conditional)**
- Action: If a consent page appears with "Grant" button, click "Grant" button
- Expected Result: Consent is granted and user is redirected to the Cancer Data Commons Hub main page
- Wait For: "Grant" button to be visible and clickable (timeout: 10 seconds), or page to navigate away automatically
- After Click: Wait for navigation/redirect to complete (timeout: 15 seconds). The page may take a few seconds to redirect after clicking "Grant"
- Validation: If consent page appears (URL contains 'sts.nih.gov/auth/oauth/v2/authorize/consent'), click "Grant". After clicking, wait for redirect to complete. User is redirected to the Cancer Data Commons Hub main page (URL contains 'hub-stage.datacommons.cancer.gov')

**Step 12: Verify Successful Login**
- Action: Verify successful login
- Expected Result: User is logged in and can see the hub's main dashboard/content
- Wait For: Hub main page to load (timeout: 15 seconds)
- Validation: URL contains 'hub-stage.datacommons.cancer.gov' and page shows logged-in user content (not login page)

## Important Notes

1. **Implicit Waits**: Each step that involves clicking or filling should wait for the target element to be present and visible before performing the action. Use a timeout of 10 seconds for most elements, 15 seconds for page loads.

2. **Conditional Steps**: 
   - Step 2 (popup banner) is conditional - if the popup doesn't appear, the step should pass automatically.
   - Step 10.5 (2FA reminder page) is conditional - if the page doesn't appear, the step should pass automatically.
   - Step 11 (Grant consent) is conditional - if the consent page doesn't appear, the step should pass automatically.

3. **Navigation Expectations**: 
   - After Step 4 (Click Log In), expect to be on the login page (auth.nih.gov), NOT the hub. This is correct behavior.
   - After Step 10 (Submit TOTP), expect to navigate away from TOTP page. May go to 2FA reminder page (second_mfa_reminder) or directly to consent page.
   - After Step 10.5 (Handle 2FA Reminder), if the reminder page appeared, expect to be on the NIH Information Sharing Consent page (sts.nih.gov/auth/oauth/v2/authorize/consent).
   - After Step 11 (Grant Consent), expect to be back on the hub main page (hub-stage.datacommons.cancer.gov). **IMPORTANT**: The redirect after clicking "Grant" may take several seconds. Wait up to 15 seconds for the redirect to complete before validating the URL.

4. **TOTP Generation**: The TOTP code must be generated dynamically using the secret key at the time of Step 9. Do not use a hardcoded code.

5. **Element Visibility**: Before clicking any element, verify it is:
   - Present in the DOM
   - Visible (not hidden by CSS)
   - Enabled (not disabled)
   - Clickable (not covered by other elements)

## Acceptance Criteria

- User can navigate to the hub main page
- User can access the login page
- User can enter credentials successfully
- User can generate and enter TOTP code
- User is successfully logged in and can access hub features
- All steps complete without errors
- Screenshots are captured at each step for verification

