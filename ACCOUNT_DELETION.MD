 # Steps to delete your account and activity data
 - Log into the Speak! ios or android app
 - Go to Settings menu
 - Click "Delete Account" to delete your account and data

This deletes your account, activity progress, song-playing progress, and messages
stored by the web service. Copies of messages already delivered to an external
email provider or mailbox are not deleted by this operation.

If deletion reports that writes are still in flight (HTTP 409), retry deletion
with the same access token after those writes finish. A cleanup failure is not
reported as success: the account remains marked for deletion and cannot create
new data. If the access token expires, sign in again to resume deletion; the
resulting session can only be used to retry deletion.

An interrupted service worker may require operator recovery. The README's
`recover-deletion` procedure applies to one deleting account only and requires
all writers to be stopped first. It is not safe to clear active-write counters
while workers are still running. Messages already in flight to an email provider
cannot be recalled.