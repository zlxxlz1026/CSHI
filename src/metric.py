# Reference: https://github.com/RUCAIBox/iEvaLM-CRS/blob/main/src/model/metric.py
import math

class Metric():
    def __init__(self, k_list=(1, 5, 10)):
        self.k_list = k_list
        self.metric = {}
        self.reset()
    
    def reset(self):
        for metric in ['recall', 'ndcg', 'hit']:
            for k in self.k_list:
                self.metric[f'{metric}@{k}'] = 0.0
        self.metric['count'] = 0
        
    def evaluate(self, preds_list, labels):
        for label in labels:
            for k in self.k_list:
                self.metric[f'recall@{k}'] += self.compute_recall(preds_list, label, k)
                self.metric[f'ndcg@{k}'] += self.compute_ndcg(preds_list, label, k)
                self.metric[f'hit@{k}'] += self.comput_hit(preds_list, label, k)
            self.metric['count'] += 1
        
    def compute_recall(self, pred_list, label, k):
        for pred in pred_list[:k]:
            if label in pred:
                return 1
        return 0
    
    def compute_ndcg(self, pred_list, label, k):
        for pred in pred_list[:k]:
            if label in pred:
                index = pred_list.index(pred)
                return math.log(2) / math.log(index + 2)
        return 0
    
    def comput_hit(self, pred_list, label, k):
        for pred in pred_list[:k]:
            if label in pred:
                return 1
        return 0
    
    def report(self):
        report = {}
        if self.metric['count'] == 0:
            return report
        for k, v in self.metric.items():
            if k != 'count':
                report[k] = v / self.metric['count']
        return report