import argparse
from src.log_subject_info import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--id', help='Subject ID', default='Pin001')
    parser.add_argument('--session', help='Session ID', default='A1')
    parser.add_argument('--hand', help='hand=Right/Left', default='Right')
    parser.add_argument('--wrist', help='wrist position=flex/pron', default='flex')
    parser.add_argument('--exp', help='exp=pinch(1)/tunnel(2)/dial(3)/learning(4)', default='1')
    args = parser.parse_args()

    LogSubjectInfo(id=args.id,session=args.session,hand=args.hand,wrist=args.wrist,exp=args.exp)
