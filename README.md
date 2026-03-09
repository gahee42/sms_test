# SMS 수신 시스템 PRD (v2)

## 1. 프로젝트 개요

Huawei E8372h-320 LTE USB 모뎀(HiLink 모드)을 이용한 SMS 수신 및 관리 시스템.
라즈베리파이에서 Python 스크립트로 모뎀의 SMS를 읽어 AWS NestJS 서버로 전송한다.

## 2. 개발/운영 환경

| | 개발 (현재) | 운영 (목표) |
|---|---|---|
| 모뎀 | N개 (`modems.json` 설정) | N개 |
| 실행 환경 | Mac 노트북 | 라즈베리파이 |
| 서버 | localhost:3000 | AWS |
| 모뎀 접속 | USB 직접 연결 | USB 직접 연결 |
| 모니터링 | Slack 웹훅 알림 | Slack 웹훅 알림 |

> `modems.json`에 모뎀별 URL/계정을 설정하고, 비밀번호는 `.env`에서 관리.

## 3. 시스템 아키텍처

```
[라즈베리파이] ──── LTE 인터넷 (USB 모뎀) ────> [AWS 서버]

  USB 모뎀 #1 ← poller 프로세스 #1 ──┐
  USB 모뎀 #2 ← poller 프로세스 #2 ──┼── POST /v1/sms (JSON) ──> NestJS 서버 (저장 + API)
  USB 모뎀 #3 ← poller 프로세스 #3 ──┘
```

### 역할 분리

| 구성요소 | 위치 | 역할 |
|---------|------|------|
| Python 스크립트 | 라즈베리파이 | 모뎀에서 SMS 읽기 → 스팸 필터 → JSON으로 서버 전송 → 답장 발송 → 용량 관리 |
| NestJS 서버 | AWS | SMS 수신(JSON), 저장, API 제공, 모뎀/유저 매핑 관리 |

### 데이터 흐름

```
모뎀 (XML 응답) → Python (XML 파싱 → JSON 변환) → POST → NestJS (JSON 저장)
```

### 핵심 설계 원칙

- XML 파싱은 **Python(라즈베리파이)에서** 처리, 서버에는 **JSON만** 전송
- 라즈베리파이는 **초기 세팅 후 재접속 불필요** (자동 업데이트, 자동 재시작)
- 모뎀 추가/제거는 **물리적으로 꽂고 빼기만** 하면 됨
- 설정 변경(phone, userId 매핑)은 **서버에서만** 처리

## 4. 하드웨어

### Huawei E8372h-320

- HiLink 모드 (HTTP API, 192.168.8.1)
- USB 연결 시 네트워크 인터페이스 자동 생성
- LTE 데이터 + SMS 동시 지원
- 내부 플래시 메모리에 SMS 저장 (USIM이 아님)
- **최대 500건 저장** (수신 + 발신 합산, LocalMax)
- 모뎀 N개 연결 시 IP 자동 분리 (192.168.8.1, 192.168.9.1, ...)

### 라즈베리파이

- 모니터/키보드 불필요 (headless, SSH 접속)
- USB 모뎀의 LTE로 인터넷 연결 (WiFi/랜선 불필요)
- 전원 + USB 모뎀만 있으면 동작
- 모뎀 N개 중 1개라도 살아있으면 인터넷 유지

### USIM 요건

- **데이터 통신 필수** (SMS 수신은 되지만 서버 전송에 인터넷 필요)
- SMS 수신 가능 (대부분 데이터 요금제에 포함)
- 트래픽 매우 적음 (월 1~2GB면 충분)
- 알뜰폰(MVNO) 저가 요금제 가능

## 5. 모뎀 API (HiLink HTTP API)

### 인증

- 로그인 필요: SHA256 기반 인증 (huawei-lte-api 라이브러리가 처리)
- POST 요청 시 CSRF 토큰(`__RequestVerificationToken`) 필수
- 응답 형식: XML

### 주요 엔드포인트

| 엔드포인트 | 메서드 | 로그인 | 설명 |
|-----------|--------|--------|------|
| /api/device/information | GET | O | 디바이스 정보 (IMEI 포함) |
| /api/device/signal | GET | O | 신호 강도 |
| /api/device/basic_information | GET | X | 기본 정보 |
| /api/sms/sms-count | GET | X | SMS 건수 통계 |
| /api/sms/sms-list | POST | O | SMS 목록 조회 |
| /api/sms/config | GET | O | SMS 설정 (LocalMax 등) |
| /api/monitoring/status | GET | X | 모니터링 상태 |
| /api/monitoring/traffic-statistics | GET | X | 트래픽 통계 |
| /api/net/current-plmn | GET | X | 현재 통신사 |
| /api/net/net-mode | GET | O | 네트워크 모드 |

### SMS 데이터 필드

| 필드 | 설명 |
|------|------|
| Index | 메시지 고유 ID |
| Phone | 발신자 번호 |
| Content | 메시지 내용 |
| Date | 수신 일시 |
| Smstat | 읽음 상태 (0=안읽음, 1=읽음) |
| SmsType | 메시지 타입 |

> 수신자(모뎀) 번호는 SMS 데이터에 포함되지 않음. IMEI로 모뎀 식별.

## 6. Python 스크립트 (라즈베리파이)

### server.py — 진입점

`aiohttp` 기반 API 서버 + 모뎀 폴링 동시 실행. `modems.json`에서 모뎀 목록 로드 후 모뎀별 독립 poll_loop을 `asyncio.create_task()`로 실행.

### services/poller.py — SMS 폴링 루프

```
반복 (모뎀별 독립 실행):
  1. 모뎀 미연결 시 재연결 시도
  2. 안읽은 SMS 조회 (Smstat=0)
  3. 스팸 필터링 (번호 prefix + 키워드)
  4. 서버로 POST (JSON + IMEI) — 스팸 포함 전체 전송
  5. 서버 응답 OK → 답장 발송 (스팸 제외) + 읽음 처리 (전체)
  6. SMS 용량 체크 → 350건(70%) 초과 시 읽은 수신 + 발신 삭제
  7. POLL_INTERVAL(기본 5초) 대기
```

### services/modem.py — 모뎀 통신 서비스

`ModemService` 클래스: 연결/재연결, SMS 조회/발송/삭제/읽음 처리, 용량 관리. `load_modem_configs()`로 `modems.json` → 인스턴스 리스트 생성.

### services/spam_filter.py — 스팸 필터

- 번호 prefix 차단 (070 등)
- 키워드 차단 (대출, 보험, 당첨 등)
- 스팸 판정 시 서버 전송은 하되 답장만 스킵

### services/slack.py — Slack 알림

웹훅 기반 fire-and-forget 알림: SMS 수신, 답장 발송, 에러, 모뎀 상태, SMS 정리.

### services/reply.py — 답장 생성

수신 메시지 → 답장 텍스트 생성. MMS는 안내 메시지 응답.

### 의존성

- `huawei-lte-api` — 모뎀 통신
- `aiohttp` — 비동기 HTTP 서버/클라이언트
- `python-dotenv` — 환경변수 관리

## 7. NestJS 서버 (AWS)

### 현재 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | / | 헬스체크 |
| POST | /v1/sms | SMS 수신 (poller → 서버, JSON) |
| GET | /v1/sms | 저장된 SMS 전체 조회 |

### 현재 저장소

JSONL 파일 (`sms_log.jsonl`) — 추후 DB 전환 예정

### 추후 구현 필요

- [ ] DB 저장 (JSONL → 실제 DB)
- [ ] 모뎀 등록/관리 API (IMEI → phone → userId 매핑)
- [ ] TypeScript 인터페이스 (모뎀 API 응답 타입 정의)
- [ ] 모뎀 헬스체크 API
- [ ] 관리자 대시보드 (모뎀 상태, userId 매핑 변경)

## 8. 모뎀 N개 운영

### 식별 방식

- 각 모뎀은 고유 **IMEI**로 식별
- Python이 IMEI를 함께 전송, 서버에서 매핑 관리

### 서버 매핑 구조

```
IMEI (모뎀 고유) → phone (전화번호) → userId (서비스 유저)
```

- phone, userId 변경은 서버 API에서만 처리
- 라즈베리파이 재접속 불필요

### 모뎀 설정 (`modems.json`)

```json
[
  { "url": "http://192.168.8.1/", "user": "admin", "env_pass": "MODEM_1_PASS" },
  { "url": "http://192.168.9.1/", "user": "admin", "env_pass": "MODEM_2_PASS" }
]
```

- 비밀번호는 `.env`에서 `env_pass` 키로 참조
- 모뎀별 독립 poll_loop (`asyncio.create_task`)으로 병렬 실행
- 추가: `modems.json`에 항목 추가 + `.env`에 비밀번호 → 서버 재시작
- 제거: `modems.json`에서 항목 삭제 → 서버 재시작

## 9. 라즈베리파이 운영

### 초기 세팅 (1회)

1. Raspberry Pi OS 설치 (Imager에서 WiFi/SSH 설정)
2. SSH 접속 → git clone → 의존성 설치
3. systemd 서비스 등록 (poller)
4. 자동 업데이트 cron 설정

### 자동화

- **프로세스 재시작**: systemd (에러로 스크립트 죽으면 자동 재시작)
- **코드 업데이트**: cron으로 주기적 git pull + 서비스 재시작
- **다수 Pi 관리**: Ansible로 일괄 명령 가능

### 접속 방식

- SSH: `ssh pi@raspberrypi.local` (같은 네트워크)
- Tailscale: 원격 접속 (네트워크 무관)

## 10. HiLink vs 스틱 모드

| | HiLink 모드 (현재) | 스틱 모드 |
|---|---|---|
| SMS 읽기 | HTTP API | AT 커맨드 (시리얼) |
| 인터넷 | O | X |
| 코드 복잡도 | 낮음 | 높음 |
| 모뎀 요건 | HiLink 지원 모뎀 필요 | 아무 LTE 모뎀 |

현재는 HiLink 모드 사용. 스틱 모드는 비용 절감 필요 시 검토.

## 11. 모니터링

### Slack 웹훅 알림

`.env`에 `SLACK_WEBHOOK_URL` 설정 시 자동 활성화. 미설정 시 무시.

| 이벤트 | 알림 내용 |
|--------|----------|
| SMS 수신 | 발신번호, 내용, 건수 |
| 답장 발송 | 수신번호, 답장 내용 |
| 에러 발생 | 에러 컨텍스트, 메시지 |
| 모뎀 상태 | 연결/재연결 |
| SMS 정리 | 삭제 건수 |

## 12. 알려진 제약사항

- 모뎀 SMS 저장 한도 500건 → 350건(70%) 초과 시 읽은 수신 + 발신 자동 정리
- 모뎀 자기 번호(수신번호) API로 조회 불가 → IMEI로 식별, 번호는 서버에서 수동 매핑
- MMS/이미지 메시지 → 안내 메시지로 자동 응답 (`[AI 발신] 지원하지 않는 형식의 문자입니다.`)
- 데이터 미지원 USIM은 SMS 수신은 되지만 서버 전송 불가
- 모뎀 비밀번호 연속 오류 시 잠금(108007) → 모뎀 전원 재시작 필요

## 12. 파일 구조

```
sms_test/
├── server.py               # 진입점 (aiohttp 서버 + 폴링 시작)
├── modems.json              # 모뎀 설정 (url, user, env_pass) — gitignored
├── modems.json.example      # 모뎀 설정 템플릿
├── .env                     # 환경변수 (모뎀 비밀번호, Slack 등) — gitignored
├── .env.example             # 환경변수 템플릿
├── requirements.txt         # Python 의존성
├── services/
│   ├── modem.py             # 모뎀 통신 서비스 (ModemService)
│   ├── poller.py            # SMS 폴링 루프
│   ├── reply.py             # 답장 생성
│   ├── slack.py             # Slack 웹훅 알림
│   ├── spam_filter.py       # 스팸 필터 (번호 + 키워드)
│   └── storage.py           # SMS 저장 서비스
├── routes/
│   └── sms.py               # API 라우트 (/v1/sms)
└── scripts/                 # 디버그/유틸 스크립트
```
