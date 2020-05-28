import argparse
from src.setup_hand import HandS

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--id', help='Subject ID', default='Pin001')
    parser.add_argument('--session', help='Session ID', default='A1')
    parser.add_argument('--hand', help='hand', default='Right')
    parser.add_argument('--wrist', help='wrist position=flex/pron', default='flex')
    parser.add_argument('--trial', help='setup trial number',default='1')
    parser.add_argument('--exp', help='exp=pinch(1)/tunnel(2)/dial(3)/learning(4)', default='1')
    args = parser.parse_args()

    setup = HandS(id=args.id,session=args.session,hand=args.hand,wrist=args.wrist,trial=args.trial,exp=args.exp)

    with setup.dev:
      setup.run()
