from disaster_tweet.wrappers.build import ALGO_WRAPPERS
from disaster_tweet.wrappers.flexmatch.flexmatch_base_wrapper import FlexMatchBaseWrapper


class FixMatchWrapper(FlexMatchBaseWrapper):

    def __init__(self, config, build_algo=True):
        assert config.algorithm == ALGO_WRAPPERS.FLEXMATCH

        if config.net in ['vit_tiny_patch2_32', 'vit_small_patch2_32', 'wrn_28_2', 'wrn_28_8']:
            config.img_size = 32
        elif config.net in ['vit_small_patch16_224', 'vit_base_patch16_224']:
            config.img_size = 224
        else:
            raise Exception(f'Net {config.net} is not supported')

        super().__init__(config, build_algo)

        # FlexMatch requires hard labels
        assert config.hard_label == True