import os
import json

import torch

from miso.utils import logging
from miso.utils.tqdm import Tqdm
from miso.utils.environment import move_to_device
from miso.utils.archival import load_archive
from miso.utils import environment
from miso.data.dataset_builder import load_dataset
from miso.data.iterators import BasicIterator

logger = logging.init_logger()


def evaluate(model, instances, iterator, device, outputdir=None):
    with torch.no_grad():
        model.eval()

        test_generator = iterator(
            instances=instances,
            shuffle=False,
            num_epochs=1
        )

        logger.info("Iterating over dataset")
        generator_tqdm = Tqdm.tqdm(
            test_generator,
            total=iterator.get_num_batches(instances)
        )
        for batch in generator_tqdm:
            batch = move_to_device(batch, device)
            # Some of this breaks the model interface.
            # `cpu_eval` tells the model to evaluate the full document
            # `skip` speeds up eval by only getting metrics at the end
            model(batch, for_training=False, for_prediction=True, cpu_eval=True, outputdir=outputdir)
            metrics = model.get_metrics(skip=True)
            description = ', '.join(["%s: %.2f" % (name, value) for name, value in metrics.items()]) + " ||"
            generator_tqdm.set_description(description, refresh=False)

        return model.get_metrics(reset=True)


def evaluate_from_args(args):
    if args.cuda_device > -1:
        device = torch.device('cuda:{}'.format(args.cuda_device))
    else:
        device = torch.device('cpu')

    # Load from archive
    archive = load_archive(args.archive_file, device, args.weights_file, args.embeddingfile)
    config = archive.config

    # Set up the environment.
    environment_params = config['environment']
    if not environment_params['serialization_dir']:
        environment_params['serialization_dir'] = args.outputdir
    environment.set_seed(environment_params)
    environment.prepare_global_logging(environment_params)

    model = archive.model
    model.eval()

    # Load the evaluation data
    # Try to use the validation dataset reader if there is one - otherwise fall back
    # to the default dataset_reader used for both training and validation.
    data_type = config['data']['data_type']
    if args.input_file:
        evaluation_data_path = args.input_file
    else:
        evaluation_data_path = os.path.join(config['data']['data_dir'], config['data']['test_data'])
    batch_size = args.batch_size if args.batch_size != -1 else config['data']['test_batch_size']

    logger.info("Reading evaluation data from %s", evaluation_data_path)
    instances = load_dataset(evaluation_data_path, data_type, **config['data'])

    iterator = BasicIterator(batch_size=batch_size)
    iterator.index_with(model.vocab)

    metrics = evaluate(model, instances, iterator, device, args.outputdir)

    logger.info("Finished evaluating.")
    logger.info("Metrics:")
    for key, metric in metrics.items():
        logger.info("%s: %s", key, metric)

    output_file = args.output_file
    if output_file:
        with open(output_file, "w") as file:
            json.dump(metrics, file, indent=4)
    return metrics


if __name__ == '__main__':
    import argparse

    description = '''Evaluate the specified model + dataset'''
    parser = argparse.ArgumentParser('evaluate.py', description=description)

    parser.add_argument('archive_file', type=str, help='path to an archived trained model')
    parser.add_argument('--input-file', type=str, help='path to the file containing the evaluation data')
    parser.add_argument('--output-file', type=str, help='path to output file')
    parser.add_argument('--weights-file', type=str, help='a path that overrides which weights file to use')
    parser.add_argument('--batch-size', type=int, default=-1, help='batch size')
    parser.add_argument('--cuda-device', type=int, default=-1, help='id of GPU to use (if any)')
    parser.add_argument('--outputdir', type=str, help='path to output directory for prediction files')
    parser.add_argument('--embeddingfile', type=str, help='path to contextualized embedding file')

    args = parser.parse_args()
    evaluate_from_args(args)
