package app.paytience;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Paytience Android client: a thin full-screen WebView around the Paytience
 * dashboard that the user runs on their own computer. It stores only the
 * server address (never passwords); login happens inside the web app.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "paytience";
    private static final String KEY_URL = "server_url";
    private static final String DEFAULT_PREFILL = "http://192.168.1.";

    private static final int BG = 0xFF0A1020;
    private static final int PANEL = 0xFF121A30;
    private static final int BLUE = 0xFF6FA8FF;
    private static final int GOLD = 0xFFD4AF37;

    private FrameLayout root;
    private WebView webView;
    private View overlay;
    private String baseUrl;
    private boolean mainFrameFailed;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        root = new FrameLayout(this);
        root.setBackgroundColor(BG);
        setContentView(root);

        baseUrl = prefs().getString(KEY_URL, null);
        if (baseUrl == null || baseUrl.isEmpty()) {
            showSetup(null);
        } else {
            openDashboard(baseUrl);
        }
    }

    private SharedPreferences prefs() {
        return getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private int dp(int v) {
        return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v,
                getResources().getDisplayMetrics());
    }

    // ---------------------------------------------------------------- overlays

    private void setOverlay(View v) {
        if (overlay != null) {
            root.removeView(overlay);
        }
        overlay = v;
        if (v != null) {
            root.addView(v, new FrameLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        }
    }

    private LinearLayout panel() {
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setGravity(Gravity.CENTER_HORIZONTAL);
        col.setPadding(dp(24), dp(48), dp(24), dp(24));
        return col;
    }

    private View wrap(LinearLayout col) {
        ScrollView sv = new ScrollView(this);
        sv.setBackgroundColor(BG);
        sv.setFillViewport(true);
        sv.addView(col, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        sv.setClickable(true); // swallow touches so the WebView underneath is inert
        return sv;
    }

    private TextView text(String s, int color, int sp, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextColor(color);
        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, sp);
        t.setGravity(Gravity.CENTER_HORIZONTAL);
        if (bold) {
            t.setTypeface(Typeface.DEFAULT_BOLD);
        }
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.bottomMargin = dp(12);
        t.setLayoutParams(lp);
        return t;
    }

    private Button button(String label, boolean primary, View.OnClickListener onClick) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(TypedValue.COMPLEX_UNIT_SP, 17);
        b.setTextColor(primary ? BG : GOLD);
        GradientDrawable bg = new GradientDrawable();
        bg.setCornerRadius(dp(10));
        if (primary) {
            bg.setColor(GOLD);
        } else {
            bg.setColor(PANEL);
            bg.setStroke(dp(1), GOLD);
        }
        b.setBackground(bg);
        b.setOnClickListener(onClick);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(52));
        lp.topMargin = dp(12);
        b.setLayoutParams(lp);
        return b;
    }

    private void showSetup(String message) {
        hideKeyboard();
        if (webView != null) {
            webView.stopLoading();
        }
        LinearLayout col = panel();
        col.addView(text("Paytience", GOLD, 30, true));
        col.addView(text("Enter your Paytience address", BLUE, 18, false));
        if (message != null) {
            col.addView(text(message, GOLD, 15, false));
        }

        final EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setImeOptions(EditorInfo.IME_ACTION_GO);
        input.setTextColor(BLUE);
        input.setHintTextColor(0x996FA8FF);
        input.setHint("http://192.168.1.20:8000");
        input.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        GradientDrawable ibg = new GradientDrawable();
        ibg.setCornerRadius(dp(10));
        ibg.setColor(PANEL);
        ibg.setStroke(dp(1), BLUE);
        input.setBackground(ibg);
        input.setPadding(dp(14), dp(12), dp(14), dp(12));
        String saved = prefs().getString(KEY_URL, null);
        String prefill = (saved != null && !saved.isEmpty()) ? saved : DEFAULT_PREFILL;
        input.setText(prefill);
        input.setSelection(prefill.length());
        LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        ilp.topMargin = dp(12);
        input.setLayoutParams(ilp);
        col.addView(input);

        final Runnable connect = new Runnable() {
            @Override
            public void run() {
                String url = normalize(input.getText().toString());
                if (url == null) {
                    Toast.makeText(MainActivity.this,
                            "That does not look like an address, e.g. http://192.168.1.20:8000",
                            Toast.LENGTH_LONG).show();
                    return;
                }
                prefs().edit().putString(KEY_URL, url).apply();
                hideKeyboard();
                openDashboard(url);
            }
        };
        input.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
                connect.run();
                return true;
            }
        });
        col.addView(button("Connect", true, new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                connect.run();
            }
        }));

        TextView help = text("On your computer run: python3 start.py --phone — it prints the address. "
                + "Same Wi-Fi only, or use your Cloudflare Tunnel https address.", BLUE, 15, false);
        ((LinearLayout.LayoutParams) help.getLayoutParams()).topMargin = dp(24);
        col.addView(help);

        setOverlay(wrap(col));
        input.requestFocus();
    }

    private void showError(String detail) {
        LinearLayout col = panel();
        col.addView(text("Paytience", GOLD, 30, true));
        col.addView(text("Can't reach Paytience", BLUE, 20, true));
        col.addView(text("Make sure Paytience is running on your computer and your phone is on the "
                + "same Wi-Fi (or the tunnel is up).", BLUE, 15, false));
        col.addView(text(baseUrl == null ? "" : baseUrl, GOLD, 14, false));
        if (detail != null && !detail.isEmpty()) {
            col.addView(text(detail, 0xAA6FA8FF, 13, false));
        }
        col.addView(button("Retry", true, new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                retry();
            }
        }));
        col.addView(button("Change address", false, new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showSetup(null);
            }
        }));
        setOverlay(wrap(col));
    }

    // ---------------------------------------------------------------- web view

    static String normalize(String raw) {
        if (raw == null) {
            return null;
        }
        String s = raw.trim();
        if (s.isEmpty()) {
            return null;
        }
        if (!s.contains("://")) {
            s = "http://" + s;
        }
        Uri u = Uri.parse(s);
        String scheme = u.getScheme();
        String host = u.getHost();
        if (scheme == null || host == null || host.isEmpty() || host.endsWith(".")
                || !(scheme.equalsIgnoreCase("http") || scheme.equalsIgnoreCase("https"))) {
            return null;
        }
        return s;
    }

    private void ensureWebView() {
        if (webView != null) {
            return;
        }
        webView = new WebView(this);
        webView.setBackgroundColor(BG);
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setAllowFileAccess(false);
        ws.setAllowContentAccess(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        CookieManager cm = CookieManager.getInstance();
        cm.setAcceptCookie(true);
        cm.setAcceptThirdPartyCookies(webView, false);

        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri target = request.getUrl();
                if (isSameHost(target)) {
                    return false;
                }
                openExternal(target);
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                mainFrameFailed = false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                if (clearHistoryAfterLoad && !mainFrameFailed) {
                    clearHistoryAfterLoad = false;
                    view.clearHistory(); // the dashboard root is the bottom of the back stack
                }
                if (!mainFrameFailed && overlay != null && isSameHost(Uri.parse(url))) {
                    setOverlay(null);
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    mainFrameFailed = true;
                    showError(String.valueOf(error.getDescription()));
                }
            }
        });
        root.addView(webView, 0, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
    }

    private boolean isSameHost(Uri target) {
        if (baseUrl == null || target == null || target.getHost() == null) {
            return false;
        }
        String scheme = target.getScheme();
        if (scheme == null || !(scheme.equals("http") || scheme.equals("https"))) {
            return false;
        }
        String baseHost = Uri.parse(baseUrl).getHost();
        return baseHost != null && baseHost.equalsIgnoreCase(target.getHost());
    }

    private void openExternal(Uri uri) {
        try {
            Intent i = new Intent(Intent.ACTION_VIEW, uri);
            i.addCategory(Intent.CATEGORY_BROWSABLE);
            startActivity(i);
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, "No app can open " + uri, Toast.LENGTH_LONG).show();
        }
    }

    private void openDashboard(String url) {
        baseUrl = url;
        ensureWebView();
        mainFrameFailed = false;
        webView.clearHistory();
        webView.loadUrl(url);
        // Keep a dark cover up until the first page finishes (or fails).
        LinearLayout col = panel();
        col.addView(text("Paytience", GOLD, 30, true));
        col.addView(text("Connecting to " + url + " …", BLUE, 15, false));
        setOverlay(wrap(col));
        clearHistoryAfterLoad = true;
    }

    private boolean clearHistoryAfterLoad;

    private void retry() {
        if (baseUrl == null) {
            showSetup(null);
            return;
        }
        String current = webView != null ? webView.getUrl() : null;
        if (current == null || current.startsWith("data:") || current.startsWith("about:")) {
            openDashboard(baseUrl);
        } else {
            mainFrameFailed = false;
            LinearLayout col = panel();
            col.addView(text("Paytience", GOLD, 30, true));
            col.addView(text("Reconnecting …", BLUE, 15, false));
            setOverlay(wrap(col));
            webView.reload();
        }
    }

    private void hideKeyboard() {
        View f = getCurrentFocus();
        if (f != null) {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) {
                imm.hideSoftInputFromWindow(f.getWindowToken(), 0);
            }
        }
    }

    // ---------------------------------------------------------------- back / lifecycle

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        if (overlay != null) {
            // On the setup or error screen: go back to the dashboard if we have one, else exit.
            if (baseUrl != null && webView != null && !mainFrameFailed && webView.getUrl() != null) {
                setOverlay(null);
            } else {
                showExitDialog();
            }
            return;
        }
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        showExitDialog();
    }

    private void showExitDialog() {
        new AlertDialog.Builder(this)
                .setTitle("Paytience")
                .setItems(new CharSequence[]{"Change server address", "Exit"},
                        new DialogInterface.OnClickListener() {
                            @Override
                            public void onClick(DialogInterface dialog, int which) {
                                if (which == 0) {
                                    showSetup(null);
                                } else {
                                    finish();
                                }
                            }
                        })
                .setNegativeButton("Cancel", null)
                .show();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.onResume();
        }
    }

    @Override
    protected void onPause() {
        if (webView != null) {
            webView.onPause();
        }
        CookieManager.getInstance().flush();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            root.removeView(webView);
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
