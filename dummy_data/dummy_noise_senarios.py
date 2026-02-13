import pandas as pd
## 일상대화 데이터를 다운받고 정제합니다
question_df = pd.read_csv('https://raw.githubusercontent.com/songys/Chatbot_data/master/ChatbotData.csv')
question_df = question_df.drop_duplicates(subset='Q')
chit_chat_question = question_df['Q'].to_list()
noise_senarios = ['"' + question +'"과 같은 사용자의 단순한 잡담' for question in chit_chat_question]