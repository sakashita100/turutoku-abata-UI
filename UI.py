import streamlit as st
import requests
import os
import json
from asari.api import Sonar

# --- 設定 ---
# サイドバーで入力するため、ここの値はプレースホルダーです
DIFY_API_KEY = "app-2ok9NHsHDqchX9mdbw51Lmff"
DIFY_API_URL = "http://localhost/v1"


sonar = Sonar()

# アバター画像のパス
AVATAR_IMAGES = {
    "normal": "avatars/normal_avatar.png",
    "positive": "avatars/happy_avatar.png",
    "negative": "avatars/sad_avatar.png",
}

# --- Streamlit アプリケーション設定 ---
st.set_page_config(layout="wide", page_title="AIエージェントチャット")

# ★★★ 解決策: ここにサイドバーのコードを追加します ★★★
st.sidebar.title("設定")
api_key_input = st.sidebar.text_input("Dify APIキーを入力", value=DIFY_API_KEY, type="password")
api_url_input = st.sidebar.text_input("Dify API URLを入力", value=DIFY_API_URL)
uploaded_file = st.sidebar.file_uploader("ファイルをアップロード (任意)", type=['txt', 'pdf', 'png', 'jpg', 'jpeg'])
# ★★★ ここまで ★★★

# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.current_avatar = AVATAR_IMAGES["normal"]
    st.session_state.conversation_id = None
    st.session_state.file_id = None

# --- UIレイアウト ---
col_char, col_chat = st.columns([1, 2])

with col_char:
    st.markdown("<h2>AIエージェント</h2>", unsafe_allow_html=True, help="Difyのエージェントと対話します。")
    st.image(st.session_state.current_avatar, use_container_width=True)
    if st.button("新しいチャットを開始", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.session_state.file_id = None
        st.session_state.current_avatar = AVATAR_IMAGES["normal"]
        st.rerun()

with col_chat:
    st.markdown("<h2>チャット</h2>", unsafe_allow_html=True)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("logs"):
                with st.expander("実行ログを表示"):
                    st.json(message["logs"])

    if prompt := st.chat_input("メッセージを送信"):
        # このif文で 'api_key_input' が使われる前に、サイドバーで定義されている必要がある
        if not api_key_input or not api_url_input or "dify-api-key-here" in api_key_input:
            st.error("サイドバーで有効なDify APIキーとURLを設定してください。")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt, "logs": None})
            
            try:
                with st.spinner("AIが考えています..."):
                    files_payload = []
                    # 'uploaded_file' もサイドバーで定義されている必要がある
                    if uploaded_file and not st.session_state.file_id:
                        file_upload_url = os.path.join(api_url_input.split('/v1')[0], "v1/files/upload")
                        headers_upload = {"Authorization": f"Bearer {api_key_input}"}
                        file_data = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        user_data = {'user': 'streamlit-user'}

                        upload_response = requests.post(file_upload_url, headers=headers_upload, files=file_data, data=user_data)
                        upload_response.raise_for_status()
                        st.session_state.file_id = upload_response.json().get('id')
                        st.sidebar.success(f"ファイル '{uploaded_file.name}' をアップロードしました。")

                    if st.session_state.file_id:
                        files_payload.append({
                            "type": "image",
                            "transfer_method": "local_file",
                            "upload_file_id": st.session_state.file_id
                        })

                    headers = {
                        "Authorization": f"Bearer {api_key_input}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "inputs": {}, "query": prompt, "user": "streamlit-user", "response_mode": "blocking", "files": files_payload
                    }
                    if st.session_state.conversation_id:
                        data["conversation_id"] = st.session_state.conversation_id

                    response = requests.post(api_url_input, headers=headers, json=data)
                    response.raise_for_status()
                    response_data = response.json()

                    answer = response_data.get("answer", "応答がありません。")
                    st.session_state.conversation_id = response_data.get("conversation_id")
                    logs = response_data.get("logs")

                    sentiment = sonar.ping(answer)["top_class"]
                    if sentiment == "positive": st.session_state.current_avatar = AVATAR_IMAGES["positive"]
                    elif sentiment == "negative": st.session_state.current_avatar = AVATAR_IMAGES["negative"]
                    else: st.session_state.current_avatar = AVATAR_IMAGES["normal"]

                    st.session_state.messages.append({"role": "assistant", "content": answer, "logs": logs})
                
                st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"APIへの接続エラー: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"エラー: {e}", "logs": None})
                st.rerun()
            except Exception as e:
                st.error(f"予期せぬエラーが発生しました: {e}")
                st.session_state.messages.append({"role": "assistant", "content": f"エラー: {e}", "logs": None})
                st.rerun()
