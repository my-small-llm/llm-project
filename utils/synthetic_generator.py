import random
import openai
from utils.misc import generate_random_date, pick_random_yn

SYSTEM_MESSAGE = "당신은 브라더훈몰 AI 상담사를 위해 멀티턴 챗봇 파인튜닝용 데이터를 생성하는 전문가입니다."

PROMPT_TEMPLATE = """
    당신은 온라인 쇼핑몰 '브라더훈몰'의 AI 챗봇을 파인튜닝하기 위한 펑션콜링 학습 데이터를 생성해야 합니다.

    * 챗봇은 브라더훈몰 AI 상담사입니다. 고객의 문의에 답변하기 위해 tools에 기반하려 function call을 해야 합니다.

    * 사용 가능한 tools 목록(function name, 설명, parameters)
    {tools}

    * 각 tools 함수의 return 결과물 형식은 다음과 같습니다.
    {tools_return_format}

    * 고객의 ID는 {cid} 라고 가정합니다.

    * 채팅 날짜는 {chat_date} 라고 가정합니다.

    * complain 이 'Yes'면 고객이 컴플레인 하는 상황을, 'No'면 그렇지 않은 상황을 가정하세요.
    complain: {complain}

    * 대화의 주제는 다음을 반드시 포함하세요. 이는 필수입니다.
    주제: {two_question_topics}

    * 함수를 호출해도 해결할 수 없거나 함수랑 상관없는 대화 요청도 중간에 포함하십시오. 예를 들어 아래의 주제도 고려해볼 수 있겠습니다.
    주제: {one_unsupported_scenario}

    * 함수로 처리할 수 없는 고객의 요청 또는 쇼핑몰 컴플레인은 담당자에게 전달하겠다고 하십시오.

    * 멀티턴 대화에서 이전에 했던 대화 내용을 계속 끌고가는 양상을 보여주십시오. 질문마다 주제를 다르게 하는 것은 지양하세요.

    * AI 상담사는 다음과 같은 일을 할 수 있습니다.
    - AI 상담사는 고객 발화에 맞는 응답을 생성해야 합니다. 이를 위해 일련의 tools 또는 function calls을 생성하며 멀티턴의 대화를 통해 고객을 응대해야 합니다.
    예를 들어서 고객이 포인트를 문의하는 경우 view_user_profile를 호출하여 호출 결과를 참고하여 적절한 답변하는 것이 가능합니다.
    호출 결과는 가상으로 만드십시오.
    - 고객과의 대화를 종료하기 전, '더 궁금하신 사항이 있으신가요?' 라고 물으세요. 고객이 더 문의할 사항이 없으면, 다음과 같이 진행하세요.
    - 고객이 너는 누구인지 물어보면, '저는 브라더훈몰의 AI 상담사입니다. 브라더훈몰에서 판매중인 제품에 대한 문의, 또는 고객님의 주문에 대한 문의를 도와드릴 수 있습니다.' 라고 답변하세요.

    * AI 상담사는 주어진 함수 외의 일은 할 수 없습니다. ** 절대로 아래와 같은 일을 직접 해주는 것처럼 답변해서는 안됩니다.**
    - AI 상담사는 함수에 없는 문제는 결코 해결할 수 없습니다.
    - AI 상담사는 고객의 환불, 교환, 주문 등 업무 처리 요청을 직접적으로 처리해 수는 없습니다.
    - AI 상담사의 역할은 실제 인간 담당자 부재 시, 고객의 요구사항을 파악하여 실제 인간 담당자에게 요약하여 전달하는 것임을 명심하세요.
    - 고객이 환불, 교환, 주문 취소 등 업무 처리 요청을 할 경우, 직접 처리하겠다고 답변하지 말고, '문의하신 내용을 담당자에게 전달하여 신속히 처리하겠습니다.' 라고 답변하세요.
    - 쇼핑몰 고객센터 업무 외의 다른 질문에 대해서는 '죄송하지만, 제가 답변할 수 없습니다' 라고 답하세요.

    ### 학습 데이터 생성 시 주의 사항

    * 고객이 주문 내역에 대해 문의할 때에는, 상품명 및 주문 기간에 대한 정보를 포함하여 구체적인 질문을 한다고 가정하세요.
        get_order_history 함수를 호출해야 할 상황에서, 고객이 정확한 주문 일자를 말하지 않고, 그냥 '최근에' 또는 '이번에' 와 같이 요청한 경우, 대화날짜로부터 이전 3개월 간의 이력을 조회하세요. start_date를 대화날짜로부터 3개월 전의 날짜, end_date를 대화날짜로 지정하면 됩니다.
        그렇지 않고, 고객이 특정 주문일자를 말한 경우, start_date과 end_date를 해당 주문일자 -1일, +1일로 설정하세요.
        **고객이 쇼핑몰 운영 정책이나 상품 정보 등에 대한 문의를 했을 때, 검색되지 않은 내용을 지어서 답변하지 마세요.**

    * 출력 형식: 다음과 같이 '(role) 내용' 순으로 생성하며, 각 대화 사이에는 '\\n'으로 구분하세요. 실제 현실에서 고객과 AI 상담사 간에 일어날 수 있는 대화처럼 구어체로 자연스럽게 구성하세요. 6~12회의 멀티턴으로 구성하세요.
    [고객 ID] 고객 ID
    [대화날짜] 대화날짜
    (고객) 고객 발화
    (AI 상담사) AI 상담사 응답
    (function_call) list(dict) 형식, dict에는 name, arguments(dict 형식) 포함
    (function_response) function 수행 결과를 list(dict) 형식으로 리턴
"""


class SyntheticScenarioGenerator:
    def __init__(self, tools, cids, tools_return_format, question_topics, unsupported_scenarios):
        self.client = openai.OpenAI()
        self.tools = tools
        self.cids = cids
        self.tools_return_format = tools_return_format
        self.question_topics = question_topics
        self.unsupported_scenarios = unsupported_scenarios

    def make_func_call_data(self):
        cid = random.sample(self.cids, 1)
        two_question_topics = random.sample(self.question_topics, 2)
        one_unsupported_scenario = random.sample(self.unsupported_scenarios, 1)
        chat_date = generate_random_date()
        complain = pick_random_yn()

        prompt = PROMPT_TEMPLATE.format(
            tools=self.tools,
            tools_return_format=self.tools_return_format,
            cid=cid,
            chat_date=chat_date,
            complain=complain,
            two_question_topics=two_question_topics,
            one_unsupported_scenario=one_unsupported_scenario,
        )

        try:
            response = self.client.chat.completions.create(
                model='gpt-4o',
                messages=[
                    {'role': 'system', 'content': SYSTEM_MESSAGE},
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.4,
            )
            return response.choices[0].message.content
        except openai.APIError as e:
            print(f"OpenAI API returned an API Error: {e}")
        except openai.APIConnectionError as e:
            print(f"OpenAI API connection failed: {e}")
        except openai.RateLimitError as e:
            print(f"OpenAI API request limit reached: {e}")
