import torch
import torch.nn.functional as F

from semilearn.algorithms.disaster.fixmatch_disaster import FixMatchDisaster
from semilearn.core.utils import ALGORITHMS


@ALGORITHMS.register('fixmatch_mmbt_bert')
class FixMatchMMBTBert(FixMatchDisaster):
    def __init__(self, args, net_builder, tb_log=None, logger=None):
        super().__init__(args, net_builder, tb_log, logger) 

    # @overrides
    def train_step(self,
                   lb_weak_image,
                   lb_weak_sentence, lb_weak_segment, lb_weak_mask,
                   lb_target,
                   ulb_weak_image, ulb_strong_image,
                   ulb_weak_sentence, ulb_weak_segment, ulb_weak_mask,
                   ulb_strong_sentence, ulb_strong_segment, ulb_strong_mask):
        
        lb_batch_size = lb_weak_image.shape[0]
        lb_target = torch.squeeze(lb_target)

        images = torch.cat((lb_weak_image, ulb_weak_image, ulb_strong_image))
        sentences = torch.cat((lb_weak_sentence, ulb_weak_sentence, ulb_strong_sentence))
        segments = torch.cat((lb_weak_segment, ulb_weak_segment, ulb_strong_segment))
        masks = torch.cat((lb_weak_mask, ulb_weak_mask, ulb_strong_mask))

        images = images.to(self.args.device)
        sentences = sentences.to(self.args.device)
        segments = segments.to(self.args.device)
        masks = masks.to(self.args.device)
        lb_target = lb_target.to(self.args.device)

        logits = self.model(sentences, masks, segments, images)
        lb_logits = logits[:lb_batch_size]
        ulb_weak_logits, ulb_strong_logits = logits[lb_batch_size:].chunk(2)

        # ToDo: Add configurable loss calculation (soft-pseudolabels, linear unsupervised loss, etc.)

        # Supervised loss
        lb_loss = F.cross_entropy(lb_logits, lb_target)

        # Compute pseudo-labels
        # ulb_weak_logits_norm = normalized logits (range [0, 1])
        # max_probs = max probability for each logit tensor
        # pseudo_labels = index with highest probability for each logit tensor
        ulb_weak_logits_norm = torch.softmax(ulb_weak_logits.detach(), dim=-1)
        max_probs, pseudo_labels = torch.max(ulb_weak_logits_norm, dim=-1)
        threshold_mask = max_probs.ge(self.p_cutoff).float()

        # Unsupervised loss
        ulb_loss = (threshold_mask * F.cross_entropy(ulb_strong_logits, pseudo_labels, reduction='none')).mean()

        # Total loss
        loss = lb_loss + self.lambda_u * ulb_loss

        out_dict = self.process_out_dict(loss=loss)
        log_dict = self.process_log_dict(sup_loss=lb_loss.item(), 
                                         unsup_loss=ulb_loss.item(), 
                                         total_loss=loss.item(), 
                                         util_ratio=threshold_mask.mean().item())
        
        return out_dict, log_dict

    # @overrides
    def get_logits(self, data, *args, **kwargs):
        images = data['lb_weak_image'].to(self.args.device)
        sentences = data['lb_weak_sentence'].to(self.args.device)
        segments = data['lb_weak_segment'].to(self.args.device)
        masks = data['lb_weak_mask'].to(self.args.device)
        return self.model(sentences, masks, segments, images)

    # @overrides
    def get_targets(self, data, *args, **kwargs):
        targets = data['lb_target'].to(self.args.device)
        return torch.squeeze(targets)