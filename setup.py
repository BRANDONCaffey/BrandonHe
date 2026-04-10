from setuptools import setup


APP = ["launch_frontend.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "AI Info Collection",
        "CFBundleDisplayName": "AI Info Collection",
        "CFBundleIdentifier": "com.local.ai-info-collection",
        "CFBundleShortVersionString": "0.1.0",
        "LSMinimumSystemVersion": "11.0",
    },
    "packages": ["ai_info_collection"],
    "includes": ["webview"],
}

setup(
    app=APP,
    name="AI Info Collection",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
