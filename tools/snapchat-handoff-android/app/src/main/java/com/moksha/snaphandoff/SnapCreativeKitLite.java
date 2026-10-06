package com.moksha.snaphandoff;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;

public final class SnapCreativeKitLite {
    private static final String SNAPCHAT_PACKAGE = "com.snapchat.android";
    private static final String PREVIEW_URI = "snapchat://creativekit/preview";
    private static final String CLIENT_ID_EXTRA = "CLIENT_ID";
    private static final String CAPTION_EXTRA = "captionText";
    private static final String RESULT_INTENT_EXTRA = "RESULT_INTENT";
    private static final int REQUEST_CODE = 9071;

    private SnapCreativeKitLite() {}

    public static Intent preview(
            Context context,
            String clientId,
            String mimeType,
            Uri mediaUri,
            String caption
    ) {
        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setPackage(SNAPCHAT_PACKAGE);
        intent.setDataAndType(Uri.parse(PREVIEW_URI), mimeType);
        intent.putExtra(CLIENT_ID_EXTRA, clientId);
        intent.putExtra(Intent.EXTRA_STREAM, mediaUri);
        if (caption != null && !caption.trim().isEmpty()) {
            intent.putExtra(CAPTION_EXTRA, caption);
        }
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                ? PendingIntent.FLAG_IMMUTABLE
                : PendingIntent.FLAG_ONE_SHOT;
        PendingIntent resultIntent = PendingIntent.getActivity(
                context,
                REQUEST_CODE,
                new Intent(),
                flags
        );
        intent.putExtra(RESULT_INTENT_EXTRA, resultIntent);
        return intent;
    }
}
