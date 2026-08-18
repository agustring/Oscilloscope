[app]
title = MSO2024 Remote
project_dir = .
input_file = main.py
exec_directory = dist
project_file = pyproject.toml
icon = C:\Users\agustin.copita\AppData\Local\Programs\Python\Python313\Lib\site-packages\PySide6\scripts\deploy_lib\pyside_icon.ico

[python]
python_path = C:\Users\agustin.copita\AppData\Local\Programs\Python\Python313\python.exe
packages = Nuitka==4.0
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]
qml_files = mso2024_remote/qml/Main.qml,mso2024_remote/qml/ScopeTheme.qml,mso2024_remote/qml/components/PanZoomKnob.qml,mso2024_remote/qml/components/RotaryKnob.qml,mso2024_remote/qml/components/ScopeButton.qml,mso2024_remote/qml/components/SoftKey.qml,mso2024_remote/qml/menus/BottomBezelMenu.qml,mso2024_remote/qml/menus/SideBezelMenu.qml,mso2024_remote/qml/scope/ScopeDisplay.qml
excluded_qml_plugins = QtCharts,QtQuick3D,QtSensors,QtTest,QtWebEngine
modules = Core,Gui,Qml,Quick,QuickControls2
plugins = accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,platforminputcontexts,platforms,platforms/darwin,platformthemes,qmllint,qmltooling,scenegraph,vectorimageformats,wayland-decoration-client,wayland-graphics-integration-client,wayland-shell-integration,xcbglintegrations

[android]
wheel_pyside = 
wheel_shiboken = 
plugins = 

[nuitka]
macos.permissions = 
mode = onefile
extra_args = --quiet --noinclude-qt-translations --assume-yes-for-downloads --include-package=pyvisa --include-package=pyvisa_py --include-package=usb --include-package=libusb_package

[buildozer]
mode = debug
recipe_dir = 
jars_dir = 
ndk_path = 
sdk_path = 
local_libs = 
arch = 

