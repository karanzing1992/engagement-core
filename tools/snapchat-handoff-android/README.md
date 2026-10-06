# Moksha Snap Handoff Android

Small Android companion for Engagement Core's Snapchat queue.

It uses Snapchat Creative Kit Lite's public Android intent flow:
- full-screen photo/video
- optional caption
- opens Snapchat Preview
- user finishes the Story/send inside Snapchat

It does **not** claim that a handoff equals a published Story.

## Requirements

- Android 7.0+
- Snapchat installed
- Moksha Snap app registered and approved in the Snap Developer Portal
- Snap Client ID saved in Engagement Core
- Android pairing key copied from Engagement Core

## Build

From this directory:

```bash
gradle :app:assembleDebug
```

APK output:

`app/build/outputs/apk/debug/app-debug.apk`

## Pair

1. Open WordPress → Engagement Core → Snapchat Handoff.
2. Save the approved Snap Client ID.
3. Copy the Android pairing key.
4. Open Moksha Snap Handoff on the Android device.
5. WordPress URL: `https://mokshagoa.com`
6. Paste the pairing key and tap **Save pairing**.

## Use

From Engagement Core:
1. Write caption.
2. Pick one 9:16 photo or video from the WordPress Media Library.
3. Tap **Queue for Snapchat**.

On Android:
1. Tap **Check & open next Snap**.
2. The app claims the next queue item and downloads it.
3. Snapchat opens directly in Preview with the media and caption.
4. Finish editing and choose Story, friend, or group in Snapchat.

The queue records `opened`, not `published`, because Snapchat requires the final user action.

## Security

The pairing key is stored in the Android app's private SharedPreferences and is sent only as the `X-GREC-Snap-Key` HTTPS header to Moksha WordPress.

No Snapchat password, session cookie, or OAuth secret is stored in this repository.
