# ساخت APK انتشار تکه‌چین

این مسیر فقط APK آزمایشی انتشار می‌سازد و چیزی در بازار یا فروشگاه دیگری منتشر نمی‌کند. Android Studio لازم نیست؛ محیط ساخت را GitHub Actions فراهم می‌کند. گردش‌کار Debug قبلی مستقل باقی می‌ماند.

## وضعیت هویت برنامه

| مورد | مقدار فعلی |
| --- | --- |
| شناسه بسته | `com.example.puzzlepreview` (موقت) |
| نام نمایشی | پازل (هنوز نهایی نشده) |
| نسخه | `versionName=1.0` و `versionCode=1` |
| حداقل اندروید | API 24 / Android 7.0 |
| SDK هدف و کامپایل | API 36 |
| JDK | 21 |
| Capacitor | 8.6.2 |
| Gradle / AGP | 8.14.3 / 8.13.0 |

شناسه و نام را فقط پس از تأیید مالک نهایی کنید. برای به‌روزرسانی یک نصب قبلی، شناسه بسته و گواهی امضا باید یکسان باشند و کد نسخه افزایش یابد. نسخه Debug با گواهی متفاوت را نمی‌توان مستقیماً با Release جایگزین کرد؛ حذف Debug ممکن است پیشرفت محلی را پاک کند. قبل از حذف، داده‌های تست را در نظر بگیرید.

## کلید: فقط یک بار و تحت کنترل مالک

اگر کلید انتشار موجود است، همان کلید را استفاده کنید. این دستور فقط برای اولین کلید است. در یک پوشه خصوصی خارج از مخزن اجرا کنید؛ JDK 21 شامل `keytool` است. رمزها را در ورودی تعاملی خود keytool وارد کنید، نه آرگومان دستور و نه چت.

```powershell
keytool -genkeypair -storetype JKS -keystore tikechin-release.jks -alias tikechin-release -keyalg RSA -keysize 3072 -sigalg SHA256withRSA -validity 10000 -dname "CN=Tikechin"
keytool -exportcert -keystore tikechin-release.jks -alias tikechin-release -file tikechin-release.cer
(Get-FileHash -LiteralPath .\tikechin-release.cer -Algorithm SHA256).Hash
```

رمز مخزن و رمز کلید را مالک تعیین می‌کند. اگر برای رمز کلید Enter بزنید، keytool از رمز مخزن استفاده می‌کند؛ در این حالت همان مقدار را در هر دو Secret رمز ثبت کنید. رمز قوی را در مدیر رمز خود نگه دارید. فایل JKS رمزدار و رمزها را جدا نگه دارید و از فایل، یک پشتیبان مستقل ترجیحاً روی حافظه رمزگذاری‌شده تهیه کنید. یکسان بودن نسخه‌ها را با `Get-FileHash` بررسی کنید. GitHub Secrets جایگزین پشتیبان قابل بازیابی نیست. گواهی CER و اثر انگشت عمومی‌اند؛ فایل JKS خصوصی است.

## تنظیم GitHub Environment

پس از ادغام PR بررسی‌شده در `main`، به مخزن بروید:

1. **Settings → Environments → New environment**؛ نام دقیق `android-release`.
2. در **Deployment branches and tags** گزینه **Selected branches and tags** را انتخاب و فقط یک قانون از نوع **Branch** برای `main` اضافه کنید. Tag هم‌نام را مجاز نکنید.
3. اگر حساب پشتیبانی می‌کند، **Required reviewers** را برای بازبینی کد قبل از امضا تنظیم کنید. اگر خودتان تنها بازبین هستید، گزینه منع تأیید خودتان را طوری تنظیم نکنید که ساخت غیرممکن شود.
4. در همین Environment، بخش **Environment secrets → Add environment secret** چهار Secret زیر را ثبت کنید. آنها را در Repository secrets قرار ندهید تا شاخه‌های عادی به آنها دسترسی نداشته باشند.

| Secret | مقدار |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Base64 فایل JKS اصلی |
| `ANDROID_KEYSTORE_PASSWORD` | رمز مخزن |
| `ANDROID_KEY_ALIAS` | `tikechin-release` |
| `ANDROID_KEY_PASSWORD` | رمز همان کلید |

5. در **Environment variables → Add environment variable** متغیر `ANDROID_SIGNING_CERT_SHA256` را برابر SHA-256 گواهی CER ثبت کنید؛ ۶۴ نویسه هگز، با یا بدون دونقطه. این مقدار راز نیست و باید از گواهی اصلی مالک گرفته شود. مقدار دلخواه یا اثر انگشت یک کلید آزمایشی را جایگزین نکنید.

برای انتقال Base64، در PowerShell محلی مسیر واقعی کلید را جایگزین کنید. این دستور محتوای حساس را فقط در کلیپ‌بورد می‌گذارد؛ آن را فقط در Secret مربوطه بچسبانید و پس از ثبت کلیپ‌بورد را پاک کنید. Base64 رمزگذاری امنیتی نیست. اگر تاریخچه یا همگام‌سازی کلیپ‌بورد فعال است، از این روش استفاده نکنید؛ با ابزار قابل اعتماد محلی و بدون چاپ یا لاگ، Secret را ثبت کنید.

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('D:\private\tikechin-release.jks')) | Set-Clipboard
# After saving the secret:
Set-Clipboard -Value ''
```

فایل کلید، رمز یا Base64 را در issue، PR، لاگ، فایل تنظیمات تحت Git یا Artifact نگذارید. نام Secrets قابل مشاهده است، مقدار آنها نباید بازخوانی یا چاپ شود. محدودیت `main` در گردش‌کار جایگزین قانون Environment نیست: کاربری که به شاخه دیگری دسترسی نوشتن دارد نباید از گردش‌کار دیگری به کلید دسترسی پیدا کند.

## اجرای دستی و دریافت خروجی

1. **Actions → Android Release APK → Run workflow**، شاخه **main**؛ پس از Merge فایل گردش‌کار در فهرست دیده می‌شود.
2. اگر Environment بازبین دارد، ساخت را با کد بازبینی‌شده تأیید کنید.
3. پس از موفقیت گام **Sign, assemble and verify release**، در همان اجرا بخش **Artifacts → tikechin-release-apk** را دانلود کنید.
4. ZIP شامل `app-release.apk`، `release-verification.txt` و `app-release.apk.sha256` است؛ GitHub ممکن است مسیر پوشه‌ها را در ZIP حفظ کند. نگه‌داری Artifact برابر ۱۴ روز است؛ خروجی موردنیاز را در آرشیو خود ذخیره کنید.

فرمان واقعی ساخت از پوشه `android`، `./gradlew --no-daemon assembleRelease` است. قبل از آن `npm ci` و `npm run android:sync` اجرا می‌شود. فایل کلید فقط در `RUNNER_TEMP` بازسازی می‌شود و با trap و گام `always()` پاک می‌شود. رمزها فقط در گام امضا در دسترس‌اند. `--no-daemon` از نگه‌داری پردازش Gradle پس از ساخت جلوگیری می‌کند. Artifact فقط بعد از بررسی موفق بارگذاری می‌شود.

گام بررسی، `apksigner verify --verbose --print-certs` را اجرا می‌کند، SHA-256 گواهی APK را با گواهی کلید و مقدار مورد تأیید مالک مقایسه می‌کند، شناسه بسته و غیرقابل‌دیباگ بودن را بررسی می‌کند و HTML بسته‌بندی‌شده را بایت‌به‌بایت با بازی اصلی تطبیق می‌دهد. وجود فایل‌های رایج کلید و تنظیمات امضا در APK نیز رد می‌شود. این بررسی جایگزین بررسی جامع اسرار در منابع نیست؛ فقط فایل‌های موردنظر را برای کامیت stage کنید و diff را بازبینی کنید.

برای بررسی مستقل بعد از دانلود، از Build Tools 35.0.0 استفاده کنید:

```powershell
apksigner verify --verbose --print-certs .\app-release.apk
(Get-FileHash -LiteralPath .\app-release.apk -Algorithm SHA256).Hash
```

هش APK باید با فایل SHA256 همراه آن و گواهی با اثر انگشت اصلی مالک یکسان باشد. `release-verification.txt` نسخه، مجوزهای نهایی و جزئیات امضا را ثبت می‌کند. هیچ خروجی ساخته‌شده‌ای تا پیش از اجرای موفق این گام، تأییدشده محسوب نمی‌شود.

## ساخت محلی اختیاری

Gradle فقط این چهار متغیر محیطی را می‌خواند: `ANDROID_KEYSTORE_PATH` (ترجیحاً مسیر مطلق)، `ANDROID_KEYSTORE_PASSWORD`، `ANDROID_KEY_ALIAS` و `ANDROID_KEY_PASSWORD`. رمزها را با ورودی مخفی یا مدیر راز محلی به محیط همان پردازش بدهید؛ آنها را در دستور خطی، تاریخچه یا `gradle.properties` ذخیره نکنید. نبود هرکدام یا نبود فایل کلید، ساخت وظایف Release، از جمله وظایف تجمیعی `assemble` و `build` که Release را اجرا می‌کنند، متوقف می‌کند. Debug بدون کلید انتشار همچنان ساخته می‌شود.

## تست روی دستگاه

ساخت CI معادل نصب و تست نیست. روی دستگاه واقعی یا شبیه‌ساز، نصب، شش صفحه، انتخاب دسته و تصویر، لمس و کشیدن قطعات، تشخیص جای صحیح، تصویر مرجع، ذخیره و بازیابی پیشرفت بعد از بستن برنامه، نتیجه تکمیل، حالت پرواز و بازگشت اندروید را آزمایش کنید. منبع بازی منابع تعبیه‌شده دارد و Manifest فعلی مجوز اینترنت ندارد؛ اجرای آفلاین باید روی APK نهایی نیز آزمایش شود.

این APK با شناسه موقت برای تست انتشار است. ارسال واقعی به کافه‌بازار تنها پس از نهایی شدن نام و شناسه با تأیید مالک و بررسی الزامات جاری فروشگاه انجام می‌شود.

مراجع رسمی: [امضای اندروید](https://developer.android.com/studio/publish/app-signing)، [apksigner](https://developer.android.com/tools/apksigner)، [محیط‌های محافظت‌شده GitHub](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
