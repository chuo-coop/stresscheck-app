# ------------------------------------------------------------
# ストレスチェック簡易版（厚労省準拠 × 中大生協セルフケア版） ver2.2
# ------------------------------------------------------------
# 使い方:
#   1) 同フォルダに TITLE.png を置く（画面ヘッダー用。PDFには入れない）
#   2) `streamlit run app.py` で起動
# 必要ライブラリ:
#   pip install streamlit matplotlib reportlab pillow

import streamlit as st
import io
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader

# ========== 画面基本設定 ==========
st.set_page_config(page_title="ストレスチェック簡易版（中大生協）", layout="centered")
plt.rcParams['font.family'] = 'IPAexGothic'
plt.rcParams['axes.unicode_minus'] = False

# ========== 固定文言・色 ==========
APP_TITLE = "ストレスチェック簡易版（中大生協セルフケア版）"
CAPTION = "厚生労働省「職業性ストレス簡易調査票（57項目）」準拠／中央大学生活協同組合セルフケア版"
COLORS = {"A": "#8B0000", "B": "#003366", "C": "#004B23", "D": "#7B3F00"}
LABELS_EN = ["Workload", "Reaction", "Support", "Satisfaction"]
LABELS_JA = ["仕事の負担", "ストレス反応", "周囲の支援", "満足度"]

# ========== 設問（厚労省57項目・5件法対応） ==========
QUESTIONS = [
    # A群（17）
    "自分のペースで仕事ができる。","仕事の量が多い。","時間内に仕事を終えるのが難しい。",
    "仕事の内容が高度である。","自分の知識や技能を使う仕事である。","仕事に対して裁量がある。",
    "自分の仕事の役割がはっきりしている。","自分の仕事が組織の中で重要だと思う。",
    "仕事の成果が報われると感じる。","職場の雰囲気が良い。","職場の人間関係で気を使う。",
    "上司からのサポートが得られる。","同僚からのサポートが得られる。","仕事上の相談ができる相手がいる。",
    "顧客や取引先との関係がうまくいっている。","自分の意見が職場で尊重されている。","職場に自分の居場所がある。",
    # B群（29）
    "活気がある。","仕事に集中できる。","気分が晴れない。","ゆううつだ。","怒りっぽい。","イライラする。",
    "落ち着かない。","不安だ。","眠れない。","疲れやすい。","体がだるい。","頭が重い。","肩こりや腰痛がある。",
    "胃が痛い、食欲がない。","動悸や息苦しさがある。","手足の冷え、しびれがある。","めまいやふらつきがある。",
    "体調がすぐれないと感じる。","仕事をする気力が出ない。","集中力が続かない。","物事を楽しめない。",
    "自分を責めることが多い。","周りの人に対して興味がわかない。","自分には価値がないと感じる。",
    "将来に希望がもてない。","眠っても疲れがとれない。","小さなことが気になる。","涙もろくなる。","休日も疲れが残る。",
    # C群（9）
    "上司はあなたの意見を聞いてくれる。","上司は相談にのってくれる。","上司は公平に扱ってくれる。",
    "同僚は困ったとき助けてくれる。","同僚とは気軽に話ができる。","同僚と協力しながら仕事ができる。",
    "家族や友人はあなたを支えてくれる。","家族や友人に悩みを話せる。","家族や友人はあなたの仕事を理解してくれる。",
    # D群（2）
    "現在の仕事に満足している。","現在の生活に満足している。"
]

# 群タイプ（A=1-17, B=18-46, C=47-55, D=56-57）
Q_TYPE = (["A"]*17 + ["B"]*29 + ["C"]*9 + ["D"]*2)

# 逆転項目（1=逆転, 0=通常）
# A: 1,5,6,7,8,9,10,12,13,14,15,16,17 が逆転
# B: 18,19 が逆転
# C: 47-55 全て逆転
# D: 56-57 逆転
REVERSE = [
    # A(1-17)
    1,0,0,0, 1,1,1,1,1,1, 0,1,1,1,1,1,1,
    # B(18-46)
    1,1, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    # C(47-55)
    1,1,1,1,1,1,1,1,1,
    # D(56-57)
    1,1
]

# 回答選択肢（5件法・共通）
CHOICES = ["1：そうではない","2：あまりそうではない","3：どちらともいえない","4：ややそうだ","5：そうだ"]

# ========== セッション状態 ==========
if "page" not in st.session_state:
    st.session_state.page = 0
if "answers" not in st.session_state:
    st.session_state.answers = [None] * len(QUESTIONS)

def go_next():
    st.session_state.page += 1
    st.rerun()
def go_prev():
    if st.session_state.page > 0:
        st.session_state.page -= 1
        st.rerun()
def restart():
    st.session_state.page = 0
    st.session_state.answers = [None] * len(QUESTIONS)
    st.rerun()

# ========== 画面ヘッダー（ブラウザのみ。PDF非挿入） ==========
st.image("TITLE.png", use_column_width=True)
st.markdown(f"<p style='text-align:center; color:#555;'>{CAPTION}</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ========== 質問ページ or 解析ページ ==========
if st.session_state.page < len(QUESTIONS):
    q_num = st.session_state.page + 1
    st.subheader(f"Q{q_num} / {len(QUESTIONS)}")
    st.write(QUESTIONS[st.session_state.page])

    prev_val = st.session_state.answers[st.session_state.page]
    index_val = (prev_val - 1) if prev_val else None
    choice = st.radio("回答を選んでください：", CHOICES, index=index_val, key=f"q_{q_num}")

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # 縦配置：次へ → 前へ
    if choice:
        st.session_state.answers[st.session_state.page] = CHOICES.index(choice) + 1
        if st.button("次へ ▶"):
            go_next()

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if st.session_state.page > 0:
        if st.button("◀ 前へ"):
            go_prev()

else:
    # ===== 解析 =====
    st.subheader("解析結果")
    st.caption(f"実施日：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")

    ans = st.session_state.answers
    groups = {"A":[], "B":[], "C":[], "D":[]}
    for i, v in enumerate(ans):
        val = 6 - v if REVERSE[i]==1 else v
        groups[Q_TYPE[i]].append(val)

    def norm100(vals):
        s = sum(vals)
        mn, mx = len(vals), len(vals)*5
        return round((s - mn) / (mx - mn) * 100, 1)

    A = norm100(groups["A"])
    B = norm100(groups["B"])
    C = norm100(groups["C"])
    D = norm100(groups["D"])
    scores = {"A":A, "B":B, "C":C, "D":D}

    # 総合判定（厚労省ロジック準拠）
    if B >= 60 or (B >= 50 and (A >= 60 or C <= 40)):
        status = "高ストレス状態（専門家への相談を推奨）"
    elif B >= 50 or A >= 55 or C <= 45:
        status = "注意：ストレス反応や職場要因にやや高い傾向"
    else:
        status = "概ね安定しています（現状維持を心がけましょう）"

    st.markdown(f"**総合判定：{status}**")

    # ===== レーダーチャート（本人のみ） =====
    st.markdown("#### ストレスプロファイル（本人）")
    vals = [A, B, C, D]
    angles = np.linspace(0, 2*np.pi, 4, endpoint=False).tolist()
    vals_cyc = vals + [vals[0]]
    ang_cyc = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(4.8, 4.8), subplot_kw=dict(polar=True))
    ax.plot(ang_cyc, vals_cyc, color=COLORS["A"], linewidth=2)
    ax.fill(ang_cyc, vals_cyc, color=COLORS["A"], alpha=0.15)
    ax.set_xticks(angles)
    ax.set_xticklabels(LABELS_EN, color=COLORS["A"], fontweight="bold", fontsize=11)
    ax.set_yticklabels([])
    st.pyplot(fig)

    # ===== A〜D 詳細表示（色付き） =====
    st.markdown("#### 領域別サマリー")
    def area_comment(key, score):
        if key == "A":
            if score >= 60: return "仕事量や裁量のバランスに負担感が見られます。"
            if score < 45:  return "業務環境は安定しています。"
            return "おおむね良好です。"
        if key == "B":
            if score >= 60: return "心身のストレス反応が強い傾向です。休息・睡眠を優先しましょう。"
            if score < 45:  return "ストレス反応は安定しています。"
            return "軽い疲労傾向が見られます。"
        if key == "C":
            if score >= 60: return "周囲からの支援が十分に得られています。"
            if score < 45:  return "支援が不足している可能性があります。身近な人に相談を。"
            return "一定の支援が得られています。"
        if key == "D":
            if score >= 60: return "仕事・生活への満足度が高い状態です。"
            if score < 45:  return "満足度が低い可能性があります。見直しポイントの整理を。"
            return "概ね良好な満足度です。"
        return ""

    for key, name in zip(["A","B","C","D"], LABELS_JA):
        col = COLORS[key]
        st.markdown(
            f"<div style='margin:6px 0;'><span style='color:{col};font-weight:700'>{name}</span>："
            f"<span style='color:{col}'>{scores[key]:.1f}</span>　—　{area_comment(key, scores[key])}</div>",
            unsafe_allow_html=True
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ===== PDF生成 =====
    buf, img_buf = io.BytesIO(), io.BytesIO()
    # グラフ画像化
    fig.savefig(img_buf, format="png", bbox_inches="tight")
    img_buf.seek(0)

    # 日本語フォント
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    c = canvas.Canvas(buf, pagesize=A4)

    # テキストヘッダー（PDF。画像ヘッダーは入れない）
    c.setFont("HeiseiKakuGo-W5", 12)
    c.drawString(40, 810, "ストレスチェック簡易版（厚労省準拠／中大生協セルフケア版）")
    c.setFont("HeiseiKakuGo-W5", 9)
    c.drawString(40, 795, f"実施日：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.line(40, 785, A4[0]-40, 785)

    # レーダーチャート（位置）
    c.drawImage(ImageReader(img_buf), 60, 440, width=320, height=320)

    # 総合判定
    y = 415
    c.setFont("HeiseiKakuGo-W5", 11)
    c.drawString(40, y, f"【総合判定】{status}")
    y -= 22

    # 領域別サマリー
    c.setFont("HeiseiKakuGo-W5", 10)
    def set_rgb(hexcol):
        r = int(hexcol[1:3],16)/255; g = int(hexcol[3:5],16)/255; b = int(hexcol[5:7],16)/255
        c.setFillColorRGB(r,g,b)

    blocks = [
        ("A. 仕事の負担", A, COLORS["A"]),
        ("B. ストレス反応", B, COLORS["B"]),
        ("C. 周囲の支援", C, COLORS["C"]),
        ("D. 満足度",     D, COLORS["D"]),
    ]
    for title, val, col in blocks:
        set_rgb(col)
        c.drawString(40, y, f"{title}：{val:.1f}")
        c.setFillColorRGB(0,0,0)
        c.drawString(180, y, area_comment(title[0], val))
        y -= 18

    # 注意書き
    y -= 18
    c.setFont("HeiseiKakuGo-W5", 9)
    c.drawString(40, y, "※本チェックはセルフケアを目的としたものであり、医学的診断ではありません。")
    y -= 14
    c.drawString(40, y, "※体調の不調や不安が続く場合は、医師・保健師・カウンセラー等の専門家へご相談ください。")

    c.showPage()
    c.save()

    st.download_button(
        "📄 PDFをダウンロード",
        buf.getvalue(),
        file_name="ストレスチェック簡易版_結果.pdf",
        mime="application/pdf",
    )

    if st.button("🔁 もう一度やり直す"):
        restart()
