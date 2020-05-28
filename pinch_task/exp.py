import argparse
from src.pinch_task.pinch_task import PinchTask
from src.tunnel_pinch_task.pinch_task import TunnelPinchTask
from src.dial_pinch_task.pinch_task import DialPinchTask
from src.learning_pinch_task.pinch_task import LearningPinchTask

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--id', help='Subject ID', default='Pin001')
    parser.add_argument('--exp', help='exp=pinch(1)/tunnel(2)/dial(3)/learning(4)', default='1')
    parser.add_argument('--session', help='Session ID', default='A1')
    parser.add_argument('--hand', help='hand', default='Right')
    parser.add_argument('--wrist', help='wrist position=flex/pron', default='flex')
    parser.add_argument('--blk', help='block number', default='1')
    parser.add_argument('--mode', help='mode=demo/task', default='task')
    args = parser.parse_args()

    if args.exp == '1':
        experiment = PinchTask(id=args.id,session=args.session,hand=args.hand,block=args.blk,mode=args.mode,wrist=args.wrist)
    elif args.exp == '2':
        experiment = TunnelPinchTask(id=args.id,session=args.session,hand=args.hand,block=args.blk,mode=args.mode,wrist=args.wrist)
    elif args.exp == '3':
        experiment = DialPinchTask(id=args.id,session=args.session,hand=args.hand,block=args.blk,mode=args.mode,wrist=args.wrist)
    elif args.exp == '4':
        experiment = LearningPinchTask(id=args.id, session=args.session,hand=args.hand,block=args.blk,mode=args.mode,wrist=args.wrist)
    else:
        raise IndexError('experiment index out of range')
        
    with experiment.dev:
        experiment.run()
