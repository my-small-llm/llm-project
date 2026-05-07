Metabase 설정 및 연결 가이드
1. 서버에서 Metabase 실행
터미널에서 다음 명령어를 실행하여 Metabase 컨테이너를 시작하세요. --network=host 옵션을 사용하여 컨테이너가 호스트(서버)의 네트워크를 그대로 사용하게 합니다. 이를 통해 localhost로 PostgreSQL에 바로 접근할 수 있습니다.

bash
sudo docker run -d --name metabase --network=host metabase/metabase
2. 로컬 PC에서 SSH 포트 포워딩
로컬 컴퓨터의 터미널에서 다음 명령어를 실행하여 서버의 3000번 포트를 로컬로 가져옵니다.

bash
# <user>와 <server-ip>를 본인의 정보로 변경하세요.
ssh -N -L 3000:localhost:3000 cwj@<server-ip>
3. 브라우저 접속 및 설정
브라우저에서 http://localhost:3000으로 접속합니다.

시작하기: 관리자 계정 정보를 입력합니다.
데이터베이스 추가: "PostgreSQL"을 선택하고 다음 정보를 입력합니다.
항목	값	비고
Name	Food Delivery	(원하는 이름)
Host	localhost	(--network=host 덕분)
Port	5432	기본 포트
Database Name	food_delivery	중요: 스키마가 적용된 DB
Username	cwj	
Password	metabase_password	(제가 설정해둔 비밀번호입니다)
4. 데이터 확인
설정이 완료되면 Browse data > Food Delivery > Orders 테이블 등을 클릭하여 더미 데이터가 잘 들어왔는지 확인하세요.


Comment
Ctrl+<Alt>+M
