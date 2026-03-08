[app]

# (str) Title of your application
title = LS send

# (str) Package name
package.name = lssend

# (str) Package domain
package.domain = com.ls

# (str) Source code directory
source.dir = .

# (str) Source code main file
source.main = main.py

# (list) Source code extensions
source.include_exts = py,kv

# (str) Application version
version = 0.1

# (list) APK architectures to build
android.arch = armeabi-v7a

# (bool) Use fullscreen mode
android.fullscreen = 1

# (str) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Target SDK version
android.api = 31

# (int) Minimum SDK version
android.minapi = 21

# (str) Application author
android.author = LS team

# (str) Application description
android.window_description = A cross-platform file transfer tool

# (str) Log level
android.log_level = 2

# (str) Requirements
requirements = kivy>=2.3.0,plyer>=2.1.0,websockets>=11.0

# (bool) Use AndroidX support
android.androidx = True

# (str) Android logcat filter
android.logcat_filter = *:S Python:D

# (bool) Copy libraries instead of symlinking
android.copy_libs = True
