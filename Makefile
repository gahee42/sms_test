.PHONY: run poll check install

# 서버 실행
run:
	python server.py

# SMS 폴링 시작
poll:
	python poller.py

# 모뎀 상태 확인
check:
	python modem.py check

# 의존성 설치
install:
	pip install -r requirements.txt
