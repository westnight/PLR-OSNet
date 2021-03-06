from __future__ import absolute_import
from __future__ import division

import torch
import torch.nn as nn
from .weighted_softmargin_loss import WeightedSoftMarginLoss


class TripletLoss(nn.Module):
    """Triplet loss with hard positive/negative mining.
    
    Reference:
        Hermans et al. In Defense of the Triplet Loss for Person Re-Identification. arXiv:1703.07737.
    
    Imported from `<https://github.com/Cysu/open-reid/blob/master/reid/loss/triplet.py>`_.
    
    Args:
        margin (float, optional): margin for triplet. Default is 0.3.
    """
    
    def __init__(self, margin=0.3):
        super(TripletLoss, self).__init__()
        self.margin = margin
        if margin == 0.:
            self.ranking_loss = nn.SoftMarginLoss()
            #self.ranking_loss = WeightedSoftMarginLoss()
        else:
            self.ranking_loss = nn.MarginRankingLoss(margin=margin)

    def forward(self, inputs, targets):
        """
        Args:
            inputs (torch.Tensor): feature matrix with shape (batch_size, feat_dim).
            targets (torch.LongTensor): ground truth labels with shape (num_classes).
        """
        n = inputs.size(0)
        
        # Compute pairwise distance, replace by the official when merged
        dist = torch.pow(inputs, 2).sum(dim=1, keepdim=True).expand(n, n)
        dist = dist + dist.t()
        dist.addmm_(1, -2, inputs, inputs.t())
        dist = dist.clamp(min=1e-12).sqrt()  # for numerical stability
        
        # For each anchor, find the hardest positive and negative
        mask = targets.expand(n, n).eq(targets.expand(n, n).t())
        dist_ap, dist_an = [], []
        for i in range(n):
            tmp1 = dist[i][mask[i]]
            tmp1 = tmp1.sort()[0][1:]
            #print('****', tmp1)
            tmp1_sq = torch.pow(tmp1, 2)
            sigma_p = tmp1_sq.mean()
            dist_ap.append((torch.pow(sigma_p, -1) * (tmp1_sq.max()) + 0.5 * torch.log(sigma_p)).unsqueeze(0))
        
            tmp2 = dist[i][mask[i] == 0]
            tmp2_sq = torch.pow(tmp2, 2)
            sigma_n = tmp2_sq.mean()
            dist_an.append((torch.pow(sigma_n, -1) * (tmp2_sq.min()) + 0.5 * torch.log(sigma_n)).unsqueeze(0))
        dist_ap = torch.cat(dist_ap)
        dist_an = torch.cat(dist_an)
        
        # Compute ranking hinge loss
        y = torch.ones_like(dist_an)
        #loss = ((dist_ap - dist_an) * y).mean()
        if self.margin == 0.:
            loss = self.ranking_loss(dist_an - dist_ap, y)
        else:
            loss = self.ranking_loss(dist_an, dist_ap, y)
        return loss
