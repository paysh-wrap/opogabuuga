# Paytience for Android

A small Android app (`app.paytience`, Android 7.0+) that shows your Paytience dashboard full-screen.
Paytience itself keeps running on **your computer**; the app only remembers its address (never a password —
you log in inside the dashboard as usual).

## Install on your phone

1. Copy `android/dist/Paytience.apk` to your phone (USB cable, Google Drive, e-mail to yourself, …).
2. On the phone, open the file (Files / Downloads app).
3. Android asks to **allow "Install unknown apps"** for that app (Files, Chrome, Drive…) — allow it, go back, tap **Install**.
   Play Protect may warn that the app is from an unknown developer: tap *More details → Install anyway*.
4. Open **Paytience** from the app drawer.
5. On your computer run `python3 start.py --phone` — it prints the address (e.g. `http://192.168.1.20:8000`).
   Type that address into the app and tap **Connect**. The phone must be on the same Wi-Fi,
   or use your Cloudflare Tunnel `https://…` address instead.

Tips: **Back** goes back inside the dashboard; at the start page it offers *Change server address* / *Exit*.
If the computer is off or unreachable you get a *Retry* / *Change address* screen.
Links to other websites open in your normal browser.

## Rebuild (developers)

No Gradle needed — `build.sh` runs `aapt2 → javac → d8 → zipalign → apksigner` directly.

```bash
# one-time: Android SDK into android/.sdk (gitignored)
mkdir -p android/.sdk && cd android/.sdk
curl -LO https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip -q commandlinetools-linux-*_latest.zip -d tmp && mkdir -p cmdline-tools \
  && mv tmp/cmdline-tools cmdline-tools/latest && rm -rf tmp commandlinetools-linux-*_latest.zip
yes | cmdline-tools/latest/bin/sdkmanager --sdk_root=$PWD --licenses
cmdline-tools/latest/bin/sdkmanager --sdk_root=$PWD "platforms;android-34" "build-tools;35.0.0"
cd ../..

# build (JDK 17+)
android/build.sh          # → android/dist/Paytience.apk
```

The first build creates a personal signing key at `android/.keystore/paytience.jks` (password in
`android/.keystore/password.txt`; both gitignored). **Keep them**: Android only installs an update over an
existing install when it is signed with the same key — with a new key, uninstall the old app first.
`ANDROID_SDK_ROOT` overrides the SDK location; `BUILD_TOOLS` the build-tools version.

Files: `AndroidManifest.xml`, `src/app/paytience/MainActivity.java` (the whole app, no libraries),
`res/` (theme `#0A1020`, launcher icons from `frontend/public/icon-*.png`, cleartext-HTTP config for the LAN).
