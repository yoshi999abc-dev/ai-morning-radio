# 朝のAIラジオ

きのうのAIニュースを、毎朝 90 秒で聴ける個人ラジオ局です。[myradio](https://github.com/monoradio102/myradio)（monoradio102、プログラムは MIT）のテンプレートから作りました。

- 番組：毎朝のAIニュースだけ
- 聴く場所：GitHub Pages（`gh-pages` ブランチ）。`station.json` の `url`
- 台本：`episodes/<日付>.json`（秘書が作って PR → 本人がマージ）。作り方は [AGENTS.md](AGENTS.md)
- 声：edge-tts（`ja-JP-NanamiNeural`）。GitHub Actions で作る。音声は main に入れず、`gh-pages` に直近 30 日分だけ載せる

## 流れ

1. 秘書が台本を `episode/<日付>` ブランチに置いて PR を出す
2. 本人が確かめてマージする
3. `.github/workflows/daily.yml` が、声を作る → 時刻を台本に埋めて main に戻す → `tools/publish.sh` で公開する

## 初回の設定（手作業）

1. 最初の公開のあと（`gh-pages` ブランチができてから）、Settings → Pages で、配信元を `gh-pages` ブランチ・`/`（root）にする
2. 無料プランの非公開リポジトリは、Pages を有効にできない（GitHub Pro 以上か、公開リポジトリが要る）。公開にすると、台本・PR・Actions のログが誰にでも見える
3. Actions を一度手動で流す（Actions → publish → Run workflow）。edge-tts が Actions のサーバーから使えるかは、ここで分かる

## 中身

```
station.json                  局の自己紹介
index.html                    プレーヤー（myradio）
episodes.json                 回の一覧（Actions が更新する）
episodes/<日付>.json          台本と時刻
audio/<日付>.mp3              声（main には入れない）
character/                    キャスター（myradio のキャラクター）
tools/make_audio.py           声を作り、台本に時刻を埋める
tools/publish.sh              gh-pages への公開（myradio）
.github/workflows/daily.yml   Actions
docs/formats.md               JSON の形（myradio）
```

## ライセンス

[LICENSE](LICENSE) のとおり（プログラム部分は MIT、台本は CC0）。キャラクター（`character/`）は myradio のもので、公序良俗に反しない使い方なら自由に使えます。声は Microsoft Edge の読み上げ（edge-tts）を使っています。
