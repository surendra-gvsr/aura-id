# agent/aura_agent.spec
a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src/pms_profiles/*.json', 'pms_profiles'),
        ('installer/icons/aura.ico', 'icons'),
    ],
    hiddenimports=['keyring.backends.Windows'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter.test'],
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AuraAgent',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
    icon='installer/icons/aura.ico',
)
