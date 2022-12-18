import json
import argparse
import os

if __name__ == '__main__':
    num_levels = 5
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_dir', type=str, help='Path to output directory')

    args = parser.parse_args()

    args_dict = json.load(open(os.path.join(args.output_dir, 'args.json'), 'r'))
    cmd_suffix = ' --live' if args_dict['live'] else ''

    data_id2level_idx = json.load(open(os.path.join(args.output_dir, 'data_id2level_idx.json'), 'r'))

    all_annotation_results, all_hit_ids = [], [None for _ in range(num_levels)]
    for level in range(num_levels):
        level_dir = os.path.join(args.output_dir, f'level-{level}')
        if not os.path.exists(level_dir):
            continue
        for f in os.listdir(level_dir):
            batch_dir = os.path.join(level_dir, f)
            if 'batch-' in f:
                break

        os.system('amti expire-batch {batch_dir}'.format(batch_dir=batch_dir) + cmd_suffix)
        os.system('amti review-batch {batch_dir} --approve-all'.format(batch_dir=batch_dir) + cmd_suffix)
        os.system('amti save-batch {batch_dir}'.format(batch_dir=batch_dir) + cmd_suffix)
        os.system('amti extract tabular {batch_dir} {batch_dir}/annotation_result.jsonl'.format(batch_dir=batch_dir))

        with open('{batch_dir}/annotation_result.jsonl'.format(batch_dir=batch_dir), 'r') as f:
            for line in f:
                all_annotation_results.append(json.loads(line))
        hit_ids = json.load(open(batch_dir + '/id_info.json', 'r'))['hit_ids']
        all_hit_ids[level] = hit_ids
    all_hit_ids = [all_hit_ids[level][idx] for level, idx in data_id2level_idx]
    hit_id2annotation_results = {}
    for annotation_result in all_annotation_results:
        h = annotation_result['HITId']
        if h not in hit_id2annotation_results:
            hit_id2annotation_results[h] = []
        hit_id2annotation_results[h].append(annotation_result)

    data_annotated = []
    with open('{output_dir}/data.jsonl'.format(output_dir=args.output_dir), 'r') as f:
        for i, line in enumerate(f):
            data = json.loads(line)
            data['annotation_results'] = hit_id2annotation_results.get(all_hit_ids[i], [])
            if len(data['annotation_results']) != 0:
                print(data['annotation_results'])
            data_annotated.append(data)
    assert len(data_annotated) == len(all_hit_ids)
    with open(os.path.join(args.output_dir, 'data_annotated.jsonl'), 'w') as f:
        for data in data_annotated:
            f.write(json.dumps(data) + '\n')
