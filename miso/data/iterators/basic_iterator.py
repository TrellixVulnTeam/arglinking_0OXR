from typing import Iterable
import logging
import random

from miso.utils import lazy_groups_of
from miso.data.instance import Instance
from miso.data.iterators.data_iterator import DataIterator
from miso.data.dataset import Batch

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


@DataIterator.register("basic")
class BasicIterator(DataIterator):
    """
    A very basic iterator that takes a dataset, possibly shuffles it, and creates fixed sized batches.

    It takes the same parameters as :class:`miso.data.iterators.DataIterator`
    """
    def _create_batches(self, instances: Iterable[Instance], shuffle: bool) -> Iterable[Batch]:
        # First break the dataset into memory-sized lists:
        for instance_list in self._memory_sized_lists(instances):
            if shuffle:
                random.shuffle(instance_list)
            iterator = iter(instance_list)
            # Then break each memory-sized list into batches.
            for batch_instances in lazy_groups_of(iterator, self._batch_size):
                for possibly_smaller_batches in self._ensure_batch_is_sufficiently_small(batch_instances):
                    batch = Batch(possibly_smaller_batches)
                    yield batch
