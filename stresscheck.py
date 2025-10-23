import streamlit as st
import math
import io
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# ------------------------------------------------
# Configuration
# ------------------------------------------------
APP_TITLE = "中大生協版 職業性ストレス簡易調査 - ver1.2"

DESC = (
    "本チェックは厚生労働省の57項目票をベースにしたセルフケア版です。"
    "所要時間：約5〜7分。結果は端末内のみで処理されます（送信しません）。"
)

CHOICES = [
    "1：まったくない／ちがう",
    "2：あまりない",
    "3：どちらともいえない",
    "4：ややある",
    "5：とてもある／そうだ",
]

QUESTIONS = [
    # ※厚労省の57項目をここにすべて入れる
    "自分の仕事量は多いと感じる。",
    "仕事の質に対する要求が高い。",
    "仕事の内容がよく変わる。",
    "自分の意見が職場で尊重されていると感じる。",
    "職場での人間関係に満足している。",
    "上司や同僚からの支援を受けていると感じる。",
    # ...（以下略）
]

# ------------------------------------------------
# National Average Benchmarks (暫定値)
# ------------------------------------------------
NATIONAL_AVG = {
    "仕事の負担感": 45.0,
    "からだと気持ちの反応": 40.0,
    "周囲のサポート": 35.0,
    "仕事や生活の満足感": 30.0,
}

# ------------------------------------------------
# Streamlit Layout
# ------------------------------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.write(DESC)
st.write("---")

if "responses" not in st.session_state:
    st.session_state.responses = []

# 質問の実施
q_index = len(st.session_state.responses)
if q_index < len(QUESTIONS):
    st.subheader(f"Q{q_index + 1}／{len(QUESTIONS)}")
    st.write(QUESTIONS[q_index])
    answer = st.radio("回答を選んでください：", CHOICES, key=f"q_{q_index}")
    if st.button("次へ"):
        st.session_state.responses.append(answer)
        st.rerun()
else:
    st.success("✅ 回答完了！ 解析を開始します。")
    st.write("---")

    # ------------------------------------------------
    # 集計処理（仮スコア算出）
    # ------------------------------------------------
    scores = {
        "仕事の負担感": 45.6,
        "からだと気持ちの反応": 50.9,
        "周囲のサポート": 58.3,
        "仕事や生活の満足感": 50.0,
    }
    total_score = sum(scores.values()) / len(scores)

    # ------------------------------------------------
    # レーダーチャート描画
    # ------------------------------------------------
    categories = ["A", "B", "C", "D"]
    values = list(scores.values())
    avg_values = list(NATIONAL_AVG.values())

    angles = [n / float(len(categories)) * 2 * math.pi for n in range(len(categories))]
    values += values[:1]
    avg_values += avg_values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    ax.plot(angles, values, "r-", linewidth=2, label="あなた")
    ax.fill(angles, values, "r", alpha=0.25)
    ax.plot(angles, avg_values, "b--", linewidth=1.5, label="全国平均")
    ax.fill(angles, avg_values, "b", alpha=0.1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_yticklabels([])
    plt.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    st.pyplot(fig)

    # 注釈
    st.caption("A：仕事の負担感　B：からだと気持ちの反応　C：周囲のサポート　D：仕事や生活の満足感")

    # ------------------------------------------------
    # 結果コメント
    # ------------------------------------------------
    st.write("### 🔍 解析結果（全国平均との比較）")
    for key, val in scores.items():
        diff = val - NATIONAL_AVG[key]
        arrow = "↑" if diff >= 0 else "↓"
        st.write(f"{key}：{val:.1f} （全国平均 {NATIONAL_AVG[key]:.0f}） {arrow}{abs(diff):.1f}")

    st.write(f"**総合ストレス指数：{total_score:.1f}**")
    st.info(
        "※本結果はセルフチェックであり、医学的診断を目的とするものではありません。"
        "強いストレスや体調の変化を感じる場合は、医師・産業保健スタッフ・専門カウンセラーにご相談ください。"
    )

    # ------------------------------------------------
    # PDF出力
    # ------------------------------------------------
    def create_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # フォント設定
        try:
            pdfmetrics.registerFont(TTFont("IPAexMincho", "ipaexm.ttf"))
            font_name = "IPAexMincho"
        except:
            font_name = "Helvetica"

        c.setFont(font_name, 9)
        c.drawString(30 * mm, 280 * mm, "中大生協版 職業性ストレス簡易調査 - ver1.2")
        c.drawString(30 * mm, 275 * mm, f"結果生成日時：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # チャート画像をPDFに貼る
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format="png", bbox_inches="tight")
        img_buf.seek(0)
        img = ImageReader(img_buf)
        c.drawImage(img, 30 * mm, 140 * mm, width=150 * mm, height=120 * mm)

        # スコア部分
        text_y = 130
        for key, val in scores.items():
            c.drawString(30 * mm, text_y * mm, f"{key}：{val:.1f}（全国平均 {NATIONAL_AVG[key]:.0f}）")
            text_y -= 5

        c.drawString(30 * mm, (text_y - 5) * mm, f"総合ストレス指数：{total_score:.1f}")
        text_y -= 10

        # 注意書き
        notice_lines = [
            "【ご注意】",
            "本調査は厚生労働省「職業性ストレス簡易調査票（57項目）」をもとにした",
            "中央大学生活協同組合のセルフチェック版です。",
            "結果はご自身のストレス傾向を把握するための目安であり、",
            "医学的な診断や評価を目的とするものではありません。",
            "心身の不調が続く場合や結果に不安を感じる場合は、",
            "医師・保健師・カウンセラー等の専門家へご相談ください。",
            "",
            "──────────────────────────────",
            "Supervised by General Affairs Division / Information & Communication Team",
            "Chuo University Co-op",
            "──────────────────────────────",
        ]
        for line in notice_lines:
            c.drawString(30 * mm, (text_y - 5) * mm, line)
            text_y -= 5

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

    if st.button("📄 PDFをダウンロード"):
        pdf = create_pdf()
        st.download_button(
            label="PDFを保存する",
            data=pdf,
            file_name=f"{datetime.now().strftime('%Y%m%d')}_職業性ストレス簡易調査結果.pdf",
            mime="application/pdf",
        )
