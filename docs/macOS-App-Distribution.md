# macOS App Distribution (Skeleton)

## 1. Build Local `.app`

```bash
./scripts/build_app.sh
```

产物：

- `dist/AI Info Collection.app`

## 2. Package for Sharing

```bash
./scripts/package_app.sh
```

产物：

- `dist/AI-Info-Collection-<timestamp>.zip`

## 3. Optional: Sign

```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application: <TEAM_ORG>" "dist/AI Info Collection.app"
codesign --verify --deep --strict --verbose=2 "dist/AI Info Collection.app"
```

## 4. Optional: Notarize

```bash
xcrun notarytool submit "dist/AI-Info-Collection-<timestamp>.zip" \
  --apple-id "<APPLE_ID>" \
  --team-id "<TEAM_ID>" \
  --password "<APP_SPECIFIC_PASSWORD>" \
  --wait

xcrun stapler staple "dist/AI Info Collection.app"
```

## 5. Notes

- 首版目标是“本机可用 + 可分享打包”，签名/公证是可选增强。
- 若目标用户机器安全策略严格，建议启用签名与公证。
