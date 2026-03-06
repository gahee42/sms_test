# Huawei E8372h-320 HiLink API Raw 응답 레퍼런스

> 공식 문서 없음. `raw_dump.py`로 실제 모뎀에서 수집한 데이터 기반.
> 모든 응답은 XML 형식. `huawei-lte-api` 라이브러리 사용 시 dict로 자동 변환됨.

---

## 1. 인증 및 요청 방식

| 구분 | 설명 |
|------|------|
| 인증 | SHA256 기반 로그인 (라이브러리가 처리) |
| CSRF 토큰 | POST 요청마다 `GET /api/webserver/SesTokInfo`로 발급 |
| 세션 제한 | **동시 1개만** (다른 세션 로그인 시 기존 끊김) |
| Rate Limit | 명시적 제한 없음 (임베디드 기기 성능 한계만 존재) |
| 요청 형식 | GET 또는 POST (XML body) |
| 응답 형식 | XML (`<response>...</response>` 또는 `<error><code>...</code></error>`) |

---

## 2. GET 엔드포인트 (조회, 모뎀 변경 없음)

### 2-1. device — `GET /api/device/information` (로그인 필요)

기기 정보 + USIM 정보 + 네트워크 정보.

```xml
<response>
  <DeviceName>E8372h-320</DeviceName>
  <SerialNumber>MUJ7S21414006306</SerialNumber>
  <Imei>862147042567236</Imei>
  <Imsi>450050215130591</Imsi>
  <Iccid>8982052204601894112</Iccid>
  <Msisdn>01021513520</Msisdn>
  <HardwareVersion>CL4E8372HM01</HardwareVersion>
  <SoftwareVersion>10.0.5.1(H195SP4C983)</SoftwareVersion>
  <WebUIVersion>WEBUI 10.0.5.1(W13SP5C7702)</WebUIVersion>
  <MacAddress1>34:71:46:0D:37:F4</MacAddress1>
  <MacAddress2></MacAddress2>
  <WanIPAddress>10.19.125.192</WanIPAddress>
  <wan_dns_address>172.27.16.171,113.217.240.31</wan_dns_address>
  <WanIPv6Address></WanIPv6Address>
  <wan_ipv6_dns_address></wan_ipv6_dns_address>
  <ProductFamily>LTE</ProductFamily>
  <Classify>wingle</Classify>
  <supportmode>LTE|WCDMA|GSM</supportmode>
  <workmode>LTE</workmode>
  <submask>255.255.255.255</submask>
  <Mccmnc>45005</Mccmnc>
  <iniversion>E8372h-320-CUST 10.0.5.1(C778)</iniversion>
  <uptime>2407</uptime>
  <ImeiSvn>02</ImeiSvn>
  <WifiMacAddrWl0>34:71:46:0D:37:F4</WifiMacAddrWl0>
  <WifiMacAddrWl1></WifiMacAddrWl1>
  <spreadname_en>HUAWEI LTE Wingle</spreadname_en>
  <spreadname_zh>HUAWEI LTE Wingle</spreadname_zh>
</response>
```

| 필드 | 설명 | 비고 |
|------|------|------|
| **Imei** | 모뎀 고유 식별자 | 모뎀 식별 키 |
| **Msisdn** | 모뎀 전화번호 (수신번호) | 자동 획득 가능! |
| **Imsi** | USIM 가입자 식별번호 | |
| **Iccid** | USIM 카드 고유번호 | |
| **DeviceName** | 모뎀 모델명 | |
| **Mccmnc** | 통신사 코드 (450=한국, 05=SKT) | |
| **WanIPAddress** | LTE 할당 IP | |
| **uptime** | 가동 시간 (초) | |
| **workmode** | 현재 네트워크 모드 | LTE, WCDMA, GSM |

---

### 2-2. signal — `GET /api/device/signal` (로그인 필요)

신호 품질 정보.

```xml
<response>
  <pci>144</pci>
  <sc></sc>
  <cell_id>7267507</cell_id>
  <rsrq>-8.0dB</rsrq>
  <rsrp>-96dBm</rsrp>
  <rssi>-73dBm</rssi>
  <sinr>5dB</sinr>
  <rscp></rscp>
  <ecio></ecio>
  <mode>7</mode>
  <ulbandwidth>10MHz</ulbandwidth>
  <dlbandwidth>10MHz</dlbandwidth>
  <txpower>PPusch:7dBm PPucch:-3dBm PSrs:8dBm PPrach:3dBm</txpower>
  <tdd></tdd>
  <ul_mcs>mcsUpCarrier1:14</ul_mcs>
  <dl_mcs>mcsDownCarrier1Code0:0 mcsDownCarrier1Code1:0</dl_mcs>
  <earfcn>DL:3200 UL:21200</earfcn>
  <rrc_status></rrc_status>
  <rac></rac>
  <lac></lac>
  <tac>12583</tac>
  <band>7</band>
  <nei_cellid>No1:449</nei_cellid>
  <plmn>45005</plmn>
  <ims></ims>
  <wdlfreq></wdlfreq>
  <lteulfreq>25450</lteulfreq>
  <ltedlfreq>26650</ltedlfreq>
  <transmode>TM[3]</transmode>
  <enodeb_id>0028388</enodeb_id>
  <cqi0>8</cqi0>
  <cqi1>8</cqi1>
  <ulfrequency>2545000kHz</ulfrequency>
  <dlfrequency>2665000kHz</dlfrequency>
  <arfcn></arfcn>
  <bsic></bsic>
  <rxlev></rxlev>
</response>
```

| 필드 | 설명 | 좋음 | 보통 | 나쁨 |
|------|------|------|------|------|
| **rssi** | 신호 세기 | > -65 | -65~-85 | < -85 |
| **rsrp** | 기준 신호 세기 | > -80 | -80~-100 | < -100 |
| **rsrq** | 신호 품질 | > -5 | -5~-10 | < -10 |
| **sinr** | 신호 대 잡음비 | > 10 | 5~10 | < 5 |
| **band** | LTE Band | - | - | - |
| **cell_id** | 기지국 셀 ID | - | - | - |

---

### 2-3. basic — `GET /api/device/basic_information` (로그인 불필요)

```xml
<response>
  <productfamily>LTE</productfamily>
  <classify>wingle</classify>
  <multimode>0</multimode>
  <restore_default_status>0</restore_default_status>
  <sim_save_pin_enable>0</sim_save_pin_enable>
  <devicename>E8372h-320</devicename>
  <spreadname_en>HUAWEI LTE Wingle</spreadname_en>
  <spreadname_zh>HUAWEI LTE Wingle</spreadname_zh>
</response>
```

> `device`의 하위 호환. 로그인 없이 접근 가능한 것 외에 추가 가치 없음.

---

### 2-4. sms-count — `GET /api/sms/sms-count` (로그인 불필요)

SMS 저장 현황.

```xml
<response>
  <LocalUnread>5</LocalUnread>
  <LocalInbox>18</LocalInbox>
  <LocalOutbox>3</LocalOutbox>
  <LocalDraft>0</LocalDraft>
  <LocalDeleted>0</LocalDeleted>
  <SimUnread>0</SimUnread>
  <SimInbox>0</SimInbox>
  <SimOutbox>0</SimOutbox>
  <SimDraft>0</SimDraft>
  <LocalMax>500</LocalMax>
  <SimMax>0</SimMax>
  <SimUsed>0</SimUsed>
  <NewMsg>0</NewMsg>
</response>
```

| 필드 | 설명 | 비고 |
|------|------|------|
| **LocalUnread** | 안 읽은 SMS 수 | 폴러가 가져갈 대상 |
| **LocalInbox** | 수신함 전체 수 | |
| **LocalMax** | 최대 저장 한도 | 500건 (수신+발신 합산) |
| LocalOutbox | 발신함 수 | |
| SimMax | USIM 저장 한도 | 0 (이 모뎀은 USIM 저장 안 함) |

---

### 2-5. sms-config — `GET /api/sms/config` (로그인 필요)

SMS 설정 값.

```xml
<response>
  <SaveMode>0</SaveMode>
  <Validity>10752</Validity>
  <Sca>+82100099102151</Sca>
  <UseSReport>0</UseSReport>
  <SendType>1</SendType>
  <pagesize>20</pagesize>
  <maxphone>50</maxphone>
  <import_enabled>1</import_enabled>
  <url_enabled>1</url_enabled>
  <cdma_enabled>0</cdma_enabled>
  <smscharlang>0</smscharlang>
  <smsisusepdu>0</smsisusepdu>
  <sms_center_number_editabled>1</sms_center_number_editabled>
  <sms_forward_enable>0</sms_forward_enable>
  <switch_enable>0</switch_enable>
  <country_number></country_number>
  <phone_number></phone_number>
</response>
```

| 필드 | 설명 | 비고 |
|------|------|------|
| Sca | SMS 서비스 센터 번호 | +82100099102151 (SKT) |
| SaveMode | 저장 위치 | 0=내부 플래시, 1=USIM |
| Validity | SMS 유효기간 (분) | 10752분 ≈ 7.5일 |
| maxphone | 발송 시 최대 수신자 수 | 50명 |
| pagesize | 기본 페이지 크기 | 20건 |

---

### 2-6. status — `GET /api/monitoring/status` (로그인 불필요)

모뎀 연결 / 네트워크 / USIM 상태.

```xml
<response>
  <ConnectionStatus>901</ConnectionStatus>
  <WifiConnectionStatus></WifiConnectionStatus>
  <SignalStrength></SignalStrength>
  <SignalIcon>5</SignalIcon>
  <CurrentNetworkType>19</CurrentNetworkType>
  <CurrentServiceDomain>3</CurrentServiceDomain>
  <RoamingStatus>0</RoamingStatus>
  <BatteryStatus></BatteryStatus>
  <BatteryLevel></BatteryLevel>
  <BatteryPercent></BatteryPercent>
  <simlockStatus>0</simlockStatus>
  <PrimaryDns>223.62.230.7</PrimaryDns>
  <SecondaryDns>113.217.240.31</SecondaryDns>
  <wififrequence>0</wififrequence>
  <flymode>0</flymode>
  <PrimaryIPv6Dns></PrimaryIPv6Dns>
  <SecondaryIPv6Dns></SecondaryIPv6Dns>
  <CurrentWifiUser>1</CurrentWifiUser>
  <TotalWifiUser>16</TotalWifiUser>
  <currenttotalwifiuser>16</currenttotalwifiuser>
  <ServiceStatus>2</ServiceStatus>
  <SimStatus>1</SimStatus>
  <WifiStatus>1</WifiStatus>
  <CurrentNetworkTypeEx>101</CurrentNetworkTypeEx>
  <maxsignal>5</maxsignal>
  <wifiindooronly>0</wifiindooronly>
  <cellroam>1</cellroam>
  <classify>wingle</classify>
  <usbup>0</usbup>
  <wifiswitchstatus>1</wifiswitchstatus>
  <WifiStatusExCustom>0</WifiStatusExCustom>
  <hvdcp_online>0</hvdcp_online>
  <speedLimitStatus>0</speedLimitStatus>
</response>
```

| 필드 | 설명 | 값 |
|------|------|-----|
| **ConnectionStatus** | 연결 상태 | 900=연결중, **901=연결됨**, 902=해제됨, 903=해제중 |
| **SimStatus** | USIM 상태 | **1=정상**, 0=없음/오류 |
| **ServiceStatus** | 서비스 상태 | **2=사용가능**, 0=불가 |
| **SignalIcon** | 신호 막대 수 | 0~5 (5=최강) |
| **CurrentNetworkType** | 네트워크 타입 | 0=없음, 3=GSM, 5=WCDMA, **19=LTE** |
| CurrentNetworkTypeEx | 네트워크 타입 확장 | 101=LTE+ (CA) |
| RoamingStatus | 로밍 여부 | 0=아님, 1=로밍중 |

---

### 2-7. traffic — `GET /api/monitoring/traffic-statistics` (로그인 불필요)

데이터 사용량 통계. 단위: 바이트(byte), 속도: 바이트/초(byte/s), 시간: 초(s).

```xml
<response>
  <CurrentConnectTime>1186</CurrentConnectTime>
  <CurrentUpload>10890571</CurrentUpload>
  <CurrentDownload>11708837</CurrentDownload>
  <CurrentDownloadRate>1152</CurrentDownloadRate>
  <CurrentUploadRate>512</CurrentUploadRate>
  <TotalUpload>94343810</TotalUpload>
  <TotalDownload>298829941</TotalDownload>
  <TotalConnectTime>12198</TotalConnectTime>
  <showtraffic>1</showtraffic>
  <MaxUploadRate>194730</MaxUploadRate>
  <MaxDownloadRate>912716</MaxDownloadRate>
</response>
```

| 필드 | 설명 | 비고 |
|------|------|------|
| TotalUpload | 누적 업로드 (bytes) | |
| TotalDownload | 누적 다운로드 (bytes) | |
| TotalConnectTime | 누적 연결 시간 (초) | |
| CurrentDownloadRate | 현재 다운로드 속도 (bytes/s) | |
| CurrentUploadRate | 현재 업로드 속도 (bytes/s) | |

---

### 2-8. plmn — `GET /api/net/current-plmn` (로그인 불필요)

통신사 정보.

```xml
<response>
  <State>0</State>
  <FullName>SKTelecom</FullName>
  <ShortName>SKTelecom</ShortName>
  <Numeric>45005</Numeric>
  <Rat>7</Rat>
  <Spn></Spn>
</response>
```

| 필드 | 설명 | 비고 |
|------|------|------|
| **FullName** | 통신사 이름 | 대시보드 표시용 |
| **Numeric** | MCC+MNC | 450=한국, 05=SKT |
| **Rat** | 접속 기술 | 0=GSM, 2=WCDMA, **7=LTE** |

---

### 2-9. net-mode — `GET /api/net/net-mode` (로그인 필요)

네트워크 모드 설정.

```xml
<response>
  <NetworkMode>00</NetworkMode>
  <NetworkBand>2000004400000</NetworkBand>
  <LTEBand>80800D5</LTEBand>
</response>
```

| 필드 | 설명 | 비고 |
|------|------|------|
| NetworkMode | 모드 설정 | 00=자동, 01=GSM, 02=WCDMA, 03=LTE |

> 모뎀 설정값. 운영에서 변경할 일 없음.

---

## 3. POST 엔드포인트 (조회)

### 3-1. sms-list — `POST /api/sms/sms-list` (로그인 필요)

SMS 목록 조회.

**요청 XML:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<request>
  <PageIndex>1</PageIndex>
  <ReadCount>50</ReadCount>
  <BoxType>1</BoxType>
  <SortType>0</SortType>
  <Ascending>0</Ascending>
  <UnreadPreferred>1</UnreadPreferred>
</request>
```

**요청 파라미터:**

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| PageIndex | 1, 2, 3... | 페이지 번호 |
| ReadCount | 1~50 | 한 페이지당 개수 (최대 50) |
| BoxType | 아래 참조 | 메일함 종류 |
| SortType | 0=날짜, 1=번호, 2=Index | 정렬 기준 |
| Ascending | 0=내림차순, 1=오름차순 | 정렬 방향 |
| UnreadPreferred | 0=안함, 1=안읽은거 먼저 | 우선 배치 |

**BoxType 값:**

| 값 | 이름 | 설명 |
|----|------|------|
| 1 | LOCAL_INBOX | 수신함 |
| 2 | LOCAL_SENT | 발신함 |
| 3 | LOCAL_DRAFT | 임시저장 |
| 4 | LOCAL_TRASH | 휴지통 |

**응답 XML:**
```xml
<response>
  <Count>18</Count>
  <Messages>
    <Message>
      <Smstat>0</Smstat>
      <Index>40020</Index>
      <Phone>01094727956</Phone>
      <Content>모뎀 미설정 문자 4</Content>
      <Date>2026-03-05 16:39:48</Date>
      <Sca></Sca>
      <SaveType>0</SaveType>
      <Priority>0</Priority>
      <SmsType>1</SmsType>
    </Message>
    <!-- ... -->
  </Messages>
</response>
```

**메시지 필드:**

| 필드 | 설명 | 비고 |
|------|------|------|
| **Smstat** | 읽음 상태 | 0=안읽음, 1=읽음, 2=발신대기, 3=발신완료, 4=발신실패 |
| **Index** | 메시지 고유 ID | 삭제 시 사용 |
| **Phone** | 발신자 번호 | 하이픈 없는 숫자 |
| **Content** | 메시지 내용 | |
| **Date** | 수신 일시 | YYYY-MM-DD HH:MM:SS |
| **SmsType** | 메시지 타입 | 1=일반, 2=장문, 5=유니코드, 7=수신확인성공, 8=수신확인실패 |
| Sca | SMS 서비스 센터 | 보통 빈값 |
| SaveType | 저장 타입 | 0 |
| Priority | 우선순위 | 0 |

---

## 4. POST 엔드포인트 (액션 — 모뎀 변경 발생)

### 4-1. sms-send — `POST /api/sms/send-sms` (로그인 필요)

SMS 발송. **실제 발송됨!**

**요청 XML:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<request>
  <Index>-1</Index>
  <Phones><Phone>01094727956</Phone></Phones>
  <Sca></Sca>
  <Content>메시지 내용</Content>
  <Length>-1</Length>
  <Reserved>1</Reserved>
  <Date>-1</Date>
</request>
```

**요청 파라미터:**

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| Index | -1 | 고정값 |
| Phones | `<Phone>번호</Phone>` | 수신자 (여러 명 가능, Phone 태그 반복) |
| Content | 문자열 | 메시지 내용 |
| Length | -1 | 고정값 (자동 계산) |
| Reserved | 1 | 고정값 |
| Date | -1 | 고정값 (자동) |

> 전화번호는 **하이픈 없는 숫자만** 허용. 하이픈 포함 시 에러코드 100005.

**성공 응답:**
```xml
<response>OK</response>
```

**에러 응답:**
```xml
<error>
  <code>100005</code>
  <message></message>
</error>
```

---

### 4-2. sms-delete — `POST /api/sms/delete-sms` (로그인 필요)

SMS 삭제. **실제 삭제됨!**

**요청 XML:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<request>
  <Index>40001</Index>
</request>
```

**성공 응답:**
```xml
<response>OK</response>
```

> 주의: 존재하지 않는 Index를 삭제해도 `OK` 반환. 존재 여부 검증 안 함.

---

## 5. MMS / 이모티콘 / 특수문자 처리

### 5-1. 메시지 타입별 동작

| 보낸 것 | 모뎀 저장 | Content (raw XML) | Content (라이브러리) | XML 파싱 |
|---------|----------|-------------------|---------------------|----------|
| **텍스트만** | O | 정상 | 정상 | OK |
| **이모티콘만** | O | `    ` (빈 공백) | `None` | OK |
| **텍스트+이모티콘** | O | 이모티콘 탈락, 텍스트만 남음 | 텍스트만 남음 | OK |
| **이미지(MMS)** | O (깨진 상태) | `¾¯` + 깨진 바이트 | XML 파싱 에러 | **FAIL** |
| **이미지+텍스트** | O (합쳐짐) | `¾¯` + 텍스트 | XML 파싱 에러 | **FAIL** |

### 5-2. MMS 치명적 이슈

**MMS는 모뎀에 깨진 상태로 저장되며, 이후 수신되는 SMS를 흡수(병합)한다.**

실제 테스트 결과:
```xml
<!-- 이미지 보낸 후, 다른 번호에서 온 문자가 MMS에 병합됨 -->
<Message>
  <Index>40000</Index>
  <Phone>01094727956</Phone>           <!-- MMS 발신자 번호로 덮어씌워짐 -->
  <Content>¾¯
    성기본1G+1M요금제의 기본제공 데이터가 459MB 남았습니다.</Content>  <!-- 다른 번호에서 온 문자! -->
</Message>
```

- MMS 발신자의 Phone으로 덮어씌워짐 (원래 발신자 정보 소실)
- 이후 수신 SMS의 Content가 MMS에 합쳐짐
- **원본 SMS 복구 불가**

### 5-3. MMS 감지 및 핸들링

**감지 방법:** Content에 `¾¯` 패턴 포함 여부 (Index는 매번 달라서 사용 불가)

**폴러 핸들링 전략:**
```
1. 라이브러리로 sms-list 시도
   ├─ 성공 → 각 메시지 처리
   │   ├─ Content 정상 → 서버 전송
   │   ├─ Content = None → Content "" 으로 서버 전송
   │   └─ (MMS는 라이브러리 단계에서 파싱 실패하므로 여기 안 옴)
   │
   └─ 실패 (XML 파싱 에러 = MMS 존재) → fallback:
       ├─ raw HTTP로 sms-list 텍스트 받기
       ├─ 정규식으로 각 Message 블록에서 Index, Phone, Date, Content 추출
       ├─ Content에 "¾¯" 포함 → MMS → 즉시 삭제 + 서버에 [MMS] 기록
       ├─ Content 정상 → 서버 전송
       └─ Slack 알림: "모뎀 [IMEI]에 MMS 수신 — 자동 삭제"
```

**핵심: MMS를 빨리 삭제해야 다음 SMS가 병합되는 것을 방지할 수 있다.**

---

## 6. 에러코드

| 코드 | 의미 | 대응 |
|------|------|------|
| 100003 | 로그인 필요 | 재로그인 |
| 100005 | 잘못된 파라미터 | 요청값 확인 (전화번호 하이픈 등) |
| 125002 | 세션 에러 | 재연결 |
| 125003 | 잘못된 세션 토큰 | 재연결 |

---

## 7. 운영 데이터 요약

### 7-1. SMS 폴링 사이클에 필요한 데이터

```
[폴러 시작] → device에서 Imei, Msisdn 획득
     ↓
[폴링 루프]
     ↓
  1. sms-list (Smstat=0인 것만) → Index, Phone, Content, Date 추출
     ↓
  2. POST /v1/sms → 서버에 JSON 전송 { imei, msisdn, messages[] }
     ↓
  3. 서버 응답에 reply 있으면 → sms-send로 답장 발송
     ↓
  4. sms-delete로 처리한 SMS 삭제
     ↓
  5. POLL_INTERVAL(5초) 대기 → 1로 반복
```

**Python → 서버 전송 JSON (제안):**
```json
{
  "imei": "862147042567236",
  "msisdn": "01021513520",
  "messages": [
    {
      "index": 40020,
      "phone": "01094727956",
      "content": "메시지 내용",
      "date": "2026-03-05 16:39:48",
      "smsType": 1
    }
  ]
}
```

**서버 → Python 응답 JSON (제안):**
```json
{
  "ok": true,
  "replies": [
    {
      "phone": "01094727956",
      "message": "답장 내용"
    }
  ]
}
```

### 7-2. 모뎀 헬스체크에 필요한 데이터 (Slack 알림용)

모뎀별 상태를 주기적으로 서버에 보내고, 서버가 Slack으로 알림.

**판단 기준:**

| 항목 | 정상 | 비정상 (Slack 알림) |
|------|------|---------------------|
| ConnectionStatus | 901 | 그 외 (연결 안 됨) |
| SimStatus | 1 | 0 (USIM 없음/오류) |
| ServiceStatus | 2 | 그 외 (서비스 불가) |
| SignalIcon | 1~5 | 0 (신호 없음) |
| rssi | > -85dBm | < -85dBm (신호 약함) |
| sinr | > 5dB | < 5dB (품질 나쁨) |

**Slack 알림 시나리오:**

| 상황 | 감지 방법 | 알림 |
|------|----------|------|
| 라즈베리파이 장애 | 서버에 모든 모뎀 heartbeat 끊김 | "라즈베리파이 연결 끊김 — 모든 모뎀 응답 없음" |
| 특정 모뎀 장애 | 해당 모뎀만 heartbeat 끊김 | "모뎀 [IMEI] 연결 끊김" |
| 모뎀 신호 불량 | rssi < -85 또는 sinr < 5 | "모뎀 [IMEI] 신호 약함 (RSSI: -90dBm)" |
| USIM 오류 | SimStatus ≠ 1 | "모뎀 [IMEI] USIM 오류" |
| SMS 저장 한도 근접 | LocalInbox > 400 (500 중) | "모뎀 [IMEI] SMS 저장 80% 초과" |

**Python → 서버 헬스체크 JSON (제안):**
```json
{
  "imei": "862147042567236",
  "msisdn": "01021513520",
  "deviceName": "E8372h-320",
  "status": {
    "connectionStatus": 901,
    "simStatus": 1,
    "serviceStatus": 2,
    "signalIcon": 5,
    "networkType": 19
  },
  "signal": {
    "rssi": "-73dBm",
    "rsrp": "-96dBm",
    "rsrq": "-8.0dB",
    "sinr": "5dB",
    "band": "7"
  },
  "smsCount": {
    "localUnread": 5,
    "localInbox": 18,
    "localMax": 500
  },
  "traffic": {
    "totalUpload": 94343810,
    "totalDownload": 298829941
  },
  "carrier": "SKTelecom"
}
```
