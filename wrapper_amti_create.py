from argparse import ArgumentParser
import os
import shutil
import json
from amti import actions
from amti import settings
from amti import utils
import time

def count_total_words_in_dict(d):
    total_word = 0
    for x in d:
        if 'text' in x:
            total_word += len(d[x].split())
    return total_word


def get_reward(x):
    if x <= 256:
        return 0
    elif x <= 512:
        return 1
    elif x <= 1024:
        return 2
    elif x <= 2048:
        return 3
    else:
        return 4

rewards = [0.25, 0.5, 1.2, 1.8, 2.2]

def create_batch(definition_dir, data_path, save_dir, live):
    assert live in (True, False)
    env = 'live' if live else 'sandbox'

    worker_url = settings.ENVS[env]['worker_url']

    client = utils.mturk.get_mturk_client(env)

    estimated_cost = actions.create.estimate_batch_cost(
        definition_dir, data_path)
    print(f'The environment is {env}.')
    print(f'The estimated cost for this batch is ~{estimated_cost:.2f} USD.')
    cost_approved = input(f'Approve cost (~{estimated_cost:.2f} USD) and upload? [y/N]: ') == 'y'
    if not cost_approved:
        print('The batch cost was not approved. Aborting batch creation.')

    batch_dir = actions.create.create_batch(
        client=client,
        definition_dir=definition_dir,
        data_path=data_path,
        save_dir=save_dir)

    print(
        f'Finished creating batch directory: {batch_dir}.'
        f'\n'
        f'\n    Preview HITs: {worker_url}'
        f'\n')
    

def create_def_dir(orig_def_dir, out_def_dir, reward, qual_id, HASH):
    shutil.copytree(orig_def_dir, out_def_dir)
    hittypeproperties_file = os.path.join(out_def_dir, 'hittypeproperties.json')
    with open(hittypeproperties_file, 'r') as f:
        content = f.read()
    content = content.replace('REWARD_VAR', str(reward))
    content = content.replace('QUALIFICATION_ID_VAR', str(qual_id))
    content = content.replace('HASH_VAR', str(HASH))
    with open(hittypeproperties_file, 'w') as f:
        f.write(content)


if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument('--type', choices=['ind', 'cmp'], help='type of hypotheses to annotate')
    parser.add_argument('--live', action='store_true', help='Use live AMTI server')
    parser.add_argument('--data_path', type=str, help='Path to data file')

    args = parser.parse_args()

    definition_dir = None
    if args.type == 'ind':
        definition_dir = '../DescribeDistributionalDifferences/mturk/individual-verifier-w-qualification/definition/'
    elif args.type == 'cmp':
        definition_dir = '../DescribeDistributionalDifferences/mturk/cmp-verifier-w-qualification/definition/'

    qualification_id = None
    if not args.live:
        if args.type == 'ind':
            qualification_id = '3SRUE8JDW5S0KYR9S24O7EWME1A5OS'
        elif args.type == 'cmp':
            qualification_id = '3KHNGLCM6NY9KI7STL43HGAAKP9YA1'
    else:
        if args.type == 'ind':
            qualification_id = '3LRUXMYH0QQ5EE4G8UKFAZ5S0VJ291'
        elif args.type == 'cmp':
            qualification_id = '37U405KO6B69E6N7Q04ULQW7AMEG3H'

    HASH = str(hash(time.time()))[:6]
    output_dir = os.path.basename(args.data_path).split('.')[0] + ('-sandbox' if not args.live else 'live') + '-' + args.type + '-' + HASH

    if os.path.exists(output_dir):
        raise ValueError('Output directory already exists')
    os.makedirs(output_dir)
    args_dict = dict(vars(args))
    json.dump(args_dict, open(os.path.join(output_dir, 'args.json'), 'w'), indent=2)


    shutil.copy(args.data_path, os.path.join(output_dir, 'data.jsonl'))
    shutil.copytree(definition_dir, os.path.join(output_dir, 'definition'))

    all_data = []
    with open(args.data_path, 'r') as f:
        for line in f:
            all_data.append(json.loads(line))
    
    data_by_level = [[] for _ in range(len(rewards))]
    data_id2level_idx = []
    for i, d in enumerate(all_data):
        word_count = count_total_words_in_dict(d)
        reward_level = get_reward(word_count)
        data_id2level_idx.append((reward_level, len(data_by_level[reward_level])))
        data_by_level[reward_level].append(d)
    json.dump(data_id2level_idx, open(os.path.join(output_dir, 'data_id2level_idx.json'), 'w'))

    for level in range(len(rewards)):
        data = data_by_level[level]
        if len(data) == 0:
            continue
        reward = rewards[level]
        reward_level_dir = os.path.join(output_dir, f'level-{level}')
        os.makedirs(reward_level_dir)

        data_file = os.path.join(reward_level_dir, 'data.jsonl')
        with open(data_file, 'w') as f:
            for d in data:
                f.write(json.dumps(d) + '\n')
        
        tmp_definition_dir = os.path.join(reward_level_dir, 'definition')
        create_def_dir(definition_dir, tmp_definition_dir, reward, qualification_id, HASH)

        create_batch(tmp_definition_dir, data_file, reward_level_dir, args.live)
    