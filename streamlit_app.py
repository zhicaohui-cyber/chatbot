import streamlit as st
import requests
import json
import datetime
import csv
from io import StringIO

st.set_page_config(page_title="看護管理者向け 時間外労働削減ツール", layout="wide")

st.title("⏱️ 看護管理者向け — 時間外労働削減アシスタント")
st.markdown(
    "このツールは病棟や部署の現状を入力すると、短期・中長期の実行可能なアクションプラン、"
    "優先順位、チェックリストを自動生成して、時間外労働を削減するための支援を行います。"
)

# APIキー取得
gemini_api_key = st.secrets.get("GEMINI_API_KEY")
if not gemini_api_key:
    st.warning("Streamlit Secrets に `GEMINI_API_KEY` を設定してください。 (例: .streamlit/secrets.toml)", icon="⚠️")

# サイドバー：基本情報入力
with st.sidebar:
    st.header("病棟/部署情報")
    org_name = st.text_input("施設/部署名", value="病棟A")
    manager_name = st.text_input("管理者名", value="")
    date = st.date_input("作成日", value=datetime.date.today())
    model_name = st.selectbox("使用する Gemini モデル", ("gemini-2.5-flash", "gemini-2.5-pro"))
    st.markdown("---")
    st.info("入力情報をもとに、看護管理者向けの実行可能な対策案を生成します。", icon="ℹ️")

# メイン：現状入力フォーム
st.header("1. 現状の入力（できるだけ具体的に）")
col1, col2 = st.columns(2)

with col1:
    staff_count = st.number_input("常勤スタッフ数（フルタイム換算）", min_value=0, value=10)
    avg_overtime_per_week = st.number_input("1人当たり平均残業時間/週", min_value=0.0, value=8.0, step=0.5)
    peak_days = st.multiselect("残業が多い曜日/シフト", ["月","火","水","木","金","土","日","夜勤"], default=["金","夜勤"])
    typical_shift_length = st.number_input("典型的なシフト時間（時間）", min_value=0, value=8)

with col2:
    primary_causes = st.text_area(
        "時間外の主な原因（箇条書きで）",
        value="- 患者入退院の集中\n- 申し送り・ミーティングが長引く\n- 夜間の急変対応で人員不足\n- 書類作業が多い"
    )
    current_interventions = st.text_area("既に実施している対策（あれば）", value="- 交代制の見直し\n- 臨時スタッフ投入（費用高）")
    constraints = st.text_area("制約（人員、予算、制度、院内方針など）", value="- 常勤採用は難しい\n- 勤務表は月2回変更可能")

st.markdown("---")
st.header("2. 生成オプション")
col3, col4 = st.columns([2,1])
with col3:
    focus_horizon = st.radio("優先する実施期間", ("短期（即時〜1ヶ月）", "中期（1〜3ヶ月）", "長期（3〜12ヶ月）", "全期間"))
    max_solutions = st.slider("提案する案の最大数（合計）", min_value=1, max_value=10, value=5)
    include_checklist = st.checkbox("アクションごとのチェックリストを含める", value=True)
with col4:
    urgency_weight = st.selectbox("「効果 vs コスト」の優先度", ("効果重視", "コスト重視", "バランス"))

st.markdown("---")
st.header("3. アクションプラン生成")

if st.button("プランを生成する"):
    # 組み立てプロンプト
    prompt = {
        "role": "system",
        "content": (
            "あなたは看護管理の専門家です。以下の病棟情報を読み取り、時間外労働（残業）を減らすための"
            "実行可能なアクションプランを、短期/中期/長期ごとに分けて提案してください。"
            "各案には「説明」「期待効果（定量的に可能なら数値）」「想定コスト/負荷（低・中・高）」「実施の優先度（高/中/低）」"
            "および、実施チェックリスト（手順）」をつけてください。"
        )
    }

    user_content = (
        f"施設/部署: {org_name}\n"
        f"管理者: {manager_name}\n"
        f"作成日: {date}\n"
        f"常勤スタッフ数(FT): {staff_count}\n"
        f"平均残業時間/週: {avg_overtime_per_week}\n"
        f"残業の多いシフト: {', '.join(peak_days)}\n"
        f"シフト長: {typical_shift_length}時間\n"
        f"主な原因:\n{primary_causes}\n"
        f"既存対策:\n{current_interventions}\n"
        f"制約:\n{constraints}\n"
        f"希望する期間: {focus_horizon}\n"
        f"提案数上限: {max_solutions}\n"
        f"優先度: {urgency_weight}\n"
        f"チェックリストを含める: {include_checklist}\n"
    )
    prompt_user = {"role": "user", "content": user_content}

    # 準備：Gemini API の期待されるメッセージ構造に変換
    gemini_messages = []
    for m in (prompt, prompt_user):
        gemini_messages.append({"role": m["role"], "parts": [{"text": m["content"]}]})

    api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={gemini_api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": gemini_messages,
        "generationConfig": {
            "temperature": 0.2 if urgency_weight == "コスト重視" else 0.7,
            "topP": 0.9,
            "maxOutputTokens": 800
        }
    }

    # デバッグ表示
    st.subheader("APIリクエスト内容（デバッグ用）")
    st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    try:
        with st.spinner("アクションプランを生成中...（数秒〜30秒）"):
            response = requests.post(api_url, headers=headers, json=data, timeout=60)
            # デバッグ表示（レスポンスの内容）
            st.subheader("APIレスポンス内容（デバッグ用）")
            st.code(response.text, language="json")
            response.raise_for_status()
            result = response.json()

            # 応答抽出
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                generated_text = parts[0].get("text", "") if parts else ""
            else:
                generated_text = "（API応答の解析に失敗しました）\n" + json.dumps(result, ensure_ascii=False)

        st.subheader("提案されたアクションプラン（AI生成）")
        st.markdown(generated_text)

        # サマリーボックス：簡易抽出（そのままCSVにするための最小構造）
        st.subheader("構造化された出力（CSVダウンロード用）")
        rows = []
        rows.append(["部署", "提案", "説明（抜粋）"])
        rows.append([org_name, "AI生成プラン（全文）", generated_text[:300].replace("\n", " ")])
        csv_buf = StringIO()
        writer = csv.writer(csv_buf)
        writer.writerows(rows)
        csv_data = csv_buf.getvalue()
        st.download_button("CSVでダウンロード", data=csv_data, file_name=f"action_plan_{org_name}_{date}.csv", mime="text/csv")

        # コピーボタン（クリップボードに全文コピー）
        st.button("全文をクリップボードにコピー（ブラウザの機能を使用）")
        # 履歴に保存（セッション）
        if "plans" not in st.session_state:
            st.session_state.plans = []
        st.session_state.plans.append({"date": str(date), "content": generated_text})

    except requests.exceptions.HTTPError as e:
        st.error(f"APIリクエストエラー: {e}")
        st.error(f"エラー詳細: {getattr(e.response, 'text', str(e))}")
    except requests.exceptions.RequestException as e:
        st.error(f"APIリクエストエラー: {e}")
    except Exception as e:
        st.error(f"予期せぬエラー: {e}")

st.markdown("---")
st.header("4. 既に生成したプラン（セッション）")
if "plans" in st.session_state and st.session_state.plans:
    for p in st.session_state.plans[::-1]:
        st.markdown(f"**{p['date']}**")
        st.text_area("生成内容（編集可）", value=p["content"], height=200, key=f"plan_{p['date']}_{len(p['content'])}")
else:
    st.info("まだプランは生成されていません。上のフォームから生成してください。", icon="💡")

st.markdown("---")
st.header("5. ヒント集：時間外削減の即効対策（参考）")
st.markdown(
    "- 申し送りのフォーマットを統一して時間短縮する（テンプレ化）\n"
    "- 退院調整の早期化：入退院ラウンドを午前に固定する\n"
    "- 書類のデジタル化・テンプレート化で看護記録時間を短縮\n"
    "- 夜間のコールトリアージルールを明確化して必要最低限の対応にする\n"
    "- 研修で業務効率化（業務分担、優先順位付け）を徹底する"
)

st.markdown("---")
st.caption("注意: 本アプリは支援ツールです。生成されるプランは施設の内規や法令に照らして管理者が判断してください。")
