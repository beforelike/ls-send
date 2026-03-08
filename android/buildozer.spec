#Application
title = LS send
package.name = lssend
package.domain = com.ls

# (str) Source code directory of the application. Default is ./src
source.dir = .

# (str) Source code main file.
source.main = main.py

# (list) Source code extensions.
source.extens = py,kv

source.include_exts = py,kv

# (str) Application version
version = 0.1

# (str) Android SDK version to use
#android.sdk = 20

# (str) Android NDK version to use
#android.ndk = 19b

# (str) Android NDK directory to use
#android.ndk_path = /opt/android-ndk-r19b

# (str) Android SDK directory to use
#android.sdk_path = /opt/android-sdk

# (bool) Use androidx (arcrow)
android.use_androidx = True

# (bool) Enable JKB support
#android.enable_jkb = True

# (str) Python version to use
#python.version = 3.8

# (str) Python site-packages path to include in the APK
#android.add_site-packages = /opt/python-site-packages

# (list) APK architectures to build
android.arch = armeabi-v7a

# (bool) Build with DEBUG mode
#android.debug = 1

# (bool) Build with release mode
#android.release = 1

# (str) Initial orientation orientation
android.orientation = portrait

# (bool) Wake screen on notification
android.wake_screen = 1

# (str) Permission to add to AndroidManifest.xml
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target SDK version
android.api = 31

# (int) Minimum SDK version
android.minapi = 21

# (bool) Use the SDL2 window
#android.sdl2 = True

# (str) Private assets directory
android.private_assets = assets/

# (bool) Copy just the assets directory
android.copy_assets = True

# (str) Log level
android.log_level = 2

# (bool) Use, ignore ndk warnings
android.ignore_ndk_warnings = True

# (bool) Use, ignore python warnings
android.ignore_python_warnings = True

# (bool) Use, ignore all warnings
android.ignore_all_warnings = True

# (str) Extra python packages to add to the APK
android.add_packages = android.permission

# (str) Extra python files to add to the APK
android.add_files = main.py,locale/

# (str) Extra python directories to add to the APK
android.add_src = .

# (str) Extra Java libraries to add to the APK
#android.add_libs = lib/*

# (str) Extra Java source directories to add to the APK
#android.add_src_jar = src/

# (str) Extra Java assets to add to the APK
#android.add_assets = assets/

# (str) Extra Java resources to add to the APK
#android.add_resources = res/

# (str) Custom icon
#android.icon = icons/android-icon.png

# (str) Icon density
#android.icon_density = hdpi

# (str) Application title
#android.window_title = LS send

# (str) Application description
#android.window_description = A cross-platform file transfer tool

# (bool) Hide the application icon from the launcher
#android.hide_icon = False

# (bool) UseFullscreen mode
android.fullscreen = 1

# (bool) Use immersive mode
android.immersive = 1

# (bool) Use always-on-top mode
#android.always_on_top = False

# (str) Copyright
#android.copyright = (c) 2026 LS send

# (str) Author
#android.author = LS team

# (str) Author email
#android.author_email = support@lssend.com

# (str) Website
#android.website = https://lssend.com

# (str) Privacy policy URL
#android.privacy_policy_url = https://lssend.com/privacy

# (str) Google Play license key
#android.play_store_license_key =

# (str) Google Play public key
#android.play_store_public_key = 

# (str) Google Play encrypted key
#android.play_store_encrypted_key =

# (str) Google Play version code
#android.play_store_version_code = 1

# (str) Google Play version name
#android.play_store_version_name = 0.1

# (str) Google Play commit hash
#android.play_store_commit_hash =

# (str) Google Play release track
#android.play_store_release_track = production

# (str) Google Play internal track
#android.play_store_internal_track =

# (str) Google Play alpha track
#android.play_store_alpha_track =

# (str) Google Play beta track
#android.play_store_beta_track =

# (str) Google Play production track
#android.play_store_production_track =

# (str) Google Play testing track
#android.play_store_testing_track =

# (str) Google Play internal testing track
#android.play_store_internal_testing_track =

# (str) Google Play emergency track
#android.play_store_emergency_track =

# (str) Google Play specific track
#android.play_store_specific_track =

# (str) Google Play track
#android.play_store_track =

# (str) Google Play name
#android.play_store_name = LS send

# (str) Google Play description
#android.play_store_description = A cross-platform file transfer tool

# (str) Google Play category
#android.play_store_category = UTILITIES

# (str) Google Play rating
#android.play_store_rating = 0

# (str) Google Play reviews
#android.play_store_reviews = 

# (str) Google Play screenshots
#android.play_store_screenshots =

# (str) Google Play feature graphics
#android.play_store_feature_graphic =

# (str) Google Play icon
#android.play_store_icon =

# (str) Google Play banner
#android.play_store_banner =

# (str) Google Play TV banner
#android.play_store_tv_banner =

# (str) Google Play wear icon
#android.play_store_wear_icon =

# (str) Google Play auto icon
#android.play_store_auto_icon =

# (str) Google Play vr icon
#android.play_store_vr_icon =

# (str) Google Play icon
#android.play_store_icon =

# (str) Google Play banner
#android.play_store_banner =

# (str) Google Play TV banner
#android.play_store_tv_banner =

# (str) Google Play wear icon
#android.play_store_wear_icon =

# (str) Google Play auto icon
#android.play_store_auto_icon =

# (str) Google Play vr icon
#android.play_store_vr_icon =
