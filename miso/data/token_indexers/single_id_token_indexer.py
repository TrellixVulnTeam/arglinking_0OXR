from typing import Dict, List

from overrides import overrides

from miso.utils.string import pad_sequence_to_length
from miso.data.vocabulary import Vocabulary
from miso.data.tokenizers.token import Token
from miso.data.token_indexers.token_indexer import TokenIndexer


@TokenIndexer.register("single_id")
class SingleIdTokenIndexer(TokenIndexer[int]):
    """
    This :class:`TokenIndexer` represents tokens as single integers.

    Parameters
    ----------
    namespace : ``str``, optional (default=``tokens``)
        We will use this namespace in the :class:`Vocabulary` to map strings to indices.
    lowercase_tokens : ``bool``, optional (default=``False``)
        If ``True``, we will call ``token.lower()`` before getting an index for the token from the
        vocabulary.
    """
    # pylint: disable=no-self-use
    def __init__(self, namespace: str = 'tokens', lowercase_tokens: bool = False) -> None:
        self.namespace = namespace
        self.lowercase_tokens = lowercase_tokens

    @overrides
    def count_vocab_items(self, token: Token, counter: Dict[str, Dict[str, int]]):
        # If `text_id` is set on the token (e.g., if we're using some kind of hash-based word
        # encoding), we will not be using the vocab for this token.
        if getattr(token, 'text_id', None) is None:
            text = token.text
            if self.lowercase_tokens:
                text = text.lower()
            counter[self.namespace][text] += 1

    @overrides
    def tokens_to_indices(self,
                          tokens: List[Token],
                          vocabulary: Vocabulary,
                          index_name: str) -> Dict[str, List[int]]:
        indices: List[int] = []

        for token in tokens:
            if getattr(token, 'text_id', None) is not None:
                # `text_id` being set on the token means that we aren't using the vocab, we just use
                # this id instead.
                indices.append(token.text_id)
            else:
                text = token.text
                if self.lowercase_tokens:
                    text = text.lower()
                indices.append(vocabulary.get_token_index(text, self.namespace))

        return {index_name: indices}

    @overrides
    def get_padding_token(self) -> int:
        return 0

    @overrides
    def get_padding_lengths(self, token: int) -> Dict[str, int]:  # pylint: disable=unused-argument
        return {}

    @overrides
    def pad_token_sequence(self,
                           tokens: Dict[str, List[int]],
                           desired_num_tokens: Dict[str, int],
                           padding_lengths: Dict[str, int]) -> Dict[str, List[int]]:  # pylint: disable=unused-argument
        return {key: pad_sequence_to_length(val, desired_num_tokens[key])
                for key, val in tokens.items()}
