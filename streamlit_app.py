import streamlit as st
import requests

# タイトルと説明の表示
st.title("💬 Gemini チャットボット")
st.write("このシンプルなチャットボットは、Google の Gemini API を利用して応答を生成します。 ")

# Streamlit Community CloudのSecretsからAPIキーを取得
# .streamlit/secrets.toml に GEMINI_API_KEY = "YOUR_API_KEY" を設定してください
gemini_api_key = st.secrets.get("GEMINI_API_KEY")

if not gemini_api_key:
    st.info("Streamlit Community CloudのSecretsに `GEMINI_API_KEY` を設定してください。", icon="🗝️")
else:
    # ユーザーがモデルを選択できるようにする（正しいモデル名表記を使用）
    model_name = st.selectbox(
        "使用する Gemini モデルを選択",
        (
            "gemini-2.5-flash", 
            "gemini-2.5-pro"
        )
    )
    st.write(f"現在のモデル: **{model_name}**") # 選択中のモデルを表示

    if "messages" not in st.session_state:
        # 初期のメッセージリストをセッションステートに作成
        st.session_state.messages = []

    # 既存のチャットメッセージを表示
    for message in st.session_state.messages:
        # roleに応じて日本語で表示
        display_role = "ユーザー" if message["role"] == "user" else "アシスタント"
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーがメッセージを入力するためのチャット入力フィールド
    if prompt := st.chat_input("ここにメッセージを入力"):

        # ユーザーのプロンプトを保存・表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gemini API用にメッセージ形式を準備（ロールを "user" または "model" に変換）
        gemini_messages = []
        for m in st.session_state.messages:
            # StreamlitのロールをAPIのロールにマッピング
            api_role = "user" if m["role"] == "user" else "model"
            gemini_messages.append(
                {
                    "role": api_role,
                    "parts": [{"text": m["content"]}]
                }
            )

        # Gemini API endpoint
        api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={gemini_api_key}"

        headers = {"Content-Type": "application/json"}
        data = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.8
            }
        }

        try:
            # アシスタントの応答をチャットメッセージコンテナ内に表示
            with st.chat_message("assistant"):
                with st.spinner(f"{model_name} が応答を生成中..."):
                    response = requests.post(api_url, headers=headers, json=data, timeout=30)
                    response.raise_for_status() # HTTPエラーがあれば例外を発生
                    
                    result = response.json()
                    
                    # APIからのレスポンス構造のチェックと応答の取得
                    if "candidates" in result and result["candidates"] and \
                       "content" in result["candidates"][0] and \
                       "parts" in result["candidates"][0]["content"] and \
                       result["candidates"][0]["content"]["parts"]:
                        
                        gemini_reply = result["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        # 予期しないレスポンス形式の場合
                        gemini_reply = f"エラー: 予期しないAPI応答形式です。{result}"

                    st.markdown(gemini_reply)
            
            # アシスタントの応答をセッションステートに保存
            st.session_state.messages.append({"role": "assistant", "content": gemini_reply})

        except requests.exceptions.RequestException as e:
            error_message = f"APIリクエストエラーが発生しました: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        except Exception as e:
            error_message = f"予期せぬエラーが発生しました: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
