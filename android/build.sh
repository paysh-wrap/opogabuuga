#!/usr/bin/env bash
# Build android/dist/Paytience.apk without Gradle: javac -> d8 -> aapt2 -> zipalign -> apksigner.
# Needs JDK 17+ and an Android SDK with "platforms;android-34" and "build-tools;35.0.0".
# (build-tools 34.0.0's d8 crashes on JDK 21 class files: MethodParameters with no name.)
# SDK location: $ANDROID_SDK_ROOT, else android/.sdk (see README.md for the one-time install).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
SDK="${ANDROID_SDK_ROOT:-$HERE/.sdk}"
BT="$SDK/build-tools/${BUILD_TOOLS:-35.0.0}"
JAR="$SDK/platforms/android-34/android.jar"
for f in "$BT/aapt2" "$BT/d8" "$BT/zipalign" "$BT/apksigner" "$JAR"; do
  [ -e "$f" ] || { echo "missing $f — install the SDK first (README.md)"; exit 1; }
done

OUT="$HERE/build"; rm -rf "$OUT"; mkdir -p "$OUT"/{res,gen,classes,dex} "$HERE/dist"

# 1. resources
"$BT/aapt2" compile --dir res -o "$OUT/res/res.zip"
"$BT/aapt2" link -o "$OUT/unsigned.apk" -I "$JAR" --manifest AndroidManifest.xml \
  --java "$OUT/gen" --min-sdk-version 24 --target-sdk-version 34 \
  --version-code 1 --version-name 1.0 "$OUT/res/res.zip"

# 2. java -> classes -> dex
javac -J-Xmx256m -nowarn -Xlint:-options -source 1.8 -target 1.8 -encoding UTF-8 \
  -bootclasspath "$JAR" -d "$OUT/classes" \
  $(find src "$OUT/gen" -name '*.java')
"$BT/d8" --release --min-api 24 --lib "$JAR" --output "$OUT/dex" $(find "$OUT/classes" -name '*.class')
(cd "$OUT/dex" && zip -q -j "$OUT/unsigned.apk" classes.dex)

# 3. align + sign
"$BT/zipalign" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
KS="$HERE/.keystore/paytience.jks"
PASSFILE="$HERE/.keystore/password.txt"
if [ ! -f "$KS" ]; then
  mkdir -p "$HERE/.keystore"; chmod 700 "$HERE/.keystore"
  head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' > "$PASSFILE"; chmod 600 "$PASSFILE"
  keytool -genkeypair -keystore "$KS" -storetype PKCS12 -alias paytience -keyalg RSA -keysize 2048 \
    -validity 10000 -dname "CN=Paytience, O=Paytience (personal sideload)" \
    -storepass "$(cat "$PASSFILE")" -keypass "$(cat "$PASSFILE")"
fi
"$BT/apksigner" sign --ks "$KS" --ks-key-alias paytience --ks-pass "file:$PASSFILE" \
  --out "$HERE/dist/Paytience.apk" "$OUT/aligned.apk"
rm -f "$HERE/dist/Paytience.apk.idsig"
"$BT/apksigner" verify "$HERE/dist/Paytience.apk"
ls -la "$HERE/dist/Paytience.apk"
