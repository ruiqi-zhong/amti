from argparse import ArgumentParser
import os
import json


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--output_dir', type=str, help='Path to output directory')

    args = parser.parse_args()

    args_dict = json.load(open(os.path.join(args.output_dir, 'args.json'), 'r'))
    cmd_suffix = ' --live' if args_dict['live'] else ''

    for f in os.listdir(args.output_dir):
        if 'level-' not in f:
            continue
        level_dir = os.path.join(args.output_dir, f)
        for f2 in os.listdir(level_dir):
            if 'batch-' in f2:
                cmd = f'amti status-batch {os.path.join(level_dir, f2)}' + cmd_suffix
                print(cmd)
                os.system(cmd)
    