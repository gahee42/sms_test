"""Huawei E8372h-320 HiLink 모뎀 CLI 도구"""
import argparse
import json
import sys

from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection

MODEM_URL = 'http://192.168.8.1/'


def connect():
    conn = Connection(MODEM_URL)
    return conn, Client(conn)


def cmd_check(_args):
    """모뎀 연결 + 기기정보 + 네트워크 상태"""
    conn, client = connect()
    with conn:
        print('[1] 기기 정보')
        info = client.device.information()
        for key in ['DeviceName', 'Imei', 'SerialNumber', 'HardwareVersion', 'SoftwareVersion']:
            print(f'    {key}: {info.get(key)}')

        print('[2] SMS 개수')
        count = client.sms.sms_count()
        print(f'    수신함: {count.get("LocalInbox", 0)}건')
        print(f'    안읽음: {count.get("LocalUnread", 0)}건')

        print('[3] 신호 세기')
        signal = client.device.signal()
        print(f'    RSSI: {signal.get("rssi")}')
        print(f'    RSRP: {signal.get("rsrp")}')
        print(f'    SINR: {signal.get("sinr")}')
        print(f'    Band: {signal.get("band")}')

        print('\n✅ 모뎀 정상 연결!')


def cmd_sms_list(args):
    """SMS 목록 조회"""
    conn, client = connect()
    with conn:
        sms_list = client.sms.get_sms_list(
            args.page, BoxType=args.box, ReadCount=args.count, UnreadPreferred=1
        )
        messages = sms_list.get('Messages', {}).get('Message', [])
        if isinstance(messages, dict):
            messages = [messages]

        if not messages:
            print('SMS 없음')
            return

        for sms in messages:
            status = '📩' if sms.get('Smstat') == '0' else '✅'
            print(f'{status} [{sms.get("Index")}] {sms.get("Phone")} | {sms.get("Date")}')
            print(f'   {sms.get("Content")}')
            print()


def cmd_sms_count(_args):
    """SMS 개수 조회"""
    conn, client = connect()
    with conn:
        count = client.sms.sms_count()
        print(json.dumps(count, indent=2, ensure_ascii=False))


def cmd_sms_send(args):
    """SMS 발송"""
    conn, client = connect()
    with conn:
        client.sms.send_sms([args.phone], args.message)
        print(f'✅ 발송 완료 → {args.phone}')


def cmd_sms_delete(args):
    """SMS 삭제"""
    conn, client = connect()
    with conn:
        client.sms.delete_sms(args.index)
        print(f'✅ 삭제 완료 Index:{args.index}')


def cmd_sms_read(args):
    """SMS 읽음 처리"""
    conn, client = connect()
    with conn:
        client.sms.set_read(args.index)
        print(f'✅ 읽음 처리 완료 Index:{args.index}')


def cmd_signal(_args):
    """신호 세기 조회"""
    conn, client = connect()
    with conn:
        signal = client.device.signal()
        print(json.dumps(signal, indent=2, ensure_ascii=False))


def cmd_dump(_args):
    """모뎀 지원 API 전체 덤프"""
    conn, client = connect()
    with conn:
        sections = {
            'device.information': lambda: client.device.information(),
            'device.signal': lambda: client.device.signal(),
            'device.basic_information': lambda: client.device.basic_information(),
            'sms.sms_count': lambda: client.sms.sms_count(),
            'sms.get_sms_list(page=1)': lambda: client.sms.get_sms_list(1, BoxType=1, ReadCount=5),
            'net.current_plmn': lambda: client.net.current_plmn(),
            'net.net_mode': lambda: client.net.net_mode(),
            'monitoring.status': lambda: client.monitoring.status(),
            'monitoring.traffic_statistics': lambda: client.monitoring.traffic_statistics(),
        }

        for name, fn in sections.items():
            print(f'\n=== {name} ===')
            try:
                result = fn()
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f'  ❌ {e}')


def main():
    parser = argparse.ArgumentParser(description='Huawei E8372 모뎀 CLI')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('check', help='모뎀 연결 + 기기정보 확인')

    p_list = sub.add_parser('sms-list', help='SMS 목록 조회')
    p_list.add_argument('--page', type=int, default=1)
    p_list.add_argument('--count', type=int, default=20)
    p_list.add_argument('--box', type=int, default=1, help='1=수신함, 2=발신함')

    sub.add_parser('sms-count', help='SMS 개수 조회')

    p_send = sub.add_parser('sms-send', help='SMS 발송')
    p_send.add_argument('phone', help='수신 번호')
    p_send.add_argument('message', help='메시지 내용')

    p_del = sub.add_parser('sms-delete', help='SMS 삭제')
    p_del.add_argument('index', type=int, help='SMS Index')

    p_read = sub.add_parser('sms-read', help='SMS 읽음 처리')
    p_read.add_argument('index', type=int, help='SMS Index')

    sub.add_parser('signal', help='신호 세기 조회')
    sub.add_parser('dump', help='모뎀 지원 API 전체 덤프')

    args = parser.parse_args()

    commands = {
        'check': cmd_check,
        'sms-list': cmd_sms_list,
        'sms-count': cmd_sms_count,
        'sms-send': cmd_sms_send,
        'sms-delete': cmd_sms_delete,
        'sms-read': cmd_sms_read,
        'signal': cmd_signal,
        'dump': cmd_dump,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f'\n❌ 에러: {e}', file=sys.stderr)
        print('   - USB 연결 확인', file=sys.stderr)
        print('   - 192.168.8.1 접속 가능한지 확인', file=sys.stderr)
        print('   - USIM 장착 확인', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
