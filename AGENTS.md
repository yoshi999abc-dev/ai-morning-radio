# AGENTS.md — 朝のAIラジオの台本を作る AI（秘書）へ

このリポジトリは、毎朝のAIニュースを聴ける個人ラジオ局です（[myradio](https://github.com/monoradio102/myradio) のテンプレートから作った1言語・日本語だけの局）。番組は「毎朝のAIニュース」だけです。

## 役割分担

| 担当 | やること |
|---|---|
| 秘書（AI） | 台本 `episodes/<YYYY-MM-DD>.json` を1本作り、ブランチ `episode/<YYYY-MM-DD>` に置いて PR を出す。**声・時刻・`episodes.json` は触らない** |
| 本人 | PR の台本を確かめてマージする（出典の URL が実在するか、個人に関わる情報が入っていないか） |
| GitHub Actions（`.github/workflows/daily.yml`） | main に台本が入ったら、`tools/make_audio.py` で声を作り、台本に時刻を埋めて main に戻し、`tools/publish.sh` で `gh-pages`（GitHub Pages）に公開する |

## 台本の書き方（episodes/<YYYY-MM-DD>.json）

形の決まりは [docs/formats.md](docs/formats.md)。この局では次のとおりにする。

- ファイル名は `<日付>.json`（言語の接尾辞なし）。中の `date` はファイル名と同じ、`lang` は書かなくてよい（声を作るときに入る）
- 必ず入れる欄：`title`、`date`、`opening`、`closing`、`news[]`（`label`・`points`・`lines`・`url`）。`format` も `"monoradio/news-1"` と書く
- 話す文は `{"say": 読み上げ用, "show": 字幕用}`。`say` は読み間違えない形（英字の名前はカタカナ、数字は読みどおりの漢数字）、`show` はふつうの表記
- ニュースは3〜5本、全体で90秒前後（1文は15〜40字、全体で15〜20文が目安）
- `news[].url` は必ず付ける。事実は出典に書いてあることだけにする。URL は実在を確かめたものだけを使う。確かめられないものは入れない
- `news[].link`（リンクカード）は任意。入れるときは、記事のサイトが共有用に出している画像（OGP）の URL を書くだけにする（画像を保存しない）
- `lines_timed`・`segments`・`seconds`・`made_at` は書かない（Actions が埋める。手で書くと声とずれる）
- 台本は PR を通じて残り、公開される。個人に関わること（本人の予定・仕事・取り組み）は入れない

## 声

- 声は edge-tts（`ja-JP-NanamiNeural`）で作る。クレジットは `station.json` にある。変えるときは `station.json` の `credits`・`caster` も合わせる
- 音声は git に入れない（`.gitignore` 済み）。`gh-pages` に直近 30 日分だけ載る

## やってはいけないこと

- 音声を main にコミットしない
- 他人のサイトの画像を保存してリポジトリに入れない
- 声や素材のクレジットを消さない
- 秘密の情報（API キー、メールアドレス、ネットワークの名前）を JSON やツールに書かない
- main に直接コミットしない（台本は PR）。Actions のボットが時刻を戻すコミットだけは例外
