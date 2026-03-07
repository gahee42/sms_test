PYTHON = venv/bin/python
PIP = venv/bin/pip

.PHONY: run poll check install

# 서버 실행
run:
	$(PYTHON) server.py

# SMS 폴링 시작 (단독 실행용)
poll:
	$(PYTHON) scripts/poller.py

# 모뎀 상태 확인
check:
	$(PYTHON) scripts/modem.py check

# 의존성 설치
install:
	$(PIP) install -r requirements.txt
