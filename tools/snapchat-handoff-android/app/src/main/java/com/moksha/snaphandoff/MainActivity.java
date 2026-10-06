package com.moksha.snaphandoff;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.core.content.FileProvider;

import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String PREFS = "moksha_snap_handoff";
    private static final String DEFAULT_BASE = "https://mokshagoa.com";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;
    private EditText baseUrl;
    private EditText deviceKey;
    private TextView status;
    private Button checkButton;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        setContentView(buildUi());
    }

    private ScrollView buildUi() {
        int pad = (int) (20 * getResources().getDisplayMetrics().density);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Moksha Snap Handoff");
        title.setTextSize(24f);
        title.setTextColor(Color.BLACK);
        body.addView(title);

        TextView note = new TextView(this);
        note.setText("Claims the next prepared Moksha Snap and opens Snapchat Preview. Final Story/send confirmation remains inside Snapchat.");
        note.setPadding(0, pad / 2, 0, pad);
        body.addView(note);

        baseUrl = new EditText(this);
        baseUrl.setHint("WordPress URL");
        baseUrl.setSingleLine(true);
        baseUrl.setText(prefs.getString("base_url", DEFAULT_BASE));
        body.addView(baseUrl, fullWidth());

        deviceKey = new EditText(this);
        deviceKey.setHint("Android pairing key");
        deviceKey.setSingleLine(true);
        deviceKey.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        deviceKey.setText(prefs.getString("device_key", ""));
        body.addView(deviceKey, fullWidth());

        Button save = new Button(this);
        save.setText("Save pairing");
        save.setOnClickListener(v -> {
            prefs.edit()
                    .putString("base_url", normalizedBase())
                    .putString("device_key", deviceKey.getText().toString().trim())
                    .apply();
            setStatus("Pairing saved locally.");
        });
        body.addView(save, fullWidth());

        checkButton = new Button(this);
        checkButton.setText("Check & open next Snap");
        checkButton.setOnClickListener(v -> claimNext());
        body.addView(checkButton, fullWidth());

        status = new TextView(this);
        status.setPadding(0, pad, 0, 0);
        status.setText("Ready.");
        body.addView(status, fullWidth());

        ScrollView scroll = new ScrollView(this);
        scroll.addView(body);
        return scroll;
    }

    private LinearLayout.LayoutParams fullWidth() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
    }

    private String normalizedBase() {
        String value = baseUrl.getText().toString().trim();
        if (value.isEmpty()) value = DEFAULT_BASE;
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        return value;
    }

    private void claimNext() {
        String key = deviceKey.getText().toString().trim();
        if (key.length() < 24) {
            setStatus("Enter the pairing key from Engagement Core first.");
            return;
        }
        setBusy(true, "Checking queue…");
        executor.execute(() -> {
            try {
                JSONObject response = getJson(
                        normalizedBase() + "/wp-json/engagement-core/v1/snapchat/device/next",
                        key
                );
                JSONObject task = response.optJSONObject("task");
                if (task == null) {
                    runOnUiThread(() -> setBusy(false, "No pending Snapchat handoffs."));
                    return;
                }

                String id = task.getString("id");
                String mediaUrl = task.getString("media_url");
                String mediaType = task.getString("media_type");
                String clientId = task.getString("client_id");
                String caption = task.optString("caption", "");

                File media = download(mediaUrl, mediaType, id);
                runOnUiThread(() -> openSnapchat(id, clientId, mediaType, caption, media, key));
            } catch (Exception e) {
                runOnUiThread(() -> setBusy(false, "Error: " + e.getMessage()));
            }
        });
    }

    private void openSnapchat(
            String taskId,
            String clientId,
            String mediaType,
            String caption,
            File media,
            String key
    ) {
        String mime = "video".equals(mediaType) ? "video/*" : "image/*";
        Uri uri = FileProvider.getUriForFile(
                this,
                getPackageName() + ".fileprovider",
                media
        );

        try {
            grantUriPermission(
                    "com.snapchat.android",
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
            );
            Intent intent = SnapCreativeKitLite.preview(
                    getApplicationContext(),
                    clientId,
                    mime,
                    uri,
                    caption
            );
            startActivity(intent);
            setBusy(false, "Opened Snapchat Preview. Finish the Story/send in Snapchat.");
            executor.execute(() -> complete(taskId, "opened", "", key));
        } catch (ActivityNotFoundException e) {
            setBusy(false, "Snapchat is not installed.");
            executor.execute(() -> complete(taskId, "failed", "Snapchat is not installed", key));
        } catch (Exception e) {
            setBusy(false, "Unable to open Snapchat: " + e.getMessage());
            executor.execute(() -> complete(taskId, "failed", e.getMessage(), key));
        }
    }

    private File download(String source, String mediaType, String id) throws Exception {
        File dir = new File(getCacheDir(), "snap-media");
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IllegalStateException("Cannot create media cache.");
        }
        File out = new File(dir, id + ("video".equals(mediaType) ? ".mp4" : ".jpg"));

        HttpURLConnection connection = (HttpURLConnection) new URL(source).openConnection();
        connection.setConnectTimeout(20000);
        connection.setReadTimeout(90000);
        connection.setInstanceFollowRedirects(true);
        connection.connect();

        int code = connection.getResponseCode();
        if (code < 200 || code >= 300) {
            connection.disconnect();
            throw new IllegalStateException("Media download HTTP " + code);
        }

        try (BufferedInputStream input = new BufferedInputStream(connection.getInputStream());
             FileOutputStream output = new FileOutputStream(out)) {
            byte[] buffer = new byte[16384];
            int read;
            long total = 0;
            while ((read = input.read(buffer)) != -1) {
                total += read;
                if (total > 100L * 1024L * 1024L) {
                    throw new IllegalStateException("Media exceeds 100 MB safety limit.");
                }
                output.write(buffer, 0, read);
            }
        } finally {
            connection.disconnect();
        }
        return out;
    }

    private JSONObject getJson(String endpoint, String key) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
        connection.setRequestMethod("GET");
        connection.setRequestProperty("X-GREC-Snap-Key", key);
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(30000);
        return readJson(connection);
    }

    private void complete(String id, String completionStatus, String error, String key) {
        try {
            URL endpoint = new URL(
                    normalizedBase() + "/wp-json/engagement-core/v1/snapchat/device/complete"
            );
            HttpURLConnection connection = (HttpURLConnection) endpoint.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("X-GREC-Snap-Key", key);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setDoOutput(true);
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);

            JSONObject body = new JSONObject();
            body.put("id", id);
            body.put("status", completionStatus);
            body.put("error", error == null ? "" : error);
            byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
            connection.getOutputStream().write(bytes);
            readJson(connection);
        } catch (Exception ignored) {
            // The task will become claimable again after the server claim TTL if completion fails.
        }
    }

    private JSONObject readJson(HttpURLConnection connection) throws Exception {
        int code = connection.getResponseCode();
        BufferedReader reader = new BufferedReader(
                new InputStreamReader(
                        code >= 200 && code < 300
                                ? connection.getInputStream()
                                : connection.getErrorStream(),
                        StandardCharsets.UTF_8
                )
        );
        StringBuilder raw = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) raw.append(line);
        reader.close();
        connection.disconnect();

        JSONObject json = new JSONObject(raw.toString());
        if (code < 200 || code >= 300 || !json.optBoolean("ok", false)) {
            throw new IllegalStateException(json.optString("error", "HTTP " + code));
        }
        return json;
    }

    private void setBusy(boolean busy, String message) {
        checkButton.setEnabled(!busy);
        setStatus(message);
    }

    private void setStatus(String message) {
        status.setText(message);
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}
