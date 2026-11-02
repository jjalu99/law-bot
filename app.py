import streamlit as st
import requests
import xml.etree.ElementTree as ET

st.title("🏗️ 감리 AI 챗봇 (법령 검색 탑재)")
st.caption("국가법령정보센터 실시간 검색이 결합된 하이브리드 AI입니다.")

with st.sidebar:
    st.header("⚙️ 설정")
    gemini_api_key = st.text_input("1. 구글 Gemini API 키", type="password")
    law_api_key = st.text_input("2. 법령정보센터 인증키(OC)", type="password")
    st.markdown("---")
    st.info("💡 두 개의 키를 모두 넣어야 실시간 법령 검색이 작동합니다.")

if prompt := st.chat_input("질문을 입력하세요 (예: 정기안전진단 법적기준)"):
    if not gemini_api_key or not law_api_key:
        st.warning("👈 왼쪽 설정 메뉴에 두 개의 API 키를 먼저 입력해 주세요!")
        st.stop()
        
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        # 로딩 중 안내 문구도 변경되었습니다.
        with st.spinner("🔍 국가법령정보센터 검색 및 답변 생성 중... (최대 3분 소요)"):
            try:
                search_query = "건축법"
                if "안전진단" in prompt or "시특법" in prompt or "시설물" in prompt:
                    search_query = "시설물의 안전 및 유지관리에 관한 특별법"
                elif "건진법" in prompt or "건설기술" in prompt:
                    search_query = "건설기술 진흥법"
                    
                law_url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={law_api_key.strip()}&target=law&type=XML&query={search_query}"
                law_response = requests.get(law_url)
                
                law_context = "검색된 법령이 없습니다."
                if law_response.status_code == 200:
                    root = ET.fromstring(law_response.text)
                    laws = root.findall('.//law')
                    if laws:
                        law_name = laws[0].find('법령명한글').text
                        enforce_date = laws[0].find('시행일자').text
                        law_context = f"[{law_name}] (최신 시행일: {enforce_date})"
                        st.success(f"⚖️ 법령센터 검색 완료: {law_context}")

                clean_gemini_key = gemini_api_key.strip()
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={clean_gemini_key}"
                
                combined_prompt = f"""
                당신은 토목/건축 감리 전문가입니다. 
                아래 [실시간 검색 법령]을 반드시 참고하여, [사용자 질문]에 대해 가장 정확한 조항과 기준을 들어 대답하세요.
                
                [실시간 검색 법령]
                {law_context}
                
                [사용자 질문]
                {prompt}
                """

                headers = {'Content-Type': 'application/json'}
                data = {
                    "contents": [{"parts": [{"text": combined_prompt}]}]
                }
                
                # 💡 타이머가 180초(3분)로 연장되었습니다.
                gemini_response = requests.post(gemini_url, headers=headers, json=data, timeout=180)
                
                if gemini_response.status_code == 200:
                    result = gemini_response.json()
                    answer = result['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(answer)
                else:
                    st.error(f"⚠️ 구글 서버 오류 (코드 {gemini_response.status_code}): {gemini_response.text}")
                    
            except requests.exceptions.Timeout:
                st.error("⏳ 서버 응답 시간이 3분(180초)을 초과했습니다. 질문 내용이 너무 방대하거나 구글 서버가 혼잡할 수 있으니 질문을 약간 수정하여 다시 시도해 주세요.")
            except requests.exceptions.ConnectionError:
                st.error("📡 서버 연결에 실패했습니다. 챗봇 서버의 인터넷 통신 상태가 불안정합니다.")
            except Exception as e:
                st.error(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
