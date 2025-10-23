import streamlit as st
import math
import io
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import pandas as pd

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
APP_TITLE = "職業性ストレス簡易調査（５択・自動解析版）"
DESC = (
    "本チェックは厚生労働省の57項目票をベースにしたセルフケア版です。"
    "所要時間：約5〜7分。結果は端末内のみで処理されます（送信しません）。"
)

CHOICES = [
    "1：まったくない／ちがう",
    "2：あまりない／どちらかといえばちがう",
    "3：どちらともいえない",
    "4：まあそうだ／どちらかといえばそうだ",
    "5：とてもそうだ／そうだ",
]

# 仮の設問（あとで厚労省版57問に置換可能）
QUESTIONS = [
    "最近、仕事に満足している。",
    "職場でよく相談できる人がいる。",
    "自分の意見が尊重されていると感じる。",
    "仕事量が多すぎると感じる。",
    "上司との関係は良好だ。",
    "チームの雰囲気が良いと感じる。",
    "最近、眠れないことがある。",
    "体がだるいと感じることがある。",
    "気分が落ち込むことが多い。",
    "仕事のやりがいを感じている。",
] * 6  # 仮に10問×6セットで57問相当

# ------------------------------------------------------------
# App Logic
# ------------------------------------------------------------
st.set_page_config(APP_TITLE, layout="centered")
st.title(APP_TITLE)
st.write(DESC)
st.divider()

if "page" not in st.session_state:
    st.session_state.page = 0
if "answers" not in st.session_state:
    st.session_state.answers = [None] * len(QUESTIONS)

# ページ切替処理
def next_page():
    st.session_state.page += 1
    st.rerun()

def restart():
    st.session_state.page = 0
    st.session_state.answers = [None] * len(QUESTIONS)
    st.rerun()

# ------------------------------------------------------------
# 質問パート
# ------------------------------------------------------------
if st.session_state.page < len(QUESTIONS):
    q_num = st.session_state.page + 1
    st.subheader(f"Q{q_num} / {len(QUESTIONS)}")
    st.caption("（厚労省原文をここに表示）")
    st.write(QUESTIONS[st.session_state.page])

    choice = st.radio(
        "回答を選んでください：",
        CHOICES,
        index=None,
        key=f"q_{q_num}",
        horizontal=False,
    )

    if choice:
        st.session_state.answers[st.session_state.page] = CHOICES.index(choice) + 1
        if st.button("次へ ▶"):
            next_page()
else:
    # --------------------------------------------------------
    # 結果解析パート
    # --------------------------------------------------------
    st.success("🎉 回答完了！解析を開始します。")
    answers = st.session_state.answers
    score = sum(a for a in answers if a is not None)
    avg = round(score / len(answers), 2)

    st.metric("総合スコア", score)
    st.metric("平均スコア（1〜5）", avg)

    # グラフ描画
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["総合"], [score], color="skyblue")
    ax.set_ylim(0, len(QUESTIONS) * 5)
    ax.set_ylabel("スコア")
    st.pyplot(fig)

    # PDF出力
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(40, 800, f"職業性ストレス簡易調査 結果（{datetime.now().strftime('%Y-%m-%d %H:%M')}）")
    c.drawString(40, 780, f"総合スコア： {score}")
    c.drawString(40, 760, f"平均スコア： {avg}")
    c.showPage()
    c.save()
    st.download_button("📄 PDFをダウンロード", buf.getvalue(), file_name="stresscheck_result.pdf")

    st.divider()
    if st.button("🔁 もう一度やり直す"):
        r
